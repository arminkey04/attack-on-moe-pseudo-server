from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc
from typing import Optional, Any
from datetime import datetime, timezone
import json

from database import get_db
from models.user import User, format_parse_date
from models.user_summary import UserSummary
from models.game_data import GameData
from models.friend_relation import FriendRelation
from models.battle_log import BattleLog
from models.notice import Notice
from models.drop_box import DropBox
from services.auth import AuthService


router = APIRouter(prefix="/parse/classes", tags=["classes"])


async def get_current_user(
    x_parse_session_token: Optional[str] = Header(None, alias="X-Parse-Session-Token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not x_parse_session_token:
        return None
    return await AuthService.get_user_by_session_token(db, x_parse_session_token)


def parse_where_clause(where_json: str) -> dict:
    """Parse the where clause from JSON string"""
    if not where_json:
        return {}
    try:
        return json.loads(where_json)
    except:
        return {}


def parse_pointer(pointer: Any) -> Optional[str]:
    """Extract objectId from a Parse Pointer or return None for null values"""
    if pointer is None:
        return None
    if isinstance(pointer, dict) and pointer.get("__type") == "Pointer":
        return pointer.get("objectId")
    if isinstance(pointer, str):
        return pointer
    return None


def parse_date(date_obj: Any) -> Optional[datetime]:
    """Parse a Parse Date object"""
    if isinstance(date_obj, dict) and date_obj.get("__type") == "Date":
        iso_str = date_obj.get("iso", "")
        if iso_str:
            try:
                iso_str = iso_str.replace("Z", "+00:00")
                return datetime.fromisoformat(iso_str)
            except:
                pass
    return None


# ==================== _User (Parse internal user class) ====================

@router.get("/_User")
async def query_users(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Query User objects (Parse uses _User as class name)"""
    query = select(User)

    where_dict = parse_where_clause(where)

    if "objectId" in where_dict:
        query = query.where(User.objectId == where_dict["objectId"])

    if "username" in where_dict:
        query = query.where(User.username == where_dict["username"])

    if order:
        if order.startswith("-"):
            query = query.order_by(desc(getattr(User, order[1:], User.createdAt)))
        else:
            query = query.order_by(asc(getattr(User, order, User.createdAt)))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    return {"results": [u.to_parse_response() for u in users]}


@router.post("/_User")
async def create_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create User object (signup via classes/_User)"""
    data = await request.json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail={"code": 200, "error": "Username and password required"})

    # Check if username exists
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail={"code": 202, "error": "Username already taken"})

    # Create user
    user = User(username=username, email=data.get("email"))
    user.set_password(password)

    # Set additional fields
    if "googleUserId" in data:
        user.googleUserId = data["googleUserId"]

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create session
    session_token = await AuthService.create_session_for_user(db, user)

    return {
        "objectId": user.objectId,
        "createdAt": format_parse_date(user.createdAt),
        "sessionToken": session_token
    }


@router.get("/_User/{object_id}")
async def get_user(
    object_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get User by objectId"""
    result = await db.execute(select(User).where(User.objectId == object_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    return user.to_parse_response()


@router.put("/_User/{object_id}")
async def update_user(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update User object"""
    result = await db.execute(select(User).where(User.objectId == object_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    data = await request.json()

    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]
    if "password" in data:
        user.set_password(data["password"])
    if "googleUserId" in data:
        # Handle delete operation: {"__op": "Delete"}
        if isinstance(data["googleUserId"], dict) and data["googleUserId"].get("__op") == "Delete":
            user.googleUserId = None
        else:
            user.googleUserId = data["googleUserId"]

    await db.commit()
    await db.refresh(user)

    return {"updatedAt": format_parse_date(user.updatedAt)}


@router.post("/_User/{object_id}")
async def update_user_post(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update User object (POST with _method override)"""
    data = await request.json()

    # Handle _method override from Parse SDK
    method = data.get("_method", "POST")
    if method == "PUT":
        result = await db.execute(select(User).where(User.objectId == object_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

        if "username" in data:
            user.username = data["username"]
        if "email" in data:
            user.email = data["email"]
        if "password" in data:
            user.set_password(data["password"])
        if "googleUserId" in data:
            # Handle delete operation: {"__op": "Delete"}
            if isinstance(data["googleUserId"], dict) and data["googleUserId"].get("__op") == "Delete":
                user.googleUserId = None
            else:
                user.googleUserId = data["googleUserId"]

        await db.commit()
        await db.refresh(user)

        return {"updatedAt": format_parse_date(user.updatedAt)}

    raise HTTPException(status_code=405, detail={"code": 1, "error": "Method not allowed"})


# ==================== UserSummary ====================

async def _query_user_summary(
    where: Optional[str],
    order: Optional[str],
    limit: int,
    skip: int,
    db: AsyncSession
):
    """Internal function to query UserSummary"""
    query = select(UserSummary)

    where_dict = parse_where_clause(where)

    # Handle user pointer filter - support both Pointer and null
    if "user" in where_dict:
        user_value = where_dict["user"]
        if user_value is None:
            # Query for records where userId is NULL
            query = query.where(UserSummary.userId == None)
        else:
            user_id = parse_pointer(user_value)
            if user_id:
                query = query.where(UserSummary.userId == user_id)

    if order:
        if order.startswith("-"):
            query = query.order_by(desc(getattr(UserSummary, order[1:], UserSummary.createdAt)))
        else:
            query = query.order_by(asc(getattr(UserSummary, order, UserSummary.createdAt)))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    summaries = result.scalars().all()

    return {"results": [s.to_dict() for s in summaries]}


@router.get("/UserSummary")
async def query_user_summary(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query UserSummary objects (GET)"""
    return await _query_user_summary(where, order, limit, skip, db)


@router.post("/UserSummary")
async def create_or_query_user_summary(
    request: Request,
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create UserSummary object or query (POST with where param)"""
    # If where parameter exists, this is a query request
    if where is not None:
        return await _query_user_summary(where, order, limit, skip, db)

    # Otherwise, create new object
    data = await request.json()

    user_id = parse_pointer(data.get("user"))
    if not user_id:
        raise HTTPException(status_code=400, detail={"code": 105, "error": "Invalid user pointer"})

    # Check if UserSummary already exists for this user
    result = await db.execute(select(UserSummary).where(UserSummary.userId == user_id))
    existing_summary = result.scalar_one_or_none()

    if existing_summary:
        # Return existing summary instead of creating new one
        # This prevents client from overwriting server-side currency values
        return {
            "objectId": existing_summary.objectId,
            "createdAt": format_parse_date(existing_summary.createdAt)
        }

    # Create new UserSummary only if it doesn't exist
    summary = UserSummary(
        userId=user_id,
        displayName=data.get("displayName", ""),
        friendPoint=data.get("friendPoint", 0),
        friendLimit=data.get("friendLimit", 5),
        # Currency fields: use client values only for new users
        ruby=data.get("ruby", 0),
        gem=data.get("gem", 0),
        moecrystal=data.get("moecrystal", 0)
    )
    db.add(summary)
    await db.commit()
    await db.refresh(summary)

    return {
        "objectId": summary.objectId,
        "createdAt": format_parse_date(summary.createdAt)
    }


@router.put("/UserSummary/{object_id}")
async def update_user_summary(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update UserSummary object"""
    result = await db.execute(select(UserSummary).where(UserSummary.objectId == object_id))
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    data = await request.json()

    # Only allow updating non-currency fields from client
    # Currency fields (ruby, gem, moecrystal) are protected and can only be modified via admin
    if "displayName" in data:
        summary.displayName = data["displayName"]
    if "friendPoint" in data:
        summary.friendPoint = data["friendPoint"]
    if "friendLimit" in data:
        summary.friendLimit = data["friendLimit"]

    # Currency fields are protected - ignore client attempts to modify them
    # if "ruby" in data:
    #     summary.ruby = data["ruby"]
    # if "gem" in data:
    #     summary.gem = data["gem"]
    # if "moecrystal" in data:
    #     summary.moecrystal = data["moecrystal"]

    await db.commit()
    await db.refresh(summary)

    return {"updatedAt": format_parse_date(summary.updatedAt)}


@router.post("/UserSummary/{object_id}")
async def update_user_summary_post(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update UserSummary object (POST with _method override)"""
    data = await request.json()

    # Handle _method override from Parse SDK
    method = data.get("_method", "POST")
    if method == "PUT":
        result = await db.execute(select(UserSummary).where(UserSummary.objectId == object_id))
        summary = result.scalar_one_or_none()

        if not summary:
            raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

        # Only allow updating non-currency fields from client
        # Currency fields (ruby, gem, moecrystal) are protected and can only be modified via admin
        if "displayName" in data:
            summary.displayName = data["displayName"]
        if "friendPoint" in data:
            summary.friendPoint = data["friendPoint"]
        if "friendLimit" in data:
            summary.friendLimit = data["friendLimit"]

        # Currency fields are protected - ignore client attempts to modify them
        # if "ruby" in data:
        #     summary.ruby = data["ruby"]
        # if "gem" in data:
        #     summary.gem = data["gem"]
        # if "moecrystal" in data:
        #     summary.moecrystal = data["moecrystal"]

        await db.commit()
        await db.refresh(summary)

        return {"updatedAt": format_parse_date(summary.updatedAt)}

    raise HTTPException(status_code=405, detail={"code": 1, "error": "Method not allowed"})


# ==================== GameData ====================

async def _query_game_data(
    where: Optional[str],
    order: Optional[str],
    limit: int,
    skip: int,
    db: AsyncSession
):
    """Internal function to query GameData"""
    query = select(GameData)

    where_dict = parse_where_clause(where)

    if "user" in where_dict:
        user_value = where_dict["user"]
        if user_value is None:
            query = query.where(GameData.userId == None)
        else:
            user_id = parse_pointer(user_value)
            if user_id:
                query = query.where(GameData.userId == user_id)

    if order:
        if order.startswith("-"):
            query = query.order_by(desc(getattr(GameData, order[1:], GameData.updatedAt)))
        else:
            query = query.order_by(asc(getattr(GameData, order, GameData.updatedAt)))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    game_data_list = result.scalars().all()

    return {"results": [gd.to_dict() for gd in game_data_list]}


@router.get("/GameData")
async def query_game_data(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query GameData objects"""
    return await _query_game_data(where, order, limit, skip, db)


@router.post("/GameData")
async def create_or_query_game_data(
    request: Request,
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create GameData object or query"""
    if where is not None:
        return await _query_game_data(where, order, limit, skip, db)

    data = await request.json()

    user_id = parse_pointer(data.get("user"))
    if not user_id:
        raise HTTPException(status_code=400, detail={"code": 105, "error": "Invalid user pointer"})

    game_data = GameData(
        userId=user_id,
        data=data.get("data", "")
    )
    db.add(game_data)
    await db.commit()
    await db.refresh(game_data)

    return {
        "objectId": game_data.objectId,
        "createdAt": format_parse_date(game_data.createdAt)
    }


@router.put("/GameData/{object_id}")
async def update_game_data(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update GameData object"""
    result = await db.execute(select(GameData).where(GameData.objectId == object_id))
    game_data = result.scalar_one_or_none()

    if not game_data:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    data = await request.json()

    if "data" in data:
        game_data.data = data["data"]

    await db.commit()
    await db.refresh(game_data)

    return {"updatedAt": format_parse_date(game_data.updatedAt)}


@router.post("/GameData/{object_id}")
async def update_game_data_post(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update GameData object (POST with _method override)"""
    data = await request.json()

    # Handle _method override from Parse SDK
    method = data.get("_method", "POST")
    if method == "PUT":
        result = await db.execute(select(GameData).where(GameData.objectId == object_id))
        game_data = result.scalar_one_or_none()

        if not game_data:
            raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

        if "data" in data:
            game_data.data = data["data"]

        await db.commit()
        await db.refresh(game_data)

        return {"updatedAt": format_parse_date(game_data.updatedAt)}

    raise HTTPException(status_code=405, detail={"code": 1, "error": "Method not allowed"})


# ==================== FriendRelation ====================

async def _query_friend_relation(
    where: Optional[str],
    order: Optional[str],
    limit: int,
    skip: int,
    db: AsyncSession
):
    """Internal function to query FriendRelation"""
    query = select(FriendRelation)

    where_dict = parse_where_clause(where)

    if "users" in where_dict:
        user_id = parse_pointer(where_dict["users"])
        if user_id:
            query = query.where(
                or_(
                    FriendRelation.user1Id == user_id,
                    FriendRelation.user2Id == user_id
                )
            )

    if order:
        if order.startswith("-"):
            query = query.order_by(desc(getattr(FriendRelation, order[1:], FriendRelation.createdAt)))
        else:
            query = query.order_by(asc(getattr(FriendRelation, order, FriendRelation.createdAt)))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    relations = result.scalars().all()

    return {"results": [r.to_dict() for r in relations]}


@router.get("/FriendRelation")
async def query_friend_relation(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query FriendRelation objects"""
    return await _query_friend_relation(where, order, limit, skip, db)


@router.post("/FriendRelation")
async def create_or_query_friend_relation(
    request: Request,
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create FriendRelation object or query"""
    if where is not None:
        return await _query_friend_relation(where, order, limit, skip, db)

    data = await request.json()

    users = data.get("users", [])
    if len(users) != 2:
        raise HTTPException(status_code=400, detail={"code": 105, "error": "Invalid users array"})

    user1_id = parse_pointer(users[0])
    user2_id = parse_pointer(users[1])

    if not user1_id or not user2_id:
        raise HTTPException(status_code=400, detail={"code": 105, "error": "Invalid user pointers"})

    relation = FriendRelation(
        user1Id=user1_id,
        user2Id=user2_id
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)

    return {
        "objectId": relation.objectId,
        "createdAt": format_parse_date(relation.createdAt)
    }


@router.delete("/FriendRelation/{object_id}")
async def delete_friend_relation(
    object_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete FriendRelation object"""
    result = await db.execute(select(FriendRelation).where(FriendRelation.objectId == object_id))
    relation = result.scalar_one_or_none()

    if not relation:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    await db.delete(relation)
    await db.commit()

    return {}


# ==================== BattleLog ====================

async def _query_battle_log(
    where: Optional[str],
    order: Optional[str],
    limit: int,
    skip: int,
    db: AsyncSession
):
    """Internal function to query BattleLog"""
    query = select(BattleLog)

    where_dict = parse_where_clause(where)

    conditions = []

    if "sender" in where_dict:
        sender_value = where_dict["sender"]
        if sender_value is None:
            conditions.append(BattleLog.senderId == None)
        else:
            sender_id = parse_pointer(sender_value)
            if sender_id:
                conditions.append(BattleLog.senderId == sender_id)

    if "receiver" in where_dict:
        receiver_value = where_dict["receiver"]
        if receiver_value is None:
            conditions.append(BattleLog.receiverId == None)
        else:
            receiver_id = parse_pointer(receiver_value)
            if receiver_id:
                conditions.append(BattleLog.receiverId == receiver_id)

    if "receiverClaim" in where_dict:
        conditions.append(BattleLog.receiverClaim == where_dict["receiverClaim"])

    if "senderClaim" in where_dict:
        conditions.append(BattleLog.senderClaim == where_dict["senderClaim"])

    if "expired" in where_dict:
        conditions.append(BattleLog.expired == where_dict["expired"])

    if "objectId" in where_dict:
        conditions.append(BattleLog.objectId == where_dict["objectId"])

    if conditions:
        query = query.where(and_(*conditions))

    if order:
        if order.startswith("-"):
            field_name = order[1:]
            if field_name == "createdAt":
                query = query.order_by(desc(BattleLog.createdAt))
            else:
                query = query.order_by(desc(getattr(BattleLog, field_name, BattleLog.createdAt)))
        else:
            if order == "createdAt":
                query = query.order_by(asc(BattleLog.createdAt))
            else:
                query = query.order_by(asc(getattr(BattleLog, order, BattleLog.createdAt)))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {"results": [log.to_dict() for log in logs]}


@router.get("/BattleLog")
async def query_battle_log(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query BattleLog objects"""
    return await _query_battle_log(where, order, limit, skip, db)


@router.post("/BattleLog")
async def create_or_query_battle_log(
    request: Request,
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create BattleLog object or query"""
    if where is not None:
        return await _query_battle_log(where, order, limit, skip, db)

    data = await request.json()

    sender_id = parse_pointer(data.get("sender"))
    receiver_id = parse_pointer(data.get("receiver"))

    if not sender_id or not receiver_id:
        raise HTTPException(status_code=400, detail={"code": 105, "error": "Invalid sender or receiver pointer"})

    received_at = parse_date(data.get("receivedAt"))

    battle_log = BattleLog(
        senderId=sender_id,
        receiverId=receiver_id,
        senderScore=data.get("senderScore", 0),
        receiverScore=data.get("receiverScore", 0),
        senderWin=data.get("senderWin", False),
        senderClaim=data.get("senderClaim", False),
        receiverClaim=data.get("receiverClaim", False),
        expired=data.get("expired", False),
        receivedAt=received_at
    )
    db.add(battle_log)
    await db.commit()
    await db.refresh(battle_log)

    return {
        "objectId": battle_log.objectId,
        "createdAt": format_parse_date(battle_log.createdAt)
    }


@router.put("/BattleLog/{object_id}")
async def update_battle_log(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update BattleLog object"""
    result = await db.execute(select(BattleLog).where(BattleLog.objectId == object_id))
    battle_log = result.scalar_one_or_none()

    if not battle_log:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    data = await request.json()

    if "senderScore" in data:
        battle_log.senderScore = data["senderScore"]
    if "receiverScore" in data:
        battle_log.receiverScore = data["receiverScore"]
    if "senderWin" in data:
        battle_log.senderWin = data["senderWin"]
    if "senderClaim" in data:
        battle_log.senderClaim = data["senderClaim"]
    if "receiverClaim" in data:
        battle_log.receiverClaim = data["receiverClaim"]
    if "expired" in data:
        battle_log.expired = data["expired"]
    if "receivedAt" in data:
        battle_log.receivedAt = parse_date(data["receivedAt"]) or datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(battle_log)

    return {"updatedAt": format_parse_date(battle_log.updatedAt)}


@router.post("/BattleLog/{object_id}")
async def update_battle_log_post(
    object_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update BattleLog object (POST with _method override)"""
    data = await request.json()

    # Handle _method override from Parse SDK
    method = data.get("_method", "POST")
    if method == "PUT":
        result = await db.execute(select(BattleLog).where(BattleLog.objectId == object_id))
        battle_log = result.scalar_one_or_none()

        if not battle_log:
            raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

        if "senderScore" in data:
            battle_log.senderScore = data["senderScore"]
        if "receiverScore" in data:
            battle_log.receiverScore = data["receiverScore"]
        if "senderWin" in data:
            battle_log.senderWin = data["senderWin"]
        if "senderClaim" in data:
            battle_log.senderClaim = data["senderClaim"]
        if "receiverClaim" in data:
            battle_log.receiverClaim = data["receiverClaim"]
        if "expired" in data:
            battle_log.expired = data["expired"]
        if "receivedAt" in data:
            battle_log.receivedAt = parse_date(data["receivedAt"]) or datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(battle_log)

        return {"updatedAt": format_parse_date(battle_log.updatedAt)}

    raise HTTPException(status_code=405, detail={"code": 1, "error": "Method not allowed"})


@router.delete("/BattleLog/{object_id}")
async def delete_battle_log(
    object_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete BattleLog object"""
    result = await db.execute(select(BattleLog).where(BattleLog.objectId == object_id))
    battle_log = result.scalar_one_or_none()

    if not battle_log:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    await db.delete(battle_log)
    await db.commit()

    return {}


# ==================== Notice ====================

async def _query_notice(
    where: Optional[str],
    order: Optional[str],
    limit: int,
    skip: int,
    db: AsyncSession
):
    """Internal function to query Notice"""
    query = select(Notice)

    # Filter out notices with empty imageURL (they cause client to hang)
    query = query.where(Notice.imageURL != None).where(Notice.imageURL != "")

    if order:
        if order.startswith("-"):
            query = query.order_by(desc(getattr(Notice, order[1:], Notice.order)))
        else:
            query = query.order_by(asc(getattr(Notice, order, Notice.order)))
    else:
        query = query.order_by(asc(Notice.order))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    notices = result.scalars().all()

    return {"results": [n.to_dict() for n in notices]}


@router.get("/Notice")
async def query_notice(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Query Notice objects (GET)"""
    return await _query_notice(where, order, limit, skip, db)


@router.post("/Notice")
async def query_notice_post(
    request: Request,
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Query Notice objects (POST) - Parse SDK sometimes uses POST for queries"""
    return await _query_notice(where, order, limit, skip, db)


# ==================== DropBox ====================

async def _query_drop_box(
    where: Optional[str],
    order: Optional[str],
    limit: int,
    skip: int,
    db: AsyncSession
):
    """Internal function to query DropBox"""
    query = select(DropBox)

    # Parse where clause to filter by user
    if where:
        try:
            where_dict = json.loads(where)
            # Handle user pointer filter: {"user":{"__type":"Pointer","className":"_User","objectId":"xxx"}}
            if "user" in where_dict:
                user_pointer = where_dict["user"]
                if isinstance(user_pointer, dict) and "objectId" in user_pointer:
                    query = query.where(DropBox.userId == user_pointer["objectId"])
        except json.JSONDecodeError:
            pass

    if order:
        if order.startswith("-"):
            query = query.order_by(desc(getattr(DropBox, order[1:], DropBox.createdAt)))
        else:
            query = query.order_by(asc(getattr(DropBox, order, DropBox.createdAt)))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return {"results": [item.to_dict() for item in items]}


@router.get("/DropBox")
async def query_drop_box(
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Query DropBox objects"""
    return await _query_drop_box(where, order, limit, skip, db)


@router.post("/DropBox")
async def query_drop_box_post(
    request: Request,
    where: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    skip: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Query DropBox objects (POST)"""
    return await _query_drop_box(where, order, limit, skip, db)


@router.post("/DropBox/{object_id}")
async def delete_drop_box_post(
    object_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete DropBox item (POST with _method override from Parse SDK)"""
    data = await request.json()

    # Handle _method override from Parse SDK
    method = data.get("_method", "POST")
    if method == "DELETE":
        result = await db.execute(select(DropBox).where(DropBox.objectId == object_id))
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

        await db.delete(item)
        await db.commit()

        return {}

    raise HTTPException(status_code=405, detail={"code": 1, "error": "Method not allowed"})


@router.delete("/DropBox/{object_id}")
async def delete_drop_box(
    object_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a DropBox item (after claiming reward)"""
    result = await db.execute(select(DropBox).where(DropBox.objectId == object_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail={"code": 101, "error": "Object not found"})

    await db.delete(item)
    await db.commit()

    return {}
