"""
routes/shipping.py
Paste → backend/app/routes/shipping.py
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.mcp import shiprocket as sh
from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business

router = APIRouter()


def _verify_ownership(business_id: int, user_id: int, db: Session) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


class TCSBooking(BaseModel):
    sender_name: str; sender_phone: str; sender_city: str
    receiver_name: str; receiver_phone: str; receiver_city: str; receiver_address: str
    weight: float; cod: float = 0

class LeoBooking(BaseModel):
    shipper_name: str; shipper_email: str; shipper_phone: str
    shipper_address: str; shipper_city: int
    consignee_name: str; consignee_phone: str
    consignee_address: str; consignee_city: int
    weight: float = 0.5; pieces: int = 1; amount: float = 0; order_id: str = ""


# ------------------------------------------------------------------ #
# Connect / status / disconnect — Shiprocket, TCS, Leopards all run on
# platform-level API credentials (env vars), so "connect" here is a
# per-business opt-in that also verifies the platform credentials
# actually work before flipping the flag on, rather than a no-op toggle.
# ------------------------------------------------------------------ #

@router.post("/shiprocket/connect")
def shiprocket_connect(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    try:
        sh.sr_get_shipments()  # verifies the Shiprocket credentials actually work
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Couldn't verify Shiprocket credentials: {e}")
    business.shiprocket_connected = True
    db.commit()
    return {"message": "Shiprocket connected"}

@router.get("/shiprocket/status")
def shiprocket_status(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"shiprocket_connected": business.shiprocket_connected}

@router.post("/shiprocket/disconnect")
def shiprocket_disconnect(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    business.shiprocket_connected = False
    db.commit()
    return {"message": "Shiprocket disconnected"}


@router.post("/tcs/connect")
def tcs_connect(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    try:
        sh.tcs_cities()  # verifies the TCS credentials actually work
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Couldn't verify TCS credentials: {e}")
    business.tcs_connected = True
    db.commit()
    return {"message": "TCS connected"}

@router.get("/tcs/status")
def tcs_status(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"tcs_connected": business.tcs_connected}

@router.post("/tcs/disconnect")
def tcs_disconnect(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    business.tcs_connected = False
    db.commit()
    return {"message": "TCS disconnected"}


@router.post("/leopards/connect")
def leopards_connect(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    try:
        sh.leo_cities()  # verifies the Leopards credentials actually work
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Couldn't verify Leopards credentials: {e}")
    business.leopards_connected = True
    db.commit()
    return {"message": "Leopards connected"}

@router.get("/leopards/status")
def leopards_status(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"leopards_connected": business.leopards_connected}

@router.post("/leopards/disconnect")
def leopards_disconnect(business_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = _verify_ownership(business_id, current_user.id, db)
    business.leopards_connected = False
    db.commit()
    return {"message": "Leopards disconnected"}


# Shiprocket
@router.get("/shiprocket/shipments")
def sr_shipments(status: str = None):
    try:    return sh.sr_get_shipments(status)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/shiprocket/track/{shipment_id}")
def sr_track(shipment_id: str):
    try:    return sh.sr_track(shipment_id)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/shiprocket/track-awb")
def sr_track_awb(awb: str = Query(...)):
    try:    return sh.sr_track_awb(awb)
    except Exception as e: raise HTTPException(500, str(e))

# TCS
@router.post("/tcs/book")
def tcs_book(body: TCSBooking):
    try:    return sh.tcs_book(body.sender_name,body.sender_phone,body.sender_city,body.receiver_name,body.receiver_phone,body.receiver_city,body.receiver_address,body.weight,body.cod)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/tcs/track")
def tcs_track(tracking_no: str = Query(...)):
    try:    return sh.tcs_track(tracking_no)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/tcs/cities")
def tcs_cities():
    try:    return sh.tcs_cities()
    except Exception as e: raise HTTPException(500, str(e))

# Leopards
@router.post("/leopards/book")
def leo_book(body: LeoBooking):
    try:    return sh.leo_book(**body.dict())
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/leopards/track")
def leo_track(tracking_no: str = Query(...)):
    try:    return sh.leo_track(tracking_no)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/leopards/cities")
def leo_cities():
    try:    return sh.leo_cities()
    except Exception as e: raise HTTPException(500, str(e))