# Guide

## Overview

This guide provides a comprehensive introduction to using the `StreamGet` library to fetch and process live streaming data from various platforms. It covers the essential request parameters, methods, and attributes you need to know to get started.

## Instantiating an Object

To begin, you need to instantiate an object for the specific live streaming platform you are interested in. For example, to work with Douyin Live, you would use:

```python
>>> from streamget import DouyinLiveStream
>>> live = DouyinLiveStream()
```

You can also pass additional parameters during instantiation, such as cookies or proxy settings, which will be discussed later in this guide.

## fetch_web_stream_data Method

The `fetch_web_stream_data` method is used to fetch data from a live streaming webpage. It has two main parameters:

- **url**: The URL of the live streaming webpage.
- **process_data**: A boolean parameter that determines whether the fetched data should be processed or returned in its raw form.

### Example Usage

```python
>>> url = "https://example.com/live"
>>> data = asyncio.run(live.fetch_web_stream_data(url, process_data=True))
```

### Parameters

- **url**: The URL of the live streaming webpage.
- **process_data**: If `True`, the data will be processed and returned in a structured format. If `False`, the raw data from the official API will be returned.

### Return Value

The method returns a dictionary containing the processed data. If `process_data` is `True`, the dictionary might look like this:

```json
{
    "anchor_name": "xxxxx",
    "is_live": True,
    "title": "xxxx",
    ...
}
```

If `process_data` is `False`, the raw data from the official API will be returned.

## fetch_stream_url Method

The `fetch_stream_url` method is used to fetch the streaming URL from the processed data obtained from `fetch_web_stream_data`. It has two main parameters:

- **data**: The processed data returned by `fetch_web_stream_data`.
- **video_quality**: The desired video quality of the stream.

### Example Usage

```python
>>> stream_obj = asyncio.run(live.fetch_stream_url(data, video_quality="OD"))
```

### Parameters

- **data**: The processed data returned by `fetch_web_stream_data`.
- **video_quality**: The desired video quality of the stream (e.g., "OD" for original definition).

### Return Value

The method returns a `Stream` object containing the streaming URL and other relevant information.

## Stream Object

The `Stream` object returned by `fetch_stream_url` has the following attributes:

- **platform**: The name of the live streaming platform.
- **anchor_name**: The name of the live stream anchor.
- **is_live**: A boolean indicating whether the stream is live.
- **title**: The title of the live stream.
- **quality**: The quality of the stream.
- **m3u8_url**: The URL of the stream in M3U8 format.
- **flv_url**: The URL of the stream in FLV format.
- **record_url**: The URL for recording the stream.
- **new_cookies**: Any new cookies obtained during the request.
- **new_token**: Any new token obtained during the request.
- **extra**: Any additional information.

### Example Stream Object

```python
StreamData(
    platform='抖音',
    anchor_name='Jack',
    is_live=True,
    title='Hello everyone ~',
    quality='OD',
    m3u8_url='https://example.com/xxxx.m3u8',
    flv_url='https://example.com/xxxx.flv',
    record_url='https://example.com/xxxx.flv',
    new_cookies=None,
    new_token=None,
    extra=None
)
```

## Converting to JSON

The `Stream` object provides a `.to_json()` method that converts the object's attributes to a JSON string.

### Example Usage

```python
>>> json_str = stream_obj.to_json()
>>> print(json_str)
'{"platform": "抖音", "anchor_name": "Jack", "is_live": True, "flv_url": "https://example.com/xxxx.flv", "m3u8_url": "https://example.com/xxxx.m3u8" ...}'
```

## Using Cookies

To include additional cookies in the outgoing request, you can pass a string of cookies during object instantiation:

```python
>>> cookies = 'key1=value1;key2=value2;'
>>> live = DouyinLiveStream(cookies=cookies)
```

The final `Stream` object returned will also contain a `new_cookies` attribute if any new cookies are obtained during the request.

## Using Proxy

For platforms that require proxy access, you can pass a proxy URL during object instantiation:

```python
>>> proxy = "http://127.0.0.1:7890"
>>> live = DouyinLiveStream(proxy=proxy)
```

## Troubleshooting

If you encounter issues with parsing URLs,  it might be due to network issues or an invalid URL:

In such cases, please check the following:

1. **URL Validity**: Ensure that the URL is correct and accessible.
2. **Network Connection**: Verify that your network connection is stable.
3. **Retry the Request**: Sometimes, retrying the request can resolve transient issues.

If the problem persists, you may need to manually configure your environment or seek further assistance.

