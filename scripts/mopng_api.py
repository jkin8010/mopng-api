#!/usr/bin/env python3
"""MoPNG read-only helper (model listing) for OpenClaw.

Paid image work is not implemented here: it goes through mopng_agent.py after
the user reviews and approves a Plan.
"""

import argparse
import os
import sys

try:
    from _http import JsonHttpClient
except ImportError:  # executed as a module (`python -m scripts.mopng_api`)
    from scripts._http import JsonHttpClient

DEFAULT_API_BASE_URL = "https://mo-api.mopng.cn"
BASE_URL = os.getenv("MOPNG_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
UPSCALE_URL = os.getenv("MOPNG_UPSCALE_BASE_URL", BASE_URL).rstrip("/")


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
