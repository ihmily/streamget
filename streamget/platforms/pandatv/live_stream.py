import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class PandaLiveStream(BaseLiveStream):
    """
    A class for fetching and processing PandaLive live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'origin': 'https://www.pandalive.co.kr',
            'referer': 'https://www.pandalive.co.kr/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
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
        user_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        url2 = 'https://api.pandalive.co.kr/v1/live/play'
        data = {
            'userId': user_id,
            'info': 'media fanGrade',
        }
        room_password = self.get_params(url, "pwd")
        if not room_password:
            room_password = ''
        data2 = {
            'action': 'watch',
            'userId': user_id,
            'password': room_password,
            'shareLinkType': '',
        }

        result = {"anchor_name": "", "is_live": False}
        json_str = await async_req('https://api.pandalive.co.kr/v1/member/bj',
                                   proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_id = json_data['bjInfo']['id']
        anchor_name = f"{json_data['bjInfo']['nick']}-{anchor_id}"
        result['anchor_name'] = anchor_name
        live_status = 'media' in json_data

        if live_status:
            json_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data2)
            json_data = json.loads(json_str)
            if 'errorData' in json_data:
                if json_data['errorData']['code'] == 'needAdult':
                    raise RuntimeError(f"{url} The live room requires login and is only accessible to adults. Please "
                                       f"correctly fill in the login cookie in the configuration file.")
                else:
                    raise RuntimeError(json_data['errorData']['code'], json_data['message'])
            play_url = json_data['PlayList']['hls'][0]['url']
            play_url_list = await self.get_play_url_list(m3u8=play_url, proxy=self.proxy_addr, headers=self.pc_headers)
            result |= {'is_live': True, 'm3u8_url': play_url, 'play_url_list': play_url_list}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='PandaTV')
        return wrap_stream(data)

