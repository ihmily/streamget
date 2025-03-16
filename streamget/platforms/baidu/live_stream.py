import json
import random
import re
import time
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class BaiduLiveStream(BaseLiveStream):
    """
        A class for fetching and processing Baidu live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        uid = random.choice([
            'h5-683e85bdf741bf2492586f7ca39bf465',
            'h5-c7c6dc14064a136be4215b452fab9eea',
            'h5-4581281f80bb8968bd9a9dfba6050d3a'
        ])
        room_id = re.search('room_id=(.*?)&', url).group(1)
        params = {
            'cmd': '371',
            'action': 'star',
            'service': 'bdbox',
            'osname': 'baiduboxapp',
            'data': '{"data":{"room_id":"' + room_id + '","device_id":"h5-683e85bdf741bf2492586f7ca39bf465",'
                                                       '"source_type":0,"osname":"baiduboxapp"},"replay_slice":0,'
                                                       '"nid":"","schemeParams":{"src_pre":"pc","src_suf":"other",'
                                                       '"bd_vid":"","share_uid":"","share_cuk":"","share_ecid":"",'
                                                       '"zb_tag":"","shareTaskInfo":"{\\"room_id\\":\\"9175031377\\"}",'
                                                       '"share_from":"","ext_params":"","nid":""}}',
            'ua': '360_740_ANDROID_0',
            'bd_vid': '',
            'uid': uid,
            '_': str(int(time.time() * 1000)),
        }
        app_api = f'https://mbd.baidu.com/searchbox?{urllib.parse.urlencode(params)}'
        json_str = await async_req(url=app_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        key = list(json_data['data'].keys())[0]
        data = json_data['data'][key]
        anchor_name = data['host']['name']
        result = {"anchor_name": anchor_name, "is_live": False}
        if data['status'] == "0":
            result["is_live"] = True
            live_title = data['video']['title']
            play_url_list = data['video']['url_clarity_list']
            url_list = []
            prefix = 'https://hls.liveshow.bdstatic.com/live/'
            if play_url_list:
                for i in play_url_list:
                    url_list.append(
                        prefix + i['urls']['flv'].rsplit('.', maxsplit=1)[0].rsplit('/', maxsplit=1)[1] + '.m3u8')
            else:
                play_url_list = data['video']['url_list']
                for i in play_url_list:
                    url_list.append(prefix + i['urls'][0]['hls'].rsplit('?', maxsplit=1)[0].rsplit('/', maxsplit=1)[1])

            if url_list:
                result |= {"is_live": True, "title": live_title, 'play_url_list': url_list}
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, platform='百度')
        return wrap_stream(data)
