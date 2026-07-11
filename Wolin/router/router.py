from fastapi import FastAPI

from Wolin.api.coreApi import router as core_router
from Wolin.api.questionApi import router as question_router
from Wolin.api.recordApi import router as record_router
from Base.Api.authApi import register_auth_router


def init_router(app: FastAPI):
    # 注册认证路由（包含登录、注册、用户管理等 API）
    register_auth_router(app)

    app.include_router(core_router, prefix="/interview", tags=["Interview"])
    app.include_router(question_router, prefix="/interview", tags=["Interview Questions"])
    app.include_router(record_router, prefix="/interview", tags=["Interview Records"])
