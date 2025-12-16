from Wolin.api.coreApi import router as interview_router
from main import app

app.include_router(interview_router, prefix="/interview", tags=["Interview"])
