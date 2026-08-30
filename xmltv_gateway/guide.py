"""Fetch the guide from the configured provider and write it to CACHE_FILE.

Run from cron as `python -m xmltv_gateway.guide`.
"""

import logging
import os
import sys
from pathlib import Path
from xml.etree import ElementTree

from .providers import PROVIDERS

log = logging.getLogger(__name__)


def refresh(path: Path, provider) -> bool:
    """Fetch and replace the guide, leaving the previous one if anything fails."""
    try:
        data = provider()
    except Exception:
        log.exception("provider failed, keeping existing guide")
        return False

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        log.error("provider returned unparseable XML (%s), discarding", exc)
        return False

    if root.tag != "tv":
        log.error("provider returned <%s>, not XMLTV, discarding", root.tag)
        return False

    tmp = path.with_name(f".{path.name}.tmp")

    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except OSError:
        log.exception("could not write guide, keeping existing one")
        tmp.unlink(missing_ok=True)
        return False

    log.info("refreshed guide (%d bytes)", len(data))
    return True


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    if not refresh(Path(os.environ["CACHE_FILE"]), PROVIDERS[os.environ["PROVIDER"]]):
        sys.exit(1)


if __name__ == "__main__":
    main()
