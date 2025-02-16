import re
import json
import time
import urllib.parse
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class YYLiveStream(BaseLiveStream):
    """
    A class for fetching and processing YY live stream information.
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
        html_str = await async_req(url.strip(), proxy_addr=self.proxy_addr, headers=self.pc_headers)
        anchor_name = re.search('nick: "(.*?)",\n\\s+logo', html_str).group(1)
        cid = re.search('sid : "(.*?)",\n\\s+ssid', html_str, re.DOTALL).group(1)

        data = '{"head":{"seq":1701869217590,"appidstr":"0","bidstr":"121","cidstr":"' + cid + '","sidstr":"' + cid + '","uid64":0,"client_type":108,"client_ver":"5.17.0","stream_sys_ver":1,"app":"yylive_web","playersdk_ver":"5.17.0","thundersdk_ver":"0","streamsdk_ver":"5.17.0"},"client_attribute":{"client":"web","model":"web0","cpu":"","graphics_card":"","os":"chrome","osversion":"0","vsdk_version":"","app_identify":"","app_version":"","business":"","width":"1920","height":"1080","scale":"","client_type":8,"h265":0},"avp_parameter":{"version":1,"client_type":8,"service_type":0,"imsi":0,"send_time":1701869217,"line_seq":-1,"gear":4,"ssl":1,"stream_format":0}}'
        data_bytes = data.encode('utf-8')
        params = {
            "uid": "0",
            "cid": cid,
            "sid": cid,
            "appid": "0",
            "sequence": "1701869217590",
            "encode": "json"
        }
        api = f'https://stream-manager.yy.com/v3/channel/streams?{urllib.parse.urlencode(params)}'
        json_str = await async_req(api, data=data_bytes, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        json_data['anchor_name'] = anchor_name

        params = {
            'uid': '',
            'sid': cid,
            'ssid': cid,
            '_': int(time.time() * 1000),
        }
        detail_api = f'https://www.yy.com/live/detail?{urllib.parse.urlencode(params)}'
        json_str2 = await async_req(detail_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data2 = json.loads(json_str2)
        json_data['title'] = json_data2['data']['roomName']
        return json_data

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        anchor_name = json_data.get('anchor_name', '')
        result = {
            "platform": "YY直播",
            "anchor_name": anchor_name,
            "is_live": False,
        }
        if 'avp_info_res' in json_data:
            stream_line_addr = json_data['avp_info_res']['stream_line_addr']
            cdn_info = list(stream_line_addr.values())[0]
            flv_url = cdn_info['cdn_info']['url']
            result |= {
                'is_live': True,
                'title': json_data['title'],
                'quality': 'OD',
                'flv_url': flv_url,
                'record_url': flv_url
            }
        return wrap_stream(result)
