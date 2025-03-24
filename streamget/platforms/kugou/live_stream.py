import json
import re
import time
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class KugouLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Kugou live stream information.
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
        if 'roomId' in url:
            room_id = re.search('roomId=(\\d+)', url).group(1)
        else:
            room_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]

        app_api = f'https://service2.fanxing.kugou.com/roomcen/room/web/cdn/getEnterRoomInfo?roomId={room_id}'
        json_str = await async_req(url=app_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        anchor_name = json_data['data']['normalRoomInfo']['nickName']
        result = {"anchor_name": anchor_name, "is_live": False}
        if not anchor_name:
            raise RuntimeError(
                "Music channel live rooms are not supported for recording, please switch to a different live room."
            )
        live_status = json_data['data']['liveType']
        if live_status != -1:
            params = {
                'std_rid': room_id,
                'std_plat': '7',
                'std_kid': '0',
                'streamType': '1-2-4-5-8',
                'ua': 'fx-flash',
                'targetLiveTypes': '1-5-6',
                'version': '1000',
                'supportEncryptMode': '1',
                'appid': '1010',
                '_': str(int(time.time() * 1000)),
            }
            api = f'https://fx1.service.kugou.com/video/pc/live/pull/mutiline/streamaddr?{urllib.parse.urlencode(params)}'
            json_str2 = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_data2 = json.loads(json_str2)
            stream_data = json_data2['data']['lines']
            if stream_data:
                flv_url = stream_data[-1]['streamProfiles'][0]['httpsFlv'][0]
                result |= {"is_live": True, "flv_url": flv_url, "record_url": flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "酷狗直播"}
        return wrap_stream(json_data)
