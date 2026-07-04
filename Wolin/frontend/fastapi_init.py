# 挂载静态文件
from pathlib import Path

from starlette.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from fastapi import Request

from fastapi import FastAPI
# 定位当前目录作为模板根路径 （如此 需要 .html 文件和当前文件同目录下）
BASE_DIR = Path(__file__).parent


def frontend_init(app : FastAPI):
    # 模板配置
    templates = Jinja2Templates(directory=BASE_DIR)

    @app.get("/", response_class=RedirectResponse)
    async def root_redirect(request: Request):
        """根路径重定向到前端面试分析页面"""
        return RedirectResponse(url="http://localhost:3001/")

    @app.get("/interview-analysis", response_class=HTMLResponse)
    async def interview_upload_page(request: Request):
        """面试分析上传页面"""
        return templates.TemplateResponse("interviewAnalysis.html", {"request": request})

    @app.get("/camera-test", response_class=HTMLResponse)
    async def camera_test_page(request: Request):
        """摄像头测试页面"""
        return templates.TemplateResponse("camera-test.html", {"request": request})

    @app.get("/interview-chat", response_class=HTMLResponse)
    async def interview_chat_page(request: Request):
        """模拟面试对话页面"""
        return templates.TemplateResponse("interviewChat.html", {"request": request})

    @app.get("/interview-record-manager", response_class=HTMLResponse)
    async def interview_record_manager_page(request: Request):
        """面试记录管理页面"""
        return templates.TemplateResponse("interviewRecordManager.html", {"request": request})
