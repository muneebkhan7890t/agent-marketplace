from app.runtime.gmail_runtime import GmailRuntime

BUSINESS_ID = 1
runtime = GmailRuntime()

results = runtime.run(BUSINESS_ID)

print(results)