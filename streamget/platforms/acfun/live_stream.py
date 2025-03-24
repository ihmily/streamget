import json
import urllib.parse
from operator import itemgetter

from ... import utils
from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class AcfunLiveStream(BaseLiveStream):
    """
        A class for fetching and processing Acfun live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    async def _get_acfun_sign_params(self) -> tuple:
        did = f'web_{utils.generate_random_string(16)}'
        headers = {
            'referer': 'https://live.acfun.cn/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'cookie': f'_did={did};',
        }
        data = {
            'sid': 'acfun.api.visitor',
        }
        api = 'https://id.app.acfun.cn/rest/app/visitor/login'
        json_str = await async_req(api, data=data, proxy_addr=self.proxy_addr, headers=headers)
        json_data = json.loads(json_str)
        user_id = json_data["userId"]
        visitor_st = json_data["acfun.api.visitor_st"]
        return user_id, did, visitor_st

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        author_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        user_info_api = f'https://live.acfun.cn/rest/pc-direct/user/userInfo?userId={author_id}'
        json_str = await async_req(user_info_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        anchor_name = json_data['profile']['name']
        status = 'liveId' in json_data['profile']
        result = {"anchor_name": anchor_name, "is_live": False}
        if status:
            result["is_live"] = True
            user_id, did, visitor_st = await self._get_acfun_sign_params()
            params = {
                'subBiz': 'mainApp',
                'kpn': 'ACFUN_APP',
                'kpf': 'PC_WEB',
                'userId': user_id,
                'did': did,
                'acfun.api.visitor_st': visitor_st,
            }

            data = {
                'authorId': author_id,
                'pullStreamType': 'FLV',
            }
            play_api = f'https://api.kuaishouzt.com/rest/zt/live/web/startPlay?{urllib.parse.urlencode(params)}'
            json_str = await async_req(play_api, data=data, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_data = json.loads(json_str)
            live_title = json_data['data']['caption']
            videoPlayRes = json_data['data']['videoPlayRes']
            play_url_list = json.loads(videoPlayRes)['liveAdaptiveManifest'][0]['adaptationSet']['representation']
            play_url_list = sorted(play_url_list, key=itemgetter('bitrate'), reverse=True)
            result |= {'play_url_list': play_url_list, 'title': live_title}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(
            json_data, video_quality, url_type='flv', flv_extra_key='url', platform='Acfun')
        return wrap_stream(data)
