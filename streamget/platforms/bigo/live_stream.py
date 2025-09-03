import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class BigoLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Bigo live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
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
        if 'bigo.tv' not in url:
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            web_url = re.search(
                '<meta data-n-head="ssr" data-hid="al:web:url" property="al:web:url" content="(.*?)">',
                html_str).group(1)
            room_id = web_url.split('&amp;h=')[-1]
        else:
            if '&h=' in url:
                room_id = url.split('&h=')[-1]
            else:
                room_id = url.split("?")[0].rsplit("/", maxsplit=1)[-1]

        data = {'siteId': room_id}  # roomId
        url2 = 'https://ta.bigo.tv/official_website/studio/getInternalStudioInfo'
        json_str = await async_req(url=url2, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_name = json_data['data']['nick_name']
        live_status = json_data['data']['alive']
        result = {"anchor_name": anchor_name, "is_live": False, "live_url": url}

        if live_status == 1:
            live_title = json_data['data']['roomTopic']
            m3u8_url = json_data['data']['hls_src']
            result['m3u8_url'] = m3u8_url
            result['record_url'] = m3u8_url
            result |= {"title": live_title, "is_live": True, "m3u8_url": m3u8_url, 'record_url': m3u8_url}
        elif result['anchor_name'] == '':
            html_str = await async_req(url=f'https://www.bigo.tv/{url.split("/")[3]}/{room_id}',
                                       proxy_addr=self.proxy_addr, headers=self.pc_headers)
            match_anchor_name = re.search('<title>欢迎来到(.*?)的直播间</title>', html_str, re.DOTALL)
            if match_anchor_name:
                anchor_name = match_anchor_name.group(1)
            else:
                match_anchor_name = re.search('<meta data-n-head="ssr" data-hid="og:title" property="og:title" '
                                              'content="(.*?) - BIGO LIVE">', html_str, re.DOTALL)
                anchor_name = match_anchor_name.group(1)
            result['anchor_name'] = anchor_name
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": 'Bigo'}
        return wrap_stream(json_data)
