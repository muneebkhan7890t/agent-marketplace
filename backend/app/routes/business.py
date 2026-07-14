from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user

from app.models.business import Business
from app.models.user import User

from app.schemas.business_schema import BusinessCreate, AutomationSettings

router = APIRouter()

@router.post("/")
def create_business(
    business: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_business = Business(
        user_id=current_user.id,
        business_name=business.business_name,
        industry=business.industry,
        website_url=business.website_url
    )

    db.add(new_business)

    db.commit()

    db.refresh(new_business)

    return {
        "message": "Business created",
        "business_id": new_business.id
    }

@router.get("/")
def get_my_businesses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    businesses = db.query(Business).filter(
        Business.user_id == current_user.id
    ).all()

    return businesses

@router.delete("/{business_id}")
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    db.delete(business)

    db.commit()

    return {
        "message": "Business deleted"
    }


@router.patch("/{business_id}/automation-settings")
def update_automation_settings(
    business_id: int,
    settings: AutomationSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Where the Shopify automation pipeline should send low-stock / order
    alerts, and the threshold that counts as 'low stock'. Set
    owner_alert_whatsapp to YOUR OWN number (not the customer's) --
    that's what the AI messages when something needs your attention.
    """
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if settings.owner_alert_whatsapp is not None:
        business.owner_alert_whatsapp = settings.owner_alert_whatsapp
    if settings.owner_alert_email is not None:
        business.owner_alert_email = settings.owner_alert_email
    if settings.shopify_low_stock_threshold is not None:
        business.shopify_low_stock_threshold = settings.shopify_low_stock_threshold

    db.commit()

    return {
        "message": "Automation settings updated",
        "owner_alert_whatsapp": business.owner_alert_whatsapp,
        "owner_alert_email": business.owner_alert_email,
        "shopify_low_stock_threshold": business.shopify_low_stock_threshold,
    }