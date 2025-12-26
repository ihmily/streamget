import asyncio
import hashlib
import re
import time

import httpx

from ...data import StreamData, wrap_stream
from ..base import BaseLiveStream


class DouyuLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Douyu live stream information.
    """
    DEFAULT_DID = "10000000000000000000000000001501"
    WEB_DOMAIN = "www.douyu.com"
    PLAY_DOMAIN = "playweb.douyucdn.cn"
    MOBILE_DOMAIN = "m.douyu.com"

    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.client: httpx.AsyncClient | None = None
        self.white_encrypt_key: dict = {}
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            transport = httpx.AsyncHTTPTransport(proxy=self.proxy_addr) if self.proxy_addr else None
            self.client = httpx.AsyncClient(timeout=30.0, transport=transport)
        return self.client

    async def _update_white_key(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(
                f"https://{self.WEB_DOMAIN}/wgapi/livenc/liveweb/websec/getEncryption",
                params={"did": self.DEFAULT_DID},
                headers={"User-Agent": self.user_agent},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error") != 0:
                return False
            self.white_encrypt_key = data["data"]
            self.white_encrypt_key["cpp"]["expire_at"] = int(time.time()) + 86400
            return True
        except Exception:
            return False

    async def _is_key_valid(self) -> bool:
        return (
            bool(self.white_encrypt_key)
            and self.white_encrypt_key.get("cpp", {}).get("expire_at", 0) > int(time.time())
        )

    async def _get_sign(self, rid: str) -> dict:
        for _ in range(3):
            if not await self._is_key_valid():
                if not await self._update_white_key():
                    continue
            break
        else:
            raise RuntimeError("无法获取有效白名单密钥")

        ts = int(time.time())
        rand_str = self.white_encrypt_key["rand_str"]
        enc_time = self.white_encrypt_key["enc_time"]
        key = self.white_encrypt_key["key"]
        is_special = self.white_encrypt_key["is_special"]

        secret = rand_str
        salt = "" if is_special else f"{rid}{ts}"
        for _ in range(enc_time):
            secret = hashlib.md5(f"{secret}{key}".encode()).hexdigest()
        auth = hashlib.md5(f"{secret}{key}{salt}".encode()).hexdigest()

        key_data = {k: v for k, v in self.white_encrypt_key.items() if k != "cpp"}

        return {"key": key_data, "auth": auth, "ts": ts}

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        client = await self._get_client()

        rid_match = re.search(r'douyu\.com/(\d+)', url) or re.search(r'rid=(\d+)', url)
        if rid_match:
            rid = rid_match.group(1)
        else:
            path = url.split("douyu.com/")[1].split("?")[0].split("/")[0]
            resp = await client.get(f"https://{self.MOBILE_DOMAIN}/{path}")
            rid = re.search(r'"rid":(\d+)', resp.text).group(1)

        resp = await client.get(f"https://{self.WEB_DOMAIN}/betard/{rid}")
        json_data = resp.json()["room"]

        if not process_data:
            return json_data

        is_live = json_data["show_status"] == 1 and json_data["videoLoop"] == 0
        title = f"录播 {json_data['room_name']}" if not is_live else json_data["room_name"]

        result = {
            "anchor_name": json_data["nickname"],
            "is_live": is_live,
            "live_url": url,
            "room_id": json_data["room_id"],
            "title": title.replace('&nbsp;', ' ').strip(),
        }
        return result

    async def fetch_stream_url(
            self, json_data: dict, video_quality: str | int | None = None, cdn: str | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        platform = '斗鱼直播'
        rid = str(json_data["room_id"])
        json_data.pop("room_id", None)

        video_quality_options = {
            "OD": '0',
            "BD": '0',
            "UHD": '3',
            "HD": '2',
            "SD": '1',
            "LD": '1'
        }

        if not video_quality:
            video_quality = "OD"
        else:
            if str(video_quality).isdigit():
                video_quality = list(video_quality_options.keys())[int(video_quality)]
            else:
                video_quality = video_quality.upper()

        rate = video_quality_options.get(video_quality, '0')

        client = await self._get_client()
        headers = {
            "Referer": f"https://{self.WEB_DOMAIN}/",
            "Origin": f"https://{self.WEB_DOMAIN}",
            "User-Agent": self.user_agent,
        }

        base_params = {
            "rate": rate,
            "ver": "219032101",
            "iar": "0",
            "ive": "0",
            "rid": rid,
            "hevc": "0",
            "fa": "0",
            "sov": "0",
        }

        flv_url_list = []

        async def fetch_for_cdn(cdn_name: str | None = None):
            current_params = base_params.copy()
            if cdn_name:
                current_params["cdn"] = cdn_name

            for attempt in range(3):
                try:
                    sign_data = await self._get_sign(rid)
                    params = current_params.copy()
                    params.update({
                        "enc_data": sign_data["key"]["enc_data"],
                        "tt": sign_data["ts"],
                        "did": self.DEFAULT_DID,
                        "auth": sign_data["auth"],
                    })

                    url = f"https://{self.PLAY_DOMAIN}/lapi/live/getH5PlayV1/{rid}"
                    resp = await client.post(url, headers=headers, params=params, data=params)
                    resp.raise_for_status()
                    data = resp.json()

                    if data.get("error") != 0:
                        raise ValueError(data.get("msg", "API error"))

                    play_info = data["data"]
                    raw_url = f"{play_info['rtmp_url']}/{play_info['rtmp_live']}"

                    if raw_url not in flv_url_list:
                        flv_url_list.append(raw_url)

                    return play_info

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        await self._update_white_key()
                    else:
                        break
                except Exception:
                    break
            return None

        main_play_info = await fetch_for_cdn(None)

        if not main_play_info:
            if self.client:
                await self.client.aclose()
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': None,
                'record_url': None,
                'extra': {'backup_url_list': []}
            }
            return wrap_stream(json_data)

        if cdn and main_play_info.get('rtmp_cdn') != cdn:
            await fetch_for_cdn(cdn)

        cdns_with_name = main_play_info.get('cdnsWithName', [])
        default_cdn = main_play_info.get('rtmp_cdn')

        other_cdn_tasks = [
            fetch_for_cdn(item['cdn'])
            for item in cdns_with_name
            if item['cdn'] != default_cdn and (cdn is None or item['cdn'] != cdn)
        ]

        if other_cdn_tasks:
            await asyncio.gather(*other_cdn_tasks, return_exceptions=True)

        main_url = flv_url_list[0]
        backup_urls = flv_url_list[1:] if len(flv_url_list) > 1 else []

        json_data |= {
            "platform": platform,
            'quality': video_quality,
            'flv_url': main_url,
            'record_url': main_url,
            'extra': {'backup_url_list': backup_urls}
        }

        if self.client:
            await self.client.aclose()

        return wrap_stream(json_data)
