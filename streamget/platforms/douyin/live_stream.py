import json
import re
import urllib.parse

from deprecated import deprecated

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req, get_response_status
from ..base import BaseLiveStream
from .ab_sign import ab_sign
from .utils import DouyinUtils, UnsupportedUrlError


class DouyinLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Douyin live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None, stream_orientation: int | None = 1):
        super().__init__(proxy_addr, cookies)
        self.stream_orientation = stream_orientation
        self.mobile_headers = self._get_mobile_headers()
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/141.0.0.0 Safari/537.36',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or '__ac_nonce=064caded4009deafd8b89',
            'referer': 'https://live.douyin.com/'
        }

    @staticmethod
    def sort_streams_by_bitrate(data):

        streams = []

        for quality, stream_info in data.items():
            try:
                main = stream_info.get("main")
                if not main:
                    continue

                sdk_params_str = main.get("sdk_params")
                if not sdk_params_str:
                    continue

                sdk_params = json.loads(sdk_params_str) if isinstance(sdk_params_str, str) else sdk_params_str
                vbitrate = sdk_params.get("vbitrate")
                if not isinstance(vbitrate, (int, float)) or vbitrate <= 0:
                    continue

                flv_url = main.get("flv", "")
                hls_url = main.get("hls", "")

                if not flv_url and not hls_url:
                    continue

                streams.append({
                    "name": quality,
                    "bitrate": int(vbitrate),
                    "flv": flv_url,
                    "hls": hls_url
                })

            except (json.JSONDecodeError, Exception) as _:
                continue

        sorted_streams = sorted(streams, key=lambda x: x["bitrate"], reverse=True)
        return sorted_streams

    async def _get_web_stream_data(self, web_rid: str, process_data: bool = True):

        headers = {
            'referer': 'https://live.douyin.com/335354047186',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/123.0.0.0 Safari/537.36',
            'cookie': "ttwid=1%7CmDcInbJ7AJ-2PGtsgrG4xj7SOiNMzePqQBF1LMO2Qkg%7C1761107324%7Cbbf97c2cd9f8eae8e8c36db"
                      "4ef50c323deaa4b161179170aaf659590867c162d"
        }
        if self.cookies and 'ttwid=' in self.cookies:
            headers['cookie'] = self.cookies

        params = {
            "aid": "6383",
            "app_name": "douyin_web",
            "live_id": "1",
            "device_platform": "web",
            "language": "zh-CN",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "116.0.0.0",
            "web_rid": web_rid,
            'is_need_double_stream': 'false',
            'msToken': '',
        }

        api = 'https://live.douyin.com/webcast/room/web/enter/?' + urllib.parse.urlencode(params)
        a_bogus = ab_sign(urllib.parse.urlparse(api).query, headers['user-agent'])
        api += "&a_bogus=" + a_bogus
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=headers)
        if not json_str:
            raise Exception("it triggered risk control")

        if not process_data:
            return json.loads(json_str)
        else:
            json_data = json.loads(json_str)['data']
            if not json_data.get('data') or not json_data['data']:
                raise Exception("VR live is not supported")

            room_data = json_data['data'][0]
            room_data['anchor_name'] = json_data['user']['nickname']
            room_data['live_url'] = "https://live.douyin.com/" + str(web_rid)

            if room_data.get('status') == 4:
                return room_data
            stream_orientation = room_data['stream_url']['stream_orientation']
            pull_datas = room_data['stream_url'].get('pull_datas')
            orientation = 2 if stream_orientation == 2 and self.stream_orientation == 2 and pull_datas else 1

            if orientation == 2:
                room_data['stream_orientation'] = 2
                stream_data_str = list(room_data['stream_url']['pull_datas'].values())[0]['stream_data']
                stream_data = json.loads(stream_data_str)
                sorted_stream_data = self.sort_streams_by_bitrate(stream_data["data"])
                hls_pull_url_map = {}
                flv_pull_url_map = {}
                for i in sorted_stream_data:
                    hls_pull_url_map[i["name"]] = i['hls']
                    flv_pull_url_map[i["name"]] = i['flv']
                    room_data['stream_url']['hls_pull_url_map'] = hls_pull_url_map
                    room_data['stream_url']['flv_pull_url'] = flv_pull_url_map
                return room_data
            else:
                room_data['stream_orientation'] = 1
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

    async def _get_app_web_stream_data(self, url: str, process_data: bool = True):
        html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        match_json_str = re.search(
            '</script><script >self.__rsc_f.push\\(\\[1,"(\\{.*?)"]\\)</script><script >self.__rsc_f.push', html_str)

        if not match_json_str:
            raise Exception("Fetch stream data error")

        json_str = match_json_str.group(1)
        cleaned_string = json_str.replace('\\', '').replace(r'u0026', r'&').replace(
            '"sdk_params":"', '"sdk_params":').replace('","enableEncryption', ',"enableEncryption')
        cleaned_string = '{"data":' + cleaned_string.split(',"data":')[1]
        json_data = json.loads(cleaned_string)

        json_str2 = re.findall('</script><script >self.__rsc_f.push\\(\\[1,"5(.*?)</script>$', html_str)[-1]
        json_str2 = json_str2.replace('\\\\\\"', '"').replace('\\"', '"').replace('"{', '{').replace('}"', '}')
        json_str2 = json_str2.split(':["$","$L7",null,', maxsplit=1)[-1].split(']\\n"])', maxsplit=1)[0]
        json_data2 = json.loads(json_str2)

        if not process_data:
            return json_data2

        room_data = json_data2['data']['room']
        room_data['anchor_name'] = room_data['owner']['nickname']
        room_data['live_url'] = "http://live.douyin.com/live/" + room_data['owner']['webRid']

        if room_data.get('status') == 4:
            return room_data

        stream_url = room_data['streamUrl']
        stream_orientation = stream_url['streamOrientation']
        pull_datas = stream_url.get('pullDatas')
        orientation = 2 if stream_orientation == 2 and self.stream_orientation == 2 and pull_datas else 1

        if orientation == 2:
            room_data['stream_orientation'] = 2
            stream_data_str = list(pull_datas.values())[0]['streamData']
            stream_data = json.loads(stream_data_str)
            sorted_stream_data = self.sort_streams_by_bitrate(stream_data["data"])
            hls_pull_url_map = {}
            flv_pull_url_map = {}
            for i in sorted_stream_data:
                hls_pull_url_map[i["name"]] = i['hls']
                flv_pull_url_map[i["name"]] = i['flv']
                room_data['stream_url']['hls_pull_url_map'] = hls_pull_url_map
                room_data['stream_url']['flv_pull_url'] = flv_pull_url_map
            return room_data
        else:
            room_data['stream_orientation'] = 1
            stream_data = stream_url['liveCoreSdkData']['pullData']['streamData']
            if orientation == 1 and not stream_data.startswith('$'):
                origin_data = json.loads(stream_data)['data']['origin']['main']
            else:
                origin_data = json_data['data']['origin']['main']
            sdk_params = origin_data['sdk_params']
            origin_hls_codec = sdk_params.get('VCodec') or ''
            origin_m3u8 = {'ORIGIN': origin_data["hls"] + '&codec=' + origin_hls_codec}
            origin_flv = {'ORIGIN': origin_data["flv"] + '&codec=' + origin_hls_codec}
            hls_pull_url_map = stream_url['hlsPullUrlMap']
            flv_pull_url = stream_url['flvPullUrl']
            room_data['streamUrl']['hlsPullUrlMap'] = {**origin_m3u8, **hls_pull_url_map}
            room_data['streamUrl']['flvPullUrl'] = {**origin_flv, **flv_pull_url}
            return room_data

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
            if self.stream_orientation == 2:
                # return await self._get_app_web_stream_data(url, process_data)
                if 'https://live.douyin.com/' in url:
                    web_rid = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
                else:
                    html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
                    web_rid = re.search('webRid(.*?)desensitizedNickname', html_str).group(1)
                    web_rid = re.search(r'(\d+)', web_rid).group(1)
                return await self._get_web_stream_data(web_rid, process_data)

            room_id, sec_uid = await douyin_utils.get_sec_user_id(url, proxy_addr=self.proxy_addr)
            app_params = {
                "verifyFp": "verify_lxj5zv70_7szNlAB7_pxNY_48Vh_ALKF_GA1Uf3yteoOY",
                "type_id": "0",
                "live_id": "1",
                "room_id": room_id,
                "sec_user_id": sec_uid,
                "version_code": "99.99.99",
                "app_id": "1128",
                "is_need_double_stream": True
            }
            api = 'https://webcast.amemv.com/webcast/room/reflow/info/?' + urllib.parse.urlencode(app_params)
            a_bogus = ab_sign(urllib.parse.urlparse(api).query, self.mobile_headers['user-agent'])
            api += "&a_bogus=" + a_bogus
            json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
            if not json_str:
                raise Exception("it triggered risk control")

            if not process_data:
                return json.loads(json_str)
            else:
                json_data = json.loads(json_str)['data']
                if not json_data.get('room'):
                    raise Exception(f"{url} VR live is not supported")

                room_data = json_data.get('room')
                owner_data = room_data['owner']
                room_data['anchor_name'] = owner_data['nickname']
                web_rid = owner_data.get('web_rid')
                room_data['live_url'] = "https://live.douyin.com/" + str(web_rid) if web_rid else None

                if room_data.get('status') == 4:
                    return room_data

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
                room_data['stream_orientation'] = 1
                return room_data

        except UnsupportedUrlError:
            unique_id = await douyin_utils.get_unique_id(url, proxy_addr=self.proxy_addr)
            return await self.fetch_web_stream_data('https://live.douyin.com/' + unique_id)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        web_rid = url.split('?')[0].rsplit('/', maxsplit=1)[-1]
        return await self._get_web_stream_data(web_rid, process_data)

    @deprecated(reason="Use fetch_web_stream_data() instead.", version="4.0.9")
    async def fetch_web_stream_data_v1(self, url: str, process_data: bool = True) -> dict:
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
            room_store = room_store.split(',"has_commerce_goods"')[0] + '}'*3

            title_str = re.search('"title":"(.*?)","user_count_str"', room_store).group(1)
            rstr = r"[\/\\\:\\\"\, ]"
            new_title_str = re.sub(rstr, "_", title_str.strip())

            room_store = room_store.replace(title_str, new_title_str)
            if not process_data:
                return json.loads(room_store)
            else:
                json_data = json.loads(room_store)['roomInfo']['room']
                json_data['anchor_name'] = anchor_name
                json_data['live_url'] = url.split('?')[0]
                if json_data.get('status') == 4:
                    return json_data
                stream_orientation = json_data['stream_url']['stream_orientation']
                match_json_str2 = re.findall(r'"(\{\\"common\\":.*?)"]\)</script><script nonce=', html_str)
                orientation = 2 if stream_orientation == 2 and self.stream_orientation == 2 else 1

                if match_json_str2 and orientation == 2 and len(match_json_str2) > 1:
                    json_str = match_json_str2[1]
                    json_str2 = json.loads(
                        json_str.replace('\\', '').replace('"{', '{').replace('}"', '}').replace('u0026', '&'))

                    sorted_stream_data = self.sort_streams_by_bitrate(json_str2["data"])
                    hls_pull_url_map = {}
                    flv_pull_url_map = {}
                    for i in sorted_stream_data:
                        hls_pull_url_map[i["name"]] = i['hls']
                        flv_pull_url_map[i["name"]] = i['flv']
                        json_data['stream_url']['hls_pull_url_map'] = hls_pull_url_map
                        json_data['stream_url']['flv_pull_url'] = flv_pull_url_map

                    json_data['stream_orientation'] = 2
                    return json_data

                else:
                    if match_json_str2:
                        json_str = match_json_str2[0]
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

                    json_data['stream_orientation'] = 1

            return json_data

        except Exception as e:
            raise Exception(f"Fetch failed: {url}, {e}")

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        anchor_name = json_data.get('anchor_name')
        live_url = json_data.get('live_url')
        result = {"platform": "抖音", "anchor_name": anchor_name, "is_live": False, "live_url": live_url,
                  "extra": {"stream_orientation": json_data.get('stream_orientation')}}
        status = json_data.get("status", 4)
        if status == 2:
            stream_url = json_data.get('stream_url', json_data.get('streamUrl'))
            flv_url_dict = stream_url.get('flv_pull_url', stream_url.get('flvPullUrl'))
            flv_url_list: list = list(flv_url_dict.values())
            m3u8_url_dict = stream_url.get('hls_pull_url_map', stream_url.get('hlsPullUrlMap'))
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
                'title': json_data.get('title'),
                'quality': video_quality,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': m3u8_url or flv_url
            }
        return wrap_stream(result)
