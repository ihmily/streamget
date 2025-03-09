import re
import time
import execjs
import urllib.parse
from ... import utils
from ... import JS_SCRIPT_PATH
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class TaobaoLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Taobao live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'referer': 'https://huodong.m.taobao.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
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
        if '_m_h5_tk' not in self.pc_headers['cookie']:
            raise Exception('Error: Cookies is empty! please input correct cookies')

        live_id = self.get_params(url, 'id')
        if not live_id:
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            redirect_url = re.findall("var url = '(.*?)';", html_str)[0]
            live_id = self.get_params(redirect_url, 'id')

        params = {
            'jsv': '2.7.0',
            'appKey': '12574478',
            't': '1733104933120',
            'sign': '',
            'AntiFlood': 'true',
            'AntiCreep': 'true',
            'api': 'mtop.mediaplatform.live.livedetail',
            'v': '4.0',
            'preventFallback': 'true',
            'type': 'jsonp',
            'dataType': 'jsonp',
            'callback': 'mtopjsonp1',
            'data': '{"liveId":"' + live_id + '","creatorId":null}',
        }

        for i in range(2):
            app_key = '12574478'
            _m_h5_tk = re.findall('_m_h5_tk=(.*?);', self.pc_headers['cookie'])[0]
            t13 = int(time.time() * 1000)
            pre_sign_str = f'{_m_h5_tk.split("_")[0]}&{t13}&{app_key}&' + params['data']
            try:
                sign = execjs.compile(open(f'{JS_SCRIPT_PATH}/taobao-sign.js').read()).call('sign', pre_sign_str)
            except execjs.ProgramError:
                raise execjs.ProgramError('Failed to execute JS code. Please check if the Node.js environment')
            params |= {'sign': sign, 't': t13}
            api = f'https://h5api.m.taobao.com/h5/mtop.mediaplatform.live.livedetail/4.0/?{urllib.parse.urlencode(params)}'
            jsonp_str, new_cookie = await async_req(url=api, proxy_addr=self.proxy_addr, headers=self.pc_headers,
                                                    timeout=20, return_cookies=True, include_cookies=True)
            json_data = utils.jsonp_to_json(jsonp_str)
            if not process_data:
                return json_data
            ret_msg = json_data['ret']
            if ret_msg == ['SUCCESS::调用成功']:
                anchor_name = json_data['data']['broadCaster']['accountName']
                result = {"anchor_name": anchor_name, "is_live": False}
                live_status = json_data['data']['streamStatus']
                if live_status == '1':
                    live_title = json_data['data']['title']
                    play_url_list = json_data['data']['liveUrlList']
                    play_url_list = sorted(play_url_list, key=lambda x: int(x['codeLevel']), reverse=True)
                    result |= {"is_live": True, "title": live_title, "play_url_list": play_url_list, 'live_id': live_id}

                if '_m_h5_tk' in new_cookie and '_m_h5_tk_enc' in new_cookie:
                    self.pc_headers['cookie'] = re.sub('_m_h5_tk=(.*?);', new_cookie['_m_h5_tk'],
                                                       self.pc_headers['cookie'])
                    self.pc_headers['cookie'] = re.sub('_m_h5_tk_enc=(.*?);', new_cookie['_m_h5_tk_enc'],
                                                       self.pc_headers['cookie'])
                else:
                    raise Exception(
                        'Error: Try to update cookie failed, please update the cookies in the configuration file')
                return result
            else:
                raise Exception(f'Error: Taobao live data fetch failed, {ret_msg[0]}')

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(
            json_data, video_quality, url_type='all', hls_extra_key='hlsUrl', flv_extra_key='flvUrl', platform='淘宝直播')
        return wrap_stream(data)
