import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class KwaiLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Kuaishou live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict | None:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        try:
            html_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        except Exception as e:
            raise Exception(f"Failed to fetch data from {url}.{e}")

        try:
            json_str = re.search('<script>window.__INITIAL_STATE__=(.*?);\\(function\\(\\)\\{var s;', html_str).group(1)
            play_list = re.findall('(\\{"liveStream".*?),"gameInfo', json_str)[0] + "}"
            play_list = json.loads(play_list)
        except (AttributeError, IndexError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to parse JSON data from {url}. Error: {e}")

        result = {"type": 2, "is_live": False, 'live_url': url}

        if 'errorType' in play_list or 'liveStream' not in play_list:
            error_msg = play_list['errorType']['title'] + play_list['errorType']['content']
            raise Exception(f"Failed URL: {url} Error message: {error_msg}")

        if not play_list.get('liveStream'):
            raise Exception("IP banned. Please change device or network.")

        anchor_name = play_list['author'].get('name', '')
        result.update({"anchor_name": anchor_name})

        if play_list['liveStream'].get("playUrls"):
            if 'h264' in play_list['liveStream']['playUrls']:
                if 'adaptationSet' not in play_list['liveStream']['playUrls']['h264']:
                    return result
                play_url_list = play_list['liveStream']['playUrls']['h264']['adaptationSet']['representation']
            else:
                play_url_list = play_list['liveStream']['playUrls'][0]['adaptationSet']['representation']
            result.update({"flv_url_list": play_url_list, "is_live": True})

        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        platform = "快手直播"
        if json_data['type'] == 1 and not json_data["is_live"]:
            json_data |= {"platform": platform}
            return wrap_stream(json_data)
        live_status = json_data['is_live']

        result = {
            "platform": platform,
            "anchor_name": json_data['anchor_name'],
            "is_live": live_status,
            "live_url": json_data['live_url'],
        }

        if live_status:

            quality_mapping_bit = {'OD': 99999, 'BD': 4000, 'UHD': 2000, 'HD': 1000, 'SD': 800, 'LD': 600}
            video_quality, quality_index = self.get_quality_index(video_quality)

            if 'm3u8_url_list' in json_data:
                m3u8_url_list = json_data['m3u8_url_list'][::-1]
                while len(m3u8_url_list) < 5:
                    m3u8_url_list.append(m3u8_url_list[-1])
                m3u8_url = m3u8_url_list[quality_index]['url']
                result['m3u8_url'] = m3u8_url

            if 'flv_url_list' in json_data:
                if 'bitrate' in json_data['flv_url_list'][0]:
                    flv_url_list = json_data['flv_url_list']
                    flv_url_list = sorted(flv_url_list, key=lambda x: x['bitrate'], reverse=True)

                    quality_index_bitrate_value = quality_mapping_bit.get(video_quality, 99999)
                    quality_index = next(
                        (i for i, x in enumerate(flv_url_list) if x['bitrate'] <= quality_index_bitrate_value),
                        None)
                    if quality_index is None:
                        quality_index = len(flv_url_list) - 1
                    flv_url = flv_url_list[quality_index]['url']

                    result['flv_url'] = flv_url
                    result['record_url'] = flv_url
                else:
                    flv_url_list = json_data['flv_url_list'][::-1]
                    while len(flv_url_list) < 5:
                        flv_url_list.append(flv_url_list[-1])
                    flv_url = flv_url_list[quality_index]['url']
                    result |= {'flv_url': flv_url, 'record_url': flv_url}
            result['is_live'] = True
            result['quality'] = video_quality
        return wrap_stream(result)

