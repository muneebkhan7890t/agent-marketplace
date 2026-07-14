from app.mcp.gmail import read_emails


class GmailService:

    def get_new_emails(self):
        return read_emails()