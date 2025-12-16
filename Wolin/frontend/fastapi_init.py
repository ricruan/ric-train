# 挂载静态文件
from pathlib import Path

from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi import Request

from fastapi import FastAPI
BASE_DIR = Path(__file__).parent


def frontend_init(app : FastAPI):
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    # 模板配置
    templates = Jinja2Templates(directory=BASE_DIR)

    @app.get("/", response_class=HTMLResponse)
    async def interview_upload_page(request: Request):
        """面试分析上传页面"""
        return templates.TemplateResponse("interviewAnalysis.html", {"request": request})
