import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream
from .utils import calculate_sign


class LaixiuLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Laixiu live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self):
        sign_data = calculate_sign(ua_type='pc')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            'mobileModel': 'web',
            'timestamp': str(sign_data['timestamp']),
            'loginType': '2',
            'versionCode': '10003',
            'imei': sign_data['imei'],
            'requestId': sign_data['requestId'],
            'channel': '9',
            'version': '1.0.0',
            'os': 'web',
            'platform': 'WEB',
            'Origin': 'https://www.imkktv.com',
            'Referer': 'https://www.imkktv.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        }
        return headers

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        pattern = r"(?:roomId|anchorId)=(.*?)(?=&|$)"
        match = re.search(pattern, url)
        room_id = match.group(1) if match else ''
        play_api = f'https://api.imkktv.com/liveroom/getShareLiveVideo?roomId={room_id}'
        json_str = await async_req(play_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        room_data = json_data['data']
        anchor_name = room_data['nickname']
        live_status = room_data['playStatus'] == 0

        result = {"anchor_name": anchor_name, "is_live": False, "live_url": url}
        if live_status:
            flv_url = room_data['playUrl']
            result |= {'is_live': True, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "来秀直播"}
        return wrap_stream(json_data)
