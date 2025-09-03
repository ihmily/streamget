import re
import urllib.parse

from ..requests.async_http import async_req


class BaseLiveStream:
    """
    Base class for live stream fetchers.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        """
        Initializes a new instance of BaseLiveStream.

        Args:
            proxy_addr (str | None): The proxy address to use for requests. Defaults to None.
            cookies (str | None): The cookies to include in requests. Defaults to None.
        """
        self.proxy_addr = proxy_addr
        self.cookies = cookies

    def _get_mobile_headers(self) -> dict:
        """
        Returns headers for mobile requests.

        Returns:
            dict: Mobile headers with default values.
        """
        return {
            'user-agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or ''
        }

    def _get_pc_headers(self) -> dict:
        """
        Returns headers for PC requests.

        Returns:
            dict: PC headers with default values.
        """
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or ''
        }

    @staticmethod
    def get_quality_index(quality: str | int | None = None) -> tuple:
        """
        Maps a quality string to its corresponding index.

        Args:
            quality (str | int): The quality string (e.g., 'OD', 'HD') or index.

        Returns:
            tuple: A tuple containing the quality string and its index.
        """
        QUALITY_MAPPING = {"OD": 0, "UHD": 1, "HD": 2, "SD": 3, "LD": 4}

        if not quality:
            return list(QUALITY_MAPPING.items())[0]

        quality_str = str(quality).upper()
        if quality_str.isdigit():
            quality_str = list(QUALITY_MAPPING.keys())[int(quality_str)]
        return quality_str, QUALITY_MAPPING.get(quality_str, 0)

    @staticmethod
    def parse_url(url: str) -> dict:
        """
        Parses a URL and extracts query parameters.

        Args:
            url (str): The URL to parse.

        Returns:
            dict: A dictionary of query parameters.
        """
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        return query_params

    @staticmethod
    def get_params(url: str, params: str) -> str | None:
        """
        Extracts a specific query parameter from a URL.

        Args:
            url (str): The URL to parse.
            params (str): The parameter name to extract.

        Returns:
            str | None: The value of the specified parameter, or None if not found.
        """
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if params in query_params:
            return query_params[params][0]

    async def get_stream_url(self, json_data: dict, video_quality: str, url_type: str = 'm3u8', spec: bool = False,
                             hls_extra_key: str | int | None = None, flv_extra_key: str | int | None = None,
                             platform: str | None = None) -> dict:
        """
        Fetches the stream URL based on the provided data and quality.

        Returns:
            dict: A dictionary containing the stream URL and other relevant information.
        """
        if not json_data['is_live']:
            json_data |= {"platform": platform}
            return json_data

        play_url_list = json_data['play_url_list']
        while len(play_url_list) < 5:
            play_url_list.append(play_url_list[-1])

        video_quality, selected_quality = self.get_quality_index(video_quality)
        data = {
            "platform": platform,
            "anchor_name": json_data.get('anchor_name'),
            "is_live": True,
            "live_url": json_data.get('live_url')
        }

        def get_url(key):
            play_url = play_url_list[selected_quality]
            return play_url[key] if key else play_url

        if url_type == 'all':
            m3u8_url = get_url(hls_extra_key)
            flv_url = get_url(flv_extra_key)
            data |= {
                "m3u8_url": json_data['m3u8_url'] if spec else m3u8_url,
                "flv_url": json_data['flv_url'] if spec else flv_url,
                "record_url": m3u8_url
            }
        elif url_type == 'm3u8':
            m3u8_url = get_url(hls_extra_key)
            data |= {"m3u8_url": json_data['m3u8_url'] if spec else m3u8_url, "record_url": m3u8_url}
        else:
            flv_url = get_url(flv_extra_key)
            data |= {"flv_url": flv_url, "record_url": flv_url}
        data['title'] = json_data.get('title')
        data['quality'] = video_quality
        return data

    @staticmethod
    async def get_play_url_list(m3u8: str, proxy: str | None = None, headers: dict | None = None) -> list[str]:
        """
        Fetches a list of play URLs from an M3U8 file.

        Args:
            m3u8 (str): The URL of the M3U8 file.
            proxy (str | None): The proxy address to use. Defaults to None.
            headers (dict | None): Custom headers for the request. Defaults to None.

        Returns:
            List[str]: A list of play URLs sorted by bandwidth (highest first).
        """
        resp = await async_req(m3u8, proxy_addr=proxy, headers=headers)
        play_url_list = []
        for i in resp.split('\n'):
            if i.startswith('https://'):
                play_url_list.append(i.strip())
        if not play_url_list:
            for i in resp.split('\n'):
                if i.strip().endswith('m3u8'):
                    play_url_list.append(i.strip())
        bandwidth_pattern = re.compile(r'BANDWIDTH=(\d+)')
        bandwidth_list = bandwidth_pattern.findall(resp)
        url_to_bandwidth = {url: int(bandwidth) for bandwidth, url in zip(bandwidth_list, play_url_list)}
        play_url_list = sorted(play_url_list, key=lambda url: url_to_bandwidth[url], reverse=True)
        return play_url_list
