import json
import re

import httpx

from ... import utils
from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class PopkonTVLiveStream(BaseLiveStream):
    """
    A class for fetching and processing PopkonTV live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None, username: str | None = None,
                 password: str | None = None, access_token: str | None = None, partner_code: str | None = 'P-00001'):
        super().__init__(proxy_addr, cookies)
        self.username = username
        self.password = password
        self.access_token = access_token
        self.partner_code = partner_code
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'clientKey': 'Client FpAhe6mh8Qtz116OENBmRddbYVirNKasktdXQiuHfm88zRaFydTsFy63tzkdZY0u',
            'content-type': 'application/json',
            'origin': 'https://www.popkontv.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'cookie': self.cookies or '',
        }

    async def _get_room_info(self, url: str) -> tuple:
        if 'mcid' in url:
            anchor_id = re.search('mcid=(.*?)&', url).group(1)
        else:
            anchor_id = re.search('castId=(.*?)(?=&|$)', url).group(1)

        data = {
            'partnerCode': self.partner_code,
            'searchKeyword': anchor_id,
            'signId': self.username,
        }

        api = 'https://www.popkontv.com/api/proxy/broadcast/v1/search/all'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers, json_data=data)
        json_data = json.loads(json_str)

        partner_code = ''
        anchor_name = 'Unknown'
        for item in json_data['data']['broadCastList']:
            if item['mcSignId'] == anchor_id:
                mc_name = item['nickName']
                anchor_name = f"{mc_name}-{anchor_id}"
                partner_code = item['mcPartnerCode']
                break

        if not partner_code:
            if 'mcPartnerCode' in url:
                regex_result = re.search('mcPartnerCode=(P-\\d+)', url)
            else:
                regex_result = re.search('partnerCode=(P-\\d+)', url)
            partner_code = regex_result.group(1) if regex_result else self.partner_code
            notices_url = f'https://www.popkontv.com/channel/notices?mcid={anchor_id}&mcPartnerCode={partner_code}'
            notices_response = await async_req(notices_url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
            mc_name_match = re.search(r'"mcNickName":"([^"]+)"', notices_response)
            mc_name = mc_name_match.group(1) if mc_name_match else 'Unknown'
            anchor_name = f"{anchor_id}-{mc_name}"

        live_url = f"https://www.popkontv.com/live/view?castId={anchor_id}&partnerCode={partner_code}"
        html_str2 = await async_req(live_url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_str2 = re.search('<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_str2).group(1)
        json_data2 = json.loads(json_str2)
        if 'mcData' in json_data2['props']['pageProps']:
            room_data = json_data2['props']['pageProps']['mcData']['data']
            is_private = room_data['mc_isPrivate']
            cast_start_date_code = room_data['mc_castStartDate']
            mc_sign_id = room_data['mc_signId']
            cast_type = room_data['castType']
            return anchor_name, [cast_start_date_code, partner_code, mc_sign_id, cast_type, is_private]
        else:
            return anchor_name, None

    async def login_popkontv(self) -> tuple:
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Authorization': 'Basic FpAhe6mh8Qtz116OENBmRddbYVirNKasktdXQiuHfm88zRaFydTsFy63tzkdZY0u',
            'Content-Type': 'application/json',
            'Origin': 'https://www.popkontv.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        }

        data = {
            'partnerCode': self.partner_code,
            'signId': self.username,
            'signPwd': self.password,
        }

        url = 'https://www.popkontv.com/api/proxy/member/v1/login'

        try:
            proxy_addr = utils.handle_proxy_addr(self.proxy_addr)
            async with httpx.AsyncClient(proxy=proxy_addr, timeout=20, verify=False) as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()

                json_data = response.json()
                login_status_code = json_data.get("statusCd")

                if login_status_code == 'E4010':
                    raise Exception("popkontv login failed, please reconfigure the correct login account or password!")
                elif login_status_code == 'S2000':
                    token = json_data['data'].get("token")
                    partner_code = json_data['data'].get("partnerCode")
                    return token, partner_code
                else:
                    raise Exception(f"popkontv login failed, {json_data.get('statusMsg', 'unknown error')}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP status error occurred during login: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"An exception occurred during popkontv login: {e}")

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        anchor_name, room_info = await self._get_room_info(url)
        result = {"anchor_name": anchor_name, "is_live": False}
        new_token = None
        if room_info:
            cast_start_date_code, cast_partner_code, mc_sign_id, cast_type, is_private = room_info
            result["is_live"] = True
            room_password = self.get_params(url, "pwd")
            if int(is_private) != 0 and not room_password:
                raise RuntimeError(f"Failed to retrieve live room data because {anchor_name}'s room is a private room. "
                                   f"Please configure the room password and try again.")

            async def fetch_data(code: str | None = None) -> str:
                data = {
                    'androidStore': 0,
                    'castCode': f'{mc_sign_id}-{cast_start_date_code}',
                    'castPartnerCode': cast_partner_code,
                    'castSignId': mc_sign_id,
                    'castType': cast_type,
                    'commandType': 0,
                    'exePath': 5,
                    'isSecret': is_private,
                    'partnerCode': code,
                    'password': room_password,
                    'signId': self.username,
                    'version': '4.6.2',
                }
                play_api = 'https://www.popkontv.com/api/proxy/broadcast/v1/castwatchonoff'
                return await async_req(play_api, proxy_addr=self.proxy_addr, json_data=data)

            json_str = await fetch_data(self.partner_code)

            if 'HTTP Error 400' in json_str or 'statusCd":"E5000' in json_str:

                if len(self.username) < 4 or len(self.password) < 10:
                    raise RuntimeError("popkontv login failed! Please enter the correct account and password for the "
                                       "popkontv platform in the config.ini file.")
                # print("Logging into popkontv platform...")
                new_access_token, new_partner_code = await self.login_popkontv()
                if new_access_token and len(new_access_token) == 640:
                    # print("Logged into popkontv platform successfully! Starting to fetch live streaming data...")
                    self.pc_headers['Authorization'] = f'Bearer {new_access_token}'
                    new_token = f'Bearer {new_access_token}'
                    json_str = await fetch_data(new_partner_code)
                else:
                    raise RuntimeError("popkontv login failed, please check if the account and password are correct")
            json_data = json.loads(json_str)
            status_msg = json_data["statusMsg"]
            if json_data['statusCd'] == "L000A":
                # print("Failed to retrieve live stream source,", status_msg)
                raise RuntimeError("You are an unverified member. After logging into the popkontv official website, "
                                   "please verify your mobile phone at the bottom of the 'My Page' > 'Edit My "
                                   "Information' to use the service.")
            elif json_data['statusCd'] == "L0001":
                cast_start_date_code = int(cast_start_date_code) - 1
                json_str = await fetch_data(self.partner_code)
                json_data = json.loads(json_str)
                m3u8_url = json_data['data']['castHlsUrl']
                result |= {"m3u8_url": m3u8_url, "record_url": m3u8_url}
            elif json_data['statusCd'] == "L0000":
                m3u8_url = json_data['data']['castHlsUrl']
                result |= {"m3u8_url": m3u8_url, "record_url": m3u8_url}
            else:
                raise RuntimeError("Failed to retrieve live stream source,", status_msg)
            if not process_data:
                return json_data
        result['new_token'] = new_token
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str = 'OD') -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "PopkonTV"}
        return wrap_stream(json_data)
