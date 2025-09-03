import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class WinkTVLiveStream(BaseLiveStream):
    """
    A class for fetching and processing WinkTV live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'content-type': 'application/x-www-form-urlencoded',
            'referer': 'https://www.winktv.co.kr',
            'origin': 'https://www.winktv.co.kr',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'cookie': self.cookies or '',
        }

    async def get_winktv_bj_info(self, url: str) -> tuple:

        user_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        data = {
            'userId': user_id,
            'info': 'media',
        }

        info_api = 'https://api.winktv.co.kr/v1/member/bj'
        json_str = await async_req(url=info_api, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data)
        json_data = json.loads(json_str)
        live_status = 'media' in json_data
        anchor_id = json_data['bjInfo']['id']
        anchor_name = f"{json_data['bjInfo']['nick']}-{anchor_id}"
        return anchor_name, live_status

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        user_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        room_password = self.get_params(url, "pwd")
        if not room_password:
            room_password = ''
        data = {
            'action': 'watch',
            'userId': user_id,
            'password': room_password,
            'shareLinkType': '',
        }

        anchor_name, live_status = await self.get_winktv_bj_info(url)
        result = {"anchor_name": anchor_name, "is_live": live_status, "live_url": url}
        if live_status:
            play_api = 'https://api.winktv.co.kr/v1/live/play'
            json_str = await async_req(url=play_api, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data)
            if '403: Forbidden' in json_str:
                raise ConnectionError(f"Your network has been banned from accessing WinkTV ({json_str})")
            json_data = json.loads(json_str)
            if 'errorData' in json_data:
                if json_data['errorData']['code'] == 'needAdult':
                    raise RuntimeError(
                        f"{url} The live stream is only accessible to logged-in adults. Please ensure that "
                        f"the cookie is correctly filled in the configuration file after logging in.")
                else:
                    raise RuntimeError(json_data['errorData']['code'], json_data['message'])
            if not process_data:
                return json_data
            m3u8_url = json_data['PlayList']['hls'][0]['url']
            play_url_list = await self.get_play_url_list(m3u8=m3u8_url, proxy=self.proxy_addr, headers=self.pc_headers)
            result['m3u8_url'] = m3u8_url
            result['play_url_list'] = play_url_list
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='WinkTV')
        return wrap_stream(data)

