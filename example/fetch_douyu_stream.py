import asyncio

from streamget import DouyuLiveStream


async def main():
    url = "https://live.douyu.com/74751"

    douyu_stream = DouyuLiveStream(proxy_addr=None)

    try:
        # Fetch the live stream data from the provided URL
        data = await douyu_stream.fetch_web_stream_data(url)

        # Fetch the stream URL
        stream_data = await douyu_stream.fetch_stream_url(data, "OD")
        print(stream_data)

        # Convert to json string
        json_str = stream_data.to_json()
        print(json_str)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
