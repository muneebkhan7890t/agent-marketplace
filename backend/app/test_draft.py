from app.mcp.gmail import create_draft

BUSINESS_ID = 1
result = create_draft(
    BUSINESS_ID ,
    "your_email@gmail.com",
    "Testing AI Draft",
    "Hello,\n\nThis is an AI generated draft.\n\nThanks."
)

print(result)