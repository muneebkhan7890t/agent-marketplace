class MCPManager:

    def get_connector(self, service_name):

        connectors = {
            "shopify": "ShopifyConnector",
            "gmail": "GmailConnector",
            "whatsapp": "WhatsAppConnector",
            "stripe": "StripeConnector",
            "hubspot": "HubSpotConnector"
        }

        return connectors.get(service_name)