import logging
from Base.Config.logConfig import setup_logging

# 日志配置初始化
setup_logging("wolin")

logger = logging.getLogger(__name__)

# 注册数据库连接（在导入任何其他 Wolin 模块之前）
from Wolin.db.connectionInit import register_wolin_connection
register_wolin_connection()

from Wolin.frontend.fastapi_init import frontend_init
from Wolin.router.router import init_router

from fastapi import FastAPI

logger.info("启动自 Wolin 包")
app = FastAPI()
# 初始化前端
frontend_init(app=app)
init_router(app=app)





if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app, host="0.0.0.0", port=8002)
