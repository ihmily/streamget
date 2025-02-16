import re
import json
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class ShowRoomLiveStream(BaseLiveStream):
    """
    A class for fetching and processing ShowRoom live stream information.
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
        url = url.strip()
        if '/room/profile' in url:
            room_id = url.split('room_id=')[-1]
        else:
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            room_id = re.search('href="/room/profile\\?room_id=(.*?)"', html_str).group(1)
        info_api = f'https://www.showroom-live.com/api/live/live_info?room_id={room_id}'
        json_str = await async_req(info_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        anchor_name = json_data['room_name']
        result = {"anchor_name": anchor_name, "is_live": False}
        live_status = json_data['live_status']
        if live_status == 2:
            result["is_live"] = True
            web_api = f'https://www.showroom-live.com/api/live/streaming_url?room_id={room_id}&abr_available=1'
            json_str = await async_req(web_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            if json_str:
                json_data = json.loads(json_str)
                streaming_url_list = json_data['streaming_url_list']

                for i in streaming_url_list:
                    if i['type'] == 'hls_all':
                        m3u8_url = i['url']
                        result['m3u8_url'] = m3u8_url
                        if m3u8_url:
                            m3u8_url_list = await self.get_play_url_list(
                                m3u8_url, proxy=self.proxy_addr, headers=self.pc_headers)
                            if m3u8_url_list:
                                result['play_url_list'] = [f"{m3u8_url.rsplit('/', maxsplit=1)[0]}/{i}" for i in
                                                           m3u8_url_list]
                            else:
                                result['play_url_list'] = [m3u8_url]
                            result['play_url_list'] = [i.replace('https://', 'http://') for i in
                                                       result['play_url_list']]
                            break
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform="ShowRoom")
        return wrap_stream(data)

