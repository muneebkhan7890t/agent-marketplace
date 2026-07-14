"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, apiBaseUrl, Business } from "@/lib/api";
import { IntegrationCard } from "@/components/IntegrationCard";

export default function IntegrationsPage() {
  const params = useParams();
  const businessId = Number(params.businessId);

  const [business, setBusiness] = useState<Business | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api
      .get<Business[]>("/businesses/")
      .then((list) => {
        const found = list.find((b) => b.id === businessId) ?? null;
        setBusiness(found);
        if (!found) setError("Business not found");
      })
      .catch(() => setError("Couldn't load business"));
  }, [businessId]);

  useEffect(refresh, [refresh]);

  // OAuth connect flows (Shopify, Gmail) finish on a backend page in a
  // separate tab. Re-check status automatically when the user comes back.
  useEffect(() => {
    function onFocus() {
      refresh();
    }
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refresh]);

  if (error) {
    return <p className="text-danger">{error}</p>;
  }
  if (!business) {
    return <p className="font-mono text-sm text-ink-muted">Loading…</p>;
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          {business.business_name} — Integrations
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Every rail your AI agents can read from or act through. Wire one in
          to let the relevant agents use it.
        </p>
      </div>

      <Section title="AI channels">
        <IntegrationCard
          name="Gmail"
          description="Lets agents read incoming support/sales emails and send replies."
          connected={business.gmail_connected}
          onConnectRedirect={() =>
            window.open(
              `${apiBaseUrl()}/gmail/connect?business_id=${business.id}`,
              "_blank"
            )
          }
          onDisconnect={() => api.post(`/gmail/disconnect?business_id=${business.id}`).then(refresh)}
        />
        <WhatsAppCard business={business} onChange={refresh} />
      </Section>

      <Section title="Storefront">
        <IntegrationCard
          name="Shopify"
          description="Order lookups, inventory, low-stock alerts, and fulfillment updates."
          connected={business.shopify_connected}
          detail={business.shopify_store_url}
          onConnectRedirect={() => {
            const shop = window.prompt("Your Shopify store domain (e.g. mystore.myshopify.com):");
            if (!shop) return;
            window.open(
              `${apiBaseUrl()}/shopify/connect?shop=${encodeURIComponent(shop)}&business_id=${business.id}`,
              "_blank"
            );
          }}
          onDisconnect={() => api.post(`/shopify/disconnect?business_id=${business.id}`).then(refresh)}
        />
        <WooCommerceCard business={business} onChange={refresh} />
      </Section>

      <Section title="Payments">
        <IntegrationCard
          name="Stripe"
          description="Payment links, refunds, and transaction lookups for global customers."
          connected={business.stripe_connected}
          detail={business.stripe_customer_id}
          onConnect={() => api.post<{ message: string }>(`/stripe/connect?business_id=${business.id}`).then(refresh)}
          onDisconnect={() => api.post(`/stripe/disconnect?business_id=${business.id}`).then(refresh)}
        />
        <IntegrationCard
          name="Razorpay"
          description="Payments and refunds for customers in India."
          connected={business.razorpay_connected}
          readOnly
          detail="Configured by your admin — contact support to enable."
        />
        <IntegrationCard
          name="JazzCash"
          description="Mobile wallet payments for customers in Pakistan."
          connected={business.jazzcash_connected}
          readOnly
          detail="Configured by your admin — contact support to enable."
        />
      </Section>

      <Section title="Shipping & fulfillment">
        <IntegrationCard
          name="Shiprocket"
          description="Create and track shipments for orders shipping within India."
          connected={business.shiprocket_connected}
          onConnect={() => api.post(`/shipping/shiprocket/connect?business_id=${business.id}`).then(refresh)}
          onDisconnect={() => api.post(`/shipping/shiprocket/disconnect?business_id=${business.id}`).then(refresh)}
        />
        <IntegrationCard
          name="TCS Courier"
          description="Book and track shipments for orders shipping within Pakistan."
          connected={business.tcs_connected}
          onConnect={() => api.post(`/shipping/tcs/connect?business_id=${business.id}`).then(refresh)}
          onDisconnect={() => api.post(`/shipping/tcs/disconnect?business_id=${business.id}`).then(refresh)}
        />
        <IntegrationCard
          name="Leopards Courier"
          description="An alternative courier for Pakistan-based fulfillment."
          connected={business.leopards_connected}
          onConnect={() => api.post(`/shipping/leopards/connect?business_id=${business.id}`).then(refresh)}
          onDisconnect={() => api.post(`/shipping/leopards/disconnect?business_id=${business.id}`).then(refresh)}
        />
      </Section>

      <Section title="Marketing & CRM">
        <IntegrationCard
          name="HubSpot"
          description="Lead scoring, contact sync, and CRM follow-up notes."
          connected={business.hubspot_connected}
          readOnly
          detail="Configured by your admin — contact support to enable."
        />
        <IntegrationCard
          name="Mailchimp"
          description="Abandoned-cart recovery emails and campaign sends."
          connected={business.mailchimp_connected}
          readOnly
          detail="Configured by your admin — contact support to enable."
        />
        <IntegrationCard
          name="Meta Ads"
          description="Draft and stage Facebook/Instagram ad campaigns."
          connected={business.meta_ads_connected}
          readOnly
          detail="Configured by your admin — contact support to enable."
        />
        <IntegrationCard
          name="Google Sheets"
          description="Daily/weekly order and revenue summaries, exported automatically."
          connected={business.sheets_connected}
          readOnly
          detail="Configured by your admin — contact support to enable."
        />
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-10">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.15em] text-ink-muted">
        {title}
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </div>
  );
}

