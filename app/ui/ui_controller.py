from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.dependencies import get_db_session
from src.users.user_repository import UserRepository
from src.users.user_models import CertaUser
from src.users.user_schemas import CertaUserResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/ui", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_db_session)):
    # counts
    total = session.query(CertaUser).count()
    busy = session.query(CertaUser).filter(CertaUser.is_locked == True).count()
    free = total - busy

    users = session.query(CertaUser).order_by(CertaUser.id).limit(200).all()
    users_data = [CertaUserResponse.model_validate(u).model_dump() for u in users]

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "counts": {"total": total, "busy": busy, "free": free}, "users": users_data},
    )


@router.get("/ui/users", response_class=HTMLResponse)
def users_table(request: Request, session: Session = Depends(get_db_session)):
    users = session.query(CertaUser).order_by(CertaUser.id).limit(500).all()
    users_data = [CertaUserResponse.model_validate(u).model_dump() for u in users]
    return templates.TemplateResponse("_users_table.html", {"request": request, "users": users_data})


@router.get("/ui/refresh", response_class=HTMLResponse)
def refresh(request: Request, session: Session = Depends(get_db_session)):
    total = session.query(CertaUser).count()
    busy = session.query(CertaUser).filter(CertaUser.is_locked == True).count()
    free = total - busy

    users = session.query(CertaUser).order_by(CertaUser.id).limit(500).all()
    users_data = [CertaUserResponse.model_validate(u).model_dump() for u in users]

    return templates.TemplateResponse(
        "_users_and_counts.html",
        {"request": request, "counts": {"total": total, "busy": busy, "free": free}, "users": users_data},
    )


@router.get("/ui/user/{user_id}", response_class=HTMLResponse)
def user_detail(request: Request, user_id: int, session: Session = Depends(get_db_session)):
    repo = UserRepository(session)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_data = CertaUserResponse.model_validate(user).model_dump()

    total = session.query(CertaUser).count()
    busy = session.query(CertaUser).filter(CertaUser.is_locked == True).count()
    free = total - busy

    return templates.TemplateResponse(
        "_detail_and_counts.html",
        {"request": request, "user": user_data, "counts": {"total": total, "busy": busy, "free": free}},
    )


@router.post("/ui/user/{user_id}/update", response_class=HTMLResponse)
async def user_update(request: Request, user_id: int, session: Session = Depends(get_db_session)):
    form = await request.form()
    repo = UserRepository(session)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update allowed fields from form
    role = form.get("role")
    is_locked = form.get("is_locked")
    is_healthy = form.get("is_healthy")
    tags = form.get("tags")

    if role is not None:
        user.role = role
    user.is_locked = True if is_locked in ("on", "true", "1") else False
    user.is_healthy = True if is_healthy in ("on", "true", "1") else False
    if tags is not None:
        user.tags = tags

    updated = repo.update(user)
    repo.commit()

    # recompute counts and fresh users list
    total = session.query(CertaUser).count()
    busy = session.query(CertaUser).filter(CertaUser.is_locked == True).count()
    free = total - busy

    users = session.query(CertaUser).order_by(CertaUser.id).limit(500).all()
    users_data = [CertaUserResponse.model_validate(u).model_dump() for u in users]

    user_data = CertaUserResponse.model_validate(updated).model_dump()
    return templates.TemplateResponse(
        "_detail_and_counts_and_users.html",
        {"request": request, "user": user_data, "users": users_data, "counts": {"total": total, "busy": busy, "free": free}},
    )


@router.post("/ui/user/{user_id}/delete", response_class=HTMLResponse)
def user_delete(request: Request, user_id: int, session: Session = Depends(get_db_session)):
    repo = UserRepository(session)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_locked:
        # can't delete locked user
        return templates.TemplateResponse(
            "_delete_failed.html",
            {"request": request, "user": CertaUserResponse.model_validate(user).model_dump()},
            status_code=status.HTTP_409_CONFLICT,
        )

    repo.delete(user)
    repo.commit()

    # recompute counts and fresh users list
    total = session.query(CertaUser).count()
    busy = session.query(CertaUser).filter(CertaUser.is_locked == True).count()
    free = total - busy

    users = session.query(CertaUser).order_by(CertaUser.id).limit(500).all()
    users_data = [CertaUserResponse.model_validate(u).model_dump() for u in users]

    # Return the cleared detail pane plus a fresh users table and counts (full swap via OOB on users-container)
    return templates.TemplateResponse(
        "_detail_and_counts_and_users.html",
        {"request": request, "user": {}, "users": users_data, "counts": {"total": total, "busy": busy, "free": free}},
    )
