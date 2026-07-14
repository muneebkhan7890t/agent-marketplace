import os
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def create_flow(redirect_uri: str = None):
    """
    Build an OAuth2 Flow from env vars.
    Pass redirect_uri explicitly when the business_id must be embedded in state/redirect.
    """
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/callback")
                ],
            }
        },
        scopes=SCOPES,
    )

    flow.redirect_uri = redirect_uri or os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/gmail/callback"
    )

    return flow
