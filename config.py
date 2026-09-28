"""Load and validate required environment variables from .env for Groq and Hindsight."""
import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

# Only HINDSIGHT_API_KEY and GROQ_API_KEY are required now
REQUIRED = ("HINDSIGHT_API_KEY", "GROQ_API_KEY")

missing = [name for name in REQUIRED if not os.getenv(name, "").strip()]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}. Check your .env file.")

HINDSIGHT_API_KEY = os.environ["HINDSIGHT_API_KEY"].strip()
GROQ_API_KEY = os.environ["GROQ_API_KEY"].strip()

# Recommended fast, free-tier model on Groq
AGENT_MODEL = os.getenv("AGENT_MODEL", "openai/gpt-oss-20b").strip()

# Optional: override to point at a self-hosted Hindsight server.
HINDSIGHT_BASE_URL = (os.getenv("HINDSIGHT_BASE_URL") or "https://api.hindsight.vectorize.io").strip().rstrip("/")

# Validate Hindsight URL
_url = urlparse(HINDSIGHT_BASE_URL)
if _url.scheme not in ("http", "https") or not _url.netloc:
    raise RuntimeError(f"HINDSIGHT_BASE_URL is not a valid http(s) URL: {HINDSIGHT_BASE_URL!r}")
