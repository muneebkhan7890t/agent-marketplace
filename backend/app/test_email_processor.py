from app.services.email_processor import EmailProcessor

BUSINESS_ID = 1
processor = EmailProcessor()

results = processor.process_all(BUSINESS_ID)

for item in results:
    print(item)
    print("-" * 60)