import json
import re

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class LookLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Look live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.pc_headers = self._get_pc_headers()

    def _get_pc_headers(self) -> dict:

        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or '',
        }

    @staticmethod
    def _get_looklive_secret_data(text) -> tuple:
        """
        params: 由两次AES加密完成
        ncSecKey: 由一次自写的加密函数完成，值可固定
        """
        # 本算法参考项目：https://github.com/785415581/MusicBox/blob/b8f716d43d/doc/analysis/analyze_captured_data.md

        modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec' \
                  '4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813' \
                  'cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
        nonce = b'0CoJUm6Qyw8W8jud'
        public_key = '010001'
        import base64
        import binascii
        import secrets

        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        def create_secret_key(size: int) -> bytes:
            charset = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+-=[]{}|;:,.<>?'
            return ''.join(secrets.choice(charset) for _ in range(size)).encode('utf-8')

        def aes_encrypt(_text: str | bytes, _sec_key: str | bytes) -> bytes:
            if isinstance(_text, str):
                _text = _text.encode('utf-8')
            if isinstance(_sec_key, str):
                _sec_key = _sec_key.encode('utf-8')
            _sec_key = _sec_key[:16]  # 16 (AES-128), 24 (AES-192), or 32 (AES-256) bytes
            iv = bytes('0102030405060708', 'utf-8')
            encryptor = AES.new(_sec_key, AES.MODE_CBC, iv)
            padded_text = pad(_text, AES.block_size)
            ciphertext = encryptor.encrypt(padded_text)
            encoded_ciphertext = base64.b64encode(ciphertext)
            return encoded_ciphertext

        def rsa_encrypt(_text: str | bytes, pub_key: str, mod: str) -> str:
            if isinstance(_text, str):
                _text = _text.encode('utf-8')
            text_reversed = _text[::-1]
            text_int = int(binascii.hexlify(text_reversed), 16)
            encrypted_int = pow(text_int, int(pub_key, 16), int(mod, 16))
            return format(encrypted_int, 'x').zfill(256)

        sec_key = create_secret_key(16)
        enc_text = aes_encrypt(aes_encrypt(json.dumps(text), nonce), sec_key)
        enc_sec_key = rsa_encrypt(sec_key, public_key, modulus)
        return enc_text.decode(), enc_sec_key

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """

        room_id = re.search('live\\?id=(.*?)&', url).group(1)
        params, secretkey = self._get_looklive_secret_data({"liveRoomNo": room_id})
        request_data = {'params': params, 'encSecKey': secretkey}
        api = 'https://api.look.163.com/weapi/livestream/room/get/v3'
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.pc_headers, data=request_data)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        anchor_name = json_data['data']['anchor']['nickName']
        live_status = json_data['data']['liveStatus']
        result = {"anchor_name": anchor_name, "is_live": False}
        if live_status == 1:
            result["is_live"] = True
            if json_data['data']['roomInfo']['liveType'] != 1:
                play_url_list = json_data['data']['roomInfo']['liveUrl']
                live_title = json_data['data']['roomInfo']['title']
                result |= {
                    "title": live_title,
                    "flv_url": play_url_list['httpPullUrl'],
                    "m3u8_url": play_url_list['hlsPullUrl'],
                    "record_url": play_url_list['hlsPullUrl'],
                }
        return result

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live room and wraps it into a StreamData object.
        """
        json_data |= {"platform": "Look"}
        return wrap_stream(json_data)
