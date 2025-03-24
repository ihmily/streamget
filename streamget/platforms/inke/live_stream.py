import json
import time
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class InkeLiveStream(BaseLiveStream):
    """
      A class for fetching and processing Inke live stream information.
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
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        uid = query_params['uid'][0]
        live_id = query_params['id'][0]
        params = {
            'uid': uid,
            'id': live_id,
            '_t': str(int(time.time())),
        }

        api = f'https://webapi.busi.inke.cn/web/live_share_pc?{urllib.parse.urlencode(params)}'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_name = json_data['data']['media_info']['nick']
        live_status = json_data['data']['status']

        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == 1:
            m3u8_url = json_data['data']['live_addr'][0]['hls_stream_addr']
            flv_url = json_data['data']['live_addr'][0]['stream_addr']
            result |= {'is_live': True, 'm3u8_url': m3u8_url, 'flv_url': flv_url, 'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
            Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "映客直播"}
        return wrap_stream(json_data)
