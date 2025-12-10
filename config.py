import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Constants
MAX_PASSWORD_BYTES = 72  # bcrypt ignores everything after 72 bytes

# Validate required environment variables
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
