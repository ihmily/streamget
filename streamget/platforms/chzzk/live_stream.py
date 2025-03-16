import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class ChzzkLiveStream(BaseLiveStream):
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'origin': 'https://chzzk.naver.com',
            'referer': 'https://chzzk.naver.com/live/458f6ec20b034f49e0fc6d03921646d2',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
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
        play_api = f'https://api.chzzk.naver.com/service/v3/channels/{room_id}/live-detail'
        json_str = await async_req(play_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        live_data = json_data['content']
        anchor_name = live_data['channel']['channelName']
        live_status = live_data['status']

        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == 'OPEN':
            play_data = json.loads(live_data['livePlaybackJson'])
            m3u8_url = play_data['media'][0]['path']
            m3u8_url_list = await self.get_play_url_list(m3u8_url, proxy=self.proxy_addr, headers=self.pc_headers)
            prefix = m3u8_url.split('?')[0].rsplit('/', maxsplit=1)[0]
            m3u8_url_list = [prefix + '/' + i for i in m3u8_url_list]
            result |= {"is_live": True, "m3u8_url": m3u8_url, "play_url_list": m3u8_url_list}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='CHZZK')
        return wrap_stream(data)
