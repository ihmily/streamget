import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class LangLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Lang live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'origin': 'https://www.lang.live',
            'referer': 'https://www.lang.live/',
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
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
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        api_1 = f'https://api.lang.live/langweb/v1/room/liveinfo?room_id={room_id}'
        json_str = await async_req(api_1, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        live_info = json_data['data']['live_info']
        anchor_name = live_info['nickname']
        live_status = live_info['live_status']
        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == 1:
            flv_url = json_data['data']['live_info']['liveurl']
            m3u8_url = json_data['data']['live_info']['liveurl_hls']
            result |= {'is_live': True, 'm3u8_url': m3u8_url, 'flv_url': flv_url, 'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "浪Live"}
        return wrap_stream(json_data)
