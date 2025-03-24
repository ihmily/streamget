import json
import urllib.parse

import execjs

from ... import JS_SCRIPT_PATH
from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class LiveMeLiveStream(BaseLiveStream):
    """
    A class for fetching and processing LiveMe live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'origin': 'https://www.liveme.com',
            'referer': 'https://www.liveme.com',
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
        room_id = url.split("/index.html")[0].rsplit('/', maxsplit=1)[-1]
        try:
            with open(f'{JS_SCRIPT_PATH}/liveme.js') as f:
                js_code = f.read()
            sign_data = execjs.compile(js_code).call('sign', room_id, f'{JS_SCRIPT_PATH}/crypto-js.min.js')
        except execjs.ProgramError:
            raise execjs.ProgramError('Failed to execute JS code. Please check if the Node.js environment')
        lm_s_sign = sign_data.pop("lm_s_sign")
        tongdun_black_box = sign_data.pop("tongdun_black_box")
        platform = sign_data.pop("os")
        self.mobile_headers['lm-s-sign'] = lm_s_sign

        params = {
            'alias': 'liveme',
            'tongdun_black_box': tongdun_black_box,
            'os': platform,
        }

        api = f'https://live.liveme.com/live/queryinfosimple?{urllib.parse.urlencode(params)}'
        json_str = await async_req(api, data=sign_data, proxy_addr=self.proxy_addr,
                                   headers=self.mobile_headers)
        json_data = json.loads(json_str)
        stream_data = json_data['data']['video_info']
        anchor_name = stream_data['uname']
        live_status = stream_data['status']
        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == "0":
            m3u8_url = stream_data['hlsvideosource']
            flv_url = stream_data['videosource']
            result |= {
                'is_live': True,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': m3u8_url or flv_url
            }
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "Liveme"}
        return wrap_stream(json_data)
