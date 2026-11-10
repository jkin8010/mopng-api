#!/usr/bin/env python3
"""MoPNG read-only helper (model listing, URL safety checks) for OpenClaw.

Paid image work is not implemented here: it goes through mopng_agent.py after
the user reviews and approves a Plan.
"""

import argparse
import ipaddress
import os
import sys
from pathlib import Path
from urllib import parse

try:
    from _http import JsonHttpClient
except ImportError:  # executed as a module (`python -m scripts.mopng_api`)
    from scripts._http import JsonHttpClient

DEFAULT_API_BASE_URL = "https://mo-api.mopng.cn"
BASE_URL = os.getenv("MOPNG_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
# Separate entry so upscale can move to its own host without touching call sites.
UPSCALE_URL = os.getenv("MOPNG_UPSCALE_BASE_URL", BASE_URL).rstrip("/")

# Remote image URL passed as --input: only https, host must be under MoPNG or MOPNG_EXTRA_ALLOWED_IMAGE_HOSTS.
_USER_URL_SUFFIX = "mopng.cn"
_FORBIDDEN_RESULT_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",  # nosec B104 — blocklisted hostname for SSRF checks, not socket bind
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
    }
)


def _workspace_root() -> Path:
    """Workspace boundary for input/output paths.

    Resolved once (no CWD fallback) so the security boundary does not drift with
    the process working directory. Falls back to the checkout that contains these
    scripts, then to CWD for callers outside the OpenClaw layout.
    """
    env_root = os.getenv("OPENCLAW_WORKSPACE")
    if env_root:
        return Path(env_root).expanduser().resolve()
    # Layout: <root>/scripts/mopng_api.py — only use it when that layout holds.
    script_file = Path(__file__).resolve()
    if script_file.parent.name == "scripts":
        return script_file.parent.parent
    return Path.cwd().resolve()


def _ensure_within(path: Path, root: Path, label: str) -> None:
    """Reject paths whose fully resolved form escapes ``root``.

    Both sides are normalised: ``..`` segments and symlinks are resolved before
    the prefix check, so a literal path under the root cannot point outside it.
    """
    try:
        path.resolve(strict=False).relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"{label} must be inside workspace: {root}")


def _extra_allowed_user_image_hosts() -> frozenset[str]:
    raw = os.environ.get("MOPNG_EXTRA_ALLOWED_IMAGE_HOSTS", "")
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def _host_matches_user_allowlist(host: str) -> bool:
    h = host.lower().rstrip(".")
    if not h:
        return False
    if h == _USER_URL_SUFFIX or h.endswith("." + _USER_URL_SUFFIX):
        return True
    for entry in _extra_allowed_user_image_hosts():
        e = entry.rstrip(".").lower()
        if not e:
            continue
        if e.startswith("."):
            suf = e[1:]
            if h == suf or h.endswith("." + suf):
                return True
        elif h == e or h.endswith("." + e):
            return True
    return False


def _validate_user_image_url(url: str) -> None:
    """Restrict user-supplied image URLs (SSRF mitigation for URLs forwarded to MoPNG)."""
    u = url.strip()
    p = parse.urlparse(u)
    if p.scheme.lower() != "https":
        raise ValueError("Remote image input must use https:// (http is not allowed).")
    if not p.hostname:
        raise ValueError("Remote image URL must include a valid hostname.")
    if p.username is not None or p.password is not None:
        raise ValueError("URLs with embedded credentials are not allowed.")
    host = p.hostname
    if not _host_matches_user_allowlist(host):
        raise ValueError(
            "Remote image URL host is not allowed. "
            f"Use a hostname under {_USER_URL_SUFFIX}, or set MOPNG_EXTRA_ALLOWED_IMAGE_HOSTS "
            "(comma-separated hosts or suffixes such as .cdn.example.com)."
        )


def _host_is_ssrf_risk(host: str) -> bool:
    hn = host.lower().strip(".")
    if not hn:
        return True
    if hn in _FORBIDDEN_RESULT_HOSTS:
        return True
    if hn.endswith(".local") or hn.endswith(".localhost"):
        return True
    for candidate in (hn, hn.strip("[]")):
        try:
            ip = ipaddress.ip_address(candidate)
            return bool(
                ip.is_private
                or ip.is_loopback
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_link_local
            )
        except ValueError:
            continue
    return False


def _validate_result_download_url(url: str) -> None:
    """Validate URLs returned by MoPNG before downloading (HTTPS + no obvious SSRF targets)."""
    u = url.strip()
    p = parse.urlparse(u)
    if p.scheme.lower() != "https":
        raise ValueError("Download URL must use https.")
    if not p.hostname:
        raise ValueError("Download URL must include a hostname.")
    if p.username is not None or p.password is not None:
        raise ValueError("Download URL with credentials is not allowed.")
    if _host_is_ssrf_risk(p.hostname):
        raise ValueError("Download URL host is not allowed.")


def _api_request(method: str, endpoint: str, api_key: str, data: dict | None = None,
                 files: dict | None = None, timeout: int = 90, base_url: str = BASE_URL) -> dict:
    """Make API request with proper auth"""
    client = JsonHttpClient(base_url, {"Authorization": f"Bearer {api_key}"}, timeout)
    return client.request(method, endpoint, data=data, files=files)


def cmd_list_models(args, api_key: str) -> int:
    """List available AI models"""
    endpoint = "/api/v1/open/ai/models"
    if args.type:
        endpoint += f"?type={args.type}"
    
    resp = _api_request("GET", endpoint, api_key)
    models = resp.get("data", {}).get("models", [])
    
    print(f"Available models ({len(models)} total):")
    print("-" * 60)
    for m in models:
        print(f"  Model: {m.get('model')}")
        print(f"  Type: {m.get('type')}")
        print(f"  Provider: {m.get('provider')}")
        print(f"  Description: {m.get('description', 'N/A')}")
        print("-" * 60)
    
    return 0


def main(argv: list[str] | None = None) -> int:
    """Read-only CLI.

    Paid image operations are intentionally *not* exposed here: they run only
    through `mopng_agent.py` after the user reviews and approves a Plan.
    """
    p = argparse.ArgumentParser(
        description="MoPNG read-only helper (paid work goes through mopng_agent.py)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # list-models
    cmd_lm = sub.add_parser("list-models", help="List available models (no cost)")
    cmd_lm.add_argument("--type", choices=["text_to_image", "image_to_image", "image_edit"], help="Filter by type")

    args = p.parse_args(argv)
    
    # Get API key
    api_key = os.getenv("MOPNG_API_KEY")
    if not api_key:
        print("Missing MOPNG_API_KEY environment variable", file=sys.stderr)
        return 2
    
    try:
        if args.command == "list-models":
            return cmd_list_models(args, api_key)
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
