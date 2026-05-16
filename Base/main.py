from Base.Api.ai.chatApi import register_ai_chat_router
from Base.Api.authApi import register_auth_router
from Base.Config.logConfig import setup_logging
from Base.Service.scheduler.auto_register import auto_register_all_scheduler

setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_ai_chat_router(app)
register_auth_router(app)

# 自动注册定时任务
auto_register_all_scheduler()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app, host="0.0.0.0", port=8010)
