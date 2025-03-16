import asyncio

from streamget import RedNoteLiveStream


async def main():
    # URL of the RedNote live stream
    url = "https://www.xiaohongshu.com/user/profile/5ac7123ce8ac2b1d1503e920"

    # Initialize the RedNote object
    rednote_stream = RedNoteLiveStream()

    try:
        # Fetch the live stream data from the provided URL
        data = await rednote_stream.fetch_app_stream_data(url)

        # Fetch the stream URL and convert it to JSON format
        stream_data = await rednote_stream.fetch_stream_url(data)
        print(stream_data)

        # Convert to json string
        json_str = stream_data.to_json()
        print(json_str)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
