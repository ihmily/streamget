import os
import sys
from pathlib import Path

from .__version__ import __description__, __title__, __version__

current_file_path = Path(__file__).resolve()
current_dir = current_file_path.parent
JS_SCRIPT_PATH = current_dir / 'js'

execute_dir = os.path.split(os.path.realpath(sys.argv[0]))[0]
node_execute_dir = Path(execute_dir) / 'node'
current_env_path = os.environ.get('PATH')
os.environ['PATH'] = str(node_execute_dir) + os.pathsep + current_env_path

from .data import StreamData
from .platforms.acfun.live_stream import AcfunLiveStream
from .platforms.baidu.live_stream import BaiduLiveStream
from .platforms.bigo.live_stream import BigoLiveStream
from .platforms.bilibili.live_stream import BilibiliLiveStream
from .platforms.blued.live_stream import BluedLiveStream
from .platforms.changliao.live_stream import ChangliaoLiveStream
from .platforms.chzzk.live_stream import ChzzkLiveStream
from .platforms.douyin.live_stream import DouyinLiveStream
from .platforms.douyu.live_stream import DouyuLiveStream
from .platforms.faceit.live_stream import FaceitLiveStream
from .platforms.flextv.live_stream import FlexTVLiveStream
from .platforms.haixiu.live_stream import HaixiuLiveStream
from .platforms.huajiao.live_stream import HuajiaoLiveStream
from .platforms.huamao.live_stream import HuamaoLiveStream
from .platforms.huya.live_stream import HuyaLiveStream
from .platforms.inke.live_stream import InkeLiveStream
from .platforms.jd.live_stream import JDLiveStream
from .platforms.kuaishou.live_stream import KwaiLiveStream
from .platforms.kugou.live_stream import KugouLiveStream
from .platforms.langlive.live_stream import LangLiveStream
from .platforms.lehai.live_stream import LehaiLiveStream
from .platforms.lianjie.live_stream import LianJieLiveStream
from .platforms.liveme.live_stream import LiveMeLiveStream
from .platforms.look.live_stream import LookLiveStream
from .platforms.maoer.live_stream import MaoerLiveStream
from .platforms.netease.live_stream import NeteaseLiveStream
from .platforms.pandatv.live_stream import PandaLiveStream
from .platforms.piaopiao.live_stream import PiaopaioLiveStream
from .platforms.popkontv.live_stream import PopkonTVLiveStream
from .platforms.qiandurebo.live_stream import QiandureboLiveStream
from .platforms.rednote.live_stream import RedNoteLiveStream
from .platforms.shopee.live_stream import ShopeeLiveStream
from .platforms.showroom.live_stream import ShowRoomLiveStream
from .platforms.sixroom.live_stream import SixRoomLiveStream
from .platforms.soop.live_stream import SoopLiveStream
from .platforms.taobao.live_stream import TaobaoLiveStream
from .platforms.tiktok.live_stream import TikTokLiveStream
from .platforms.twitcasting.live_stream import TwitCastingLiveStream
from .platforms.twitch.live_stream import TwitchLiveStream
from .platforms.vvxq.live_stream import VVXQLiveStream
from .platforms.weibo.live_stream import WeiboLiveStream
from .platforms.winktv.live_stream import WinkTVLiveStream
from .platforms.yinbo.live_stream import YinboLiveStream
from .platforms.yiqilive.live_stream import YiqiLiveStream
from .platforms.youtube.live_stream import YoutubeLiveStream
from .platforms.yy.live_stream import YYLiveStream
from .platforms.zhihu.live_stream import ZhihuLiveStream

__all__ = [
    "AcfunLiveStream",
    "BaiduLiveStream",
    "BigoLiveStream",
    "BilibiliLiveStream",
    "BluedLiveStream",
    "ChangliaoLiveStream",
    "ChzzkLiveStream",
    "DouyinLiveStream",
    "DouyuLiveStream",
    "FaceitLiveStream",
    "FlexTVLiveStream",
    "HaixiuLiveStream",
    "HuajiaoLiveStream",
    "HuamaoLiveStream",
    "HuyaLiveStream",
    "InkeLiveStream",
    "JDLiveStream",
    "KugouLiveStream",
    "KwaiLiveStream",
    "LangLiveStream",
    "LehaiLiveStream",
    "LianJieLiveStream",
    "LiveMeLiveStream",
    "LookLiveStream",
    "MaoerLiveStream",
    "NeteaseLiveStream",
    "PandaLiveStream",
    "PiaopaioLiveStream",
    "PopkonTVLiveStream",
    "QiandureboLiveStream",
    "RedNoteLiveStream",
    "ShopeeLiveStream",
    "ShowRoomLiveStream",
    "SixRoomLiveStream",
    "SoopLiveStream",
    "StreamData",
    "TaobaoLiveStream",
    "TikTokLiveStream",
    "TwitCastingLiveStream",
    "TwitchLiveStream",
    "VVXQLiveStream",
    "WeiboLiveStream",
    "WinkTVLiveStream",
    "YYLiveStream",
    "YinboLiveStream",
    "YiqiLiveStream",
    "YoutubeLiveStream",
    "ZhihuLiveStream",
    "__description__",
    "__title__",
    "__version__",
]

__locals = locals()
for __name in __all__:
    if not __name.startswith("__"):
        __locals[__name].__module__ = "streamget"

# from .scripts.node_setup import check_node
# check_node()