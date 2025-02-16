# -*- coding: utf-8 -*-

import os
custom_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> - <level>{message}</level>"
os.environ["LOGURU_FORMAT"] = custom_format
from loguru import logger

