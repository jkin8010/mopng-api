#!/usr/bin/env python3
"""Small stdlib-only client for motu-agent's public MoPNG Agent API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib import parse

try:
    from _http import JsonHttpClient
except ImportError:  # executed as a module (`python -m scripts.mopng_agent`)
    from scripts._http import JsonHttpClient


DEFAULT_BASE_URL = "https://agent-api.mopng.cn"
API_PREFIX = "/api/v1/open/agent"


def _json(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc


class AgentClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 90) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._http = JsonHttpClient(
            self.base_url + API_PREFIX,
            {"Accept": "application/json", "X-API-Key": api_key},
            timeout,
            service="motu-agent",
        )

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        return self._http.request(method, path, data=body)


def _client(args: argparse.Namespace) -> AgentClient:
    key = os.getenv("MOPNG_API_KEY")
    if not key:
        raise ValueError("MOPNG_API_KEY is required")
    return AgentClient(os.getenv("MOPNG_AGENT_BASE_URL", DEFAULT_BASE_URL), key, args.timeout)


def _as_number(value: object) -> float | None:
    """Coerce a plan amount to a number.

    The service sends mixed types: ``total_cost`` arrives as an int while
    ``llm_billing.cost_virtual`` arrives as a decimal string ("0.23"). Adding
    them directly raised TypeError, so normalise everything here.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _estimated_cost(plan: object) -> float | None:
    """Estimated points for a Plan: step cost plus planning virtual cost."""
    if not isinstance(plan, dict):
        return None
    total = _as_number(plan.get("total_cost"))
    if total is None:
        return None
    llm_billing = plan.get("llm_billing")
    cost_virtual = _as_number(llm_billing.get("cost_virtual")) if isinstance(llm_billing, dict) else None
    return total + (cost_virtual or 0.0)


def _format_points(value: float) -> str:
    """Render points without a trailing ``.0`` for whole numbers."""
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _brief(args: argparse.Namespace) -> dict:
    references = args.reference_url or []
    if len(references) > 14:
        raise ValueError("at most 14 --reference-url values are allowed")
    reference = references[0] if references else "prompt-only"
    subject_type = "image" if references else "text"
    style = {}
    if args.style_constraint:
        style["constraint"] = args.style_constraint
    if args.avoid:
        style["avoid"] = args.avoid
    brief = {
        "user_intent": args.intent,
        "spec": {
            "goal": args.goal,
            "usage": args.usage,
            "subject": {"type": subject_type, "reference": reference},
            "style": style,
            "format": args.format,
        },
        "budget": {
            "cost_mode": args.cost_mode,
            "max_cost_points": args.max_cost_points,
            "max_time_sec": args.max_time_sec,
        },
    }
    if references:
        brief["spec"]["subject"]["references"] = references
    if args.width or args.height:
        if not args.width or not args.height:
            raise ValueError("--width and --height must be provided together")
        brief["spec"]["size"] = {"width": args.width, "height": args.height}
    return brief


def _print(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=float, default=90)


def _add_brief_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--intent", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--reference-url", action="append", help="reference image URL; repeat up to 14 times")
    parser.add_argument("--usage")
    parser.add_argument("--style-constraint")
    parser.add_argument("--avoid")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--format", choices=("png", "jpg", "jpeg", "webp"), default="png")
    parser.add_argument("--cost-mode", choices=("economy", "balanced", "premium"), default="balanced")
    parser.add_argument("--max-cost-points", type=int, default=10)
    parser.add_argument("--max-time-sec", type=int, default=120)


def _collect_text(payload: object) -> str:
    """Flatten all string/number values of a failure payload into one blob."""
    parts: list[str] = []
    stack = [payload]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            parts.append(str(item))
    return " ".join(parts).lower()


# Service-side temporary failures: the safety/moderation backend timed out or
# errored. Retrying later may work; the content itself was not judged.
_TRANSIENT_MARKERS = (
    "timeout", "timed out", "超时", "暂时不可用", "暂不可用", "服务不可用",
    "不可用", "unavailable", "temporarily", "temporary", "try again later",
    "请稍后", "稍后重试", "稍后再试", "connection", "connectionerror",
    "connection reset", "network", "gateway timeout", "internal error",
    "internal server error", "service error", "upstream", "rate limit",
    "too many requests", "overloaded", "system busy", "服务异常", "系统繁忙",
)

# Content was judged and rejected: retrying the same request will not help.
_REJECTION_MARKERS = (
    "violat", "unsafe", "not allowed", "prohibited", "forbidden", "banned",
    "explicit", "nsfw", "sexual", "porn", "nudity", "violence", "gore",
    "违规", "敏感", "不安全", "禁止", "不通过", "未通过", "未通过检测",
    "内容不合规", "不合规", "色情", "暴力", "违禁", "驳回",
)

FAILURE_TRANSIENT = "transient"
FAILURE_REJECTED = "rejected"
FAILURE_UNKNOWN = "unknown"


