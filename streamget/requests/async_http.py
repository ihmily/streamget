from typing import Any

import httpx

from .. import utils

OptionalStr = str | None
OptionalDict = dict[str, Any] | None


async def async_req(
        url: str,
        proxy_addr: OptionalStr = None,
        headers: OptionalDict = None,
        data: dict | bytes | None = None,
        json_data: dict | list | None = None,
        timeout: int = 20,
        redirect_url: bool = False,
        return_cookies: bool = False,
        include_cookies: bool = False,
        verify: bool = False,
        http2: bool = True
) -> OptionalDict | OptionalStr | tuple:
    """
    Sends an asynchronous HTTP request to the specified URL.

    This function supports both GET and POST requests. It allows for customization of headers,
    data, and other request parameters. It also handles proxy addresses, SSL verification,
    and HTTP/2 support.

    Args:
        url (str): The URL to send the request to.
        proxy_addr (OptionalStr): The proxy address to use. Defaults to None.
        headers (OptionalDict): Custom headers to include in the request. Defaults to None.
        data (dict | bytes | None): Data to send in the request body. Defaults to None.
        json_data (dict | list | None): JSON data to send in the request body. Defaults to None.
        timeout (int): The request timeout in seconds. Defaults to 20.
        redirect_url (bool): If True, returns the final URL after redirects. Defaults to False.
        return_cookies (bool): If True, returns the response cookies. Defaults to False.
        include_cookies (bool): If True, includes cookies in the response tuple. Defaults to False.
        verify (bool): If, True verifies the SSL certificate. Defaults to False.
        http2 (bool): If True, enables HTTP/2 support. Defaults to True.

    Returns:
        OptionalDict | OptionalStr | tuple: The response text, JSON data,
        or a tuple containing the response text and cookies.

    Raises:
        Exception: If an error occurs during the request.

    Example:
        >>> import asyncio
        >>> async def main():
        ...     result = await async_req("https://example.com", proxy_addr="http://proxy.example.com")
        ...     print(result)
        >>> asyncio.run(main())
        Response text or JSON data

    Note:
        - If `data` or `json_data` is provided, a POST request is sent; otherwise, a GET request is sent.
        - The `redirect_url` parameter only returns the final URL after following redirects.
        - If `return_cookies` is True, the function returns a tuple containing the response text and cookies.
    """
    if headers is None:
        headers = {}
    try:
        proxy_addr = utils.handle_proxy_addr(proxy_addr)
        if data or json_data:
            async with httpx.AsyncClient(proxy=proxy_addr, timeout=timeout, verify=verify, http2=http2) as client:
                response = await client.post(url, data=data, json=json_data, headers=headers)
        else:
            async with httpx.AsyncClient(proxy=proxy_addr, timeout=timeout, verify=verify, http2=http2) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)

        if redirect_url:
            return str(response.url)
        elif return_cookies:
            cookies_dict = dict(response.cookies.items())
            return (response.text, cookies_dict) if include_cookies else cookies_dict
        else:
            resp_str = response.text
    except Exception as e:
        resp_str = str(e)

    return resp_str


async def get_response_status(
        url: str,
        proxy_addr: OptionalStr = None,
        headers: OptionalDict = None,
        timeout: int = 10,
        verify: bool = False,
        http2: bool = True
) -> int:
    """
    Checks if a URL returns a successful HTTP status code (200 OK).

    This function sends a HEAD request to the specified URL and checks the response status code.
    It supports custom headers, proxy addresses, and SSL verification.

    Args:
        url (str): The URL to check.
        proxy_addr (OptionalStr): The proxy address to use. Defaults to None.
        headers (OptionalDict): Custom headers to include in the request. Defaults to None.
        timeout (int): The request timeout in seconds. Defaults to 10.
        verify (bool): If True, verifies the SSL certificate. Defaults to False.
        http2 (bool): If True, enables HTTP/2 support. Defaults to True.

    Returns:
        int: such as 200, 304, 403.

    Raises:
        Exception: If an error occurs during the request.

    Example:
        >>> import asyncio
        >>> async def main():
        ...     status = await get_response_status("https://example.com")
        ...     print(status)
        >>> asyncio.run(main())
        200

    Note:
        - This function uses the HEAD request method, which is lightweight and suitable for checking status codes.
        - returns a status code other than 200 OK.
    """
    try:
        proxy_addr = utils.handle_proxy_addr(proxy_addr)
        async with httpx.AsyncClient(proxy=proxy_addr, timeout=timeout, verify=verify, http2=http2) as client:
            response = await client.head(url, headers=headers, follow_redirects=True)
            return response.status_code
    except Exception as e:
        print(e)
    return False
