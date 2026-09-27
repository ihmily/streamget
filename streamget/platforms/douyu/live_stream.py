import base64
import json
import random
import re
import time
from urllib.parse import parse_qsl, urlencode, urlparse

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream
from .douyu_signature import DEFAULT_DEVICE_ID, amd, csign, header_auth

DOUYU_HUOS_DOMAIN = "openflv-huos.douyucdn2.cn"
DOUYU_P2P_DOMAIN_TCT = "hdltctwk.douyucdn.cn"
DOUYU_P2PSDK_APIS = (
    "https://sdkapiv4.douyucdn.cn",
    "https://sdkapi.douyucdn.cn",
)
PLAY_CLIENT_DOMAIN = "playclient.douyucdn.cn"
ANDROID_APP_VERSION = "8.2.2.0"

WS_EXPIRE_OVERRIDE = "&expire=0"


def _trim_end_matches(s: str, suffix: str) -> str:
    if not suffix:
        return s
    while s.endswith(suffix):
        s = s[: -len(suffix)]
    return s


def _random_android_device() -> str:
    def letter() -> str:
        return chr(ord("A") + random.randint(0, 25))

    return (
        f"{letter()}{letter()}{letter()}-"
        f"{letter()}{letter()}{random.randint(0, 9)}{random.randint(0, 9)}"
    )


