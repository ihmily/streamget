# QuickStart

First, start by importing StreamGet:

```python
>>> import asyncio
>>> import streamget
```

Now, let’s try to get a webpage.

```python
>>> live = streamget.DouyinLiveStream()
>>> data = asyncio.run(live.fetch_web_stream_data(url))
>>> data
{'anchor_name': 'xxxxx', 'is_live': False}
or
{'anchor_name': 'xxxxx', 'is_live': True, 'title': 'xxxx', ...}
```

Similarly, to get the official API raw data:

```python
>>> data = asyncio.run(live.fetch_web_stream_data(url, process_data=False))
>>> data
The official API raw data will be returned
```

Or, you can also directly obtain live streaming source data.

```python
>>> import asyncio
>>> from streamget import DouyinLiveStream
>>> live = DouyinLiveStream()
>>> data = asyncio.run(live.fetch_web_stream_data(url, process_data=True))

>>> stream_obj = asyncio.run(live.fetch_stream_url(data, "OD"))
StreamData(platform='xxxx', anchor_name='xxxx', is_live=True, m3u8_url="xxx"...)

```

Note: that `process_data` params must be True in this case.

## Install NodeJS

Some live streaming platforms require Node.js dependencies to obtain data

You can install Node.js using built-in commands

```python
streamget install-node
```

You can also view installation nodejs help info

```python
streamget install-node -h
```

If the installation cannot be successful, please manually download and configure the environment variables.

## JSON Response Content

Use `to_json` method will be encoded as JSON.

```python
>>> stream_obj = asyncio.run(live.fetch_stream_url(data, "OD"))
StreamData(platform='xxxx', anchor_name='xxxx', is_live=True, m3u8_url="xxx"...)
>>> json_str = stream_obj.to_json()
'{"anchor_name": "xxxx", "is_live": True, "flv_url": "...", "m3u8_url": "..."}'
```

## Use Cookies

To include additional cookies in the outgoing request, use the `cookies` keyword argument:

```python
>>> cookies = 'key1=value1;key2=value2;'  # string
>>> live = streamget.DouyinLiveStream(cookies=cookies)
```

By initiating the request in this way, the final `Stream` object returned also contains a new_comkie attribute

## Use Proxy

For platforms that require proxy access, you can use the proxy parameter when instantiating objects

```python
>>> proxy = 'http://127.0.0.1:7890'
>>> live = streamget.DouyinLiveStream(proxy=proxy)
```

## Supported Platforms

The currently supported platforms are as follows：

```markdown
抖音 -> DouyinLiveStream
TikTok -> TikTokLiveStream
快手 -> KwaiLiveStream
虎牙 -> HuyaLiveStream
斗鱼 -> DouyuLiveStream
YY -> YYLiveStream
B站 -> BilibiliLiveStream
小红书 -> RedNoteLiveStream
Bigo -> BigoLiveStream
Blued -> BluedLiveStream
SOOP -> SoopLiveStream
网易CC -> NeteaseLiveStream
千度热播 -> QiandureboLiveStream
PandaTV -> PandaLiveStream
猫耳FM -> MaoerLiveStream
Look -> LookLiveStream
WinkTV -> WinkTVLiveStream
FlexTV -> FlexTVLiveStream
PopkonTV -> PopkonTVLiveStream
TwitCasting -> TwitCastingLiveStream
百度直播 -> BaiduLiveStream
微博直播 -> WeiboLiveStream
酷狗直播 -> KugouLiveStream
TwitchTV -> TwitchLiveStream
LiveMe -> LiveMeLiveStream
花椒直播 -> HuajiaoLiveStream
ShowRoom -> ShowRoomLiveStream
Acfun -> AcfunLiveStream
映客直播 -> InkeLiveStream
音播直播 -> YinboLiveStream
知乎直播 -> ZhihuLiveStream
CHZZK -> ChzzkLiveStream
嗨秀直播 -> HaixiuLiveStream
VV星球直播 -> VVXQLiveStream
17Live -> YiqiLiveStream
浪Live -> LangLiveStream
飘飘直播 -> PiaopaioLiveStream
六间房直播 -> SixRoomLiveStream
乐嗨直播 -> LehaiLiveStream
花猫直播 -> HuamaoLiveStream
Shopee -> ShopeeLiveStream
Youtube -> YoutubeLiveStream
淘宝 -> TaobaoLiveStream
京东 -> JDLiveStream
Faceit -> FaceitLiveStream
```

You can use the command line to view the supported live streaming platforms:

```bash
streamget -h
```

Will return the help info, it inclued return a list of supported platforms.

