import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream
from ..twitch.live_stream import TwitchLiveStream


class FaceitLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Faceit live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        nickname = re.findall('/players/(.*?)/stream', url)[0]
        api = f'https://www.faceit.com/api/users/v1/nicknames/{nickname}'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        user_id = json_data['payload']['id']
        api2 = f'https://www.faceit.com/api/stream/v1/streamings?userId={user_id}'
        json_str2 = await async_req(api2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data2 = json.loads(json_str2)
        if not json_data2.get('payload'):
            return {'anchor_name': nickname, 'is_live': False}
        platform_info = json_data2['payload'][0]
        anchor_name = platform_info.get('userNickname')
        anchor_id = platform_info.get('platformId')
        platform = platform_info.get('platform')
        if platform == 'twitch':
            twitch_stream = TwitchLiveStream(proxy_addr=self.proxy_addr)
            result = await twitch_stream.fetch_web_stream_data(f'https://www.twitch.tv/{anchor_id}')
            result['anchor_name'] = anchor_name
        else:
            result = {'anchor_name': anchor_name, 'is_live': False}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='Faceit')
        return wrap_stream(data)