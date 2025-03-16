import json
import random
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class TwitchLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Twitch live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None, access_token: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.access_token = access_token
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'accept-language': 'en-US',
            'referer': 'https://www.twitch.tv/',
            'client-id': 'kimne78kx3ncx6brgo4mv6wki5h1ko',
            'client-integrity': self.access_token or '',
            'content-type': 'text/plain;charset=UTF-8',
            'cookie': self.cookies or '',
        }

    async def get_twitchtv_room_info(self, url: str) -> tuple:

        uid = url.split('?')[0].rsplit('/', maxsplit=1)[-1]

        data = [
            {
                "operationName": "ChannelShell",
                "variables": {
                    "login": uid
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "580ab410bcd0c1ad194224957ae2241e5d252b2c5173d8e0cce9d32d5bb14efe"
                    }
                }
            },
        ]

        json_str = await async_req('https://gql.twitch.tv/gql', proxy_addr=self.proxy_addr, headers=self.pc_headers,
                                   json_data=data)
        json_data = json.loads(json_str)
        user_data = json_data[0]['data']['userOrError']
        login_name = user_data["login"]
        nickname = f"{user_data['displayName']}-{login_name}"
        status = True if user_data['stream'] else False
        return nickname, status

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """

        uid = url.split('?')[0].rsplit('/', maxsplit=1)[-1]

        data = {
            "operationName": "PlaybackAccessToken_Template",
            "query": "query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, "
                     "$isVod: Boolean!, $playerType: String!) {  streamPlaybackAccessToken(channelName: $login, "
                     "params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) "
                     "@include(if: $isLive) {    value    signature   authorization { isForbidden forbiddenReasonCode }"
                     "   __typename  }  videoPlaybackAccessToken(id: $vodID, params: {platform: \"web\", "
                     "playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isVod) {    value   "
                     " signature   __typename  }}",
            "variables": {
                "isLive": True,
                "login": uid,
                "isVod": False,
                "vodID": "",
                "playerType": "site"
            }
        }

        json_str = await async_req('https://gql.twitch.tv/gql', proxy_addr=self.proxy_addr, headers=self.pc_headers,
                                   json_data=data)
        json_data = json.loads(json_str)
        token = json_data['data']['streamPlaybackAccessToken']['value']
        sign = json_data['data']['streamPlaybackAccessToken']['signature']

        anchor_name, live_status = await self.get_twitchtv_room_info(url.strip())
        result = {"anchor_name": anchor_name, "is_live": live_status}
        if live_status:
            play_session_id = random.choice(["bdd22331a986c7f1073628f2fc5b19da", "064bc3ff1722b6f53b0b5b8c01e46ca5"])
            params = {
                "acmb": "e30=",
                "allow_source": "true",
                "browser_family": "firefox",
                "browser_version": "124.0",
                "cdm": "wv",
                "fast_bread": "true",
                "os_name": "Windows",
                "os_version": "NT%2010.0",
                "p": "3553732",
                "platform": "web",
                "play_session_id": play_session_id,
                "player_backend": "mediaplayer",
                "player_version": "1.28.0-rc.1",
                "playlist_include_framerate": "true",
                "reassignments_supported": "true",
                "sig": sign,
                "token": token,
                "transcode_mode": "cbr_v1"
            }
            access_key = urllib.parse.urlencode(params)
            m3u8_url = f'https://usher.ttvnw.net/api/channel/hls/{uid}.m3u8?{access_key}'
            play_url_list = await self.get_play_url_list(m3u8=m3u8_url, proxy=self.proxy_addr,
                                                         headers=self.pc_headers)
            result |= {'m3u8_url': m3u8_url, 'play_url_list': play_url_list}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='Twitch')
        return wrap_stream(data)

