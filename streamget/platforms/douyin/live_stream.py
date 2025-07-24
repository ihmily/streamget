import json
import re
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req, get_response_status
from ..base import BaseLiveStream
from .utils import DouyinUtils, UnsupportedUrlError


class DouyinLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Douyin live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or '__ac_nonce=064caded4009deafd8b89;',
            'referer': 'https://live.douyin.com/'
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
        url = url.strip()
        douyin_utils = DouyinUtils()
        try:
            room_id, sec_uid = await douyin_utils.get_sec_user_id(url, proxy_addr=self.proxy_addr)
            app_params = {
                "verifyFp": "verify_lxj5zv70_7szNlAB7_pxNY_48Vh_ALKF_GA1Uf3yteoOY",
                "type_id": "0",
                "live_id": "1",
                "room_id": room_id,
                "sec_user_id": sec_uid,
                "version_code": "99.99.99",
                "app_id": "1128"
            }
            api = 'https://webcast.amemv.com/webcast/room/reflow/info/?' + urllib.parse.urlencode(app_params)
            json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            if not process_data:
                return json.loads(json_str)
            else:
                json_data = json.loads(json_str)['data']
                room_data = json_data['room']
                room_data['anchor_name'] = room_data['owner']['nickname']
                stream_data = room_data['stream_url']['live_core_sdk_data']['pull_data']['stream_data']
                origin_data = json.loads(stream_data)['data']['origin']['main']
                sdk_params = json.loads(origin_data['sdk_params'])
                origin_hls_codec = sdk_params.get('VCodec') or ''
                origin_m3u8 = {'ORIGIN': origin_data["hls"] + '&codec=' + origin_hls_codec}
                origin_flv = {'ORIGIN': origin_data["flv"] + '&codec=' + origin_hls_codec}
                hls_pull_url_map = room_data['stream_url']['hls_pull_url_map']
                flv_pull_url = room_data['stream_url']['flv_pull_url']
                room_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
                room_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}
                return room_data

        except UnsupportedUrlError:
            unique_id = await douyin_utils.get_unique_id(url, proxy_addr=self.proxy_addr)
            return await self.fetch_web_stream_data('https://live.douyin.com/' + unique_id)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        try:
            url = url.strip()
            origin_url_list = None
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            match_json_str = re.search(r'(\{\\"state\\":.*?)]\\n"]\)', html_str)
            if not match_json_str:
                match_json_str = re.search(r'(\{\\"common\\":.*?)]\\n"]\)</script><div hidden', html_str)
            json_str = match_json_str.group(1)
            cleaned_string = json_str.replace('\\', '').replace(r'u0026', r'&')
            room_store = re.search('"roomStore":(.*?),"linkmicStore"', cleaned_string, re.DOTALL).group(1)
            anchor_name = re.search('"nickname":"(.*?)","avatar_thumb', room_store, re.DOTALL).group(1)
            room_store = room_store.split(',"has_commerce_goods"')[0] + '}}}'
            if not process_data:
                return json.loads(room_store)
            else:
                json_data = json.loads(room_store)['roomInfo']['room']
                json_data['anchor_name'] = anchor_name
                if 'status' in json_data and json_data['status'] == 4:
                    return json_data
                stream_orientation = json_data['stream_url']['stream_orientation']
                match_json_str2 = re.findall(r'"(\{\\"common\\":.*?)"]\)</script><script nonce=', html_str)
                if match_json_str2:
                    json_str = match_json_str2[0] if stream_orientation == 1 else match_json_str2[1]
                    json_data2 = json.loads(
                        json_str.replace('\\', '').replace('"{', '{').replace('}"', '}').replace('u0026', '&'))
                    if 'origin' in json_data2['data']:
                        origin_url_list = json_data2['data']['origin']['main']

                else:
                    html_str = html_str.replace('\\', '').replace('u0026', '&')
                    match_json_str3 = re.search('"origin":\\{"main":(.*?),"dash"', html_str, re.DOTALL)
                    if match_json_str3:
                        origin_url_list = json.loads(match_json_str3.group(1) + '}')

                if origin_url_list:
                    origin_hls_codec = origin_url_list['sdk_params'].get('VCodec') or ''
                    origin_m3u8 = {'ORIGIN': origin_url_list["hls"] + '&codec=' + origin_hls_codec}
                    origin_flv = {'ORIGIN': origin_url_list["flv"] + '&codec=' + origin_hls_codec}
                    hls_pull_url_map = json_data['stream_url']['hls_pull_url_map']
                    flv_pull_url = json_data['stream_url']['flv_pull_url']
                    json_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
                    json_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}
            return json_data

        except Exception as e:
            raise Exception(f"Fetch failed: {url}, {e}")

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        anchor_name = json_data.get('anchor_name')
        result = {"platform": "抖音", "anchor_name": anchor_name, "is_live": False}
        status = json_data.get("status", 4)
        if status == 2:
            stream_url = json_data['stream_url']
            flv_url_dict = stream_url['flv_pull_url']
            flv_url_list: list = list(flv_url_dict.values())
            m3u8_url_dict = stream_url['hls_pull_url_map']
            m3u8_url_list: list = list(m3u8_url_dict.values())
            while len(flv_url_list) < 5:
                flv_url_list.append(flv_url_list[-1])
                m3u8_url_list.append(m3u8_url_list[-1])
            video_quality, quality_index = self.get_quality_index(video_quality)
            m3u8_url = m3u8_url_list[quality_index]
            flv_url = flv_url_list[quality_index]
            ok = await get_response_status(url=m3u8_url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            if not ok:
                index = quality_index+1 if quality_index < 4 else quality_index - 1
                m3u8_url = m3u8_url_list[index]
                flv_url = flv_url_list[index]

            result |= {
                'is_live': True,
                'title': json_data['title'],
                'quality': video_quality,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': m3u8_url or flv_url,
            }
        return wrap_stream(result)
