import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class PicartoLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Maoer live stream information.
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
        anchor_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        api = f'https://ptvintern.picarto.tv/api/channel/detail/{anchor_id}'

        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_name = json_data['channel']['name']
        live_status = json_data['channel']['online']

        result = {"anchor_name": anchor_name, "is_live": live_status}
        if live_status:
            title = json_data['channel']['title']
            m3u8_url = f"https://1-edge1-us-newyork.picarto.tv/stream/hls/golive+{anchor_name}/index.m3u8"
            result |= {'is_live': True, 'title': title, 'm3u8_url': m3u8_url, 'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "Picarto"}
        return wrap_stream(json_data)
