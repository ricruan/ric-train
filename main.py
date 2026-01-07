import logging
from Base.RicUtils.config.logConfig import setup_logging
# 日志配置初始化
setup_logging()

from fastapi import FastAPI, Body

from Base.Client.mysqlClient import MySQLClient


app = FastAPI()



@app.post("/execute_sql")
def read_root(sql:str= Body(..., embed=True)):
    result = MySQLClient().execute_sync(sql)
    return result


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000)