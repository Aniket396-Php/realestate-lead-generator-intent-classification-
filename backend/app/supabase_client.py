import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

SUPABASE_URL              = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY         = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

import logging as _logging
_logger = _logging.getLogger(__name__)

# Fix: Force stdout/stderr to UTF-8 on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7 doesn't have reconfigure

# -- Public client (anon key - respects RLS, used by frontend) -----------------
supabase: Client = None
if not SUPABASE_URL or not SUPABASE_ANON_KEY or "your-project" in (SUPABASE_URL or ""):
    _logger.warning("WARNING: Supabase anon credentials missing. Data persistence disabled.")
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        _logger.info("Supabase public client initialized.")
    except Exception as e:
        _logger.error("WARNING: Failed to initialize Supabase public client: %s", e)

# -- Admin client (service role key - bypasses RLS, backend writes only) -------
supabase_admin: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        _logger.info("Supabase admin client (service role) initialized.")
    except Exception as e:
        _logger.error("WARNING: Failed to initialize Supabase admin client: %s", e)
else:
    _logger.warning("WARNING: SUPABASE_SERVICE_ROLE_KEY not set - lead storage will fail.")
