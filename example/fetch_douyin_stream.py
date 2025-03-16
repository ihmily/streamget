import asyncio

from streamget import DouyinLiveStream


async def main():
    # URL of the Douyin live stream
    url = "https://live.douyin.com/991562466558"

    # Initialize the DouyinLiveStream object
    douyin_stream = DouyinLiveStream()

    try:
        # Fetch the live stream data from the provided URL
        data = await douyin_stream.fetch_web_stream_data(url)

        # Fetch the stream URL
        stream_data = await douyin_stream.fetch_stream_url(data, "OD")
        print(stream_data)

        # Convert to json string
        json_str = stream_data.to_json()
        print(json_str)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
