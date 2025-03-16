import gzip
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

import requests

no_proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(no_proxy_handler)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
OptionalStr = str | None
OptionalDict = dict | None


def sync_req(
        url: str,
        proxy_addr: OptionalStr = None,
        headers: OptionalDict = None,
        data: dict | bytes | None = None,
        json_data: dict | list | None = None,
        timeout: int = 20,
        redirect_url: bool = False,
        abroad: bool = False,
        content_conding: str = 'utf-8'
) -> str:
    """
    Sends a synchronous HTTP request to the specified URL.

    This function supports both GET and POST requests, with optional proxy support, custom headers,
    and data encoding. It can handle gzip-compressed responses and provides options for redirect handling.

    Args:
        url (str): The URL to send the request to.
        proxy_addr (OptionalStr): The proxy address to use (e.g., "http://proxy.example.com"). Defaults to None.
        headers (OptionalDict): Custom headers to include in the request. Defaults to None.
        data (dict | bytes | None): Data to send in the request body. If a dictionary, it will be URL-encoded.
        Defaults to None.
        json_data (dict | list | None): JSON data to send in the request body. If provided, `data` will be ignored.
        Defaults to None.
        timeout (int): The request timeout in seconds. Defaults to 20.
        redirect_url (bool): If True, returns the final URL after redirects. Defaults to False.
        abroad (bool): If True, uses the global `opener` with no proxy. Otherwise, uses `urllib.request.urlopen`.
        Defaults to False.
        content_conding (str): The encoding to use for request data and response decoding. Defaults to 'utf-8'.

    Returns:
        str: The response text, or the final URL if `redirect_url` is True. If an error occurs,
        returns the error message as a string.

    Raises:
        Exception: If an error occurs during the request.

    Example:
        >>> result = sync_req("https://example.com")
        >>> print(result)
        Response text or error message

    Note:
        - If both `data` and `json_data` are provided, `json_data` takes precedence.
        - If `redirect_url` is True, the function returns the final URL after following redirects.
        - If `abroad` is True, the function uses the global `opener` configured with no proxy.
        - The function handles gzip-compressed responses automatically.
    """
    if headers is None:
        headers = {}
    try:
        if proxy_addr:
            proxies = {
                'http': proxy_addr,
                'https': proxy_addr
            }
            if data or json_data:
                response = requests.post(
                    url, data=data, json=json_data, headers=headers, proxies=proxies, timeout=timeout
                )
            else:
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            if redirect_url:
                return response.url
            resp_str = response.text
        else:
            if data and not isinstance(data, bytes):
                data = urllib.parse.urlencode(data).encode(content_conding)
            if json_data and isinstance(json_data, (dict, list)):
                data = json.dumps(json_data).encode(content_conding)

            req = urllib.request.Request(url, data=data, headers=headers)

            try:
                if abroad:
                    response = urllib.request.urlopen(req, timeout=timeout)
                else:
                    response = opener.open(req, timeout=timeout)
                if redirect_url:
                    return response.url
                content_encoding = response.info().get('Content-Encoding')
                try:
                    if content_encoding == 'gzip':
                        with gzip.open(response, 'rt', encoding=content_conding) as gzipped:
                            resp_str = gzipped.read()
                    else:
                        resp_str = response.read().decode(content_conding)
                finally:
                    response.close()

            except urllib.error.HTTPError as e:
                if e.code == 400:
                    resp_str = e.read().decode(content_conding)
                else:
                    raise
            except urllib.error.URLError as e:
                print(f"URL Error: {e}")
                raise
            except Exception as e:
                print(f"An error occurred: {e}")
                raise

    except Exception as e:
        resp_str = str(e)

    return resp_str
