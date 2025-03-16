import json
import re
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class BluedLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Blued live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        html_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_str = re.search('decodeURIComponent\\(\"(.*?)\"\\)\\),window\\.Promise', html_str, re.DOTALL).group(1)
        json_str = urllib.parse.unquote(json_str)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_name = json_data['userInfo']['name']
        live_status = json_data['userInfo']['onLive']
        result = {"anchor_name": anchor_name, "is_live": False}

        if live_status:
            m3u8_url = "http:" + json_data['liveInfo']['liveUrl']
            result |= {"is_live": True, "m3u8_url": m3u8_url, 'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": 'Blued'}
        return wrap_stream(json_data)
