"""
routes/whatsapp.py  (superseded)
----------------------------------
All WhatsApp endpoints now live in app/whatsapp_suite.py (one file, all
10 phases) and are wired into main.py from there. This file is kept
only as a compat re-export in case anything imports `router` from here
directly -- main.py itself already imports from whatsapp_suite.
"""

from app.whatsapp_suite import router  # noqa: F401
