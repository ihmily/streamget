import json
import re
import urllib.parse
import uuid

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class SoopLiveStream(BaseLiveStream):
    """
    A class for fetching and processing SOOP live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None,
                 username: str | None = None, password: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.username = username
        self.password = password
        self.pc_headers = self._get_pc_headers()
        self.mobile_headers = self._get_mobile_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://play.sooplive.co.kr',
            'referer': 'https://play.sooplive.co.kr/superbsw123/277837074',
            'cookie': self.cookies or '',
        }

    def _get_mobile_headers(self) -> dict:
        return {
            'client-id': str(uuid.uuid4()),
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, '
                          'like Gecko) Version/18.5 Mobile/15E148 Safari/604.1 Edg/141.0.0.0',
            'cookie': self.cookies or '',
        }

    async def login_sooplive(self) -> str | None:
        if self.username and self.password and len(self.username) < 6 or len(self.password) < 10:
            raise RuntimeError("sooplive login failed! Please enter the correct account and password for the sooplive "
                               "platform in the config.ini file.")

        data = {
            'szWork': 'login',
            'szType': 'json',
            'szUid': self.username,
            'szPassword': self.password,
            'isSaveId': 'true',
            'isSavePw': 'true',
            'isSaveJoin': 'true',
            'isLoginRetain': 'Y',
        }

        url = 'https://login.sooplive.co.kr/app/LoginAction.php'

        try:
            cookie_dict = await async_req(url, proxy_addr=self.proxy_addr, headers=self.pc_headers,
                                          data=data, return_cookies=True, timeout=20)
            self.cookies = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
            self.pc_headers['cookie'] = self.cookies
            return self.cookies
        except Exception as e:
            raise Exception(
                f"sooplive login failed, please check if the account password in the configuration file is correct. {e}"
            )

    async def _get_sooplive_cdn_url(self, broad_no: str) -> dict:
        params = {
            'return_type': 'gcp_cdn',
            'use_cors': 'false',
            'cors_origin_url': 'play.sooplive.co.kr',
            'broad_key': f'{broad_no}-common-master-hls',
            'time': '8361.086329376785',
        }

        url2 = 'http://livestream-manager.sooplive.co.kr/broad_stream_assign.html?' + urllib.parse.urlencode(params)
        json_str = await async_req(url=url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)

        return json_data

    async def get_sooplive_tk(self, url: str, rtype: str) -> str | tuple:
        split_url = url.split('/')
        bj_id = split_url[3] if len(split_url) < 6 else split_url[5]
        room_password = self.get_params(url, "pwd")
        if not room_password:
            room_password = ''
        data = {
            'bid': bj_id,
            'bno': '',
            'type': rtype,
            'pwd': room_password,
            'player_type': 'html5',
            'stream_type': 'common',
            'quality': 'master',
            'mode': 'landing',
            'from_api': '0',
            'is_revive': 'false',
        }

        url2 = f'https://live.sooplive.co.kr/afreeca/player_live_api.php?bjid={bj_id}'
        json_str = await async_req(url=url2, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data)
        json_data = json.loads(json_str)

        if rtype == 'aid':
            token = json_data["CHANNEL"]["AID"]
            return token
        else:
            bj_name = json_data['CHANNEL']['BJNICK']
            bj_id = json_data['CHANNEL']['BJID']
            return f"{bj_name}-{bj_id}", json_data['CHANNEL']['BNO']

    async def _get_soop_channel_info_global(self, bj_id) -> str:
        api = 'https://api.sooplive.com/v2/channel/info/' + str(bj_id)
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        nickname = json_data['data']['streamerChannelInfo']['nickname']
        channelId = json_data['data']['streamerChannelInfo']['channelId']
        anchor_name = f"{nickname}-{channelId}"
        return anchor_name

    async def _get_soop_stream_info_global(self, bj_id) -> tuple:
        api = 'https://api.sooplive.com/v2/stream/info/' + str(bj_id)
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.mobile_headers)
        json_data = json.loads(json_str)
        status = json_data['data']['isStream']
        title = json_data['data']['title']
        return status, title

    async def _fetch_web_stream_data_global(self, url: str, process_data: bool = True) -> dict:
        split_url = url.split('/')
        bj_id = split_url[3] if len(split_url) < 6 else split_url[5]
        anchor_name = await self._get_soop_channel_info_global(bj_id)
        result = {"anchor_name": anchor_name or '', "is_live": False, "live_url": url}
        status, title = await self._get_soop_stream_info_global(bj_id)
        if not status:
            return result
        else:
            async def _get_url_list(m3u8: str) -> list[str]:
                headers = {
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
                }
                resp = await async_req(url=m3u8, proxy_addr=self.proxy_addr, headers=headers)
                play_url_list = []
                url_prefix = '/'.join(m3u8.split('/')[0:3])
                for i in resp.split('\n'):
                    if not i.startswith('#') and i.strip():
                        play_url_list.append(url_prefix + i.strip())
                bandwidth_pattern = re.compile(r'BANDWIDTH=(\d+)')
                bandwidth_list = bandwidth_pattern.findall(resp)
                url_to_bandwidth = {purl: int(bandwidth) for bandwidth, purl in zip(bandwidth_list, play_url_list)}
                play_url_list = sorted(play_url_list, key=lambda purl: url_to_bandwidth[purl], reverse=True)
                return play_url_list

            m3u8_url = 'https://global-media.sooplive.com/live/' + str(bj_id) + '/master.m3u8'
            result |= {
                'is_live': True,
                'title': title,
                'm3u8_url': m3u8_url,
                'play_url_list': await _get_url_list(m3u8_url)
            }
        return result

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """

        if "sooplive.com" in url:
            return await self._fetch_web_stream_data_global(url, process_data)

        split_url = url.split('/')
        bj_id = split_url[3] if len(split_url) < 6 else split_url[5]

        data = {
            'bj_id': bj_id,
            'broad_no': '',
            'agent': 'web',
            'confirm_adult': 'true',
            'player_type': 'webm',
            'mode': 'live',
        }

        url2 = 'http://api.m.sooplive.co.kr/broad/a/watch'

        json_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=data)
        json_data = json.loads(json_str)

        if 'user_nick' in json_data['data']:
            anchor_name = json_data['data']['user_nick']
            if "bj_id" in json_data['data']:
                anchor_name = f"{anchor_name}-{json_data['data']['bj_id']}"
        else:
            anchor_name = ''

        result = {"anchor_name": anchor_name or '', "is_live": False, "live_url": url}

        async def get_url_list(m3u8: str) -> list[str]:
            resp = await async_req(url=m3u8, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            play_url_list = []
            url_prefix = m3u8.rsplit('/', maxsplit=1)[0] + '/'
            for i in resp.split('\n'):
                if i.startswith('auth_playlist'):
                    play_url_list.append(url_prefix + i.strip())
            bandwidth_pattern = re.compile(r'BANDWIDTH=(\d+)')
            bandwidth_list = bandwidth_pattern.findall(resp)
            url_to_bandwidth = {purl: int(bandwidth) for bandwidth, purl in zip(bandwidth_list, play_url_list)}
            play_url_list = sorted(play_url_list, key=lambda purl: url_to_bandwidth[purl], reverse=True)
            return play_url_list

        if not anchor_name:
            async def handle_login() -> str | None:
                cookie = await self.login_sooplive()
                if 'AuthTicket=' in cookie:
                    # print("sooplive platform login successful! Starting to fetch live streaming data...")
                    return cookie

            async def fetch_data(cookie, _result) -> dict:
                aid_token = await self.get_sooplive_tk(url, rtype='aid')
                _anchor_name, _broad_no = await self.get_sooplive_tk(url, rtype='info')
                _view_url_data = await self._get_sooplive_cdn_url(_broad_no)
                _view_url = _view_url_data['view_url']
                _m3u8_url = _view_url + '?aid=' + aid_token
                _result |= {
                    "anchor_name": _anchor_name,
                    "is_live": True,
                    "m3u8_url": _m3u8_url,
                    'play_url_list': await get_url_list(_m3u8_url),
                    'new_cookies': cookie
                }
                return _result

            if json_data['data']['code'] == -3001:
                raise Exception("sooplive live stream failed to retrieve, the live stream just ended.")

            elif json_data['data']['code'] == -3002:
                # print("sooplive live stream retrieval failed, the live needs 19+, you are not logged in.")
                # print("Attempting to log in to the sooplive live streaming platform with your account and password, "
                #       "please ensure it is configured.")
                new_cookie = await handle_login()
                if new_cookie and len(new_cookie) > 0:
                    return await fetch_data(new_cookie, result)
                raise RuntimeError("sooplive login failed, please check if the account and password are correct")

            elif json_data['data']['code'] == -3004:
                if self.cookies and len(self.cookies) > 0:
                    return await fetch_data(self.cookies, result)
                else:
                    raise RuntimeError("sooplive login failed, please check if the account and password are correct")
            elif json_data['data']['code'] == -6001:
                raise Exception("error message：Please check if the input sooplive live room address is correct.")

        if json_data['result'] == 1 and anchor_name:
            broad_no = json_data['data']['broad_no']
            broad_title = json_data['data']['broad_title']
            hls_authentication_key = json_data['data']['hls_authentication_key']
            view_url_data = await self._get_sooplive_cdn_url(broad_no)
            view_url = view_url_data['view_url']
            m3u8_url = view_url + '?aid=' + hls_authentication_key
            result |= {
                'is_live': True,
                'title': broad_title,
                'm3u8_url': m3u8_url,
                'play_url_list': await get_url_list(m3u8_url)
            }
        result['new_cookies'] = None
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        data = await self.get_stream_url(json_data, video_quality, platform='SOOP', spec=True)
        return wrap_stream(data)
