import re
import json
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class YoutubeLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Youtube live stream information.
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
        html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_str = re.search('var ytInitialPlayerResponse = (.*?);var meta = document\\.createElement', html_str).group(
            1)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        result = {"anchor_name": "", "is_live": False}
        if 'videoDetails' not in json_data:
            print("Error: Please log in to YouTube on your device's webpage and configure cookies in the config.ini")
            return result
        result['anchor_name'] = json_data['videoDetails']['author']
        live_status = json_data['videoDetails'].get('isLive')
        if live_status:
            live_title = json_data['videoDetails']['title']
            m3u8_url = json_data['streamingData']["hlsManifestUrl"]
            play_url_list = await self.get_play_url_list(m3u8_url, proxy=self.proxy_addr, headers=self.pc_headers)
            result |= {"is_live": True, "title": live_title, "m3u8_url": m3u8_url, "play_url_list": play_url_list}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='Youtube')
        return wrap_stream(data)

