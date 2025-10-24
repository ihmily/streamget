import json
import re
from operator import itemgetter

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req, get_response_status
from ..base import BaseLiveStream


class TikTokLiveStream(BaseLiveStream):
    """
    A class for fetching and processing TikTok live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'referer': 'https://www.tiktok.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
            'cookie': self.cookies or 'ttwid=1%7Ctzsy_yRGZ2N8AI7luDz2s9H9a8CQI3ZisibOcuw5OHs%7C1761301927'
                                      '%7C484a25162facd523ee6e2997187c9fad4a512c031d9efc6eaddb2c4bae8ce3fb'
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
        html_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=self.pc_headers, http2=False)
        if "We regret to inform you that we have discontinued operating TikTok" in html_str:
            msg = re.search('<p>\n\\s+(We regret to inform you that we have discontinu.*?)\\.\n\\s+</p>', html_str)
            raise ConnectionError(
                "Your proxy node's regional network is blocked from accessing TikTok; please switch to a node in "
                f"another region to access. {msg.group(1) if msg else ''}"
            )
        if 'UNEXPECTED_EOF_WHILE_READING' not in html_str:
            json_str = re.findall(
                '<script id="SIGI_STATE" type="application/json">(.*?)</script>', html_str, re.DOTALL)
            if not json_str:
                raise ConnectionError("Please check if your network can access the TikTok website normally")
            json_data = json.loads(json_str[0])
            json_data['live_url'] = url
            return json_data
        return {'live_url': url}

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        if not json_data:
            return wrap_stream({})

        live_url = json_data.get("live_url")
        if 'LiveRoom' not in json_data:
            return wrap_stream({"platform": "TikTok", "anchor_name": None, "is_live": False, "live_url": live_url})

        def get_video_quality_url(stream, q_key) -> list:
            play_list = []
            for key in stream:
                url_info = stream[key]['main']
                sdk_params = url_info['sdk_params']
                sdk_params = json.loads(sdk_params)
                vbitrate = int(sdk_params['vbitrate'])
                v_codec = sdk_params.get('VCodec', '')
                play_url = ''
                if url_info.get(q_key):
                    if url_info[q_key].endswith(".flv") or url_info[q_key].endswith(".m3u8"):
                        play_url = url_info[q_key] + '?codec=' + v_codec
                    else:
                        play_url = url_info[q_key] + '&codec=' + v_codec
                resolution = sdk_params['resolution']
                if vbitrate != 0 and resolution:
                    width, height = map(int, resolution.split('x'))
                    play_list.append({'url': play_url, 'vbitrate': vbitrate, 'resolution': (width, height)})

            play_list.sort(key=itemgetter('vbitrate'), reverse=True)
            play_list.sort(key=lambda x: (-x['vbitrate'], -x['resolution'][0], -x['resolution'][1]))
            return play_list

        live_room = json_data['LiveRoom']['liveRoomUserInfo']
        user = live_room['user']
        anchor_name = f"{user['nickname']}-{user['uniqueId']}"
        status = user.get("status", 4)

        result = {
            "platform": "TikTok",
            "anchor_name": anchor_name,
            "is_live": False,
            "live_url": live_url
        }

        if status == 2:
            if 'streamData' not in live_room['liveRoom']:
                raise Exception("This live stream may be uncomfortable for some viewers. Log in to confirm your age")
            data = live_room['liveRoom']['streamData']['pull_data']['stream_data']
            data = json.loads(data).get('data', {})
            flv_url_list = get_video_quality_url(data, 'flv')
            m3u8_url_list = get_video_quality_url(data, 'hls')

            while len(flv_url_list) < 5:
                flv_url_list.append(flv_url_list[-1])
            while len(m3u8_url_list) < 5:
                m3u8_url_list.append(m3u8_url_list[-1])
            video_quality, quality_index = self.get_quality_index(video_quality)
            flv_dict: dict = flv_url_list[quality_index]
            m3u8_dict: dict = m3u8_url_list[quality_index]

            check_url = m3u8_dict.get('url') or flv_dict.get('url')
            ok = await get_response_status(
                url=check_url, proxy_addr=self.proxy_addr, headers=self.pc_headers, http2=False)

            if not ok:
                index = quality_index + 1 if quality_index < 4 else quality_index - 1
                flv_dict: dict = flv_url_list[index]
                m3u8_dict: dict = m3u8_url_list[index]

            flv_url = flv_dict['url'].replace("https://", "http://")
            m3u8_url = m3u8_dict['url'].replace("https://", "http://")
            result |= {
                'is_live': True,
                'title': live_room['liveRoom']['title'],
                'quality': video_quality,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': m3u8_url or flv_url
            }
        return wrap_stream(result)