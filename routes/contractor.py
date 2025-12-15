from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sql_repository import ProjectRepository, BidRepository, DeliverableRepository, IssueRepository
from models.review_repository import ReviewRepository
from sql_repository import ProjectRepository, BidRepository, DeliverableRepository
from .dependencies import require_auth
import os
from datetime import datetime, timezone
import time

router = APIRouter(prefix="/contractor", tags=["contractor"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    return "".join(
        c if c.isalnum() or c in (' ', '.', '_', '-') else '_'
        for c in name
    ).replace(' ', '_')

# =========================
# Dashboard
# =========================
@router.get("/dashboard", response_class=HTMLResponse)
async def contractor_dashboard(request: Request, user: dict = Depends(require_auth)):
    if user['role'] != 'contractor':
        raise HTTPException(status_code=403)

    my_projects = ProjectRepository.get_contractor_projects(user['user_id'])
    for p in my_projects:
        deliverables = DeliverableRepository.get_all_by_project_id(p["id"])
        p["has_deliverable"] = len(deliverables) > 0

    available_projects = ProjectRepository.get_available_projects()

    return templates.TemplateResponse(
        "contractor_dashboard.html",
        {
            "request": request,
            "user": user,
            "my_projects": my_projects,
            "available_projects": available_projects
        }
    )

# =========================
# 乙方查看委託需求（含甲方評價）
# =========================
@router.get("/project/{project_id}", response_class=HTMLResponse)
async def view_project(request: Request, project_id: int, user: dict = Depends(require_auth)):
    if user['role'] != 'contractor':
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_project_with_client(project_id)
    if not project:
        raise HTTPException(status_code=404)

    my_bid = BidRepository.get_contractor_bid(project_id, user['user_id'])

    # ⭐ 取得甲方（client）的評價（修正：用位置參數）
    client_reviews = ReviewRepository.get_average_and_comments(
        project["client_id"]
    )
    # ⭐ 乙方在看甲方：顯示甲方過去收到的評價
    client_id = project["client_id"]
    client_rating = ReviewRepository.get_user_avg_scores(client_id)

    # ⭐ 乙方是否已經對此專案評價過甲方
    has_reviewed = ReviewRepository.has_reviewed(project_id, user['user_id'])
    issues = IssueRepository.get_by_project(project_id)

    return templates.TemplateResponse(
        "project_detail.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "my_bid": my_bid,
            "client_reviews": client_reviews,
            "rating": client_rating,
            "has_reviewed": has_reviewed,
            "target_id": client_id,
            "issues": issues,  # 評價對象：甲方
        },
    )

# =========================
# 投標
# =========================
@router.post("/project/{project_id}/bid")
async def submit_bid(
    request: Request,
    project_id: int,
    price: int = Form(...),
    message: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_auth)
):
    if user['role'] != 'contractor':
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404)

    deadline = project.get("deadline")
    now = datetime.now(timezone.utc)
    if deadline and isinstance(deadline, datetime) and now > deadline:
        raise HTTPException(status_code=400, detail="投標截止日期已過")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅接受 PDF 檔案")

    filename_orig = file.filename
    safe_name = _sanitize_filename(filename_orig)
    unique_name = f"proposal_{project_id}_{user['user_id']}_{int(time.time())}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    BidRepository.create(
        project_id,
        user["user_id"],
        price,
        message,
        filename_orig,
        file_path
    )

    return RedirectResponse(f"/contractor/project/{project_id}", status_code=303)

# =========================
# 上傳結案檔案
# =========================
@router.get("/project/{project_id}/upload", response_class=HTMLResponse)
async def upload_page(request: Request, project_id: int, user: dict = Depends(require_auth)):
    if user['role'] != 'contractor':
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_project_by_contractor(project_id, user['user_id'])
    if not project:
        raise HTTPException(status_code=404)

    deliverables = DeliverableRepository.get_all_by_project_id(project_id)

    return templates.TemplateResponse(
        "upload_deliverable.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "deliverables": deliverables
        }
    )

@router.post("/project/{project_id}/upload")
async def upload_deliverable(
    request: Request,
    project_id: int,
    message: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_auth)
):
    if user['role'] != 'contractor':
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_project_by_contractor(project_id, user['user_id'])
    if not project:
        raise HTTPException(status_code=404)

    filename_orig = file.filename
    safe_name = _sanitize_filename(filename_orig)
    unique_name = f"deliverable_{project_id}_{user['user_id']}_{int(time.time())}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    DeliverableRepository.create(project_id, filename_orig, file_path, message)

    return RedirectResponse("/contractor/dashboard", status_code=303)

# =========================
# 已完成專案
# =========================
@router.get("/completed", response_class=HTMLResponse)
async def completed_projects(request: Request, user: dict = Depends(require_auth)):
    if user['role'] != 'contractor':
        raise HTTPException(status_code=403)

    projects = ProjectRepository.get_contractor_projects(user["user_id"])
    completed_projects = [p for p in projects if p["status"] == "completed"]

    return templates.TemplateResponse(
        "contractor_completed.html",
        {
            "request": request,
            "user": user,
            "completed_projects": completed_projects
        }
    )
