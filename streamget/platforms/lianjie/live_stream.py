import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class LianJieLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Yinbo live stream information.
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
        room_id = url.split('?')[0].rsplit('lailianjie.com/', maxsplit=1)[-1]
        play_api = f'https://api.lailianjie.com/ApiServices/service/live/getRoomInfo?&_$t=&_sign=&roomNumber={room_id}'
        json_str = await async_req(play_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        room_data = json_data['data']
        anchor_name = room_data['nickname']
        live_status = room_data['isonline']

        result = {"anchor_name": anchor_name, "is_live": False, "live_url": url}
        if live_status == 1:
            title = room_data['defaultRoomTitle']
            webrtc_url = room_data['videoUrl']
            https_url = "https://" + webrtc_url.split('webrtc://')[1]
            flv_url = https_url.replace('?', '.flv?')
            m3u8_url = https_url.replace('?', '.m3u8?')
            result |= {'is_live': True, 'title': title, 'm3u8_url': m3u8_url, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "连接直播"}
        return wrap_stream(json_data)
