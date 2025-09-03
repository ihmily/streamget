from ...data import StreamData
from ..base import BaseLiveStream
from ..haixiu.live_stream import HaixiuLiveStream


class LehaiLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Lehai live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.stream = HaixiuLiveStream(proxy_addr=self.proxy_addr, cookies=self.cookies)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        data = await self.stream.fetch_web_stream_data(url)
        data['live_url'] = url
        return data

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "乐嗨直播"}
        return await self.stream.fetch_stream_url(json_data)
