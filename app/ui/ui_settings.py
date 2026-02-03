# small independent module for settings page placeholder

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/ui/settings")
def settings_page(request: Request):
    return templates.TemplateResponse("_settings.html", {"request": request})
