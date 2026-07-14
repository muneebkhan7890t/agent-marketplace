#from app.services.gmail_agent import GmailAgent
#from app.logs.logger import AgentLogger
#from app.database import SessionLocal
#from app.models.business import Business


#def check_emails():

 #   print("Checking Gmail...")

  #  db = SessionLocal()

   # business = db.query(Business).first()

    #if not business or not business.gmail_access_token:
      #  print("No Gmail account connected.")
     #   db.close()
       # return

    #agent = GmailAgent()

    #results = agent.start(
     #   business.gmail_access_token
    #)

    #logger = AgentLogger()
    #logger.log(f"Processed {len(results)} email(s)")

    #db.close()