"""Load environment configuration from the project's .env file.

The ZooWork SDK reads ZOOWORK_API_KEY (required) and ZOOWORK_BASE_URL (optional; the SDK
defaults to production) from the process environment, so this only has to populate it.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Real environment variables take precedence over .env values.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def require_zoowork_key() -> None:
    """Fail fast, without revealing the value, when no ZooWork key is configured."""
    if not os.getenv("ZOOWORK_API_KEY"):
        raise RuntimeError(
            "ZOOWORK_API_KEY is not set. Add it to .env or the environment; "
            "create a Project key at https://platform.zoowork.ai."
        )
