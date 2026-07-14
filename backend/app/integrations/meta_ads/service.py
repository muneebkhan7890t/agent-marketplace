"""
integrations/meta_ads/service.py
----------------------------------
Meta (Facebook/Instagram) Ads integration via Marketing API.
Paste → backend/app/integrations/meta_ads/service.py

Env vars:
  META_ACCESS_TOKEN    ← long-lived system user token from Meta Business
  META_AD_ACCOUNT_ID   ← act_XXXXXXXXX (include "act_" prefix)
"""

import os
import requests

BASE = "https://graph.facebook.com/v19.0"
TOKEN      = os.getenv("META_ACCESS_TOKEN", "")
ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "")


class MetaAdsService:

    def __init__(self, access_token: str = None, ad_account_id: str = None):
        self.token      = access_token or TOKEN
        self.account_id = ad_account_id or ACCOUNT_ID
        self.params     = {"access_token": self.token}

    def _get(self, path: str, params: dict = None) -> dict:
        p = {**self.params, **(params or {})}
        r = requests.get(f"{BASE}{path}", params=p)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(f"{BASE}{path}", params=self.params, json=data)
        r.raise_for_status()
        return r.json()

    # ── Campaigns ─────────────────────────────────────────────────────

    def get_campaigns(self, fields: str = "id,name,status,objective,budget_remaining,spend_cap") -> list:
        data = self._get(f"/{self.account_id}/campaigns", {"fields": fields, "limit": 50})
        return data.get("data", [])

    def get_campaign(self, campaign_id: str, fields: str = "id,name,status,insights") -> dict:
        return self._get(f"/{campaign_id}", {"fields": fields})

    def create_campaign(self, name: str, objective: str, status: str = "PAUSED", daily_budget: int = None) -> dict:
        """
        objective: OUTCOME_TRAFFIC | OUTCOME_SALES | OUTCOME_LEADS | OUTCOME_AWARENESS
        daily_budget: in cents e.g. 1000 = $10/day
        """
        data = {
            "name":      name,
            "objective": objective,
            "status":    status,
        }
        if daily_budget:
            data["daily_budget"] = daily_budget
        return self._post(f"/{self.account_id}/campaigns", data)

    def update_campaign_status(self, campaign_id: str, status: str) -> dict:
        """status: ACTIVE | PAUSED | ARCHIVED"""
        r = requests.post(f"{BASE}/{campaign_id}", params={**self.params, "status": status})
        r.raise_for_status()
        return r.json()

    # ── Ad sets ───────────────────────────────────────────────────────

    def get_adsets(self, campaign_id: str = None, fields: str = "id,name,status,budget_remaining,daily_budget") -> list:
        path = f"/{campaign_id}/adsets" if campaign_id else f"/{self.account_id}/adsets"
        data = self._get(path, {"fields": fields, "limit": 50})
        return data.get("data", [])

    def get_adset(self, adset_id: str) -> dict:
        return self._get(f"/{adset_id}", {"fields": "id,name,status,targeting,daily_budget,lifetime_budget"})

    # ── Ads ───────────────────────────────────────────────────────────

    def get_ads(self, adset_id: str = None, fields: str = "id,name,status,creative") -> list:
        path = f"/{adset_id}/ads" if adset_id else f"/{self.account_id}/ads"
        data = self._get(path, {"fields": fields, "limit": 50})
        return data.get("data", [])

    # ── Insights / Analytics ──────────────────────────────────────────

    def get_account_insights(self, date_preset: str = "last_7d", fields: str = None) -> dict:
        """
        date_preset: today | yesterday | last_7d | last_14d | last_30d | this_month | last_month
        """
        f = fields or "impressions,clicks,spend,reach,cpc,ctr,actions,conversions"
        data = self._get(f"/{self.account_id}/insights", {
            "fields":      f,
            "date_preset": date_preset,
        })
        return data.get("data", [{}])[0] if data.get("data") else {}

    def get_campaign_insights(self, campaign_id: str, date_preset: str = "last_7d") -> dict:
        data = self._get(f"/{campaign_id}/insights", {
            "fields":      "impressions,clicks,spend,reach,cpc,ctr,actions",
            "date_preset": date_preset,
        })
        return data.get("data", [{}])[0] if data.get("data") else {}

    def get_ad_insights(self, ad_id: str, date_preset: str = "last_7d") -> dict:
        data = self._get(f"/{ad_id}/insights", {
            "fields":      "impressions,clicks,spend,cpc,ctr",
            "date_preset": date_preset,
        })
        return data.get("data", [{}])[0] if data.get("data") else {}

    # ── Audiences ─────────────────────────────────────────────────────

    def get_custom_audiences(self) -> list:
        data = self._get(f"/{self.account_id}/customaudiences",
                         {"fields": "id,name,approximate_count,subtype"})
        return data.get("data", [])

    def create_custom_audience(self, name: str, subtype: str = "CUSTOM", description: str = "") -> dict:
        """subtype: CUSTOM | WEBSITE | APP | LOOKALIKE"""
        return self._post(f"/{self.account_id}/customaudiences", {
            "name":        name,
            "subtype":     subtype,
            "description": description,
        })

    # ── Spend monitoring ──────────────────────────────────────────────

    def get_spend_summary(self) -> dict:
        """Quick spend vs budget overview for all active campaigns."""
        campaigns = self.get_campaigns(fields="id,name,status,spend_cap,budget_remaining")
        active = [c for c in campaigns if c.get("status") == "ACTIVE"]
        total_remaining = sum(float(c.get("budget_remaining", 0)) for c in active) / 100
        return {
            "active_campaigns": len(active),
            "total_budget_remaining_usd": round(total_remaining, 2),
            "campaigns": active,
        }