def _is_wangsu_stream(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = parsed.hostname or ""
    if host.startswith("ws") and (
        host.endswith(".douyucdn.cn") or host.endswith(".douyucdn2.cn")
    ):
        return True
    return any(
        k == "fcdn" and v == "ws"
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
    )


def _ws_expire_needs_override(url: str) -> bool:
    if not _is_wangsu_stream(url):
        return False
    pairs = parse_qsl(urlparse(url).query, keep_blank_values=True)
    expires = [v for k, v in pairs if k == "expire"]
    return len(expires) == 1 and expires[0] != "0"


def _with_ws_expire_override(url: str) -> str:
    if _ws_expire_needs_override(url):
        return url + WS_EXPIRE_OVERRIDE
    return url


def _parse_stream_url(url: str) -> tuple[str, list[tuple[str, str]]]:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        raise RuntimeError("斗鱼 huos 源链接缺少 stream_id")
    stream_name = parts[-1]
    stream_id = stream_name.split(".", 1)[0]
    if not stream_id:
        raise RuntimeError("斗鱼 huos 源链接 stream_id 为空")
    return stream_id, parse_qsl(parsed.query, keep_blank_values=True)


def _build_huos_url(
    stream_id: str,
    params: list[tuple[str, str]],
    tx_secret: dict,
) -> str:
    next_params: list[tuple[str, str]] = []
    has_fcdn = False

    for key, value in params:
        if key in ("txSecret", "txTime", "domain"):
            continue
        if key == "fcdn":
            if not has_fcdn:
                next_params.append((key, "hs"))
                has_fcdn = True
            continue
        next_params.append((key, value))

    if not has_fcdn:
        next_params.append(("fcdn", "hs"))
    next_params.append(("txSecret", tx_secret["tx_secret"]))
    next_params.append(("txTime", tx_secret["tx_time"]))
    next_params.append(("domain", DOUYU_P2P_DOMAIN_TCT))

    clean_stream_id = re.sub(r'_\d+$', '', stream_id)

    return f"http://{DOUYU_HUOS_DOMAIN}/live/{clean_stream_id}.xs?{urlencode(next_params)}"


class DouyuLiveStream(BaseLiveStream):
    WEB_DOMAIN = "www.douyu.com"
    MOBILE_DOMAIN = "m.douyu.com"

    APP_CDN = "hs-h5"
    FORCE_HS = True

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.base_headers = {
            'user-agent': self.USER_AGENT,
            'referer': f'https://{self.WEB_DOMAIN}/',
        }
        if cookies:
            self.base_headers['cookie'] = cookies

    async def get_room_id(self, url):
        match_rid = re.search('douyu.com/(\\d+)', url) or re.search('rid=(\\d+)', url)
        if match_rid:
            rid = match_rid.group(1)
        else:
            path = url.split("douyu.com/")[1].split("?")[0].split("/")[0]
            html_str = await async_req(
                url=f'https://{self.MOBILE_DOMAIN}/{path}',
                proxy_addr=self.proxy_addr,
                headers=self.base_headers
            )
            rid = re.search('"rid":(\\d+)', html_str).group(1)
        return rid

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        rid = await self.get_room_id(url)

        json_str = await async_req(
            url=f'https://{self.WEB_DOMAIN}/betard/{rid}',
            proxy_addr=self.proxy_addr,
            headers=self.base_headers
        )
        json_data = json.loads(json_str)['room']

        if not process_data:
            return json_data

        raw_title = json_data['room_name'].replace('&nbsp;', ' ').strip()
        has_content = json_data['show_status'] == 1
        is_loop = json_data['videoLoop'] == 1
        is_live = has_content
        title = f"【轮播】{raw_title}" if is_loop else raw_title

        result = {
            "anchor_name": json_data['nickname'],
            "is_live": is_live,
            "live_url": url,
            "room_id": json_data['room_id'],
            "title": title,
        }
        return result

    async def _fetch_web_stream_url(self, rid: str, rate: str = '-1', cdn: str | None = None) -> dict:
        try:
            room_number = int(rid)
        except (TypeError, ValueError):
            return {'error': -1, 'msg': '斗鱼房间号无效', 'data': None}

        device_id = DEFAULT_DEVICE_ID
        path = f"/lapi/live/appGetPlayer/stream/{rid}"
        timestamp = int(time.time())
        device = _random_android_device()

        rate_value = '0' if rate in (None, '', '-1') else str(rate)
        effective_cdn = _trim_end_matches(cdn or self.APP_CDN, '-h5') or 'hs'

        params: dict[str, str] = {
            'txdw': '0',
            'cdn': effective_cdn,
            'token': '',
            'rate': rate_value,
            'hevc': '1',
            'ilow': '0',
            'iar': '0',
            'net': 'WIFI',
            'device': device,
        }

        csign_value = csign(room_number, device_id, timestamp, params)
        amd_value = amd(csign_value, device_id)
        params['csign'] = csign_value
        params['cptl'] = '0103'
        params['amd'] = amd_value
        params['client_sys'] = 'android'

        auth = header_auth(path, timestamp, 'android1', params)

        user_device = base64.standard_b64encode(
            f"{device_id}|v{ANDROID_APP_VERSION}".encode()
        ).decode()

        query = urlencode(sorted(params.items()))
        url = f"https://{PLAY_CLIENT_DOMAIN}{path}?{query}"

        headers = {
            'User-Device': user_device,
            'aid': 'android1',
            'channel': '447',
            'User-Agent': f"android/{ANDROID_APP_VERSION} (android 16; ; {device})",
            'time': str(timestamp),
            'auth': auth,
            'Cookie': f'acf_did={device_id}',
        }

        try:
            body = await async_req(
                url=url,
                proxy_addr=self.proxy_addr,
                headers=headers,
            )
        except Exception as err:
            return {'error': -1, 'msg': f'请求斗鱼播放信息失败: {err}', 'data': None}

        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, TypeError) as err:
            return {'error': -1, 'msg': f'解析斗鱼播放信息失败: {err}', 'data': None}

        if parsed.get('error', 0) != 0:
            return {
                'error': parsed.get('error', -1),
                'msg': parsed.get('msg', '') or '',
                'data': None,
            }

        play_info = parsed.get('data')
        if not isinstance(play_info, dict):
            return {'error': -1, 'msg': '斗鱼播放信息缺少 data', 'data': None}

        return {
            'error': 0,
            'msg': '',
            'data': {
                'rtmp_url': play_info.get('rtmp_url', ''),
                'rtmp_live': play_info.get('rtmp_live', ''),
            },
        }

    async def _apply_stream_transforms(self, url: str, cdn: str | None = None) -> str:
        effective_cdn = cdn or self.APP_CDN
        if self.FORCE_HS and effective_cdn == self.APP_CDN:
            url = await self._maybe_build_huos_url(url)
        return _with_ws_expire_override(url)

    async def _maybe_build_huos_url(self, raw_stream_url: str) -> str:
        try:
            stream_id, params = _parse_stream_url(raw_stream_url)
            tx_secret = await self._get_txsecret(stream_id)
            return _build_huos_url(stream_id, params, tx_secret)
        except Exception:
            return raw_stream_url

    async def _get_txsecret(self, stream_id: str) -> dict:
        apis = list(DOUYU_P2PSDK_APIS)
        random.shuffle(apis)

        last_error: Exception | None = None
        for api in apis:
            try:
                return await self._request_txsecret(api, stream_id)
            except Exception as err:
                last_error = err

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"获取 txSecret 失败: {stream_id}")

    async def _request_txsecret(self, api: str, stream_id: str) -> dict:
        try:
            rsp_text = await async_req(
                url=f"{api}/p2p/get_txsecret?lid={stream_id}",
                proxy_addr=self.proxy_addr,
                headers={"user-agent": self.USER_AGENT},
            )
            data = json.loads(rsp_text)
        except Exception as err:
            raise RuntimeError(
                f"获取 txSecret 失败 api: {api}, stream_id: {stream_id}: {err}"
            ) from err

        tx_secret = data.get("xp2p_txSecret") or ""
        tx_time = data.get("xp2p_txTime") or ""
        if not tx_secret or not tx_time:
            raise RuntimeError(f"txSecret 为空: {stream_id}")
        return {"tx_secret": tx_secret, "tx_time": tx_time}

    async def fetch_stream_url(
            self, json_data: dict, video_quality: str | int | None = None, cdn: str | None = None) -> StreamData:
        platform = '斗鱼直播'
        rid = str(json_data["room_id"])
        json_data.pop("room_id")

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

        flv_url_list = []

        async def get_url(_rid: str, _rate: str, _cdn: str | None = None):
            _flv_data = await self._fetch_web_stream_url(rid=_rid, rate=_rate, cdn=_cdn)
            if _flv_data.get('error') != 0:
                return
            info = _flv_data.get('data')
            if not info:
                return
            _flv_url = f"{info['rtmp_url']}/{info['rtmp_live']}"
            _flv_url = await self._apply_stream_transforms(_flv_url, _cdn)
            if _flv_url not in flv_url_list:
                flv_url_list.append(_flv_url)
            return _flv_data

        if not json_data['is_live']:
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': None,
                'record_url': None,
                'extra': {'backup_url_list': []}
            }
            return wrap_stream(json_data)

        flv_data = await get_url(_rid=rid, _rate=rate, _cdn=cdn)

        if flv_data and flv_data.get('data'):
            rtmp_cdn = flv_data['data'].get('rtmp_cdn')
            cdn_list = flv_data['data'].get('cdnsWithName', [])

            for item in cdn_list:
                if item['cdn'] != rtmp_cdn:
                    await get_url(_rid=rid, _rate=rate, _cdn=item['cdn'])

        if flv_url_list:
            flv_url = flv_url_list[0]
            flv_url_list.remove(flv_url)
            json_data |= {
                "platform": platform,
                'quality': video_quality,
                'flv_url': flv_url,
                'record_url': flv_url,
                'extra': {'backup_url_list': flv_url_list}
            }

        return wrap_stream(json_data)