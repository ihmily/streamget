from . import __all__, __version__


def main():
    """
    Print help information for the streamget package.
    """
    print("Welcome to streamget!")
    print(f"\nVersion: {__version__}")
    print("\nDescription:")
    print("A library to fetch live stream URLs from various platforms.")
    print("\nSupported Platforms:")
    for platform in __all__:
        if not platform.startswith("__"):
            print(f"  - {platform}")
    print("\nUsage:")
    print("  import asyncio")
    print("  from streamget import DouyinLiveStream")
    print("  stream = DouyinLiveStream()")
    print("  data = asyncio.run(stream.fetch_web_stream_data('https://live.douyin.com/xxxxxx'))")
    print("  stream_obj = asyncio.run(stream.fetch_stream_url(data))")
    print("  stream_json_str = stream_obj.to_json()")
    print("\nFor more information, visit the GitHub repository: https://github.com/ihmily/streamget\n")


if __name__ == '__main__':
    main()
