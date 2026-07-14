"""
agents/marketing_ads_agent.py
---------------------------------
Marketing/Ads Agent -- turns a short brief into a (paused, for human
review) Meta Ads campaign plus a matching Mailchimp email campaign.
Uses MetaAdsService + MailchimpService, both already built but unused
by any sellable agent.

Paste -> backend/app/agents/marketing_ads_agent.py
"""

from app.mcp import meta_ads as meta_mcp
from app.mcp import mailchimp as mailchimp_mcp
from app.ai.huggingface_client import generate_response


class MarketingAdsAgent:

    role_prompt = "You are a direct-response ecommerce copywriter."

    def _draft_copy(self, brief: dict) -> dict:
        prompt = f"""
Write ad + email copy for this campaign brief:
Objective: {brief.get('objective', 'drive sales')}
Product: {brief.get('product', '')}
Audience: {brief.get('audience', 'general shoppers')}
Budget: {brief.get('budget', 'not specified')}

Return exactly three parts separated by "---":
1. A Meta ad headline (under 40 characters)
2. A Meta ad primary text (1-2 sentences)
3. An email subject line (under 8 words)
"""
        raw = generate_response(prompt).strip()
        parts = [p.strip() for p in raw.split("---")]
        while len(parts) < 3:
            parts.append("")
        return {"ad_headline": parts[0], "ad_body": parts[1], "email_subject": parts[2]}

    def launch_campaign_from_brief(self, business, brief: dict) -> dict:
        """
        brief: {"objective": "...", "product": "...", "audience": "...", "budget": "..."}
        Campaigns are created PAUSED -- this agent drafts and stages the
        campaign, it does not spend money without a human turning it on.
        """
        copy = self._draft_copy(brief)
        result = {"copy": copy}

        if getattr(business, "meta_ads_connected", False):
            objective_map = {
                "drive sales": "OUTCOME_SALES",
                "get leads": "OUTCOME_LEADS",
                "brand awareness": "OUTCOME_AWARENESS",
            }
            objective = objective_map.get(brief.get("objective", "").lower(), "OUTCOME_SALES")
            try:
                result["meta_campaign"] = meta_mcp.create_campaign(
                    name=f"{brief.get('product', 'Campaign')} — {copy['ad_headline']}",
                    objective=objective,
                    status="PAUSED",
                )
            except Exception as exc:
                result["meta_campaign_error"] = str(exc)
        else:
            result["meta_campaign"] = "skipped: Meta Ads not connected for this business"

        if getattr(business, "mailchimp_connected", False) and getattr(business, "mailchimp_list_id", None):
            try:
                result["mailchimp_campaign"] = mailchimp_mcp.create_campaign(
                    list_id=business.mailchimp_list_id,
                    subject=copy["email_subject"],
                    from_name=business.business_name,
                    reply_to=getattr(business, "owner_alert_email", "") or "no-reply@agenthub.local",
                )
            except Exception as exc:
                result["mailchimp_campaign_error"] = str(exc)
        else:
            result["mailchimp_campaign"] = "skipped: Mailchimp not connected for this business"

        return result
