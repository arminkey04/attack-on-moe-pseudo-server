from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from models.user import User, format_parse_date
from models.battle_log import BattleLog
from routers.classes import parse_pointer, parse_date
from services.auth import AuthService


router = APIRouter(prefix="/parse/batch", tags=["batch"])


async def get_current_user(
    x_parse_session_token: Optional[str] = Header(None, alias="X-Parse-Session-Token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not x_parse_session_token:
        return None
    return await AuthService.get_user_by_session_token(db, x_parse_session_token)


class BatchRequestItem(BaseModel):
    method: str
    path: str
    body: Optional[dict] = None


class BatchRequest(BaseModel):
    requests: List[BatchRequestItem]


@router.post("")
async def batch_request(
    request: BatchRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Handle batch requests"""
    results = []

    for req in request.requests:
        try:
            if req.method == "POST" and "/classes/BattleLog" in req.path:
                # Create BattleLog
                data = req.body or {}
                sender_id = parse_pointer(data.get("sender"))
                receiver_id = parse_pointer(data.get("receiver"))

                if not sender_id or not receiver_id:
                    results.append({"error": {"code": 105, "error": "Invalid sender or receiver pointer"}})
                    continue

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
                await db.flush()

                results.append({
                    "success": {
                        "objectId": battle_log.objectId,
                        "createdAt": format_parse_date(battle_log.createdAt)
                    }
                })
            else:
                results.append({"error": {"code": 1, "error": "Unsupported batch operation"}})

        except Exception as e:
            results.append({"error": {"code": 1, "error": str(e)}})

    await db.commit()

    return results
