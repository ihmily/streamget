# -*- coding: utf-8 -*-
import re
import json
import random
import string
import execjs
import functools
import traceback
from typing import Any
from .logger import logger


class Color:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

    @staticmethod
    def print_colored(text, color):
        print(f"{color}{text}{Color.RESET}")


def trace_error_decorator(func: callable) -> callable:
    @functools.wraps(func)
    def wrapper(*args: list, **kwargs: dict) -> Any:
        try:
            return func(*args, **kwargs)
        except execjs.ProgramError:
            logger.warning('Failed to execute JS code. Please check if the Node.js environment')
        except Exception as e:
            error_line = traceback.extract_tb(e.__traceback__)[-1].lineno
            error_info = f"message: type: {type(e).__name__}, {e} in function {func.__name__} at line: {error_line}"
            logger.error(error_info)
            return []

    return wrapper


def dict_to_cookie_str(cookies_dict: dict) -> str:
    cookie_str = '; '.join([f"{key}={value}" for key, value in cookies_dict.items()])
    return cookie_str


def remove_emojis(text: str, replace_text: str = '') -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(replace_text, text)


def handle_proxy_addr(proxy_addr):
    if proxy_addr:
        if not proxy_addr.startswith('http'):
            proxy_addr = 'http://' + proxy_addr
    else:
        proxy_addr = None
    return proxy_addr


def generate_random_string(length: int) -> str:
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choices(characters, k=length))
    return random_string


def jsonp_to_json(jsonp_str: str) -> dict | None:
    pattern = r'(\w+)\((.*)\);?$'
    match = re.search(pattern, jsonp_str)

    if match:
        _, json_str = match.groups()
        json_obj = json.loads(json_str)
        return json_obj
    else:
        raise Exception("No JSON data found in JSONP response.")

