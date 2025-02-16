import re
import json
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class ZhihuLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Zhihu live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'osee2unifiedRelease/21914 osee2unifiedReleaseVersion/10.39.0 Mozilla/5.0 (iPhone; CPU '
                          'iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
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

        result = {"anchor_name": '', "is_live": False}
        if 'people/' in url:
            user_id = url.split('people/')[1]
            api = f'https://api.zhihu.com/people/{user_id}/profile?profile_new_version='
            json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            json_data = json.loads(json_str)
            result['anchor_name'] = json_data['name']
            live_page_url = json_data['drama']['living_theater']['theater_url']
        else:
            live_page_url = url

        web_id = live_page_url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        html_str = await async_req(live_page_url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_str2 = re.search('<script id="js-initialData" type="text/json">(.*?)</script>', html_str)
        if not json_str2:
            return result
        json_data2 = json.loads(json_str2.group(1))
        if not process_data:
            return json_data2
        live_data = json_data2['initialState']['theater']['theaters'][web_id]
        anchor_name = live_data['actor']['name']
        result['anchor_name'] = anchor_name
        live_status = live_data['drama']['status']
        if live_status == 1:
            live_title = live_data['theme']
            play_url = live_data['drama']['playInfo']
            result |= {
                'is_live': True,
                'title': live_title,
                'm3u8_url': play_url['hlsUrl'],
                'flv_url': play_url['playUrl'],
                'record_url': play_url['hlsUrl']
            }
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "知乎直播"}
        return wrap_stream(json_data)
