import json

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class PiaopaioLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Piaopiao live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()
        self.mobile_headers = self._get_mobile_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'content-type': 'application/json',
            'origin': 'https://m.pp.weimipopo.com',
            'referer': 'https://m.pp.weimipopo.com/',
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'cookie': self.cookies or '',
        }

    async def fetch_app_stream_data(self, url: str, process_data: bool = True) -> dict:
        # use shortID not anchorUid
        short_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        json_data = {
            "platform": "iOS",
            "device": "iPhone",
            "token": "Iq6iKDovSwvmmMtJo8f3bqcThX573ndM",
            "channel": "AppStorePLIM",
            "subChannel": "",
            "version": "1.7.27",
            "meid": "",
            "uid": 92128122,
            "params": {
                "keyword": short_id
            },
            "build": "183",
            "app": "plpl",
            "imei": ""
        }
        api = 'https://api.pp.weimipopo.com/plpl/pms/search/user/v2'
        json_str = await async_req(api, json_data=json_data, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        result = {"anchor_name": '', "is_live": False, "live_url": url}
        for data in json_data['data']['userList']:
            if str(data['user']['shortId']) == str(short_id):
                anchor_name = data['user']['name']
                result['anchor_name'] = anchor_name
                live_status = json_data['data']['userList'][0].get('live')

                if live_status:
                    rtmp_url = json_data['data']['livingUsers'][0]['live']['pullUrl']
                    title = json_data['data']['livingUsers'][0]['live']['title']
                    result |= {'is_live': True, 'title': title, 'm3u8_url': rtmp_url, 'record_url': rtmp_url}
        return result

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        room_id = self.get_params(url, 'anchorUid')
        json_data = {
            'inviteUuid': '',
            'anchorUuid': room_id,
        }

        if 'catshow' in url:
            api = 'https://api.catshow168.com/live/preview'
            self.pc_headers['Origin'] = 'https://h.catshow168.com'
            self.pc_headers['Referer'] = 'https://h.catshow168.com'
        else:
            api = 'https://api.pp.weimipopo.com/live/preview'
        json_str = await async_req(api, json_data=json_data, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        live_info = json_data['data']
        anchor_name = live_info['name']
        live_status = live_info['living']
        result = {"anchor_name": anchor_name, "is_live": False, "live_url": url}
        if live_status:
            m3u8_url = live_info['pullUrl']
            result |= {'is_live': True, 'm3u8_url': m3u8_url, 'record_url': m3u8_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "飘飘直播"}
        return wrap_stream(json_data)