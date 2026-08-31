import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from lawn_api.config import settings

logger = logging.getLogger(__name__)


def post_ntfy(title: str, message: str, priority: str = "default", tags: str = "", topic: str | None = None) -> None:
    """Post a notification to an ntfy topic (default: the alerts topic).

    URL and topics come from config (NTFY_URL, NTFY_ALERTS_TOPIC,
    NTFY_BRIEFINGS_TOPIC) -- previously hardcoded, which PLATFORM_DEPS.md
    flagged for years. Runs synchronously — call from a thread or background
    job only, not from an async request handler (wrap in asyncio.to_thread
    there). Failures are logged but not re-raised so a ntfy outage doesn't
    crash the scheduler.
    """
    url = f"{settings.ntfy_url.rstrip('/')}/{topic or settings.ntfy_alerts_topic}"
    headers = {
        "Title": title.encode(),
        "Priority": priority.encode(),
    }
    if tags:
        headers["Tags"] = tags.encode()

    try:
        req = Request(
            url,
            data=message.encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            logger.debug("ntfy response: %s", resp.status)
    except URLError as exc:
        logger.warning("ntfy notification failed: %s", exc)
    except Exception:
        logger.exception("ntfy notification failed unexpectedly")
