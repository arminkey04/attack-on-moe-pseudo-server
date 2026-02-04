from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from database import get_db
from services.auth import AuthService


router = APIRouter(prefix="/parse", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/login")
async def login_get(
    username: str = Query(...),
    password: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Login user (GET method - used by Parse SDK)"""
    try:
        user, session_token = await AuthService.login(db, username, password)
        result = user.to_dict()
        result["sessionToken"] = session_token
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 101, "error": str(e)})


@router.post("/login")
async def login_post(
    request: Request,
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Login user (POST method)

    Handles both:
    1. Standard POST with JSON body containing username/password
    2. Parse SDK method override: POST with _method=GET and credentials in query string
    """
    try:
        # Try to get credentials from query string first (Parse SDK method override)
        if username and password:
            user, session_token = await AuthService.login(db, username, password)
        else:
            # Fall back to reading from body
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
            if not username or not password:
                raise HTTPException(status_code=400, detail={"code": 101, "error": "Missing username or password"})
            user, session_token = await AuthService.login(db, username, password)

        result = user.to_dict()
        result["sessionToken"] = session_token
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 101, "error": str(e)})


@router.post("/logout")
async def logout(
    x_parse_session_token: Optional[str] = Header(None, alias="X-Parse-Session-Token"),
    db: AsyncSession = Depends(get_db)
):
    """Logout user"""
    if x_parse_session_token:
        await AuthService.logout(db, x_parse_session_token)
    return {}
