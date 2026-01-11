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
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()
        self.pc_headers = self._get_pc_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'cookie': self.cookies or '',
            'referer': 'https://m.douyu.com/3125893?rid=3125893&dyshid=0-96003918aa5365bc6dcb4933000316p1&dyshci=181',
        }

    @staticmethod
    def _get_md5(data) -> str:
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    async def _get_encryption(self, rid: str, did: str, headers: dict | None = None) -> dict:
        url = f'https://www.douyu.com/wgapi/livenc/liveweb/websec/getEncryption?did={did}'
        json_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=headers)
        json_data = json.loads(json_str)
        if json_data.get('error') != 0:
            raise Exception(f"Failed to get encryption info: {json_data.get('msg')}")

        data = json_data['data']
        key = data['key']
        rand_str = data['rand_str']
        enc_time = data['enc_time']
        is_special = data['is_special']

        ts = int(time.time())
        o = "" if is_special == 1 else f"{rid}{ts}"
        u = rand_str

        for _ in range(enc_time):
            u = self._get_md5(u + key)

        auth = self._get_md5(u + key + o)

        return {
            'enc_data': data['enc_data'],
            'tt': str(ts),
            'did': did,
            'auth': auth
        }

    async def _fetch_web_stream_url(self, rid: str, rate: str = '-1', cdn: str | None = None) -> dict:
        did = '10000000000000000000000000001501'
        enc_params = await self._get_encryption(rid, did, headers=self.mobile_headers)

        data = {
            'enc_data': enc_params['enc_data'],
            'tt': enc_params['tt'],
            'did': enc_params['did'],
            'auth': enc_params['auth'],
            'ver': 'Douyu_new',
            'rid': rid,
            'rate': rate,
            'hevc': '0',
            'fa': '0',
            'ive': '0',
            'cdn': cdn if cdn else ''
        }

        app_api = f'https://www.douyu.com/lapi/live/getH5PlayV1/{rid}'
        json_str = await async_req(url=app_api, proxy_addr=self.proxy_addr, headers=self.mobile_headers, data=data)
        json_data = json.loads(json_str)
        return json_data

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        match_rid = re.search('rid=(.*?)(?=&|$)', url) or re.search('beta/(.*?)(?=\\?|$)', url)
        if match_rid:
            rid = match_rid.group(1)
        else:
            rid = re.search('douyu.com/(.*?)(?=\\?|$)', url).group(1)
            html_str = await async_req(url=f'https://m.douyu.com/{rid}', proxy_addr=self.proxy_addr,
                                       headers=self.pc_headers)
            json_str = re.findall('<script id="vike_pageContext" type="application/json">(.*?)</script>', html_str)[0]
            json_data = json.loads(json_str)
            rid = json_data['pageProps']['room']['roomInfo']['roomInfo']['rid']

        url2 = f'https://www.douyu.com/betard/{rid}'
        json_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        result = {
            "anchor_name": json_data['room']['nickname'],
            "is_live": False,
            "live_url": url
        }
        if json_data['room']['videoLoop'] == 0 and json_data['room']['show_status'] == 1:
            result["title"] = json_data['room']['room_name'].replace('&nbsp;', '')
            result["is_live"] = True
            result["room_id"] = json_data['room']['room_id']
        return result

    async def fetch_stream_url(
            self, json_data: dict, video_quality: str | int | None = None, cdn: str | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        platform = '斗鱼直播'
        if not json_data["is_live"]:
            json_data |= {"platform": platform}
            return wrap_stream(json_data)
        video_quality_options = {
            "OD": '0',
            "BD": '0',
            "UHD": '3',
            "HD": '2',
            "SD": '1',
            "LD": '1'
        }
        rid = str(json_data["room_id"])
        json_data.pop("room_id")

        if not video_quality:
            video_quality = "OD"
        else:
            if str(video_quality).isdigit():
                video_quality = list(video_quality_options.keys())[int(video_quality)]
            else:
                video_quality = video_quality.upper()

        flv_url_list = []
        rate = video_quality_options.get(video_quality, '0')

        async def get_url(rid: str, rate: str, cdn: str | None = None):
            flv_data = await self._fetch_web_stream_url(rid=rid, rate=rate, cdn=cdn)
            rtmp_url = flv_data['data'].get('rtmp_url')
            rtmp_live = flv_data['data'].get('rtmp_live')
            flv_url_list.append(f'{rtmp_url}/{rtmp_live}')
            return flv_data

        flv_data = await get_url(rid=rid, rate=rate, cdn=cdn)
        rtmp_cdn = flv_data['data'].get('rtmp_cdn')
        cdn_list = flv_data['data'].get('cdnsWithName')

        for cdn in cdn_list:
            if cdn['cdn'] != rtmp_cdn:
                await get_url(rid=rid, rate=rate, cdn=cdn['cdn'])

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
