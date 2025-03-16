import json
import re
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class RedNoteLiveStream(BaseLiveStream):
    """
    A class for fetching and processing RedNote live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'xy-common-params': 'platform=iOS&sid=session.1722166379345546829388',
            'referer': 'https://app.xhs.cn/',
        }

    async def fetch_app_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches app stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        if 'xhslink.com' in url:
            url = await async_req(url, proxy_addr=self.proxy_addr, headers=self.mobile_headers, redirect_url=True)

        host_id = self.get_params(url, 'host_id')
        user_id = re.search('/user/profile/(.*?)(?=/|\\?|$)', url)
        user_id = user_id.group(1) if user_id else host_id
        result = {"anchor_name": '', "is_live": False}
        if user_id:
            params = {'user_id_list': user_id}
            app_api = f'https://live-room.xiaohongshu.com/api/sns/v1/live/user_status?{urllib.parse.urlencode(params)}'
            json_str = await async_req(app_api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            json_data = json.loads(json_str)
            if not process_data:
                return json_data
            if json_data.get('data'):
                live_link = json_data['data'][0]['live_link']
                anchor_name = self.get_params(live_link, "host_nickname")
                flv_url = self.get_params(live_link, "flvUrl")
                room_id = flv_url.split('live/')[1].split('.')[0]
                flv_url = f'http://live-source-play.xhscdn.com/live/{room_id}.flv'
                m3u8_url = flv_url.replace('.flv', '.m3u8')
                result |= {
                    "anchor_name": anchor_name,
                    "is_live": True,
                    "flv_url": flv_url,
                    "m3u8_url": m3u8_url,
                    'record_url': flv_url
                }
            else:
                profile_url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
                html_str = await async_req(profile_url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
                anchor_name = re.search('<title>@(.*?)的个人主页</title>', html_str)
                if anchor_name:
                    result['anchor_name'] = anchor_name.group(1)

        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "小红书"}
        return wrap_stream(json_data)

