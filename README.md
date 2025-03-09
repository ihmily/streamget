<p align="center">
  <a href="https://streamget.readthedocs.io"><img width="350" height="208" src="https://raw.githubusercontent.com/ihmily/streamget/main/docs/img/eagle.png" alt='StreamGet'></a>
</p>
<p align="center"><strong>StreamGet</strong> <em>- A Multi-Platform Live Stream Parser Library.</em></p>

<p align="center">
<img alt="Python version" src="https://img.shields.io/badge/python-3.10%2B-blue.svg">
<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/streamget?color=green">
</p>


`streamget` is a lightweight  Python library for real-time live stream acquisition, supporting HLS/FLV across 40+ platforms.

## Installation

Install `StreamGet` via pip (requires Python 3.10+):

```bash
pip install streamget
```

Node.js Runtime (Optional for Some Features):

```
streamget install-node
```

To view the help information, run:  `streamget --help` .

------

## Quick Start

```python
>>> import asyncio
>>> from streamget import DouyinLiveStream
>>> url = "https://live.douyin.com/xxxxxxx"
>>> live = DouyinLiveStream()
>>> data = asyncio.run(live.fetch_web_stream_data(url))
>>> stream_obj = asyncio.run(live.fetch_stream_url(data, "OD"))
StreamData(platform='xxxx', anchor_name='xxxx', is_live=True, m3u8_url="xxx"...)
>>> json_str = stream_obj.to_json()
'{"anchor_name": "xxxx", "is_live": True, "flv_url": "...", "m3u8_url": "..."}'
```

------

## Supported Platforms

| Platform    | Support status | HLS support | FLV support | Need cookie | Requires Node.js |
| :---------- | :------------- | :---------- | :---------- | ----------- | ---------------- |
| 抖音        | ✅              | ✅           | ✅           |             | ✅                |
| TikTok      | ✅              | ✅           | ✅           |             |                  |
| 快手        | ✅              | ❌           | ✅           |             |                  |
| 虎牙直播    | ✅              | ✅           | ✅           |             |                  |
| 斗鱼直播    | ✅              | ❌           | ✅           |             | ✅                |
| YY直播      | ✅              | ❌           | ✅           |             |                  |
| 哔哩哔哩    | ✅              | ❌           | ✅           |             |                  |
| 小红书      | ✅              | ✅           | ✅           |             |                  |
| Bigo        | ✅              | ✅           | ❌           |             |                  |
| Blued       | ✅              | ✅           | ❌           |             |                  |
| SOOP        | ✅              | ✅           | ❌           |             |                  |
| 网易CC      | ✅              | ✅           | ✅           |             |                  |
| 千度热播    | ✅              | ❌           | ✅           |             |                  |
| PandaTV     | ✅              | ✅           | ❌           |             |                  |
| 猫耳FM      | ✅              | ✅           | ✅           |             |                  |
| Look        | ✅              | ✅           | ✅           |             |                  |
| WinkTV      | ✅              | ✅           | ❌           |             |                  |
| FlexTV      | ✅              | ✅           | ❌           |             |                  |
| PopkonTV    | ✅              | ✅           | ❌           |             |                  |
| TwitCasting | ✅              | ✅           | ❌           |             |                  |
| 百度直播    | ✅              | ✅           | ✅           |             |                  |
| 微博直播    | ✅              | ✅           | ✅           |             |                  |
| 酷狗直播    | ✅              | ❌           | ✅           |             |                  |
| TwitchTV    | ✅              | ✅           | ❌           |             |                  |
| LiveMe      | ✅              | ✅           | ✅           |             | ✅                |
| 花椒直播    | ✅              | ❌           | ✅           |             |                  |
| ShowRoom    | ✅              | ✅           | ❌           |             |                  |
| 映客直播    | ✅              | ✅           | ✅           |             |                  |
| Acfun       | ✅              | ✅           | ✅           |             |                  |
| 音播直播    | ✅              | ✅           | ✅           |             |                  |
| 知乎直播    | ✅              | ✅           | ✅           |             |                  |
| CHZZK       | ✅              | ✅           | ❌           |             |                  |
| 嗨秀直播    | ✅              | ❌           | ✅           |             | ✅                |
| vv星球直播  | ✅              | ✅           | ❌           |             |                  |
| 17Live      | ✅              | ❌           | ✅           |             |                  |
| 浪Live      | ✅              | ✅           | ✅           |             |                  |
| 畅聊直播    | ✅              | ✅           | ✅           |             |                  |
| 飘飘直播    | ✅              | ✅           | ✅           |             |                  |
| 六间房直播  | ✅              | ❌           | ✅           |             |                  |
| 乐嗨直播    | ✅              | ✅           | ✅           |             | ✅                |
| 花猫直播    | ✅              | ✅           | ❌           |             |                  |
| Shopee      | ✅              | ❌           | ✅           |             |                  |
| YouTube     | ✅              | ✅           | ❌           | ✅           |                  |
| 淘宝        | ✅              | ✅           | ✅           | ✅           | ✅                |
| 京东        | ✅              | ✅           | ✅           |             |                  |
| Faceit      | ✅              | ✅           | ❌           |             |                  |
| More ...    |                |             |             |             |                  |

### Notes

1. **Support Status**: ✅ indicates supported or necessary, ❌ indicates unsupported or optional.
1. **Cookie Need**: ✅ indicates necessary
1. **Requires Node.js**: require Node.js for fetching data

------

## Supported Quality

| Chinese clarity | abbreviation | Full Name             | Note                                                |
| :-------------- | :----------- | :-------------------- | :-------------------------------------------------- |
| 原画            | `OD`         | Original Definition   | Highest clarity, original picture quality, Blue-ray |
| 超清            | `UHD`        | Ultra High Definition | Ultra high definition                               |
| 高清            | `HD`         | High Definition       | High definition, usually referring to 1080p         |
| 标清            | `SD`         | Standard Definition   | Standard clarity, usually referring to 480p         |
| 流畅            | `LD`         | Low Definition        | Low definition, usually referring to 360p or lower  |

## Contributing

Contributions are welcome! If you'd like to add support for a new platform or improve the package, please check out the [GitHub repository](https://github.com/ihmily/streamget) and submit a pull request.

------

## Documentation

For full documentation and advanced usage, visit the [official documentation](https://streamget.readthedocs.io/).

------

<p align="center"><i>StreamGet is <a href="https://github.com/ihmily/streamget/blob/main/LICENSE.md">MIT licensed</a> code.<br/>Where there's a live stream, there's StreamGet.</i><br/>&mdash; 🦅 &mdash;</p>

