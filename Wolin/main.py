import logging

from RicUtils.config.logConfig import setup_logging
from Wolin.router.router import init_router

# 日志配置初始化
setup_logging()

logger = logging.getLogger(__name__)
from Wolin.frontend.fastapi_init import frontend_init

from fastapi import FastAPI

logger.info("启动自Wolin包")
app = FastAPI()
# 初始化前端
frontend_init(app=app)
init_router(app=app)





if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000)