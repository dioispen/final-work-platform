from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sql_repository import ProjectRepository, BidRepository, DeliverableRepository, IssueRepository
from models.review_repository import ReviewRepository
from .dependencies import require_auth

router = APIRouter(prefix="/client", tags=["client"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def client_dashboard(request: Request, user: dict = Depends(require_auth)):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    projects_all = ProjectRepository.get_by_client_id(user['user_id'])
    active_projects = [p for p in projects_all if p.get('status') != 'completed']
    return templates.TemplateResponse("client_dashboard.html", {
        "request": request,
        "user": user,
        "projects": active_projects
    })

# 已完成專案
@router.get("/completed", response_class=HTMLResponse)
async def client_completed_projects(request: Request, user: dict = Depends(require_auth)):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    projects_all = ProjectRepository.get_by_client_id(user['user_id'])
    completed_projects = [p for p in projects_all if p.get('status') == 'completed']
    return templates.TemplateResponse("client_completed.html", {
        "request": request,
        "user": user,
        "completed_projects": completed_projects
    })

@router.get("/project/new", response_class=HTMLResponse)
async def new_project_page(request: Request, user: dict = Depends(require_auth)):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        "project_form.html",
        {"request": request, "user": user, "project": None}
    )

@router.post("/project/new")
async def create_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    budget: int = Form(...),
    deadline: str = Form(...),
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    ProjectRepository.create(title, description, budget, user['user_id'], deadline)
    return RedirectResponse("/client/dashboard", status_code=303)

@router.get("/project/{project_id}/edit", response_class=HTMLResponse)
async def edit_project_page(
    request: Request,
    project_id: int,
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    project = ProjectRepository.get_by_id(project_id)
    if not project or project['client_id'] != user['user_id']:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "project_form.html",
        {"request": request, "user": user, "project": project}
    )

@router.post("/project/{project_id}/edit")
async def update_project(
    request: Request,
    project_id: int,
    title: str = Form(...),
    description: str = Form(...),
    budget: int = Form(...),
    deadline: str = Form(...),
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    ProjectRepository.update(
        project_id,
        title,
        description,
        budget,
        user['user_id'],
        deadline
    )
    return RedirectResponse("/client/dashboard", status_code=303)

# =========================
# 甲方查看投標列表（⭐ 新增評價資料在這裡）
# =========================
@router.get("/project/{project_id}/bids", response_class=HTMLResponse)
async def view_bids(
    request: Request,
    project_id: int,
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_by_id(project_id)
    bids = BidRepository.get_by_project_id(project_id)

    if not project or project['client_id'] != user['user_id']:
        raise HTTPException(status_code=404)

    # ⭐⭐ ⭐ 新增：替每一個 bid 補上乙方評價 ⭐⭐ ⭐
    for bid in bids:
        bid["contractor_reviews"] = ReviewRepository.get_average_and_comments(
            bid["contractor_id"]
        )

    return templates.TemplateResponse(
        "bids_list.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "bids": bids
        }
    )

@router.post("/bid/{bid_id}/accept")
async def accept_bid(
    request: Request,
    bid_id: int,
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)

    bid = BidRepository.get_by_id(bid_id)
    if not bid or bid['client_id'] != user['user_id']:
        raise HTTPException(status_code=404)

    BidRepository.accept(bid_id)
    ProjectRepository.assign_contractor(bid['project_id'], bid['contractor_id'])
    BidRepository.reject_others(bid['project_id'], bid_id)

    return RedirectResponse(
        f"/client/project/{bid['project_id']}/bids",
        status_code=303
    )

@router.get("/project/{project_id}/deliverable", response_class=HTMLResponse)
async def view_deliverable(
    request: Request,
    project_id: int,
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)

    project = ProjectRepository.get_by_id(project_id)
    if not project or project['client_id'] != user['user_id']:
        raise HTTPException(status_code=404)

    deliverables = DeliverableRepository.get_all_by_project_id(project_id)

    contractor_id = project.get("contractor_id")

    rating = ReviewRepository.get_user_avg_scores(contractor_id)
    reviews = ReviewRepository.get_reviews_for_user(contractor_id)
    has_reviewed = ReviewRepository.has_reviewed(project_id, user["user_id"])
    issues = IssueRepository.get_by_project(project_id)

    return templates.TemplateResponse(
        "deliverable_review.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "deliverables": deliverables,
            "rating": rating,
            "reviews": reviews,
            "has_reviewed": has_reviewed,
            "target_id": contractor_id,
            "issues": issues,
        },
    )

@router.post("/project/{project_id}/complete")
async def complete_project(
    request: Request,
    project_id: int,
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    ProjectRepository.complete(project_id, user['user_id'])
    return RedirectResponse("/client/dashboard", status_code=303)

@router.post("/project/{project_id}/reject")
async def reject_deliverable(
    request: Request,
    project_id: int,
    user: dict = Depends(require_auth)
):
    if user['role'] != 'client':
        raise HTTPException(status_code=403)
    ProjectRepository.reject(project_id, user['user_id'])
    return RedirectResponse("/client/dashboard", status_code=303)
