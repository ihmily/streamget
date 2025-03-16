import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class MaoerLiveStream(BaseLiveStream):
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
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        url2 = f'https://fm.missevan.com/api/v2/live/{room_id}'

        json_str = await async_req(url=url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_name = json_data['info']['creator']['username']
        live_status = False
        if 'room' in json_data['info']:
            live_status = json_data['info']['room']['status']['broadcasting']

        result = {"anchor_name": anchor_name, "is_live": live_status}
        if live_status:
            stream_list = json_data['info']['room']['channel']
            m3u8_url = stream_list['hls_pull_url']
            flv_url = stream_list['flv_pull_url']
            title = json_data['info']['room']['name']
            result |= {'is_live': True, 'title': title, 'm3u8_url': m3u8_url, 'flv_url': flv_url,
                       'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "猫耳FM直播"}
        return wrap_stream(json_data)
