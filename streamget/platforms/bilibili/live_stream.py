import json
import urllib.parse
from operator import itemgetter

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class BilibiliLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Bilibili live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()
        self.pc_headers = self._get_pc_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or '',
            'origin': 'https://live.bilibili.com',
            'referer': 'https://live.bilibili.com/26066074',
        }

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or '__ac_nonce=064caded4009deafd8b89;',
            'origin': 'https://live.bilibili.com',
            'referer': 'https://live.bilibili.com/26066074',
        }

    async def _get_bilibili_room_info_h5(self, url: str) -> str:
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        api = f'https://api.live.bilibili.com/xlive/web-room/v1/index/getH5InfoByRoom?room_id={room_id}'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        room_info = json.loads(json_str)
        title = room_info['data']['room_info']['title'] if room_info.get('data') else ''
        return title

    async def get_bilibili_stream_data(self, url: str, qn: str = '10000', platform: str = 'web') -> str | None:

        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
        params = {
            'cid': room_id,
            'qn': qn,
            'platform': platform,
        }
        play_api = f'https://api.live.bilibili.com/room/v1/Room/playUrl?{urllib.parse.urlencode(params)}'
        json_str = await async_req(play_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if json_data and json_data['code'] == 0:
            for i in json_data['data']['durl']:
                if 'd1--cn-gotcha' in i['url']:
                    return i['url']
            return json_data['data']['durl'][-1]['url']
        else:
            params = {
                "room_id": room_id,
                "protocol": "0,1",
                "format": "0,1,2",
                "codec": "0,1,2",
                "qn": qn,
                "platform": "web",
                "ptype": "8",
                "dolby": "5",
                "panorama": "1",
                "hdr_type": "0,1"
            }

            # 此接口因网页上有限制, 需要配置登录后的cookie才能获取最高画质
            encode_params = urllib.parse.urlencode(params)
            api = f'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?{encode_params}'
            json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_data = json.loads(json_str)
            if json_data['data']['live_status'] == 0:
                print("The anchor did not start broadcasting.")
                return
            playurl_info = json_data['data']['playurl_info']
            format_list = playurl_info['playurl']['stream'][0]['format']
            stream_data_list = format_list[0]['codec']
            sorted_stream_list = sorted(stream_data_list, key=itemgetter("current_qn"), reverse=True)
            # qn: 30000=杜比 20000=4K 10000=原画 400=蓝光 250=超清 150=高清 80=流畅
            video_quality_options = {'10000': 0, '400': 1, '250': 2, '150': 3, '80': 4}
            qn_count = len(sorted_stream_list)
            select_stream_index = min(video_quality_options[qn], qn_count - 1)
            stream_data: dict = sorted_stream_list[select_stream_index]
            base_url = stream_data['base_url']
            host = stream_data['url_info'][0]['host']
            extra = stream_data['url_info'][0]['extra']
            m3u8_url = host + base_url + extra
            return m3u8_url

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
            room_id = url.split('?')[0].rsplit('/', maxsplit=1)[1]
            json_str = await async_req(f'https://api.live.bilibili.com/room/v1/Room/room_init?id={room_id}',
                                       proxy_addr=self.proxy_addr, headers=self.pc_headers)
            room_info = json.loads(json_str)
            uid = room_info['data']['uid']
            live_status = True if room_info['data']['live_status'] == 1 else False

            api = f'https://api.live.bilibili.com/live_user/v1/Master/info?uid={uid}'
            json_str2 = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            anchor_info = json.loads(json_str2)
            anchor_name = anchor_info['data']['info']['uname']

            title = await self._get_bilibili_room_info_h5(url)
            live_url = 'https://live.bilibili.com/' + str(room_id)
            return {"anchor_name": anchor_name, "live_status": live_status, "room_url": live_url, "title": title}
        except Exception as e:
            print(e)
            return {"anchor_name": '', "live_status": False, "room_url": url}

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.

        This method takes the provided room data (including anchor name, live status, and room URL),
        fetches the stream URL based on the specified video quality, and returns a StreamData object
        containing all relevant information.
        """
        platform = "哔哩哔哩"
        anchor_name = json_data.get('anchor_name')
        room_url = json_data.get('room_url')

        if not json_data["live_status"]:
            return wrap_stream(
                {"platform": platform, "anchor_name": anchor_name, "is_live": False, "live_url": room_url}
            )

        video_quality_options = {
            "OD": '10000',
            "BD": '400',
            "UHD": '250',
            "HD": '150',
            "SD": '80',
            "LD": '80'
        }

        if not video_quality:
            video_quality = "OD"
        else:
            if str(video_quality).isdigit():
                video_quality = list(video_quality_options.keys())[int(video_quality)]
            else:
                video_quality = video_quality.upper()

        select_quality = video_quality_options.get(video_quality, '10000')
        play_url = await self.get_bilibili_stream_data(
            room_url, qn=select_quality, platform='web')
        data = {
            'platform': platform,
            'anchor_name': json_data['anchor_name'],
            'is_live': True,
            'title': json_data['title'],
            'quality': video_quality,
            'record_url': play_url,
            'live_url': room_url
        }
        return wrap_stream(data)
