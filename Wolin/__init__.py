# 挂载静态文件
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi import Request

from main import app

app.mount("/static", StaticFiles(directory="Wolin/static"), name="static")

# 模板配置
templates = Jinja2Templates(directory="Wolin/frontend")

@app.get("/", response_class=HTMLResponse)
async def interview_upload_page(request: Request):
    """面试分析上传页面"""
    return templates.TemplateResponse("interviewAnalysis.html", {"request": request})
