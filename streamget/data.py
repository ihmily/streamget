import json
from dataclasses import dataclass


@dataclass
class StreamData:
    """
    Represents metadata and URLs associated with a streaming session.

    This class encapsulates essential information about a stream, including platform details,
    streamer information, stream status, and URLs for different stream formats.
    It also provides a method to convert the object to a JSON string.

    Attributes:
        platform (str): The streaming platform (e.g., "Twitch", "SOOP", "TikTok").
        anchor_name (str): The name of the streamer.
        is_live (bool): Indicates whether the stream is currently live.
        title (str): The title of the stream.
        quality (str): The quality of the stream (e.g., "OD", "BD", "UHD", "HD").
        m3u8_url (str): The URL for the m3u8 stream format.
        flv_url (str): The URL for the FLV stream format.
        record_url (str): The URL for recording the stream.
        new_cookies (str): Updated cookies required for accessing the stream.
        new_token (str): Updated token required for accessing the stream.
        extra (dict): Additional metadata or custom fields.

    Example:
        >>> stream_data = StreamData(platform="Twitch", anchor_name="StreamerName", is_live=True, title="Live Title")
        >>> json_data = stream_data.to_json()
        >>> print(json_data)
        JSON representation of the stream data

    Note:
        The `extra` attribute can be used to store any additional metadata that is not explicitly defined in the class.
    """
    platform: str = None
    anchor_name: str = None
    is_live: bool = None
    title: str = None
    quality: str = None
    m3u8_url: str = None
    flv_url: str = None
    record_url: str = None
    new_cookies: str = None
    new_token: str = None
    extra: dict = None

    def to_json(self) -> str:
        """
        Converts the StreamData object to a JSON string.

        This method serializes the object's attributes into a JSON format, making it easy to
        transmit or store the stream data.

        Returns:
            str: A JSON representation of the StreamData object.

        Example:
            >>> stream_data = StreamData(platform="Twitch", anchor_name="StreamerName")
            >>> json_data = stream_data.to_json()
            >>> print(json_data)
            {
                "platform": "Twitch",
                "anchor_name": "StreamerName",
                ...
            }
        """
        return json.dumps(self.__dict__, ensure_ascii=False, indent=4)


def wrap_stream(data: dict) -> StreamData:
    """
    Wraps a dictionary into a StreamData object with default values for missing fields.

    This function ensures that all required and optional fields are present in the input dictionary.
    If a field is missing, it is set to `None`.

    Args:
        data (dict): A dictionary containing stream data.

    Returns:
        StreamData: An instance of StreamData with default values for missing fields.

    Raises:
        TypeError: If the input is not a dictionary.

    Example:
        >>> json_data = {"platform": "Bilibili", "anchor_name": "StreamerName"}
        >>> stream_data = wrap_stream(json_data)
        >>> print(stream_data)
        StreamData(platform='Bilibili', anchor_name='StreamerName', ...)

    Note:
        The function assumes that the input dictionary contains valid data types for each field.
    """
    if not isinstance(data, dict):
        raise TypeError("Input must be a dictionary")

    required_fields = ["platform", "anchor_name", "is_live", "title", "quality", "m3u8_url", "flv_url", "record_url"]
    optional_fields = ["new_cookies", "new_token"]

    for field in required_fields + optional_fields:
        if field not in data:
            data[field] = None

    return StreamData(**data)
