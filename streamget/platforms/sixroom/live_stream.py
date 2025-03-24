import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class SixRoomLiveStream(BaseLiveStream):
    """
    A class for fetching and processing SixRoom live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:

        return {
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'referer': 'https://ios.6.cn/?ver=8.0.3&build=4',
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
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        html_str = await async_req(f'https://v.6.cn/{room_id}', proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        room_id = re.search('rid: \'(.*?)\',\n\\s+roomid', html_str).group(1)
        data = {
            'av': '3.1',
            'encpass': '',
            'logiuid': '',
            'project': 'v6iphone',
            'rate': '1',
            'rid': '',
            'ruid': room_id,
        }

        api = 'https://v.6.cn/coop/mobile/index.php?padapi=coop-mobile-inroom.php'
        json_str = await async_req(api, data=data, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        flv_title = json_data['content']['liveinfo']['flvtitle']
        anchor_name = json_data['content']['roominfo']['alias']
        result = {"anchor_name": anchor_name, "is_live": False}
        if flv_title:
            flv_url = f'https://wlive.6rooms.com/httpflv/{flv_title}.flv'
            result |= {'is_live': True, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "六间房直播"}
        return wrap_stream(json_data)
