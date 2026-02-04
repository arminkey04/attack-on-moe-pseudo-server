from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc
from typing import Optional
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.friend_relation import FriendRelation
from models.battle_log import BattleLog
from services.auth import AuthService


router = APIRouter(prefix="/parse/functions", tags=["functions"])


async def get_current_user(
    x_parse_session_token: Optional[str] = Header(None, alias="X-Parse-Session-Token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not x_parse_session_token:
        return None
    return await AuthService.get_user_by_session_token(db, x_parse_session_token)


class ClearSessionTokenRequest(BaseModel):
    username: str
    password: str


class GetUserSessionTokenRequest(BaseModel):
    authCode: str


class LinkGoogleIDRequest(BaseModel):
    authCode: str


class AddFriendRequest(BaseModel):
    targetUserID: str


@router.post("/clearSessionToken")
async def clear_session_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Clear all session tokens for a user"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Parse request body manually to handle both direct and wrapped formats
        body = await request.json()
        logger.info(f"clearSessionToken received body: {body}")

        # Handle both direct format and wrapped format (e.g., from Parse SDK)
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            raise HTTPException(status_code=400, detail={"code": 101, "error": "Missing username or password"})

        await AuthService.clear_user_sessions(db, username, password)
        return {"result": "success"}
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"clearSessionToken ValueError: {e}")
        raise HTTPException(status_code=400, detail={"code": 101, "error": str(e)})
    except Exception as e:
        logger.error(f"clearSessionToken unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail={"code": 101, "error": str(e)})


@router.post("/getUserSessionToken")
async def get_user_session_token(
    request: GetUserSessionTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get session token for a user by Google auth code.

    In a real implementation, this would:
    1. Exchange the auth code with Google for tokens
    2. Get the user's Google ID and email
    3. Find or create the user
    4. Return a session token

    For now, we'll simulate this by treating authCode as googleUserId
    """
    import json
    # In production, you would exchange authCode with Google OAuth
    # For now, we treat authCode as the googleUserId directly
    google_user_id = request.authCode

    # Try to find user by Google ID
    user = await AuthService.get_user_by_google_id(db, google_user_id)

    if not user:
        # User not found, return error with Google info in the format client expects
        # Client parses: {"code":101,"googleId":"...","email":"..."}
        error_data = json.dumps({
            "code": 101,
            "googleId": google_user_id,
            "email": f"{google_user_id}@google.com"
        })
        raise HTTPException(
            status_code=400,
            detail={
                "code": 101,
                "error": error_data
            }
        )

    # Create session for user
    session_token = await AuthService.create_session_for_user(db, user)

    return {"result": {"sessionToken": session_token}}


@router.post("/linkGoogleID")
async def link_google_id(
    request: LinkGoogleIDRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Link Google account to current user"""
    if not current_user:
        raise HTTPException(status_code=401, detail={"code": 209, "error": "Invalid session token"})

    # In production, exchange authCode with Google OAuth
    # For now, treat authCode as googleUserId
    google_user_id = request.authCode

    try:
        await AuthService.link_google_account(db, current_user, google_user_id)
        return {"result": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 202, "error": str(e)})


@router.post("/addFriend")
async def add_friend(
    request: AddFriendRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a friend relationship"""
    if not current_user:
        raise HTTPException(status_code=401, detail={"code": 209, "error": "Invalid session token"})

    target_user_id = request.targetUserID

    # Check if target user exists
    result = await db.execute(select(User).where(User.objectId == target_user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Target user not found"})

    # Check if relationship already exists
    result = await db.execute(
        select(FriendRelation).where(
            or_(
                and_(
                    FriendRelation.user1Id == current_user.objectId,
                    FriendRelation.user2Id == target_user_id
                ),
                and_(
                    FriendRelation.user1Id == target_user_id,
                    FriendRelation.user2Id == current_user.objectId
                )
            )
        )
    )
    existing_relation = result.scalar_one_or_none()

    if existing_relation:
        return {"result": existing_relation.to_dict()}

    # Create new friend relation
    relation = FriendRelation(
        user1Id=current_user.objectId,
        user2Id=target_user_id
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)

    return {"result": relation.to_dict()}


@router.post("/findLatestBattleLogPerFriend")
async def find_latest_battle_log_per_friend(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find the latest battle log for each friend"""
    if not current_user:
        raise HTTPException(status_code=401, detail={"code": 209, "error": "Invalid session token"})

    # Get all friend relations for current user
    result = await db.execute(
        select(FriendRelation).where(
            or_(
                FriendRelation.user1Id == current_user.objectId,
                FriendRelation.user2Id == current_user.objectId
            )
        )
    )
    relations = result.scalars().all()

    # Get friend IDs
    friend_ids = set()
    for relation in relations:
        if relation.user1Id == current_user.objectId:
            friend_ids.add(relation.user2Id)
        else:
            friend_ids.add(relation.user1Id)

    if not friend_ids:
        return {"result": []}

    # For each friend, get the latest battle log
    latest_logs = []
    for friend_id in friend_ids:
        # Get latest battle log where current user is sender and friend is receiver
        result = await db.execute(
            select(BattleLog)
            .where(
                and_(
                    BattleLog.senderId == current_user.objectId,
                    BattleLog.receiverId == friend_id
                )
            )
            .order_by(desc(BattleLog.createdAt))
            .limit(1)
        )
        log = result.scalar_one_or_none()
        if log:
            latest_logs.append(log)

    return {"result": [log.to_dict() for log in latest_logs]}
