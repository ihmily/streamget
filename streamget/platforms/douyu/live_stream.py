import hashlib
import json
import re
import time

import execjs

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

    async def _get_token_js(self, rid: str, did: str) -> list[str]:
        url = f'https://www.douyu.com/{rid}'
        html_str = await async_req(url=url, proxy_addr=self.proxy_addr)
        result = re.search(r'(vdwdae325w_64we[\s\S]*function ub98484234[\s\S]*?)function', html_str).group(1)
        func_ub9 = re.sub(r'eval.*?;}', 'strc;}', result)
        js = execjs.compile(func_ub9)
        res = js.call('ub98484234')

        t10 = str(int(time.time()))
        v = re.search(r'v=(\d+)', res).group(1)
        rb = self._get_md5(str(rid) + str(did) + str(t10) + str(v))

        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"')

        try:
            js = execjs.compile(func_sign)
            params = js.call('sign', rid, did, t10)
            params_list = re.findall('=(.*?)(?=&|$)', params)
            return params_list
        except execjs.ProgramError:
            raise execjs.ProgramError('Failed to execute JS code. Please check if the Node.js environment')

    async def _fetch_web_stream_url(self, rid: str, rate: str = '-1') -> dict:

        did = '10000000000000000000000000003306'
        params_list = await self._get_token_js(rid, did)
        data = {
            'v': params_list[0],
            'did': params_list[1],
            'tt': params_list[2],
            'sign': params_list[3],  # 10分钟有效期
            'ver': '22011191',
            'rid': rid,
            'rate': rate,  # 0蓝光、3超清、2高清、-1默认
        }

        # app_api = 'https://m.douyu.com/hgapi/livenc/room/getStreamUrl'
        app_api = f'https://www.douyu.com/lapi/live/getH5Play/{rid}'
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
        match_rid = re.search('rid=(.*?)(?=&|$)', url)
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
            "is_live": False
        }
        if json_data['room']['videoLoop'] == 0 and json_data['room']['show_status'] == 1:
            result["title"] = json_data['room']['room_name'].replace('&nbsp;', '')
            result["is_live"] = True
            result["room_id"] = json_data['room']['room_id']
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
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

        rate = video_quality_options.get(video_quality, '0')
        flv_data = await self._fetch_web_stream_url(rid=rid, rate=rate)
        rtmp_url = flv_data['data'].get('rtmp_url')
        rtmp_live = flv_data['data'].get('rtmp_live')
        if rtmp_live:
            flv_url = f'{rtmp_url}/{rtmp_live}'
            json_data |= {"platform": platform, 'quality': video_quality, 'flv_url': flv_url, 'record_url': flv_url}
        return wrap_stream(json_data)

