import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

NTFY_URL = "http://ntfy/lawn-alerts"


def post_ntfy(title: str, message: str, priority: str = "default", tags: str = "") -> None:
    """Post a notification to the ntfy lawn-alerts topic.

    Runs synchronously — call from a thread or background job only, not from
    an async request handler. Failures are logged but not re-raised so a ntfy
    outage doesn't crash the scheduler.
    """
    headers = {
        "Title": title.encode(),
        "Priority": priority.encode(),
    }
    if tags:
        headers["Tags"] = tags.encode()

    try:
        req = Request(
            NTFY_URL,
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