def _classify_failure(result: dict) -> str:
    """Tell a service outage apart from a content rejection.

    Uses signal combination rather than a fixed error-code list: the safety
    fields are inspected first, then the message texts. Anything we cannot
    place with confidence stays ``unknown`` and is reported as-is, so an
    unrecognised code is never silently called a content rejection.
    """
    if not isinstance(result, dict):
        return FAILURE_UNKNOWN

    messages = []
    for key in ("user_message", "message", "error", "error_message", "detail", "reason"):
        value = result.get(key)
        if isinstance(value, str):
            messages.append(value)
        elif value is not None:
            # Nested payloads ({"detail": {"reason": "..."}}) are scanned too.
            messages.append(value)
    text = _collect_text(messages) if messages else ""

    # 1. An explicit safety/moderation code means content was judged.
    safety_code = any(
        isinstance(result.get(key), str) and "safety" in result[key].lower()
        for key in ("error_code", "errorCode", "code")
    )
    transient = any(marker in text for marker in _TRANSIENT_MARKERS)
    rejected = any(marker in text for marker in _REJECTION_MARKERS)

    # 2. Transient evidence wins over the generic "safety" label: a safety
    #    check that timed out did not judge the content (this is the failure
    #    observed in practice: safety_failed + "内容安全检测服务暂时不可用（超时）").
    if transient:
        return FAILURE_TRANSIENT
    # 3. A safety code with no outage/transient evidence means it was refused.
    if safety_code:
        return FAILURE_REJECTED
    if rejected:
        return FAILURE_REJECTED
    return FAILURE_UNKNOWN


def _failure_guidance(result: dict) -> str | None:
    """One-line advice for a failed execution, or None when successful."""
    if not isinstance(result, dict):
        return None
    if result.get("status") not in {"failed", "partial_failed", "terminated"}:
        return None
    kind = _classify_failure(result)
    if kind == FAILURE_TRANSIENT:
        return (
            "上游服务临时故障（安全检测/推理服务不可用或超时），不是内容被拒。"
            "出图步骤未计入费用；请稍后重试，持续失败需要服务端排查。"
        )
    if kind == FAILURE_REJECTED:
        return (
            "内容未通过服务端安全检测：这是对生成内容的判定结果，原样重试不会通过。"
            "请调整提示词或参考图后重新规划。"
        )
    return (
        "执行失败；服务端未给出可归类的错误信息，请以原始 error_code/user_message 为准，"
        "不要自行判定是内容违规还是服务故障。"
    )


def _watch(client: AgentClient, session_id: str, interval: float) -> dict:
    while True:
        result = client.call("GET", f"/session/{session_id}/exec")
        status = result.get("status")
        if status in {"success", "partial_failed", "failed", "terminated"}:
            return result
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Keep the skill-facing form ``... mopng_agent.py agent run`` while also
    # allowing the shorter CLI form ``... mopng_agent.py run``.
    if argv and argv[0] == "agent":
        argv = argv[1:]
    parser = argparse.ArgumentParser(description="Call motu-agent MoPNG Agent OpenAPI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="create a Brief and show its Plan for review")
    _add_common(run)
    _add_brief_args(run)

    brief = sub.add_parser("brief", help="create a session and return its Plan")
    _add_common(brief)
    _add_brief_args(brief)

    plan = sub.add_parser("plan")
    _add_common(plan)
    plan.add_argument("session_id")

    revision = sub.add_parser("revision")
    _add_common(revision)
    revision.add_argument("session_id")
    revision.add_argument("--plan-id", required=True)
    revision.add_argument("--round", type=int, required=True)
    revision.add_argument("--feedback-json", required=True)
    revision.add_argument("--reason")

    approve = sub.add_parser("approve")
    _add_common(approve)
    approve.add_argument("session_id")

    status = sub.add_parser("status")
    _add_common(status)
    status.add_argument("session_id")
    status.add_argument("--watch", action="store_true")
    status.add_argument("--poll-interval", type=float, default=3)

    models = sub.add_parser("models", help="list models currently exposed by motu-agent")
    _add_common(models)
    models.add_argument("--capability", default="text-to-image")

    for name in ("interrupt", "delete"):
        command = sub.add_parser(name)
        _add_common(command)
        command.add_argument("session_id")

    args = parser.parse_args(argv)
    try:
        client = _client(args)
        if args.command in {"run", "brief"}:
            result = client.call("POST", "/session", _brief(args))
            _print(result)
            if args.command == "run":
                # Never approve on the user's behalf: `run` only prepares the
                # session and shows the Plan. Spending requires an explicit
                # `approve` call made by the user.
                session_id = result.get("session_id")
                estimated = _estimated_cost(result.get("plan"))
                if estimated is None:
                    print("Plan cost unavailable; review and approve manually.", file=sys.stderr)
                else:
                    print(f"Estimated cost: {_format_points(estimated)} points. Review the Plan above, then run:")
                    print(f"  python3 scripts/mopng_agent.py approve {session_id}")
        elif args.command == "plan":
            _print(client.call("GET", f"/session/{args.session_id}/plan"))
        elif args.command == "models":
            capability = parse.quote(args.capability, safe="-_")
            _print(client.call("GET", f"/models?capability={capability}"))
        elif args.command == "revision":
            feedback = _json(args.feedback_json)
            if not isinstance(feedback, list):
                raise ValueError("--feedback-json must be a JSON array")
            body = {"plan_id": args.plan_id, "round": args.round, "feedback": feedback}
            if args.reason:
                body["reason"] = args.reason
            _print(client.call("POST", f"/session/{args.session_id}/revision", body))
        elif args.command == "approve":
            _print(client.call("POST", f"/session/{args.session_id}/approve"))
        elif args.command == "status":
            result = _watch(client, args.session_id, args.poll_interval) if args.watch else client.call("GET", f"/session/{args.session_id}/exec")
            _print(result)
            guidance = _failure_guidance(result)
            if guidance:
                print(f"Hint: {guidance}", file=sys.stderr)
        elif args.command == "interrupt":
            _print(client.call("POST", f"/session/{args.session_id}/interrupt"))
        else:
            client.call("DELETE", f"/session/{args.session_id}")
    except (RuntimeError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
