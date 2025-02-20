import os
import sys
from pathlib import Path
from .node_setup import check_node
from .__version__ import __description__, __title__, __version__

current_file_path = Path(__file__).resolve()
current_dir = current_file_path.parent
JS_SCRIPT_PATH = current_dir / 'js'

execute_dir = os.path.split(os.path.realpath(sys.argv[0]))[0]
node_execute_dir = Path(current_dir) / 'node'
current_env_path = os.environ.get('PATH')
os.environ['PATH'] = str(node_execute_dir) + os.pathsep + current_env_path

from .data import StreamData
from .platforms.douyin.live_stream import DouyinLiveStream
from .platforms.tiktok.live_stream import TikTokLiveStream
from .platforms.kuaishou.live_stream import KwaiLiveStream
from .platforms.huya.live_stream import HuyaLiveStream
from .platforms.douyu.live_stream import DouyuLiveStream
from .platforms.yy.live_stream import YYLiveStream
from .platforms.bilibili.live_stream import BilibiliLiveStream
from .platforms.rednote.live_stream import RedNoteLiveStream
from .platforms.bigo.live_stream import BigoLiveStream
from .platforms.blued.live_stream import BluedLiveStream
from .platforms.soop.live_stream import SoopLiveStream
from .platforms.netease.live_stream import NeteaseLiveStream
from .platforms.qiandurebo.live_stream import QiandureboLiveStream
from .platforms.pandatv.live_stream import PandaLiveStream
from .platforms.maoer.live_stream import MaoerLiveStream
from .platforms.winktv.live_stream import WinkTVLiveStream
from .platforms.flextv.live_stream import FlexTVLiveStream
from .platforms.look.live_stream import LookLiveStream
from .platforms.popkontv.live_stream import PopkonTVLiveStream
from .platforms.twitcasting.live_stream import TwitCastingLiveStream
from .platforms.baidu.live_stream import BaiduLiveStream
from .platforms.weibo.live_stream import WeiboLiveStream
from .platforms.kugou.live_stream import KugouLiveStream
from .platforms.twitch.live_stream import TwitchLiveStream
from .platforms.liveme.live_stream import LiveMeLiveStream
from .platforms.huajiao.live_stream import HuajiaoLiveStream
from .platforms.showroom.live_stream import ShowRoomLiveStream
from .platforms.acfun.live_stream import AcfunLiveStream
from .platforms.inke.live_stream import InkeLiveStream
from .platforms.yinbo.live_stream import YinboLiveStream
from .platforms.zhihu.live_stream import ZhihuLiveStream
from .platforms.chzzk.live_stream import ChzzkLiveStream
from .platforms.haixiu.live_stream import HaixiuLiveStream
from .platforms.vvxq.live_stream import VVXQLiveStream
from .platforms.yiqilive.live_stream import YiqiLiveStream
from .platforms.langlive.live_stream import LangLiveStream
from .platforms.piaopiao.live_stream import PiaopaioLiveStream
from .platforms.sixroom.live_stream import SixRoomLiveStream
from .platforms.lehai.live_stream import LehaiLiveStream
from .platforms.huamao.live_stream import HuamaoLiveStream
from .platforms.shopee.live_stream import ShopeeLiveStream
from .platforms.youtube.live_stream import YoutubeLiveStream
from .platforms.taobao.live_stream import TaobaoLiveStream
from .platforms.jd.live_stream import JDLiveStream
from .platforms.faceit.live_stream import FaceitLiveStream


__all__ = [
    "__description__",
    "__title__",
    "__version__",
    "StreamData",
    "DouyinLiveStream",
    "TikTokLiveStream",
    "KwaiLiveStream",
    "HuyaLiveStream",
    "DouyuLiveStream",
    "YYLiveStream",
    "BilibiliLiveStream",
    "RedNoteLiveStream",
    "BigoLiveStream",
    "BluedLiveStream",
    "SoopLiveStream",
    "NeteaseLiveStream",
    "QiandureboLiveStream",
    "PandaLiveStream",
    "MaoerLiveStream",
    "WinkTVLiveStream",
    "FlexTVLiveStream",
    "LookLiveStream",
    "PopkonTVLiveStream",
    "TwitCastingLiveStream",
    "BaiduLiveStream",
    "WeiboLiveStream",
    "KugouLiveStream",
    "TwitchLiveStream",
    "LiveMeLiveStream",
    "HuajiaoLiveStream",
    "ShowRoomLiveStream",
    "AcfunLiveStream",
    "InkeLiveStream",
    "YinboLiveStream",
    "ZhihuLiveStream",
    "ChzzkLiveStream",
    "HaixiuLiveStream",
    "VVXQLiveStream",
    "YiqiLiveStream",
    "LangLiveStream",
    "PiaopaioLiveStream",
    "SixRoomLiveStream",
    "LehaiLiveStream",
    "HuamaoLiveStream",
    "ShopeeLiveStream",
    "YoutubeLiveStream",
    "TaobaoLiveStream",
    "JDLiveStream",
    "FaceitLiveStream",
]

__locals = locals()
for __name in __all__:
    if not __name.startswith("__"):
        setattr(__locals[__name], "__module__", "streamget")

check_node()



