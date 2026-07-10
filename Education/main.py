import logging
from Base.Config.logConfig import setup_logging
from Education.api.router import router_register
from Education.frontend.register import frontend_init

# 日志配置初始化
setup_logging()

logger = logging.getLogger(__name__)


from fastapi import FastAPI

app = FastAPI()

router_register(app=app)
frontend_init(app=app)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app, host="0.0.0.0", port=8022)