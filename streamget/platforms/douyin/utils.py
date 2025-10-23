import re
import urllib.parse

import execjs
import httpx

from ... import JS_SCRIPT_PATH, utils


class UnsupportedUrlError(Exception):
    pass


class DouyinUtils:
    HEADERS = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
        'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'cookie': 's_v_web_id=verify_lk07kv74_QZYCUApD_xhiB_405x_Ax51_GYO9bUIyZQVf'
    }

    HEADERS_PC = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'cookie': 'sessionid=7494ae59ae06784454373ce25761e864; __ac_nonce=0670497840077ee4c9eb2; '
                  '__ac_signature=_02B4Z6wo00f012DZczQAAIDCJJBb3EjnINdg-XeAAL8-db;  '
                  's_v_web_id=verify_m1ztgtjj_vuHnMLZD_iwZ9_4YO4_BdN1_7wLP3pyqXsf2; '
    }

    @staticmethod
    async def get_xbogus(url: str, headers: dict | None = None) -> str | None:
        if not headers or 'user-agent' not in (k.lower() for k in headers):
            headers = DouyinUtils.HEADERS
        query = urllib.parse.urlparse(url).query
        try:
            with open(f'{JS_SCRIPT_PATH}/x-bogus.js') as f:
                js_code = f.read()
            xbogus = execjs.compile(js_code).call('sign', query, headers.get("User-Agent") or headers.get("user-agent"))
            return xbogus
        except execjs.ProgramError:
            raise execjs.ProgramError('Failed to execute JS code. Please check if the Node.js environment')

    @staticmethod
    async def get_sec_user_id(url: str, proxy_addr: str | None = None, headers: dict | None = None) -> tuple | None:
        if not headers or all(k.lower() not in ['user-agent', 'cookie'] for k in headers):
            headers = DouyinUtils.HEADERS

        try:
            proxy_addr = utils.handle_proxy_addr(proxy_addr)
            async with httpx.AsyncClient(proxy=proxy_addr, timeout=15) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                redirect_url = response.url
                if 'reflow/' in str(redirect_url):
                    match = re.search(r'sec_user_id=([\w_\-]+)&', str(redirect_url))
                    if match:
                        sec_user_id = match.group(1)
                        room_id = str(redirect_url).split('?')[0].rsplit('/', maxsplit=1)[1]
                        return room_id, sec_user_id
                    else:
                        raise RuntimeError("Could not find sec_user_id in the URL.")
                else:
                    raise UnsupportedUrlError("The redirect URL does not contain 'reflow/'.")
        except UnsupportedUrlError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"An error occurred: {e}")
        return None

    @staticmethod
    async def get_unique_id(url: str, proxy_addr: str | None = None, headers: dict | None = None) -> str | None:
        """Get unique_id from user profile"""
        if not headers or all(k.lower() not in ['user-agent', 'cookie'] for k in headers):
            headers = DouyinUtils.HEADERS

        try:
            proxy_addr = utils.handle_proxy_addr(proxy_addr)
            async with httpx.AsyncClient(proxy=proxy_addr, timeout=15) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                redirect_url = str(response.url)
                if 'reflow/' in str(redirect_url):
                    raise UnsupportedUrlError("Unsupported URL")

                sec_user_id = redirect_url.split('?')[0].rsplit('/', maxsplit=1)[1]

                headers['cookie'] = ('ttwid=1%7C4ejCkU2bKY76IySQENJwvGhg1IQZrgGEupSyTKKfuyk%7C1740470403%7Cbc9a'
                                     'd2ee341f1a162f9e27f4641778030d1ae91e31f9df6553a8f2efa3bdb7b4; __ac_nonce=06'
                                     '83e59f3009cc48fbab0; __ac_signature=_02B4Z6wo00f01mG6waQAAIDB9JUCzFb6.TZhmsU'
                                     'AAPBf34; __ac_referer=__ac_blank')
                profile_response = await client.get(f'https://www.iesdouyin.com/share/user/{sec_user_id}',
                                                    headers=headers, follow_redirects=True)
                matches = re.findall(r'unique_id":"(.*?)","verification_type', profile_response.text)

                if matches:
                    unique_id = matches[-1]
                    return unique_id
                else:
                    raise RuntimeError("Could not find unique_id in the response.")

        except UnsupportedUrlError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"An error occurred: {e}")
        return None

    @staticmethod
    async def get_live_room_id(room_id: str, sec_user_id: str, proxy_addr: str | None = None,
                               params: dict | None = None,
                               headers: dict | None = None) -> str:
        if not headers or all(k.lower() not in ['user-agent', 'cookie'] for k in headers):
            headers = DouyinUtils.HEADERS

        if not params:
            params = {
                "verifyFp": "verify_lk07kv74_QZYCUApD_xhiB_405x_Ax51_GYO9bUIyZQVf",
                "type_id": "0",
                "live_id": "1",
                "room_id": room_id,
                "sec_user_id": sec_user_id,
                "app_id": "1128",
                "msToken": "wrqzbEaTlsxt52-vxyZo_mIoL0RjNi1ZdDe7gzEGMUTVh_HvmbLLkQrA_1HKVOa2C6gkxb6IiY6TY2z8enAkPEwGq--"
                           "gM-me3Yudck2ailla5Q4osnYIHxd9dI4WtQ==",
            }

        api = f'https://webcast.amemv.com/webcast/room/reflow/info/?{urllib.parse.urlencode(params)}'
        xbogus = await DouyinUtils.get_xbogus(api)
        api = api + "&X-Bogus=" + xbogus

        try:
            proxy_addr = utils.handle_proxy_addr(proxy_addr)
            async with httpx.AsyncClient(proxy=proxy_addr, timeout=15) as client:
                response = await client.get(api, headers=headers)
                response.raise_for_status()
                json_data = response.json()
                return json_data['data']['room']['owner']['web_rid']
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP status error occurred: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"An exception occurred during get_live_room_id: {e}")
