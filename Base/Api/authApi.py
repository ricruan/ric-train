from pydantic import BaseModel, Field
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from Base.RicUtils.httpUtils import HttpResponse
from Base.Service.authService import AuthService


router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    email: Optional[str] = None
    phone: Optional[str] = None
    source_module: str = Field("default", description="来源模块")
    extra_data: Optional[dict] = None


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新 Token")


security = HTTPBearer(auto_error=False)


@router.post("/register")
def register(req: RegisterRequest):
    ok, user, msg = AuthService.register(
        username=req.username,
        password=req.password,
        source_module=req.source_module,
        email=req.email,
        phone=req.phone,
        extra_data=req.extra_data,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return HttpResponse.ok(
        data={"id": user.id, "username": user.username, "source_module": user.source_module},
        msg="注册成功",
    )


@router.post("/login")
def login(req: LoginRequest):
    ok, user, access_token, refresh_token, msg = AuthService.login(
        username=req.username,
        password=req.password,
    )
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return HttpResponse.ok(
        data={
            "id": user.id,
            "username": user.username,
            "source_module": user.source_module,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        msg="登录成功",
    )


@router.post("/refresh")
def refresh(req: RefreshRequest):
    ok, new_token, msg = AuthService.refresh_access_token(req.refresh_token)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return HttpResponse.ok(data={"access_token": new_token})


@router.get("/me")
def me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    user = AuthService.get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return HttpResponse.ok(data={
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "source_module": user.source_module,
        "status": user.status,
    })


def register_auth_router(app):
    app.include_router(router)
