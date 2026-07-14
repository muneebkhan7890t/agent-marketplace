

"""
models/business.py
REPLACE → backend/app/models/business.py
"""
from sqlalchemy import Boolean, Column, Text, Integer, String, ForeignKey
from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id"))
    business_name = Column(String)
    industry      = Column(String)
    website_url   = Column(String)

    # Gmail
    gmail_access_token  = Column(Text,    nullable=True)
    gmail_refresh_token = Column(Text,    nullable=True)
    gmail_token_expiry  = Column(Text,    nullable=True)
    gmail_connected     = Column(Boolean, default=False)

    # Shopify
    shopify_store_url    = Column(String,  nullable=True)
    shopify_access_token = Column(Text,    nullable=True)
    shopify_connected    = Column(Boolean, default=False)

    # Shopify automation (order -> email/WhatsApp/low-stock pipeline)
    shopify_low_stock_threshold = Column(Integer, default=5)     # "less in store" trigger point
    owner_alert_whatsapp       = Column(String,  nullable=True)  # merchant's OWN number -- where low-stock/order alerts go
    owner_alert_email          = Column(String,  nullable=True)  # optional override; falls back to the connected Gmail address

    # WooCommerce
    woo_store_url       = Column(String,  nullable=True)
    woo_consumer_key    = Column(Text,    nullable=True)
    woo_consumer_secret = Column(Text,    nullable=True)
    woo_connected       = Column(Boolean, default=False)

    # Amazon
    amazon_connected = Column(Boolean, default=False)
    amazon_seller_id = Column(String,  nullable=True)

    # WhatsApp
    whatsapp_business_number = Column(String, nullable=True)   # human-readable number the user typed in
    whatsapp_phone_id    = Column(String,  nullable=True)      # Meta Phone Number ID (used for API calls + webhook routing)
    whatsapp_token       = Column(Text,    nullable=True)
    whatsapp_connected   = Column(Boolean, default=False)

    # Stripe
    stripe_customer_id   = Column(String,  nullable=True)
    stripe_connected     = Column(Boolean, default=False)

    # Razorpay
    razorpay_connected   = Column(Boolean, default=False)

    # JazzCash
    jazzcash_connected   = Column(Boolean, default=False)
    jazzcash_merchant_id = Column(String,  nullable=True)

    # Shipping
    shiprocket_connected = Column(Boolean, default=False)
    tcs_connected        = Column(Boolean, default=False)
    leopards_connected   = Column(Boolean, default=False)

    # Google Sheets
    sheets_spreadsheet_id = Column(String, nullable=True)
    sheets_connected      = Column(Boolean, default=False)

    # HubSpot
    hubspot_connected    = Column(Boolean, default=False)
    hubspot_portal_id    = Column(String,  nullable=True)

    # Mailchimp
    mailchimp_connected  = Column(Boolean, default=False)
    mailchimp_list_id    = Column(String,  nullable=True)

    # Meta Ads
    meta_ads_connected   = Column(Boolean, default=False)
    meta_ad_account_id   = Column(String,  nullable=True)