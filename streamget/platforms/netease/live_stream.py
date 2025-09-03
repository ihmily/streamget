import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class NeteaseLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Netease CC live stream information.
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
        url = url + '/' if url[-1] != '/' else url
        html_str = await async_req(url.strip(), proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_str = re.search('<script id="__NEXT_DATA__" .* crossorigin="anonymous">(.*?)</script></body>',
                             html_str, re.DOTALL).group(1)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        room_data = json_data['props']['pageProps']['roomInfoInitData']
        live_data = room_data['live']
        result = {"is_live": False, "live_url": url}
        live_status = live_data.get('status') == 1
        result["anchor_name"] = live_data.get('nickname', room_data.get('nickname'))
        if live_status:
            result |= {
                'is_live': True,
                'title': live_data['title'],
                'stream_list': live_data.get('quickplay'),
                'm3u8_url': live_data.get('sharefile')
            }
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        if not json_data['is_live']:
            json_data |= {"platform": "网易CC直播"}
            return wrap_stream(json_data)

        m3u8_url = json_data['m3u8_url']
        flv_url = None
        if json_data.get('stream_list'):
            stream_list = json_data['stream_list']['resolution']
            order = ['blueray', 'ultra', 'high', 'standard']
            sorted_keys = [key for key in order if key in stream_list]
            while len(sorted_keys) < 5:
                sorted_keys.append(sorted_keys[-1])
            video_quality, quality_index = self.get_quality_index(video_quality)
            selected_quality = sorted_keys[quality_index]
            flv_url_list = stream_list[selected_quality]['cdn']
            selected_cdn = list(flv_url_list.keys())[0]
            flv_url = flv_url_list[selected_cdn]

        data = {
            "platform": "网易CC直播",
            "anchor_name": json_data['anchor_name'],
            "is_live": True,
            "title": json_data['title'],
            'quality': video_quality,
            "m3u8_url": m3u8_url,
            "flv_url": flv_url,
            "record_url": flv_url or m3u8_url
        }
        return wrap_stream(data)
