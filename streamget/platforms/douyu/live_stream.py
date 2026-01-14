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

    async def get_room_id(self, url):
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
        return rid

    async def fetch_app_stream_data(self, url: str, process_data: bool = True):

        rid = await self.get_room_id(url)

        data = {
            'sk': rid,
            'log_token': '',
            'ct_code': '26',
            'token': '',
        }

        json_str = await async_req(
            url='https://wxapp.douyucdn.cn/api/wechatsearch/nc/search/multiv2',
            proxy_addr=self.proxy_addr,
            headers=self.base_headers,
            data=data
        )
        json_data = json.loads(json_str)

        if not process_data:
            return json_data

        live_data = json_data['data']['recom']
        result = {
            "anchor_name": live_data.get('nickname'),
            "is_live": False,
            "live_url": url,
            "source": "app"
        }
        if live_data.get('isLive') == 1:
            result |= {
                "anchor_name": live_data.get('nickname'),
                "is_live": live_data.get('isLive') == 1,
                "live_url": url,
                "title": live_data.get('roomName'),
                'flv_url': live_data.get('stream'),
                'record_url': live_data.get('stream'),
                "quality": "OD"
            }
        return result

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        rid = await self.get_room_id(url)

        json_str = await async_req(
            url=f'https://{self.WEB_DOMAIN}/betard/{rid}',
            proxy_addr=self.proxy_addr,
            headers=self.base_headers
        )
        json_data = json.loads(json_str)['room']

        if not process_data:
            return json_data

        raw_title = json_data['room_name'].replace('&nbsp;', ' ').strip()
        has_content = json_data['show_status'] == 1
        is_loop = json_data['videoLoop'] == 1
        is_live = has_content
        title = f"【轮播】{raw_title}" if is_loop else raw_title

        result = {
            "anchor_name": json_data['nickname'],
            "is_live": is_live,
            "live_url": url,
            "room_id": json_data['room_id'],
            "title": title,
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

    async def _fetch_web_stream_url(self, rid: str, rate: str = '-1', cdn: str | None = None) -> dict:
        white = await self._update_white_key()
        ts = int(time.time())
        secret = white['rand_str']
        salt = f"{rid}{ts}" if not white['is_special'] else ""
        for _ in range(white['enc_time']):
            secret = hashlib.md5((secret + white['key']).encode()).hexdigest()
        auth = hashlib.md5((secret + white['key'] + salt).encode()).hexdigest()

        params = {
            'rate': rate,
            'ver': '219032101',
            'iar': '0',
            'ive': '0',
            'rid': rid,
            'hevc': '0',
            'fa': '0',
            'sov': '0',
            'enc_data': white['enc_data'],
            'tt': ts,
            'did': self.DEFAULT_DID,
            'auth': auth,
        }
        if cdn:
            params['cdn'] = cdn

        json_str = await async_req(
            url=f'https://{self.PLAY_DOMAIN}/lapi/live/getH5PlayV1/{rid}',
            proxy_addr=self.proxy_addr,
            headers=self._get_headers(origin=True, content_type=True),
            data=params
        )
        return json.loads(json_str)

    async def fetch_stream_url(
            self, json_data: dict, video_quality: str | int | None = None, cdn: str | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        platform = '斗鱼直播'
        if json_data.get('source') == "app":
            json_data.pop('source')
            json_data |= {"platform": platform, 'extra': {'backup_url_list': []}}
            return wrap_stream(json_data)

        rid = str(json_data["room_id"])
        json_data.pop("room_id")

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

        flv_url_list = []

        async def get_url(_rid: str, _rate: str, _cdn: str | None = None):
            _flv_data = await self._fetch_web_stream_url(rid=_rid, rate=_rate, cdn=_cdn)
            if _flv_data.get('error') != 0:
                return
            info = _flv_data.get('data')
            if not info:
                return
            _flv_url = f"{info['rtmp_url']}/{info['rtmp_live']}"
            if _flv_url not in flv_url_list:
                flv_url_list.append(_flv_url)
            return _flv_data

        if not json_data['is_live']:
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': None,
                'record_url': None,
                'extra': {'backup_url_list': []}
            }
            return wrap_stream(json_data)

        flv_data = await get_url(_rid=rid, _rate=rate, _cdn=cdn)

        if flv_data and flv_data.get('data'):
            rtmp_cdn = flv_data['data'].get('rtmp_cdn')
            cdn_list = flv_data['data'].get('cdnsWithName', [])

            for item in cdn_list:
                if item['cdn'] != rtmp_cdn:
                    await get_url(_rid=rid, _rate=rate, _cdn=item['cdn'])

        if flv_url_list:
            flv_url = flv_url_list[0]
            flv_url_list.remove(flv_url)
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': flv_url,
                'record_url': flv_url,
                'extra': {'backup_url_list': flv_url_list}
            }

        return wrap_stream(json_data)
