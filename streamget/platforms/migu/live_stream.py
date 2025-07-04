import json
import subprocess
import time
import urllib.parse
import uuid

import execjs

from ... import JS_SCRIPT_PATH
from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class MiguLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Migu live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'origin': 'https://www.miguvideo.com',
            'referer': 'https://www.miguvideo.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'appCode': 'miguvideo_default_www',
            'appId': 'miguvideo',
            'channel': 'H5',
            'cookie': self.cookies or '',
        }

    async def _get_live_room_info(self, url):
        web_id = url.split('?')[0].rsplit('/')[-1]
        api = f'https://vms-sc.miguvideo.com/vms-match/v6/staticcache/basic/basic-data/{web_id}/miguvideo'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        room_id = json_data['body']['pId']
        anchor_name = json_data['body'].get('title')
        title = anchor_name + '-' + json_data['body'].get('detailPageTitle', '')
        return room_id, anchor_name, title

    @staticmethod
    async def _get_dd_calcu(url):
        try:
            result = subprocess.run(
                ["node", f"{JS_SCRIPT_PATH}/migu.js", url],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except execjs.ProgramError:
            raise execjs.ProgramError('Failed to execute JS code. Please check if the Node.js environment')

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """

        room_id, anchor_name, live_title = await self._get_live_room_info(url)
        result = {"anchor_name": anchor_name, "is_live": False}
        if not room_id:
            raise RuntimeError("Room ID fetch error")
        params = {
            'contId': room_id,
            'rateType': '3',
            'clientId': str(uuid.uuid4()),
            'timestamp': int(time.time()*1000),
            'flvEnable': 'true',
            'xh265': 'false',
            'chip': 'mgwww',
            'channelId': '',
        }

        api = f'https://webapi.miguvideo.com/gateway/playurl/v3/play/playurl?{urllib.parse.urlencode(params)}'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        live_status = json_data['body']['content']['currentLive']
        if live_status != '1':
            return result
        else:
            result['title'] = live_title
            source_url = json_data['body']['urlInfo']['url']
            ddCalcu = await self._get_dd_calcu(source_url)
            real_source_url = f'{source_url}&ddCalcu={ddCalcu}&sv=10010'
            if '.m3u8' in real_source_url:
                m3u8_url = await async_req(
                    real_source_url, proxy_addr=self.proxy_addr, headers=self.pc_headers, redirect_url=True)
                result['m3u8_url'] = m3u8_url
                result['record_url'] = m3u8_url
            else:
                result['flv_url'] = real_source_url
                result['record_url'] = real_source_url
            result['is_live'] = True
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "咪咕直播"}
        return wrap_stream(json_data)
