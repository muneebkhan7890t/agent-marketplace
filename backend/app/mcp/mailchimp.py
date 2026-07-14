"""
mcp/mailchimp.py
Paste → backend/app/mcp/mailchimp.py
"""
from app.integrations.mailchimp.service import MailchimpService
_mc = None
def _m(): global _mc; _mc = _mc or MailchimpService(); return _mc

def get_lists() -> list:                                              return _m().get_lists()
def subscribe(list_id: str, email: str, first: str = "", last: str = "", tags: list = None) -> dict:
    return _m().subscribe(list_id, email, first, last, tags)
def unsubscribe(list_id: str, email: str) -> dict:                    return _m().unsubscribe(list_id, email)
def add_tags(list_id: str, email: str, tags: list) -> dict:           return _m().add_tags(list_id, email, tags)
def get_campaigns(count: int = 10) -> list:                           return _m().get_campaigns(count)
def create_campaign(list_id: str, subject: str, from_name: str, reply_to: str) -> dict:
    return _m().create_campaign(list_id, subject, from_name, reply_to)
def send_campaign(campaign_id: str) -> dict:                          return _m().send_campaign(campaign_id)
def get_campaign_report(campaign_id: str) -> dict:                    return _m().get_campaign_report(campaign_id)

