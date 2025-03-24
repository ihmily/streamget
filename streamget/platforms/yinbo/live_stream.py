import json
import re
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class YinboLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Yinbo live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'referer': 'https://live.ybw1666.com/800005143?promoters=0',
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
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        params = {
            'roomidx': room_id,
            'currentUrl': f'https://wap.ybw1666.com/{room_id}',
        }
        play_api = f'https://wap.ybw1666.com/api/ui/room/v1.0.0/live.ashx?{urllib.parse.urlencode(params)}'
        json_str = await async_req(play_api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        room_data = json_data['data']['roomInfo']
        anchor_name = room_data['nickname']
        live_status = room_data['live_stat']

        async def get_live_domain(page_url):
            html_str = await async_req(page_url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            config_json_str = re.findall("var config = (.*?)config.webskins",
                                         html_str, re.DOTALL)[0].rsplit(";", maxsplit=1)[0].strip()
            config_json_data = json.loads(config_json_str)
            stream_flv_domain = config_json_data['domainpullstream_flv']
            stream_hls_domain = config_json_data['domainpullstream_hls']
            return stream_flv_domain, stream_hls_domain

        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == 1:
            flv_domain, hls_domain = await get_live_domain(url)
            live_id = room_data['liveID']
            flv_url = f'{flv_domain}/{live_id}.flv'
            m3u8_url = f'{hls_domain}/{live_id}.m3u8'
            result |= {'is_live': True, 'm3u8_url': m3u8_url, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "音播直播"}
        return wrap_stream(json_data)
