import hashlib
import json
import re
import time

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class DouyuLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Douyu live stream information.
    """
    DEFAULT_DID = "10000000000000000000000000001501"
    WEB_DOMAIN = "www.douyu.com"
    PLAY_DOMAIN = "playweb.douyucdn.cn"
    MOBILE_DOMAIN = "m.douyu.com"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.base_headers = {
            'user-agent': self.USER_AGENT,
            'referer': f'https://{self.WEB_DOMAIN}/',
        }
        if cookies:
            self.base_headers['cookie'] = cookies

    def _get_headers(self, *, origin: bool = False, content_type: bool = False) -> dict:
        headers = self.base_headers.copy()
        if origin:
            headers['origin'] = f'https://{self.WEB_DOMAIN}'
        if content_type:
            headers['content-type'] = 'application/x-www-form-urlencoded'
        return headers

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        match_rid = re.search('douyu.com/(\\d+)', url) or re.search('rid=(\\d+)', url)
        if match_rid:
            rid = match_rid.group(1)
        else:
            path = url.split("douyu.com/")[1].split("?")[0].split("/")[0]
            html_str = await async_req(
                url=f'https://{self.MOBILE_DOMAIN}/{path}',
                proxy_addr=self.proxy_addr,
                headers=self.base_headers
            )
            rid = re.search('"rid":(\\d+)', html_str).group(1)

        json_str = await async_req(
            url=f'https://{self.WEB_DOMAIN}/betard/{rid}',
            proxy_addr=self.proxy_addr,
            headers=self.base_headers
        )
        json_data = json.loads(json_str)['room']

        if not process_data:
            return json_data

        raw_title = json_data['room_name'].replace('&nbsp;', ' ')
        is_live = json_data['show_status'] == 1 and json_data['videoLoop'] == 0
        title = f"录播 {raw_title}" if not is_live else raw_title

        result = {
            "anchor_name": json_data['nickname'],
            "is_live": is_live,
            "live_url": url,
            "title": title.strip(),
        }
        return result

    async def _update_white_key(self) -> dict:
        url = f'https://{self.WEB_DOMAIN}/wgapi/livenc/liveweb/websec/getEncryption?did={self.DEFAULT_DID}'
        json_str = await async_req(
            url=url,
            proxy_addr=self.proxy_addr,
            headers={'user-agent': self.USER_AGENT}
        )
        data = json.loads(json_str)
        if data.get('error') != 0:
            raise RuntimeError('获取白名单密钥失败')
        return data['data']

    async def _get_sign_params(self, rid: str) -> dict:
        white = await self._update_white_key()
        ts = int(time.time())
        secret = white['rand_str']
        salt = f"{rid}{ts}" if not white['is_special'] else ""
        for _ in range(white['enc_time']):
            secret = hashlib.md5((secret + white['key']).encode()).hexdigest()
        auth = hashlib.md5((secret + white['key'] + salt).encode()).hexdigest()

        return {
            'enc_data': white['enc_data'],
            'tt': ts,
            'did': self.DEFAULT_DID,
            'auth': auth,
        }

    async def fetch_stream_url(
            self, json_data: dict, video_quality: str | int | None = None, cdn: str | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        platform = '斗鱼直播'

        rid = re.search('douyu.com/(\\d+)', json_data['live_url']).group(1)

        video_quality_options = {
            "OD": '0',
            "BD": '0',
            "UHD": '3',
            "HD": '2',
            "SD": '1',
            "LD": '1'
        }

        if not video_quality:
            video_quality = "OD"
        else:
            if str(video_quality).isdigit():
                video_quality = list(video_quality_options.keys())[int(video_quality)]
            else:
                video_quality = video_quality.upper()

        rate = video_quality_options.get(video_quality, '0')
        async def get_url(cdn_name: str | None = None):
            params = {
                'rate': rate,
                'ver': '219032101',
                'iar': '0',
                'ive': '0',
                'rid': rid,
                'hevc': '0',
                'fa': '0',
                'sov': '0',
            }
            if cdn_name:
                params['cdn'] = cdn_name

            sign = await self._get_sign_params(rid)
            params.update(sign)

            json_str = await async_req(
                url=f'https://{self.PLAY_DOMAIN}/lapi/live/getH5PlayV1/{rid}',
                proxy_addr=self.proxy_addr,
                headers=self._get_headers(origin=True, content_type=True),
                data=params
            )
            data = json.loads(json_str)
            if data.get('error') != 0:
                return None

            return data.get('data')

        if not json_data['is_live']:
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': None,
                'record_url': None,
                'extra': {'backup_url_list': []}
            }
            return wrap_stream(json_data)

        main_data = await get_url()

        if not main_data:
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': None,
                'record_url': None,
                'extra': {'backup_url_list': []}
            }
            return wrap_stream(json_data)

        main_url = f"{main_data['rtmp_url']}/{main_data['rtmp_live']}"
        backup_urls = []

        if cdn and main_data.get('rtmp_cdn') != cdn:
            for item in main_data.get('cdnsWithName', []):
                if item['cdn'] and item['cdn'] == cdn:
                    main_data = await get_url(cdn)
                    if main_data.get('rtmp_cdn') == cdn:
                        backup_urls.append(main_url)
                        main_url = f"{main_data['rtmp_url']}/{main_data['rtmp_live']}"

        json_data |= {
            "platform": platform,
            'quality': video_quality,
            'flv_url': main_url,
            'record_url': main_url,
            'extra': {'backup_url_list': backup_urls}
        }

        return wrap_stream(json_data)
