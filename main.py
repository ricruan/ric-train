import logging
from RicUtils.config.logConfig import setup_logging
# 日志配置初始化
setup_logging()
from typing import Union

from fastapi import FastAPI, Body

from Client.mysqlClient import MySQLClient

from Wolin.api.coreApi import router as interview_router

app = FastAPI()

import Wolin.frontend.fastapi_init

app.include_router(interview_router, prefix="/interview", tags=["Interview"])


@app.post("/execute_sql")
def read_root(sql:str= Body(..., embed=True)):
    result = MySQLClient().execute_sync(sql)
    return result


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000)