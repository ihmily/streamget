import json
import random
import re
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ...utils import generate_random_string
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
            'device-id': generate_random_string(16).lower(),
            'cookie': self.cookies or '',
        }

    async def get_twitchtv_room_info(self, url: str) -> tuple:

        uid = url.split('?')[0].rsplit('/', maxsplit=1)[-1]

        data = [
            {
                "operationName": "ComscoreStreamingQuery",
                "variables": {
                    "channel": uid.lower(),
                    "clipSlug": "",
                    "isClip": False,
                    "isLive": True,
                    "isVodOrCollection": False,
                    "vodID": "",
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "e1edae8122517d013405f237ffcc124515dc6ded82480a88daef69c83b53ac01"
                    }
                }
            },
        ]

        json_str = await async_req('https://gql.twitch.tv/gql', proxy_addr=self.proxy_addr, headers=self.pc_headers,
                                   json_data=data,http2=False)
        json_data = json.loads(json_str)
        user_data = json_data[0]['data']['user']
        nickname = f"{user_data['displayName']}-{uid}"
        status = True if user_data['stream'] else False
        title = user_data['broadcastSettings']['title']
        return nickname, status, title

    async def get_play_url_list(self, m3u8: str, proxy: str | None = None, headers: dict | None = None) -> list[dict]:
        """
        Fetches and parses the M3U8 playlist, returning structured stream information including audio-only streams.

        Returns a list of dictionaries containing stream info:
        {
            'url': str,
            'bandwidth': int,
            'resolution': str | None,
            'group_id': str,
            'name': str,
            'is_audio_only': bool
        }
        """
        resp = await async_req(m3u8, proxy_addr=proxy, headers=headers)
        play_url_list = []

        lines = resp.split('\n')
        current_stream_info = {}
        current_group_id = None
        current_name = None

        for line in lines:
            line = line.strip()

            # Parse #EXT-X-MEDIA line to get GROUP-ID and NAME
            if line.startswith('#EXT-X-MEDIA:'):
                group_id_match = re.search(r'GROUP-ID="([^"]+)"', line)
                name_match = re.search(r'NAME="([^"]+)"', line)
                if group_id_match:
                    current_group_id = group_id_match.group(1)
                if name_match:
                    current_name = name_match.group(1)

            # Parse #EXT-X-STREAM-INF line
            elif line.startswith('#EXT-X-STREAM-INF:'):
                bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
                resolution_match = re.search(r'RESOLUTION=(\d+x\d+)', line)

                current_stream_info['bandwidth'] = int(bandwidth_match.group(1)) if bandwidth_match else 0
                current_stream_info['resolution'] = resolution_match.group(1) if resolution_match else None

            # URL line - add stream to list
            elif line.startswith('https://') and current_stream_info:
                stream = {
                    'url': line,
                    'bandwidth': current_stream_info.get('bandwidth', 0),
                    'resolution': current_stream_info.get('resolution'),
                    'group_id': current_group_id or 'unknown',
                    'name': current_name or 'unknown',
                    'is_audio_only': current_group_id == 'audio_only'
                }
                play_url_list.append(stream)

                # Reset for next stream
                current_stream_info = {}
                current_group_id = None
                current_name = None

        # Sort by bandwidth descending (highest quality first)
        play_url_list.sort(key=lambda x: x['bandwidth'], reverse=True)
        return play_url_list

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
                                   json_data=data,http2=False)
        json_data = json.loads(json_str)
        token = json_data['data']['streamPlaybackAccessToken']['value']
        sign = json_data['data']['streamPlaybackAccessToken']['signature']

        anchor_name, live_status, live_title = await self.get_twitchtv_room_info(url.strip())
        result = {"anchor_name": anchor_name, "is_live": live_status, "live_url": url, "title": live_title}
        if live_status:
            play_session_id = random.choice(["bdd22331a986c7f1073628f2fc5b19da", "064bc3ff1722b6f53b0b5b8c01e46ca5"])
            params = {
                "acmb": "e30=",
                "allow_audio_only": "true",
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

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.

        Supports quality options:
        - "AD": Audio-only stream
        - "OD", "UHD", "HD", etc.: Video streams (uses base class logic)
        """
        platform = 'Twitch'
        if not json_data['is_live']:
            json_data |= {"platform": platform}
            return wrap_stream(json_data)

        play_url_list = json_data.get('play_url_list', [])

        if not play_url_list:
            json_data |= {"platform": platform}
            return wrap_stream(json_data)

        # Handle audio-only quality (AD)
        if video_quality == 'AD':
            audio_stream = next((s for s in play_url_list if s.get('is_audio_only')), None)
            if audio_stream:
                data = {
                    "platform": platform,
                    "anchor_name": json_data.get('anchor_name'),
                    "is_live": True,
                    "live_url": json_data.get('live_url'),
                    "title": json_data.get('title'),
                    "quality": "AD",
                    "m3u8_url": json_data.get('m3u8_url'),
                    "record_url": audio_stream['url'],
                    "extra": {
                        'bandwidth': audio_stream.get('bandwidth'),
                        'is_audio_only': True
                    }
                }
                return wrap_stream(data)

        # For other qualities, convert dict list to URL list for base class compatibility
        url_list = [stream['url'] for stream in play_url_list]
        json_data['play_url_list'] = url_list
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform=platform)
        return wrap_stream(data)
