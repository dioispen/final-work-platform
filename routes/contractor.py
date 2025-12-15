from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sql_repository import ProjectRepository, BidRepository, DeliverableRepository, IssueRepository
from models.review_repository import ReviewRepository
from .dependencies import require_auth
import os

router = APIRouter(prefix="/contractor", tags=["contractor"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/dashboard", response_class=HTMLResponse)
async def contractor_dashboard(request: Request, user: dict = Depends(require_auth)):
    if user["role"] != "contractor":
        raise HTTPException(status_code=403)

    my_projects = ProjectRepository.get_contractor_projects(user["user_id"])
    for p in my_projects:
        try:
            deliverable = DeliverableRepository.get_by_project_id(p.get("id"))
        except Exception:
            deliverable = None
        p["has_deliverable"] = bool(deliverable)

    available_projects = ProjectRepository.get_available_projects()

    return templates.TemplateResponse(
        "contractor_dashboard.html",
        {
            "request": request,
            "user": user,
            "my_projects": my_projects,
            "available_projects": available_projects,
        },
    )


# 專案詳情（乙方看到甲方需求＋甲方歷史評價）
@router.get("/project/{project_id}", response_class=HTMLResponse)
async def view_project(request: Request, project_id: int, user: dict = Depends(require_auth)):
    if user["role"] != "contractor":
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_project_with_client(project_id)
    if not project:
        raise HTTPException(status_code=404)

    user_id = user["user_id"]
    my_bid = BidRepository.get_contractor_bid(project_id, user_id)

    # ⭐ 乙方在看甲方：顯示甲方過去收到的評價
    client_id = project["client_id"]
    client_rating = ReviewRepository.get_user_avg_scores(client_id)
    client_reviews = ReviewRepository.get_reviews_for_user(client_id)

    # ⭐ 乙方是否已經對此專案評價過甲方
    has_reviewed = ReviewRepository.has_reviewed(project_id, user_id)
    issues = IssueRepository.get_by_project(project_id)

    return templates.TemplateResponse(
        "project_detail.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "my_bid": my_bid,
            "rating": client_rating,
            "reviews": client_reviews,
            "has_reviewed": has_reviewed,
            "target_id": client_id,
            "issues": issues,  # 評價對象：甲方
        },
    )


@router.post("/project/{project_id}/bid")
async def submit_bid(
    request: Request,
    project_id: int,
    price: int = Form(...),
    message: str = Form(...),
    user: dict = Depends(require_auth),
):
    if user["role"] != "contractor":
        raise HTTPException(status_code=403)

    BidRepository.create(project_id, user["user_id"], price, message)
    return RedirectResponse(f"/contractor/project/{project_id}", status_code=303)


@router.get("/project/{project_id}/upload", response_class=HTMLResponse)
async def upload_page(request: Request, project_id: int, user: dict = Depends(require_auth)):
    if user["role"] != "contractor":
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_project_by_contractor(project_id, user["user_id"])
    if not project:
        raise HTTPException(status_code=404)

    deliverable = DeliverableRepository.get_by_project_id(project_id)
    return templates.TemplateResponse(
        "upload_deliverable.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "deliverable": deliverable,
        },
    )


@router.post("/project/{project_id}/upload")
async def upload_deliverable(
    request: Request,
    project_id: int,
    message: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    if user["role"] != "contractor":
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_project_by_contractor(project_id, user["user_id"])
    if not project:
        raise HTTPException(status_code=404)

    if DeliverableRepository.get_by_project_id(project_id):
        DeliverableRepository.delete_by_project_id(project_id)

    filename = f"{project_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    DeliverableRepository.create(project_id, file.filename, file_path, message)
    return RedirectResponse("/contractor/dashboard", status_code=303)


@router.get("/completed", response_class=HTMLResponse)
async def completed_projects(request: Request, user: dict = Depends(require_auth)):
    if user["role"] != "contractor":
        raise HTTPException(status_code=403)

    all_projects = ProjectRepository.get_contractor_projects(user["user_id"])
    completed_projects = [p for p in all_projects if p["status"] == "completed"]

    return templates.TemplateResponse(
        "contractor_completed.html",
        {
            "request": request,
            "user": user,
            "completed_projects": completed_projects,
        },
    )
