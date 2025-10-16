from typing import Union

from fastapi import FastAPI, Body

from Client.mysqlClient import MySQLClient

app = FastAPI()


@app.post("/execute_sql")
def read_root(sql:str= Body(..., embed=True)):
    result = MySQLClient().execute_sync(sql)
    return result
