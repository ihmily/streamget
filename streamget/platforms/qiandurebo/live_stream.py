import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class QiandureboLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Qiandurebo live stream information.
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
        html_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        data = re.search('var user = (.*?)\r\n\\s+user\\.play_url', html_str, re.DOTALL).group(1)
        anchor_name = re.findall('"zb_nickname": "(.*?)",\r\n', data)

        result = {"anchor_name": "", "is_live": False}
        if len(anchor_name) > 0:
            result['anchor_name'] = anchor_name[0]
            play_url = re.findall('"play_url": "(.*?)",\r\n', data)

            if len(play_url) > 0 and 'common-text-center" style="display:block' not in html_str:
                result |= {
                    'anchor_name': anchor_name[0],
                    'is_live': True,
                    'flv_url': play_url[0],
                    'record_url': play_url[0]
                }
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "千度热播直播"}
        return wrap_stream(json_data)
