import json
import re
import time
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class HuajiaoLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Huajiao live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'referer': 'https://www.huajiao.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'cookie': self.cookies or '',
        }

    async def get_huajiao_sn(self, url: str) -> tuple | None:

        live_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        api = f'https://www.huajiao.com/l/{live_id}'
        try:
            html_str = await async_req(url=api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_str = re.search('var feed = (.*?});', html_str).group(1)
            json_data = json.loads(json_str)
            sn = json_data['feed']['sn']
            uid = json_data['author']['uid']
            nickname = json_data['author']['nickname']
            live_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
            return nickname, sn, uid, live_id
        except Exception:
            raise RuntimeError(
                "Failed to retrieve live room data, the Huajiao live room address is not fixed, please use "
                "the anchor's homepage address for recording.")

    async def get_huajiao_user_info(self, url: str) -> dict | None:

        if 'user' in url:
            uid = url.split('?')[0].split('user/')[1]
            params = {
                'uid': uid,
                'fmt': 'json',
                '_': str(int(time.time() * 1000)),
            }

            api = f'https://webh.huajiao.com/User/getUserFeeds?{urllib.parse.urlencode(params)}'
            json_str = await async_req(url=api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_data = json.loads(json_str)

            html_str = await async_req(url=f'https://www.huajiao.com/user/{uid}', proxy_addr=self.proxy_addr,
                                       headers=self.pc_headers)
            anchor_name = re.search('<title>(.*?)的主页.*</title>', html_str).group(1)
            if json_data['data'] and 'sn' in json_data['data']['feeds'][0]['feed']:
                feed = json_data['data']['feeds'][0]['feed']
                return {
                    "anchor_name": anchor_name,
                    "title": feed['title'],
                    "is_live": True,
                    "sn": feed['sn'],
                    "liveid": feed['relateid'],
                    "uid": uid
                }
            else:
                return {"anchor_name": anchor_name, "is_live": False}

    async def get_huajiao_stream_url_app(self, url: str) -> dict | None:
        headers = {
            'User-Agent': 'living/9.4.0 (com.huajiao.seeding; build:2410231746; iOS 17.0.0) Alamofire/9.4.0',
            'accept-language': 'zh-Hans-US;q=1.0',
            'sdk_version': '1',
            'cookie': self.cookies or ''
        }

        room_id = url.rsplit('/', maxsplit=1)[1]
        api = f'https://live.huajiao.com/feed/getFeedInfo?relateid={room_id}'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=headers)
        json_data = json.loads(json_str)

        if json_data['errmsg'] or not json_data['data'].get('creatime'):
            raise Exception(
                "Failed to retrieve live room data, the Huajiao live room address is not fixed, please manually change "
                "the address for recording.")

        data = json_data['data']
        return {
            "anchor_name": data['author']['nickname'],
            "title": data['feed']['title'],
            "is_live": True,
            "sn": data['feed']['sn'],
            "liveid": data['feed']['relateid'],
            "uid": data['author']['uid']
        }

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        result = {"anchor_name": "", "is_live": False, "live_url": url}

        if 'user/' in url:
            if not self.cookies:
                return result
            room_data = await self.get_huajiao_user_info(url)
        else:
            url = await async_req(url.strip(), proxy_addr=self.proxy_addr, headers=self.pc_headers, redirect_url=True)
            if url.rstrip('/') == 'https://www.huajiao.com':
                raise Exception(
                    "Failed to retrieve live room data, the Huajiao live room address is not fixed, please manually "
                    "change the address for recording.")
            room_data = await self.get_huajiao_stream_url_app(url)

        if room_data:
            result["anchor_name"] = room_data.pop("anchor_name")
            live_status = room_data.pop("is_live")

            if live_status:
                result["title"] = room_data.pop("title")
                params = {
                    "time": int(time.time() * 1000),
                    "version": "1.0.0",
                    **room_data,
                    "encode": "h265"
                }

                api = f'https://live.huajiao.com/live/substream?{urllib.parse.urlencode(params)}'
                json_str = await async_req(url=api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
                json_data = json.loads(json_str)
                result |= {
                    'is_live': True,
                    'flv_url': json_data['data']['h264_url'],
                    'record_url': json_data['data']['h264_url'],
                }
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
         Fetches the stream URL for a live room and wraps it into a StreamData object.
         """
        json_data |= {"platform": "花椒直播"}
        return wrap_stream(json_data)
