import json
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class ShopeeLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Shopee live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:

        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'referer': 'https://live.shopee.sg/share?from=live&session=802458&share_user_id=',
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
        result = {"anchor_name": "", "is_live": False}
        is_living = False

        if 'live.shopee' not in url and 'uid' not in url:
            url = await async_req(url, proxy_addr=self.proxy_addr, headers=self.mobile_headers, redirect_url=True)

        if 'live.shopee' in url:
            host_suffix = url.split('/')[2].rsplit('.', maxsplit=1)[1]
            is_living = self.get_params(url, 'uid') is None
        else:
            host_suffix = url.split('/')[2].split('.', maxsplit=1)[0]

        uid = self.get_params(url, 'uid')
        api_host = f'https://live.shopee.{host_suffix}'
        session_id = self.get_params(url, 'session')
        if uid:
            json_str = await async_req(f'{api_host}/api/v1/shop_page/live/ongoing?uid={uid}',
                                       proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            json_data = json.loads(json_str)
            if json_data['data']['ongoing_live']:
                session_id = json_data['data']['ongoing_live']['session_id']
                is_living = True
            else:
                json_str = await async_req(f'{api_host}/api/v1/shop_page/live/replay_list?offset=0&limit=1&uid={uid}',
                                           proxy_addr=self.proxy_addr, headers=self.mobile_headers)
                json_data = json.loads(json_str)
                if json_data['data']['replay']:
                    result['anchor_name'] = json_data['data']['replay'][0]['nick_name']
                    return result

        json_str = await async_req(f'{api_host}/api/v1/session/{session_id}',
                                   proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        if not json_data.get('data'):
            print("Fetch shopee live data failed, please update the address of the live broadcast room and try again.")
            return result
        uid = json_data['data']['session']['uid']
        anchor_name = json_data['data']['session']['nickname']
        live_status = json_data['data']['session']['status']
        result["anchor_name"] = anchor_name
        result['extra'] = {'uid': f'uid={uid}&session={session_id}'}
        if live_status == 1 and is_living:
            flv_url = json_data['data']['session']['play_url']
            title = json_data['data']['session']['title']
            result |= {'is_live': True, 'title': title, 'flv_url': flv_url, 'record_url': flv_url}
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "Shopee"}
        return wrap_stream(json_data)
