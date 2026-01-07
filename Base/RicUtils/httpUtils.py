import json
import logging
import os
from enum import Enum

import aiohttp

class HttpStatus(Enum):
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

class HttpResponse:
    def __init__(self, status_code: int | HttpStatus, data: dict | None, msg: str):
        if not data:
            data = {}
        if isinstance(status_code,HttpStatus):
            status_code = status_code.value

        self.status_code = status_code
        self.data = data
        self.msg = msg


    @staticmethod
    def ok(data = None, msg: str = "success."):
        return HttpResponse(HttpStatus.OK, data, msg)

    @staticmethod
    def error(msg: str = "error."):
        return HttpResponse(HttpStatus.INTERNAL_SERVER_ERROR,None,msg)



logger = logging.getLogger(__name__)
TIMEOUT = int(os.getenv("HTTP_TIMEOUT",360))
HEADERS = {
    "Content-Type": "application/json",
}

STREAM_HEADERS = {
    "Content-Type": "text/event-stream",
}

async def normal_post(url: str, data: dict, headers: dict)  -> dict:
    """
     常规Post请求封装(异步),可以便与后期统一拦截
    :param url: API URL
    :param data: API 请求参数
    :param headers: API 请求头
    :return:
    """
    headers = {**HEADERS, **headers}
    para_json = {**data}
    logger.info(f"\n请求地址:{url}\n请求参数:{para_json}\n请求头:{headers}")

    async with aiohttp.ClientSession() as session:
        async with session.post(
                url,
                json=para_json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as response:
            result_text = await response.text()
            result_text = json.loads(result_text)
            logger.info(f"\n请求地址:{url}\n响应结果:{result_text}")

            return result_text