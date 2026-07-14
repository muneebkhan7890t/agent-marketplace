from app.mcp.shopify import ShopifyConnector
from app.mcp.whatsapp import WhatsAppConnector
from app.agents.customer_support import CustomerSupportAgent
from app.models.agent import Agent


class ToolExecutor:

    def execute(
        self,
        tool_name
    ):

        if tool_name == "shopify_orders":

            shopify = ShopifyConnector()

            return shopify.get_orders()

        elif tool_name == "gmail_reader":

            return {
        "message": "Please authenticate with Gmail first by visiting /gmail/login"
    }   

        elif tool_name == "whatsapp_sender":

            whatsapp = WhatsAppConnector(business_id=1)  # placeholder/demo business

            return whatsapp.send_message(
                "000000",
                "Test"
            )

        return {
            "error": "Tool not found"
        }
