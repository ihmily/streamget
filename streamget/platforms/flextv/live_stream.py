import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class FlexTVLiveStream(BaseLiveStream):
    """
    A class for fetching and processing FlexTV live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None, username: str | None = None,
                 password: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.username = username
        self.password = password
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'content-type': 'application/json;charset=UTF-8',
            'referer': 'https://www.flextv.co.kr/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'cookie': self.cookies or '',
        }

    async def login_flextv(self) -> str | None:
        data = {
            'loginId': self.username,
            'password': self.password,
            'loginKeep': True,
            'saveId': True,
            'device': 'PCWEB',
        }

        url = 'https://api.flextv.co.kr/v2/api/auth/signin'

        try:
            cookie_dict = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers, json_data=data,
                                          return_cookies=True, timeout=20)
            if cookie_dict and 'flx_oauth_access' in cookie_dict:
                cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
                return cookie_str
            else:
                raise Exception(
                    "Please check if the FlexTV account and password in the configuration file are correct.")

        except Exception as e:
            raise Exception(f"FlexTV login request exception: {e}")

    async def get_flextv_stream_url(self, url: str) -> str:
        async def fetch_data() -> dict:
            user_id = url.split('/live')[0].rsplit('/', maxsplit=1)[-1]
            play_api = f'https://api.flextv.co.kr/api/channels/{user_id}/stream?option=all'
            json_str = await async_req(play_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            if 'HTTP Error 400: Bad Request' in json_str:
                raise ConnectionError(
                    "Failed to retrieve FlexTV live streaming data, please switch to a different proxy and try again."
                )
            return json.loads(json_str)

        json_data = await fetch_data()
        if 'sources' in json_data and len(json_data['sources']) > 0:
            play_url = json_data['sources'][0]['url']
            return play_url

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        user_id = url.split('/live')[0].rsplit('/', maxsplit=1)[-1]
        result = {"anchor_name": '', "is_live": False}
        new_cookies = None
        try:
            url2 = f'https://www.flextv.co.kr/channels/{user_id}/live'
            html_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_str = re.search('<script id="__NEXT_DATA__" type=".*">(.*?)</script>', html_str).group(1)
            json_data = json.loads(json_str)
            channel_data = json_data['props']['pageProps']['channel']
            login_need = 'message' in channel_data and '로그인후 이용이 가능합니다.' in channel_data.get('message')
            if login_need:
                if len(self.username) < 6 or len(self.password) < 8:
                    raise RuntimeError("FlexTV login failed! Please fill in the correct FlexTV platform account"
                                       " and password in the config. ini configuration file")
                new_cookies = await self.login_flextv()
                if not new_cookies:
                    raise RuntimeError("FlexTV login failed")
                cookies = new_cookies if new_cookies else self.cookies
                self.pc_headers['Cookie'] = cookies
                html_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
                json_str = re.search('<script id="__NEXT_DATA__" type=".*">(.*?)</script>', html_str).group(1)
                json_data = json.loads(json_str)
                channel_data = json_data['props']['pageProps']['channel']

            live_status = 'message' not in channel_data
            if live_status:
                anchor_id = channel_data['owner']['loginId']
                anchor_name = f"{channel_data['owner']['nickname']}-{anchor_id}"
                result["anchor_name"] = anchor_name
                play_url = await self.get_flextv_stream_url(url)
                if play_url:
                    play_url_list = await self.get_play_url_list(
                        m3u8=play_url, proxy=self.proxy_addr, headers=self.pc_headers)
                    if play_url_list:
                        result['m3u8_url'] = play_url
                        result['play_url_list'] = play_url_list
                        result['is_live'] = True
            else:
                url2 = f'https://www.flextv.co.kr/channels/{user_id}'
                html_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
                anchor_name = re.search('<meta name="twitter:title" content="(.*?)의', html_str).group(1)
                result["anchor_name"] = anchor_name
        except Exception as e:
            raise Exception("Failed to retrieve data from FlexTV live room", e)

        result['new_cookies'] = new_cookies
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='FlexTV')
        return wrap_stream(data)
