import json
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class VVXQLiveStream(BaseLiveStream):
    """
    A class for fetching and processing VVXQ live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'access-control-request-method': 'GET',
            'origin': 'https://h5webcdn-pro.vvxqiu.com',
            'referer': 'https://h5webcdn-pro.vvxqiu.com/',
            'cookie': self.cookies or '',
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
        room_id = self.get_params(url, "roomId")
        api_1 = f'https://h5p.vvxqiu.com/activity-center/fanclub/activity/captain/banner?roomId={room_id}&product=vvstar'
        json_str = await async_req(api_1, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        anchor_name = json_data['data']['anchorName']
        if not anchor_name:
            params = {
                'sessionId': '',
                'userId': '',
                'product': 'vvstar',
                'tickToken': '',
                'roomId': room_id,
            }
            json_str = await async_req(
                f'https://h5p.vvxqiu.com/activity-center/halloween2023/banner?{urllib.parse.urlencode(params)}',
                proxy_addr=self.proxy_addr, headers=self.mobile_headers
            )
            json_data = json.loads(json_str)
            anchor_name = json_data['data']['memberVO']['memberName']

        result = {"anchor_name": anchor_name, "is_live": False}
        m3u8_url = f'https://liveplay-pro.wasaixiu.com/live/1400442770_{room_id}_{room_id[2:]}_single.m3u8'
        resp = await async_req(m3u8_url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        if 'Not Found' not in resp:
            result |= {'is_live': True, 'm3u8_url': m3u8_url, 'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "VV星球直播"}
        return wrap_stream(json_data)
