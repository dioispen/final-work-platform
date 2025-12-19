from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone, timedelta

from sql_repository import ProjectRepository, ReviewRepository
from .dependencies import require_auth

router = APIRouter(prefix="/review", tags=["review"])
templates = Jinja2Templates(directory="templates")


def _within_review_window(project: dict) -> bool:
	# 支援常見欄位名稱
	completed = project.get("updated_at")
	if not completed:
		return False
	# 若為字串，嘗試用 ISO 格式解析（處理 Z 時區）
	if isinstance(completed, str):
		try:
			completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
		except Exception:
			return False
	# 必須為 datetime
	if not isinstance(completed, datetime):
		return False
	# 比較時考慮時區資訊
	if completed.tzinfo is None:
		now = datetime.now(timezone.utc).replace(tzinfo=None)
	else:
		now = datetime.now(timezone.utc)
	# 若 completed 有 tzinfo，確保 now 也在同一 time zone 上（已處理）
	return (now - completed) <= timedelta(days=3)


# =========================
# 顯示評價頁面（GET）
# =========================
@router.get("/{project_id}")
async def review_page(
    project_id: int,
    request: Request,
    user: dict = Depends(require_auth)
):
    project = ProjectRepository.get_by_id(project_id)

    # 專案不存在或尚未完成
    if not project or project["status"] != "completed":
        raise HTTPException(status_code=403)

    # 新增：限完成後 7 天內可評價
    if not _within_review_window(project):
        raise HTTPException(status_code=403, detail='not in deadline')

    # 防止重複評價
    if ReviewRepository.has_reviewed(project_id, user["user_id"]):
       return templates.TemplateResponse(
        "review/already_reviewed.html",
        {
            "request": request,
            "user": user,
            "project": project
        }
    )

    # 判斷評誰
    if user["role"] == "client":
        reviewee_id = project["contractor_id"]
        reviewee_role = "contractor"
    else:
        reviewee_id = project["client_id"]
        reviewee_role = "client"

    return templates.TemplateResponse(
        "review/new.html",   # 確認 templates/new.html 存在
        {
            "user": user,
            "request": request,
            "project_id": project_id,
            "reviewee_id": reviewee_id,
            "reviewee_role": reviewee_role
        }
    )


# =========================
# 送出評價（POST）
# =========================
@router.post("/{project_id}")
async def submit_review(
    project_id: int,
    request: Request,
    user: dict = Depends(require_auth)
):
    project = ProjectRepository.get_by_id(project_id)

    # 再次檢查：專案存在且在 7 天內
    if not project or project["status"] != "completed" or not _within_review_window(project):
        raise HTTPException(status_code=403, detail="not allowed")

    form = await request.form()

    ReviewRepository.create(
        project_id=project_id,
        reviewer_id=user["user_id"],
        reviewee_id=int(form["reviewee_id"]),
        score_1=int(form["score_1"]),
        score_2=int(form["score_2"]),
        score_3=int(form["score_3"]),
        comment=form.get("comment")
    )

    # 評完回 completed
    if user["role"] == "client":
        return RedirectResponse("/client/completed", status_code=303)
    else:
        return RedirectResponse("/contractor/completed", status_code=303)