function WooCommerceCard({ business, onChange }: { business: Business; onChange: () => void }) {
  const [storeUrl, setStoreUrl] = useState("");
  const [consumerKey, setConsumerKey] = useState("");
  const [consumerSecret, setConsumerSecret] = useState("");

  async function connect() {
    await api.post(`/woocommerce/connect?business_id=${business.id}`, {
      store_url: storeUrl,
      consumer_key: consumerKey,
      consumer_secret: consumerSecret,
    });
    onChange();
  }

  return (
    <IntegrationCard
      name="WooCommerce"
      description="Order lookups, inventory, and refunds for WordPress storefronts."
      connected={business.woo_connected}
      detail={business.woo_store_url}
      onDisconnect={() => api.post(`/woocommerce/disconnect?business_id=${business.id}`).then(onChange)}
      connectForm={
        <div className="space-y-3">
          <Field label="Store URL" value={storeUrl} onChange={setStoreUrl} placeholder="https://mystore.com" />
          <Field label="Consumer key" value={consumerKey} onChange={setConsumerKey} placeholder="ck_..." />
          <Field
            label="Consumer secret"
            value={consumerSecret}
            onChange={setConsumerSecret}
            placeholder="cs_..."
            type="password"
          />
          <button
            onClick={connect}
            className="rounded bg-wire px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
          >
            Save & connect
          </button>
        </div>
      }
    />
  );
}

function WhatsAppCard({ business, onChange }: { business: Business; onChange: () => void }) {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [accessToken, setAccessToken] = useState("");

  async function connect() {
    await api.post(`/whatsapp/connect?business_id=${business.id}`, {
      phone_number: phoneNumber,
      phone_number_id: phoneNumberId,
      access_token: accessToken,
    });
    onChange();
  }

  return (
    <IntegrationCard
      name="WhatsApp"
      description="Answers customer WhatsApp messages via the Meta Business Cloud API."
      connected={business.whatsapp_connected}
      detail={business.whatsapp_business_number}
      onDisconnect={() => api.post(`/whatsapp/disconnect?business_id=${business.id}`).then(onChange)}
      connectForm={
        <div className="space-y-3">
          <Field label="WhatsApp number" value={phoneNumber} onChange={setPhoneNumber} placeholder="+923001234567" />
          <Field label="Phone number ID" value={phoneNumberId} onChange={setPhoneNumberId} placeholder="Meta Phone Number ID" />
          <Field
            label="Access token"
            value={accessToken}
            onChange={setAccessToken}
            placeholder="Meta system-user access token"
            type="password"
          />
          <button
            onClick={connect}
            className="rounded bg-wire px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
          >
            Save & connect
          </button>
        </div>
      }
    />
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-ink-muted">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
      />
    </div>
  );
}
