import json
import re
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class JDLiveStream(BaseLiveStream):
    """
    A class for fetching and processing JD live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'origin': 'https://lives.jd.com',
            'referer': 'https://lives.jd.com/',
            'x-referer-page': 'https://lives.jd.com/',
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
        redirect_url = await async_req(url, proxy_addr=self.proxy_addr, headers=self.mobile_headers, redirect_url=True)
        author_id = self.get_params(redirect_url, 'authorId')
        result = {"anchor_name": '', "is_live": False, "live_url": url}
        if not author_id:
            live_id = re.search('#/(.*?)\\?origin', redirect_url)
            if not live_id:
                return result
            live_id = live_id.group(1)
            result['anchor_name'] = f'jd_{live_id}'
        else:
            data = {
                'functionId': 'talent_head_findTalentMsg',
                'appid': 'dr_detail',
                'body': '{"authorId":"' + author_id + '","monitorSource":"1","userId":""}',
            }
            info_api = 'https://api.m.jd.com/talent_head_findTalentMsg'
            json_str = await async_req(info_api, data=data, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            json_data = json.loads(json_str)
            anchor_name = json_data['result']['talentName']
            result['anchor_name'] = anchor_name
            if 'livingRoomJump' not in json_data['result']:
                return result
            live_id = json_data['result']['livingRoomJump']['params']['id']
        params = {
            "body": '{"liveId": "' + live_id + '"}',
            "functionId": "getImmediatePlayToM",
            "appid": "h5-live"
        }

        api = f'https://api.m.jd.com/client.action?{urllib.parse.urlencode(params)}'
        # backup_api: https://api.m.jd.com/api
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        live_status = json_data['data']['status']
        if live_status == 1:
            if author_id:
                data = {
                    'functionId': 'jdTalentContentList',
                    'appid': 'dr_detail',
                    'body': '{"authorId":"' + author_id + '","type":1,"userId":"","page":1,"offset":"-1",'
                                                          '"monitorSource":"1","pageSize":1}',
                }
                json_str2 = await async_req('https://api.m.jd.com/jdTalentContentList', data=data,
                                            proxy_addr=self.proxy_addr, headers=self.mobile_headers)
                json_data2 = json.loads(json_str2)
                result['title'] = json_data2['result']['content'][0]['title']

            flv_url = json_data['data']['videoUrl']
            m3u8_url = json_data['data']['h5VideoUrl']
            result |= {"is_live": True, "m3u8_url": m3u8_url, "flv_url": flv_url, "record_url": m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "京东直播"}
        return wrap_stream(json_data)
