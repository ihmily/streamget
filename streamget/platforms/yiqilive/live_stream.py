import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class YiqiLiveStream(BaseLiveStream):
    """
    A class for fetching and processing YiqiLive live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'origin': 'https://17.live',
            'referer': 'https://17.live/',
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
        api_1 = f'https://wap-api.17app.co/api/v1/user/room/{room_id}'
        json_str = await async_req(api_1, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        anchor_name = json_data["displayName"]
        result = {"anchor_name": anchor_name, "is_live": False}
        json_data = {
            'liveStreamID': room_id,
        }
        api_1 = f'https://wap-api.17app.co/api/v1/lives/{room_id}/viewers/alive'
        json_str = await async_req(api_1, json_data=json_data, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        live_status = json_data.get("status")
        if live_status and live_status == 2:
            flv_url = json_data['pullURLsInfo']['rtmpURLs'][0]['urlHighQuality']
            result |= {'is_live': True, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "17直播"}
        return wrap_stream(json_data)

