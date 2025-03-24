from ...data import StreamData
from ..base import BaseLiveStream
from ..piaopiao.live_stream import PiaopaioLiveStream


class HuamaoLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Huamao live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.stream = PiaopaioLiveStream(proxy_addr=self.proxy_addr, cookies=self.cookies)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        return await self.stream.fetch_web_stream_data(url)

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "花猫直播"}
        return await self.stream.fetch_stream_url(json_data)
