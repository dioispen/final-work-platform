# routes/issue.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from .dependencies import require_auth
from sql_repository import IssueRepository, ProjectRepository

router = APIRouter(prefix="/issue", tags=["issue"])
templates = Jinja2Templates(directory="templates")

# 1. 建立 Issue (通常由 Client 在驗收頁面發起)
@router.post("/create")
async def create_issue(
    request: Request, 
    project_id: int = Form(...), 
    title: str = Form(...), 
    user: dict = Depends(require_auth)
):

    issue_id = IssueRepository.create_issue(project_id, user["user_id"], title)
    
    # 開完後直接導向該 Issue 的討論頁
    return RedirectResponse(f"/issue/{issue_id}", status_code=303)

# 2. 查看 Issue 詳情與留言 (雙方都能看)
@router.get("/{issue_id}", response_class=HTMLResponse)
async def issue_detail(request: Request, issue_id: int, user: dict = Depends(require_auth)):
    issue = IssueRepository.get_by_id(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    project = ProjectRepository.get_by_id(issue["project_id"])
    comments = IssueRepository.get_comments(issue_id)
    
    # 判斷當前使用者在這個 Issue 裡的角色
    return templates.TemplateResponse("issue_detail.html", {
        "request": request,
        "user": user,
        "issue": issue,
        "project": project,
        "comments": comments
    })

# 3. 發送留言 (雙方都能留)
@router.post("/{issue_id}/comment")
async def post_comment(
    request: Request, 
    issue_id: int, 
    message: str = Form(...), 
    user: dict = Depends(require_auth)
):
    IssueRepository.add_comment(issue_id, user["user_id"], message)
    return RedirectResponse(f"/issue/{issue_id}", status_code=303)

# 4. 解決/關閉 Issue
@router.post("/{issue_id}/close")
async def close_issue(request: Request, issue_id: int, user: dict = Depends(require_auth)):
    # 權限檢查：只有 Client 可以關閉 Issue
    if user["role"] != "client":
        raise HTTPException(status_code=403, detail="Only client can close issues")
        
    IssueRepository.close_issue(issue_id)
    return RedirectResponse(f"/issue/{issue_id}", status_code=303)