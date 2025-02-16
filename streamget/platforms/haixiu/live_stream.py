import json
import time
import execjs
import urllib.parse
from ... import JS_SCRIPT_PATH
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class HaixiuLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Haixiu live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'origin': 'https://www.haixiutv.com',
            'referer': 'https://www.haixiutv.com/',
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
        room_id = url.split("?")[0].rsplit('/', maxsplit=1)[-1]
        if 'haixiutv' in url:
            access_token = "pLXSC%252FXJ0asc1I21tVL5FYZhNJn2Zg6d7m94umCnpgL%252BuVm31GQvyw%253D%253D"
        else:
            access_token = "s7FUbTJ%252BjILrR7kicJUg8qr025ZVjd07DAnUQd8c7g%252Fo4OH9pdSX6w%253D%253D"

        params = {
            "accessToken": access_token,
            "tku": "3000006",
            "c": "10138100100000",
            "_st1": int(time.time() * 1000)
        }
        ajax_data = execjs.compile(open(f'{JS_SCRIPT_PATH}/haixiu.js').read()).call('sign', params,
                                                                                    f'{JS_SCRIPT_PATH}/crypto-js.min.js')

        params["accessToken"] = urllib.parse.unquote(urllib.parse.unquote(access_token))
        params['_ajaxData1'] = ajax_data
        params['_'] = int(time.time() * 1000)

        encode_params = urllib.parse.urlencode(params)
        if 'haixiutv' in url:
            api = f'https://service.haixiutv.com/v2/room/{room_id}/media/advanceInfoRoom?{encode_params}'
        else:
            self.mobile_headers['origin'] = 'https://www.lehaitv.com'
            self.mobile_headers['referer'] = 'https://www.lehaitv.com'
            api = f'https://service.lehaitv.com/v2/room/{room_id}/media/advanceInfoRoom?{encode_params}'

        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        stream_data = json_data['data']
        anchor_name = stream_data['nickname']
        live_status = stream_data['live_status']
        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == 1:
            flv_url = stream_data['media_url_web']
            result |= {'is_live': True, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "嗨秀直播"}
        return wrap_stream(json_data)
