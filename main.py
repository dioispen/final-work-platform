# main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Routers
from routes.auth import router as auth_router
from routes.client import router as client_router
from routes.contractor import router as contractor_router
from routes.review import router as review_router   # ⭐ 必須放在前面避免路徑衝突
from routes.issue import router as issue_router

app = FastAPI()

# Session
app.add_middleware(SessionMiddleware, secret_key="simple-session-key")

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Root redirect (依身分導向 dashboard)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("role") == "client":
        return RedirectResponse("/client/dashboard", status_code=303)
    else:
        return RedirectResponse("/contractor/dashboard", status_code=303)


# 404 → 導回首頁
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return RedirectResponse(url="/", status_code=303)


# ⭐ 先載入 review router（避免路徑 /client/project/... 搶先吃掉 /review/form）
app.include_router(review_router)

# 其他 routers
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(contractor_router)
app.include_router(issue_router)
