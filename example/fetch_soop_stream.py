import asyncio

from streamget import SoopLiveStream


async def main():
    # URL of the SOOP Live
    url = "https://play.sooplive.co.kr/alswl2208/281343812"

    # Initialize the SoopLiveStream object
    soop_stream = SoopLiveStream(
        # Use proxy, Ensure that your agent can access it normally
        proxy_addr='http://127.0.0.1:7890'
    )

    try:
        # Fetch the live stream data from the provided URL
        data = await soop_stream.fetch_web_stream_data(url)

        # Fetch the stream data object
        stream_data = await soop_stream.fetch_stream_url(data, "OD")
        print(stream_data)

        # Convert object to json string
        json_str = stream_data.to_json()
        print(json_str)
    except Exception as e:
        print(f"An error occurred: {e}")


# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(main())
