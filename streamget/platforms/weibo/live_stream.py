import json
from ..base import BaseLiveStream
from ...data import wrap_stream, StreamData
from ...requests.async_http import async_req


class WeiboLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Blued live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        default_cookie = ('SUB=_2AkMRNMCwf8NxqwFRmfwWymPrbI9-'
                          'zgzEieKnaDFrJRMxHRl-yT9kqmkhtRB6OrTuX5z9N_7qk9C3xxEmNR-8WLcyo2PM; '
                          'SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9WWemwcqkukCduUO11o9sBqA;')
        return {
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'cookie': self.cookies or default_cookie,
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
        room_id = ''
        result = {"anchor_name": '', "is_live": False}
        if 'show/' in url:
            room_id = url.split('?')[0].split('show/')[1]
        else:
            uid = url.split('?')[0].rsplit('/u/', maxsplit=1)[1]
            web_api = f'https://weibo.com/ajax/statuses/mymblog?uid={uid}&page=1&feature=0'
            json_str = await async_req(web_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_data = json.loads(json_str)
            for i in json_data['data']['list']:
                if 'page_info' in i and i['page_info']['object_type'] == 'live':
                    room_id = i['page_info']['object_id']
                    break
            result['anchor_name'] = json_data['data']['list'][0]['user']['screen_name']

        if room_id:
            app_api = f'https://weibo.com/l/pc/anchor/live?live_id={room_id}'
            # app_api = f'https://weibo.com/l/!/2/wblive/room/show_pc_live.json?live_id={room_id}'
            json_str = await async_req(url=app_api, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            json_data = json.loads(json_str)
            if not process_data:
                return json_data
            anchor_name = json_data['data']['user_info']['name']
            result["anchor_name"] = anchor_name
            live_status = json_data['data']['item']['status']
            if live_status == 1:
                result["is_live"] = True
                live_title = json_data['data']['item']['desc']
                play_url_list = json_data['data']['item']['stream_info']['pull']
                m3u8_url = play_url_list['live_origin_hls_url']
                flv_url = play_url_list['live_origin_flv_url']
                result['title'] = live_title
                result['play_url_list'] = [
                    {"m3u8_url": m3u8_url, "flv_url": flv_url},
                    {"m3u8_url": m3u8_url.split('_')[0] + '.m3u8', "flv_url": flv_url.split('_')[0] + '.flv'}
                ]
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, spec=True, platform='微博直播')
        return wrap_stream(data)

