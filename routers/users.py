from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any
from pydantic import BaseModel

from database import get_db
from models.user import User, format_parse_date
from services.auth import AuthService
from config import settings


router = APIRouter(prefix="/parse/users", tags=["users"])


class SignUpRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    googleUserId: Optional[str] = None


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    googleUserId: Optional[str] = None


async def get_current_user(
    x_parse_session_token: Optional[str] = Header(None, alias="X-Parse-Session-Token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not x_parse_session_token:
        return None
    return await AuthService.get_user_by_session_token(db, x_parse_session_token)


async def require_current_user(
    x_parse_session_token: Optional[str] = Header(None, alias="X-Parse-Session-Token"),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not x_parse_session_token:
        raise HTTPException(status_code=401, detail={"code": 209, "error": "Invalid session token"})
    user = await AuthService.get_user_by_session_token(db, x_parse_session_token)
    if not user:
        raise HTTPException(status_code=401, detail={"code": 209, "error": "Invalid session token"})
    return user


@router.post("")
async def sign_up(request: SignUpRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user"""
    try:
        user, session_token = await AuthService.create_user(
            db,
            username=request.username,
            password=request.password,
            email=request.email,
            google_user_id=request.googleUserId
        )
        result = user.to_dict()
        result["sessionToken"] = session_token
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 202, "error": str(e)})


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(require_current_user),
    x_parse_session_token: str = Header(None, alias="X-Parse-Session-Token")
):
    """Get current user info (become)"""
    result = current_user.to_dict()
    result["sessionToken"] = x_parse_session_token
    return result


@router.get("/{object_id}")
async def get_user(
    object_id: str,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID"""
    result = await db.execute(select(User).where(User.objectId == object_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})
    return user.to_dict()


@router.put("/{object_id}")
async def update_user(
    object_id: str,
    request: Request,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user"""
    if current_user.objectId != object_id:
        raise HTTPException(status_code=403, detail={"code": 119, "error": "Permission denied"})

    data = await request.json()

    if "username" in data:
        current_user.username = data["username"]
    if "password" in data:
        current_user.password_hash = AuthService.hash_password(data["password"])
    if "email" in data:
        current_user.email = data["email"]
    if "googleUserId" in data:
        # Handle delete operation: {"__op": "Delete"}
        if isinstance(data["googleUserId"], dict) and data["googleUserId"].get("__op") == "Delete":
            current_user.googleUserId = None
        else:
            current_user.googleUserId = data["googleUserId"]

    await db.commit()
    await db.refresh(current_user)

    return {"updatedAt": format_parse_date(current_user.updatedAt)}
