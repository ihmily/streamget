import base64
import hashlib
import json
import random
import re
import time
import urllib.parse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class HuyaLiveStream(BaseLiveStream):
    """
      A class for fetching and processing Huya live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()
        self.mobile_headers = self._get_mobile_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'xweb_xhr': '1',
            'referer': 'https://servicewechat.com/wx74767bf0b684f7d3/301/page-frame.html',
            'accept-language': 'zh-CN,zh;q=0.9',
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
        html_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_str = re.findall('stream: (\\{"data".*?),"iWebDefaultBitRate"', html_str)[0]
        json_data = json.loads(json_str + '}')
        json_data['live_url'] = url
        return json_data

    async def fetch_app_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches app stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]

        if any(char.isalpha() for char in room_id):
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            room_id = re.search('ProfileRoom":(.*?),"sPrivateHost', html_str)
            if room_id:
                room_id = room_id.group(1)
            else:
                raise Exception('Please use "https://www.huya.com/+room_number" for recording')

        live_url = 'https://www.huya.com/' + str(room_id)

        params = {
            'm': 'Live',
            'do': 'profileRoom',
            'roomid': room_id,
            'showSecret': '1',
        }
        wx_app_api = f'https://mp.huya.com/cache.php?{urllib.parse.urlencode(params)}'
        json_str = await async_req(url=wx_app_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)

        if not process_data:
            return json_data
        anchor_name = json_data['data']['profileInfo']['nick']
        live_status = json_data['data']['realLiveStatus']
        if live_status != 'ON':
            return {'anchor_name': anchor_name, 'is_live': False, 'live_url': live_url}
        else:
            live_title = json_data['data']['liveData']['introduction']
            live_type = json_data['data']['liveData']["gameHostName"]
            if live_type in ['lol']:
                return await self.fetch_web_stream_data(live_url)

            base_steam_info_list = json_data['data']['stream']['baseSteamInfoList']
            play_url_list = []
            for i in base_steam_info_list:
                cdn_type = i['sCdnType']
                stream_name = i['sStreamName']
                s_flv_url = i['sFlvUrl']
                flv_anti_code = i['sFlvAntiCode']
                s_hls_url = i['sHlsUrl']
                hls_anti_code = i['sHlsAntiCode']
                m3u8_url = f'{s_hls_url}/{stream_name}.m3u8?{hls_anti_code}'
                flv_url = f'{s_flv_url}/{stream_name}.flv?{flv_anti_code}'
                play_url_list.append(
                    {
                        'cdn_type': cdn_type,
                        'm3u8_url': m3u8_url,
                        'flv_url': flv_url,
                    }
                )

            # mStreamRatioWeb = json.loads(json_data['data']['liveData']['mStreamRatioWeb'])
            # highest_priority_key = max(mStreamRatioWeb, key=lambda k: mStreamRatioWeb[k])

            select_item = None
            for item in play_url_list:
                if item["cdn_type"] == "TX":
                    select_item = item

            select_item = select_item or play_url_list[0]
            m3u8_url = select_item.get("m3u8_url")
            flv_url = select_item.get("flv_url")
            if select_item["cdn_type"] in ["TX", "HW"]:
                flv_url = flv_url.replace("&ctype=tars_mp", "&ctype=huya_webh5").replace("&fs=bhct", "&fs=bgct")
                m3u8_url = m3u8_url.replace("&ctype=tars_mp", "&ctype=huya_webh5").replace("&fs=bhct", "&fs=bgct")

            return {
                'anchor_name': anchor_name,
                'is_live': True,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': flv_url or m3u8_url,
                'title': live_title,
                'live_url': live_url
            }

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
         Fetches the stream URL for a live room and wraps it into a StreamData object.
         """
        platform = "虎牙直播"
        if 'is_live' in json_data:
            json_data |= {"platform": platform, "quality": video_quality}
            return wrap_stream(json_data)
        game_live_info = json_data['data'][0]['gameLiveInfo']
        live_title = game_live_info['introduction']
        stream_info_list = json_data['data'][0]['gameStreamInfoList']
        anchor_name = game_live_info.get('nick', '')
        live_url = json_data.get('live_url')

        result = {
            "platform": platform,
            "anchor_name": anchor_name,
            "is_live": False,
            "live_url": live_url
        }

        if stream_info_list:
            select_cdn = stream_info_list[0]
            flv_url = select_cdn.get('sFlvUrl')
            stream_name = select_cdn.get('sStreamName')
            flv_url_suffix = select_cdn.get('sFlvUrlSuffix')
            hls_url = select_cdn.get('sHlsUrl')
            hls_url_suffix = select_cdn.get('sHlsUrlSuffix')
            flv_anti_code = select_cdn.get('sFlvAntiCode')

            def get_anti_code(old_anti_code: str) -> str:

                # js地址：https://hd.huya.com/cdn_libs/mobile/hysdk-m-202402211431.js

                params_t = 100
                sdk_version = 2403051612

                # sdk_id是13位数毫秒级时间戳
                t13 = int(time.time()) * 1000
                sdk_sid = t13

                # 计算uuid和uid参数值
                init_uuid = (int(t13 % 10 ** 10 * 1000) + int(1000 * random.random())) % 4294967295
                uid = random.randint(1400000000000, 1400009999999)  # 经过测试uid也可以使用init_uuid代替
                seq_id = uid + sdk_sid  # 移动端请求的直播流地址中包含seqId参数

                # 计算ws_time参数值(16进制) 可以是当前毫秒时间戳，当然也可以直接使用url_query['wsTime'][0]
                # 原始最大误差不得慢240000毫秒
                target_unix_time = (t13 + 110624) // 1000
                ws_time = f"{target_unix_time:x}".lower()

                # fm参数值是经过url编码然后base64编码得到的，解码结果类似 DWq8BcJ3h6DJt6TY_$0_$1_$2_$3
                # 具体细节在上面js中查看，大概在32657行代码开始，有base64混淆代码请自行替换
                url_query = urllib.parse.parse_qs(old_anti_code)
                ws_secret_pf = base64.b64decode(urllib.parse.unquote(url_query['fm'][0]).encode()).decode().split("_")[
                    0]
                ws_secret_hash = hashlib.md5(f'{seq_id}|{url_query["ctype"][0]}|{params_t}'.encode()).hexdigest()
                ws_secret = f'{ws_secret_pf}_{uid}_{stream_name}_{ws_secret_hash}_{ws_time}'
                ws_secret_md5 = hashlib.md5(ws_secret.encode()).hexdigest()

                anti_code = (
                    f'wsSecret={ws_secret_md5}&wsTime={ws_time}&seqid={seq_id}&ctype={url_query["ctype"][0]}&ver=1'
                    f'&fs={url_query["fs"][0]}&uuid={init_uuid}&u={uid}&t={params_t}&sv={sdk_version}'
                    f'&sdk_sid={sdk_sid}&codec=264'
                )
                return anti_code

            new_anti_code = get_anti_code(flv_anti_code)
            flv_url = f'{flv_url}/{stream_name}.{flv_url_suffix}?{new_anti_code}&ratio='
            m3u8_url = f'{hls_url}/{stream_name}.{hls_url_suffix}?{new_anti_code}&ratio='

            quality_list = flv_anti_code.split('&exsphd=')

            if not video_quality:
                video_quality = "OD"
            else:
                if str(video_quality).isdigit():
                    video_quality_keys = ["OD", "BD", "UHD", "HD", "SD", "LD"]
                    video_quality = video_quality_keys[int(video_quality)]
                else:
                    video_quality = video_quality.upper()

            if len(quality_list) > 1 and video_quality not in ["OD", "BD"]:
                pattern = r"(?<=264_)\d+"
                quality_list = list(re.findall(pattern, quality_list[1]))[::-1]
                while len(quality_list) < 5:
                    quality_list.append(quality_list[-1])

                video_quality_options = {
                    "UHD": quality_list[0],
                    "HD": quality_list[1],
                    "SD": quality_list[2],
                    "LD": quality_list[3]
                }

                if video_quality not in video_quality_options:
                    raise ValueError(
                        f"Invalid video quality. Available options are: {', '.join(video_quality_options.keys())}")

                flv_url = flv_url + str(video_quality_options[video_quality])
                m3u8_url = m3u8_url + str(video_quality_options[video_quality])

            result |= {
                'is_live': True,
                'title': live_title,
                'quality': video_quality,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': flv_url or m3u8_url
            }
        return wrap_stream(result)
