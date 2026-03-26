"""Check GitHub releases for newer versions of HomerFindr."""

import re
from typing import Optional

GITHUB_REPO = "iamtr0n/HomerFindr"
_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
INSTALL_CMD = "pip install --upgrade homesearch"


def check_for_update(current_version: str, timeout: float = 3.0) -> Optional[str]:
    """Return newer version string from GitHub if available, else None.

    Designed for background threads — silently returns None on any error.
    """
    try:
        import httpx
        r = httpx.get(
            _RELEASES_API,
            timeout=timeout,
            headers={"Accept": "application/vnd.github.v3+json"},
            follow_redirects=True,
        )
        if r.status_code == 200:
            tag = r.json().get("tag_name", "").lstrip("v")
            if tag and _is_newer(tag, current_version):
                return tag
    except Exception:
        pass
    return None


def _is_newer(remote: str, local: str) -> bool:
    """Return True if remote semver is strictly greater than local."""
    def _parts(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    return _parts(remote) > _parts(local)
