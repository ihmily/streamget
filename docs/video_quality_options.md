# Video Quality Options

When using the `fetch_stream_url` method, the `video_quality` parameter allows you to specify the desired video quality of the stream. The supported video qualities and their corresponding values are listed below:

## Supported Video Qualities

| Quality Index | Quality Name | Description                    |
| ------------- | ------------ | ------------------------------ |
| 0             | OD           | Original Definition (最高画质) |
| 1             | UHD          | Ultra High Definition (超高清) |
| 2             | HD           | High Definition (高清)         |
| 3             | SD           | Standard Definition (标清)     |
| 4             | LD           | Low Definition (流畅)          |

## Usage

You can specify the video quality using either the quality name (e.g., "OD", "UHD") or the corresponding index (e.g., 0, 1, 2, 3, 4). 

If the `video_quality` parameter is not provided or set to `None`, the default quality will be **OD (Original Definition)**, which is the highest available quality. For example:

```python
# Using the default quality (OD)
stream_obj = asyncio.run(live.fetch_stream_url(data))

# Explicitly setting the quality to OD
stream_obj = asyncio.run(live.fetch_stream_url(data, video_quality="OD"))

# Using quality index for OD
stream_obj = asyncio.run(live.fetch_stream_url(data, video_quality=0))
```

---

### Important Notes

- **Default Quality**: If the `video_quality` parameter is omitted or set to `None`, the method will automatically select the highest available quality, which is **OD (Original Definition)**.
- **Fallback Behavior**: If the live broadcast room does not support the selected video quality, the method will automatically fall back to the highest available quality in descending order (e.g., if "UHD" is not supported, it will try "HD", then "SD", and so on).
