from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.coupon import Coupon


router = APIRouter(prefix="/api", tags=["coupon"])


@router.post("/redeemCoupon")
async def redeem_coupon(
    coupon_code: str = Form(...),
    redeemed_by: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Redeem a coupon code"""
    # Find coupon
    result = await db.execute(select(Coupon).where(Coupon.code == coupon_code))
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": "Invalid coupon code"}}
        )

    if not coupon.isActive:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": "Coupon is no longer active"}}
        )

    # Check if max redemptions reached
    if coupon.maxRedemptions != -1 and coupon.currentRedemptions >= coupon.maxRedemptions:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": "Coupon has reached maximum redemptions"}}
        )

    # Check if user already redeemed
    redeemed_list = coupon.redeemedBy.split(",") if coupon.redeemedBy else []
    if redeemed_by in redeemed_list:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": "You have already redeemed this coupon"}}
        )

    # Update coupon
    coupon.currentRedemptions += 1
    if coupon.redeemedBy:
        coupon.redeemedBy += f",{redeemed_by}"
    else:
        coupon.redeemedBy = redeemed_by

    await db.commit()

    return {
        "relics": coupon.relics,
        "gems": coupon.gems,
        "unlockAdFree": coupon.unlockAdFree
    }


# Admin endpoints for managing coupons

@router.post("/admin/coupons")
async def create_coupon(
    code: str = Form(...),
    relics: int = Form(0),
    gems: int = Form(0),
    unlock_ad_free: bool = Form(False),
    max_redemptions: int = Form(1),
    db: AsyncSession = Depends(get_db)
):
    """Create a new coupon (admin only)"""
    # Check if coupon code already exists
    result = await db.execute(select(Coupon).where(Coupon.code == code))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail={"error": "Coupon code already exists"})

    coupon = Coupon(
        code=code,
        relics=relics,
        gems=gems,
        unlockAdFree=unlock_ad_free,
        maxRedemptions=max_redemptions
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)

    return coupon.to_dict()


@router.get("/admin/coupons")
async def list_coupons(db: AsyncSession = Depends(get_db)):
    """List all coupons (admin only)"""
    result = await db.execute(select(Coupon))
    coupons = result.scalars().all()
    return {"results": [c.to_dict() for c in coupons]}


@router.delete("/admin/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a coupon (admin only)"""
    result = await db.execute(select(Coupon).where(Coupon.objectId == coupon_id))
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(status_code=404, detail={"error": "Coupon not found"})

    await db.delete(coupon)
    await db.commit()

    return {"success": True}
