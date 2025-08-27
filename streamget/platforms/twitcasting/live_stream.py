import json
import re

from ... import utils
from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class TwitCastingLiveStream(BaseLiveStream):
    """
    A class for fetching and processing TwitCasting live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None, username: str | None = None,
                 password: str | None = None, account_type: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.username = username
        self.password = password
        self.account_type = account_type
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'content-type': 'application/x-www-form-urlencoded',
            'referer': 'https://twitcasting.tv/indexcaslogin.php?redir=%2Findexloginwindow.php%3Fnext%3D%252F&keep=1',
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'cookie': self.cookies or 'hl=zh; did=377eda93b5320f104357ab1bc98dfe4d; _ga=GA1.1.869052351.1747879503; '
                                      'keep=1; chid=relay_trade_jp;',
        }

    async def login_twitcasting(self) -> str | None:
        if self.account_type == "twitter":
            login_url = 'https://twitcasting.tv/indexpasswordlogin.php'
            login_api = 'https://twitcasting.tv/indexpasswordlogin.php?redir=/indexloginwindow.php?next=%2F&keep=1'
        else:
            login_url = 'https://twitcasting.tv/indexcaslogin.php?redir=%2F&keep=1'
            login_api = 'https://twitcasting.tv/indexcaslogin.php?redir=/indexloginwindow.php?next=%2F&keep=1'

        html_str = await async_req(login_url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        cs_session_id = re.search('<input type="hidden" name="cs_session_id" value="(.*?)">', html_str).group(1)

        data = {
            'username': self.username,
            'password': self.password,
            'action': 'login',
            'cs_session_id': cs_session_id,
        }
        try:
            cookie_dict = await async_req(
                login_api, proxy_addr=self.proxy_addr, headers=self.mobile_headers,
                data=data, return_cookies=True, timeout=20)
            if 'tc_ss' in cookie_dict:
                self.cookies = utils.dict_to_cookie_str(cookie_dict)
                self.mobile_headers['cookie'] = self.cookies
                return self.cookies
        except Exception as e:
            raise Exception("TwitCasting login error,", e)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        anchor_id = url.split('/')[3]

        async def get_data() -> tuple:
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            anchor = re.search("<title>(.*?) \\(@(.*?)\\)  的直播 - Twit", html_str)
            title = re.search('<meta name="twitter:title" content="(.*?)">\n\\s+<meta', html_str)
            status = re.search('data-is-onlive="(.*?)"\n\\s+data-view-mode', html_str)
            movie_id = re.search('data-movie-id="(.*?)" data-audience-id', html_str)
            return f'{anchor.group(1).strip()}-{anchor.group(2)}-{movie_id.group(1)}', status.group(1), title.group(1)

        result = {"anchor_name": '', "is_live": False}
        new_cookie = None
        try:
            to_login = self.get_params(url, "login")
            if to_login == 'true':
                # print("Attempting to log in to TwitCasting...")
                new_cookie = await self.login_twitcasting()
                if not new_cookie:
                    raise RuntimeError("TwitCasting login failed, please check if the account password in the "
                                       "configuration file is correct")
                # print("TwitCasting login successful! Starting to fetch data...")
                self.mobile_headers['Cookie'] = new_cookie
            anchor_name, live_status, live_title = await get_data()
        except AttributeError:
            # print("Failed to retrieve TwitCasting data, attempting to log in...")
            new_cookie = await self.login_twitcasting()
            if not new_cookie:
                raise RuntimeError("TwitCasting login failed, please check if the account and password in the "
                                   "configuration file are correct")
            # print("TwitCasting login successful! Starting to fetch data...")
            self.mobile_headers['Cookie'] = new_cookie
            anchor_name, live_status, live_title = await get_data()

        result["anchor_name"] = anchor_name
        if live_status == 'true':
            url_streamserver = f"https://twitcasting.tv/streamserver.php?target={anchor_id}&mode=client&player=pc_web"
            Twitcasting_str = await async_req(url_streamserver, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            json_data = json.loads(Twitcasting_str)
            if not json_data.get('tc-hls') or not json_data['tc-hls'].get("streams"):
                raise RuntimeError("No m3u8_url,please check the url")

            stream_dict = json_data['tc-hls']["streams"]
            quality_order = {"high": 0, "medium": 1, "low": 2}
            sorted_streams = sorted(stream_dict.items(), key=lambda item: quality_order[item[0]])
            play_url_list = [url for quality, url in sorted_streams]
            result |= {'title': live_title, 'is_live': True, "play_url_list": play_url_list}
        result['new_cookies'] = new_cookie
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=False, platform='TwitCasting')
        return wrap_stream(data)