from fastapi import FastAPI

from Wolin.api.coreApi import router as core_router


def init_router(app: FastAPI):
    app.include_router(core_router, prefix="/interview", tags=["Interview"])
