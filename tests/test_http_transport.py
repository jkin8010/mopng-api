#!/usr/bin/env python3
"""Tests for the shared transport and for the mopng_agent.py entry point."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import _http
import mopng_api
import mopng_agent


def _response(payload: bytes):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return payload

        def close(self):
            pass

    return _Resp()


class TestJsonHttpClient(unittest.TestCase):
    def test_sends_json_body_and_injected_headers(self):
        client = _http.JsonHttpClient("https://api.example", {"X-API-Key": "k"})
        with patch.object(_http.request, "urlopen", return_value=_response(b"{}")) as urlopen:
            client.request("POST", "/session", {"a": 1})
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.example/session")
        self.assertEqual(req.get_header("X-api-key"), "k")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(req.data, b'{"a": 1}')

    def test_no_body_request_omits_content_type(self):
        client = _http.JsonHttpClient("https://api.example/", {"Accept": "application/json"})
        with patch.object(_http.request, "urlopen", return_value=_response(b'{"ok": 1}')) as urlopen:
            result = client.request("GET", "/models")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.example/models")
        self.assertIsNone(req.data)
        self.assertIsNone(req.get_header("Content-type"))
        self.assertEqual(result, {"ok": 1})

    def test_empty_body_returns_empty_dict(self):
        client = _http.JsonHttpClient("https://api.example", {})
        with patch.object(_http.request, "urlopen", return_value=_response(b"")):
            self.assertEqual(client.request("DELETE", "/x"), {})

    def test_multipart_body_encodes_fields_and_file(self):
        client = _http.JsonHttpClient("https://api.example", {})
        fake = Path("/tmp/pic.png")
        with patch.object(_http.request, "urlopen", return_value=_response(b"{}")) as urlopen:
            client.request("POST", "/upload", {"k": "v"}, {"file": (fake, b"DATA")})
        req = urlopen.call_args.args[0]
        self.assertTrue(req.get_header("Content-type").startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="k"', req.data)
        self.assertIn(b'filename="pic.png"', req.data)
        self.assertIn(b"DATA", req.data)


class TestJsonHttpClientErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = _http.JsonHttpClient("https://api.example", {}, service="svc")

    def test_non_json_success_raises_runtime_error(self):
        with patch.object(_http.request, "urlopen", return_value=_response(b"<html>")):
            with self.assertRaises(RuntimeError) as ctx:
                self.client.request("GET", "/x")
        self.assertEqual(str(ctx.exception), "svc returned non-JSON data")

    def test_http_error_with_json_message(self):
        from urllib.error import HTTPError

        err = HTTPError("https://api.example", 400, "Bad", {}, _response(b'{"message": "bad key"}'))
        with patch.object(_http.request, "urlopen", side_effect=err):
            with self.assertRaises(RuntimeError) as ctx:
                self.client.request("GET", "/x")
        self.assertEqual(str(ctx.exception), "svc API error: bad key")

    def test_http_error_with_non_json_body(self):
        from urllib.error import HTTPError

        err = HTTPError("https://api.example", 502, "Bad", {}, _response(b"gateway down"))
        with patch.object(_http.request, "urlopen", side_effect=err):
            with self.assertRaises(RuntimeError) as ctx:
                self.client.request("GET", "/x")
        self.assertEqual(str(ctx.exception), "svc HTTP 502: gateway down")

    def test_urlerror_is_mapped_to_runtime_error(self):
        from urllib.error import URLError

        with patch.object(_http.request, "urlopen", side_effect=URLError("timed out")):
            with self.assertRaises(RuntimeError) as ctx:
                self.client.request("GET", "/x")
        self.assertIn("unavailable", str(ctx.exception))


class TestAgentClient(unittest.TestCase):
    def test_call_uses_agent_prefix_and_api_key_header(self):
        client = mopng_agent.AgentClient("https://agent.example/", "secret")
        with patch.object(_http.request, "urlopen", return_value=_response(b'{"session_id": "s1"}')) as urlopen:
            result = client.call("POST", "/session", {"intent": "x"})
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://agent.example/api/v1/open/agent/session")
        self.assertEqual(req.get_header("X-api-key"), "secret")
        self.assertEqual(req.get_header("Accept"), "application/json")
        self.assertEqual(result, {"session_id": "s1"})

    def test_network_failure_surfaces_as_runtime_error(self):
        from urllib.error import URLError

        client = mopng_agent.AgentClient("https://agent.example", "secret")
        with patch.object(_http.request, "urlopen", side_effect=URLError("dns")):
            with self.assertRaises(RuntimeError) as ctx:
                client.call("GET", "/models")
        self.assertTrue(str(ctx.exception).startswith("motu-agent unavailable"))


class TestAgentCLI(unittest.TestCase):
    def test_missing_api_key_returns_2(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(mopng_agent.main(["models"]), 2)

    def test_runtime_error_returns_2(self):
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call", side_effect=RuntimeError("boom")), \
                patch("sys.stdout"):
            self.assertEqual(mopng_agent.main(["models"]), 2)

    def test_models_command_prints_payload(self):
        payload = {"models": [{"name": "m1"}]}
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call", return_value=payload) as call, \
                patch("sys.stdout"):
            self.assertEqual(mopng_agent.main(["models", "--capability", "text-to-image"]), 0)
        self.assertIn("capability=text-to-image", call.call_args.args[1])

    def test_brief_rejects_too_many_references(self):
        args = mopng_agent.argparse.Namespace(
            reference_url=[f"https://x/{i}.png" for i in range(15)],
            intent="i", goal="g", usage=None, style_constraint=None, avoid=None,
            format="png", cost_mode="balanced", max_cost_points=10, max_time_sec=120,
            width=None, height=None,
        )
        with self.assertRaises(ValueError):
            mopng_agent._brief(args)

    def test_brief_requires_both_dimensions(self):
        args = mopng_agent.argparse.Namespace(
            reference_url=None, intent="i", goal="g", usage=None, style_constraint=None,
            avoid=None, format="png", cost_mode="balanced", max_cost_points=10,
            max_time_sec=120, width=1024, height=None,
        )
        with self.assertRaises(ValueError):
            mopng_agent._brief(args)


class TestGroupedCommandAlias(unittest.TestCase):
    def test_agent_prefix_is_stripped(self):
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call", return_value={}), \
                patch("sys.stdout"):
            self.assertEqual(mopng_agent.main(["agent", "models"]), 0)


class TestModuleImportModes(unittest.TestCase):
    """Both entry points must import when run as a file or via ``-m``."""

    def test_entry_points_and_helper_are_loaded(self):
        for name in ("_http", "mopng_api", "mopng_agent"):
            self.assertIn(name, sys.modules)

    def test_helper_module_is_shared_across_entry_points(self):
        import mopng_api

        self.assertIs(mopng_api.JsonHttpClient, _http.JsonHttpClient)
        self.assertIs(mopng_agent.JsonHttpClient, _http.JsonHttpClient)

    def test_scripts_http_is_a_distinct_module_object(self):
        """Run as a module, ``scripts._http`` is a separate module object.

        The two spelling must stay interchangeable: both are the same source file
        and expose the same client class, so no behaviour drifts between modes.
        """
        module = importlib.import_module("scripts._http")
        self.assertNotIn("scripts.", _http.__name__)
        self.assertEqual(
            Path(module.__file__).resolve(), Path(_http.__file__).resolve()
        )


class TestNoAutoApprove(unittest.TestCase):
    """`run` must never spend money on the user's behalf."""

    def _brief_argv(self, *extra):
        return ["run", "--intent", "i", "--goal", "g", *extra]

    def test_run_never_calls_approve(self):
        """Even a cheap Plan must stop for explicit user approval."""
        cheap_plan = {
            "session_id": "s1",
            "plan": {"total_cost": 0, "llm_billing": {"cost_virtual": 0}},
        }
        calls = []

        def fake_call(self, method, path, body=None):
            calls.append((method, path))
            return cheap_plan

        with patch.dict("os.environ", {"MOPNG_API_KEY": "k", "MOPNG_AGENT_AUTO_APPROVE_COST_POINTS": "999"}), \
                patch.object(mopng_agent.AgentClient, "call", fake_call), \
                patch("sys.stdout"):
            rc = mopng_agent.main(self._brief_argv())

        self.assertEqual(rc, 0)
        paths = [p for _, p in calls]
        self.assertNotIn("/session/s1/approve", paths)
        self.assertEqual(paths, ["/session"])

    def test_run_prints_approve_instruction(self):
        plan = {"session_id": "s2", "plan": {"total_cost": 3, "llm_billing": {"cost_virtual": 1}}}
        out = []
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call", return_value=plan), \
                patch("sys.stdout") as stdout:
            stdout.write = out.append
            mopng_agent.main(self._brief_argv())
        text = "".join(str(x) for x in out)
        self.assertIn("4", text)          # total_cost + cost_virtual
        self.assertIn("approve s2", text)

    def test_no_auto_approve_flag_is_gone(self):
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch("sys.stderr"), \
                self.assertRaises(SystemExit):
            mopng_agent.main(self._brief_argv("--no-auto-approve"))

    def test_auto_approve_env_var_is_not_read(self):
        source = Path(mopng_agent.__file__).read_text()
        self.assertNotIn("AUTO_APPROVE", source)


class TestPlanCostRendering(unittest.TestCase):
    """Plan amounts arrive as mixed types; rendering must never crash."""

    def _run(self, plan):
        out, err = [], []
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call",
                             return_value={"session_id": "s1", "plan": plan}), \
                patch("sys.stdout") as stdout, patch("sys.stderr") as stderr:
            stdout.write = out.append
            stderr.write = err.append
            rc = mopng_agent.main(["run", "--intent", "i", "--goal", "g"])
        return rc, "".join(str(x) for x in out), "".join(str(x) for x in err)

    def test_string_cost_virtual_does_not_crash(self):
        """Regression: total_cost int + cost_virtual str raised TypeError."""
        rc, out, _ = self._run({"total_cost": 0, "llm_billing": {"cost_virtual": "0.23"}})
        self.assertEqual(rc, 0)
        self.assertIn("0.23", out)

    def test_int_plus_string_sums(self):
        _, out, _ = self._run({"total_cost": 2, "llm_billing": {"cost_virtual": "0.16"}})
        self.assertIn("2.16", out)

    def test_whole_number_has_no_decimal_suffix(self):
        _, out, _ = self._run({"total_cost": 2})
        self.assertIn("Estimated cost: 2 points", out)

    def test_missing_cost_virtual_is_ignored(self):
        _, out, _ = self._run({"total_cost": 2, "llm_billing": {"cost_virtual": None}})
        self.assertIn("Estimated cost: 2 points", out)

    def test_garbage_cost_virtual_is_ignored(self):
        rc, out, _ = self._run({"total_cost": 2, "llm_billing": {"cost_virtual": "N/A"}})
        self.assertEqual(rc, 0)
        self.assertIn("Estimated cost: 2 points", out)

    def test_missing_total_cost_falls_back_to_manual_review(self):
        rc, out, err = self._run({"llm_billing": {"cost_virtual": "0.2"}})
        self.assertEqual(rc, 0)
        self.assertIn("unavailable", err)
        self.assertNotIn("Estimated cost", out)

    def test_bool_is_not_treated_as_number(self):
        self.assertIsNone(mopng_agent._as_number(True))

    def test_plan_not_a_dict(self):
        self.assertIsNone(mopng_agent._estimated_cost(["not", "a", "dict"]))
        self.assertIsNone(mopng_agent._estimated_cost(None))


class TestFailureClassification(unittest.TestCase):
    """Service outages and content rejections must not be conflated."""

    def test_safety_timeout_is_transient(self):
        """Real observation: safety_failed + moderation service timed out."""
        result = {"status": "failed", "error_code": "safety_failed",
                  "user_message": "内容安全检测服务暂时不可用（超时）"}
        self.assertEqual(mopng_agent._classify_failure(result), mopng_agent.FAILURE_TRANSIENT)

    def test_safety_violation_is_rejected(self):
        result = {"status": "failed", "error_code": "safety_failed",
                  "user_message": "生成内容包含违规信息"}
        self.assertEqual(mopng_agent._classify_failure(result), mopng_agent.FAILURE_REJECTED)

    def test_english_violation_marker_is_rejected(self):
        result = {"status": "failed", "user_message": "prompt violates safety policy"}
        self.assertEqual(mopng_agent._classify_failure(result), mopng_agent.FAILURE_REJECTED)

    def test_transient_marker_wins_over_safety_label(self):
        result = {"status": "failed", "error_code": "safety_failed",
                  "user_message": "upstream gateway timeout"}
        self.assertEqual(mopng_agent._classify_failure(result), mopng_agent.FAILURE_TRANSIENT)

    def test_unknown_code_is_not_called_rejection(self):
        result = {"status": "failed", "error_code": "weird_xyz",
                  "user_message": "something went wrong"}
        self.assertEqual(mopng_agent._classify_failure(result), mopng_agent.FAILURE_UNKNOWN)

    def test_nested_payload_is_scanned(self):
        result = {"status": "failed", "detail": {"reason": "服务不可用"}}
        self.assertEqual(mopng_agent._classify_failure(result), mopng_agent.FAILURE_TRANSIENT)

    def test_guidance_only_for_failures(self):
        self.assertIsNone(mopng_agent._failure_guidance({"status": "success"}))
        self.assertIsNone(mopng_agent._failure_guidance(None))

    def test_guidance_mentions_content_for_rejection(self):
        hint = mopng_agent._failure_guidance(
            {"status": "failed", "error_code": "safety_failed", "user_message": "违规内容"})
        self.assertIn("内容", hint)
        self.assertIn("重试不会通过", hint)

    def test_guidance_mentions_retry_for_transient(self):
        hint = mopng_agent._failure_guidance(
            {"status": "failed", "error_code": "safety_failed",
             "user_message": "内容安全检测服务暂时不可用（超时）"})
        self.assertIn("稍后重试", hint)
        self.assertIn("不是内容被拒", hint)

    def test_status_command_prints_hint_for_failure(self):
        result = {"status": "failed", "error_code": "safety_failed",
                  "user_message": "内容安全检测服务暂时不可用（超时）"}
        err = []
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call", return_value=result), \
                patch("sys.stdout"), patch("sys.stderr") as stderr:
            stderr.write = err.append
            self.assertEqual(mopng_agent.main(["status", "s1"]), 0)
        self.assertIn("Hint", "".join(str(x) for x in err))

    def test_status_command_silent_on_success(self):
        err = []
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_agent.AgentClient, "call", return_value={"status": "success"}), \
                patch("sys.stdout"), patch("sys.stderr") as stderr:
            stderr.write = err.append
            mopng_agent.main(["status", "s1"])
        self.assertEqual("".join(str(x) for x in err), "")


class TestNoDirectPaidCommands(unittest.TestCase):
    """Paid endpoints must not be reachable without a reviewed Plan."""

    PAID = ("remove-bg", "upscale", "outpainting", "translation", "text-to-image", "image-to-image")

    def test_cli_rejects_paid_commands(self):
        for command in self.PAID:
            with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                    patch("sys.stderr"), \
                    self.assertRaises(SystemExit):
                mopng_api.main([command])

    def test_module_defines_no_paid_command_handlers(self):
        for name in ("cmd_remove_bg", "cmd_upscale", "cmd_outpainting",
                     "cmd_translation", "cmd_text_to_image", "cmd_image_to_image"):
            self.assertFalse(hasattr(mopng_api, name), name)

    def test_module_has_no_paid_endpoints(self):
        source = Path(mopng_api.__file__).read_text()
        for endpoint in ("/open/image/", "/ai/generations", "/images/upload", "/ai/tools/"):
            self.assertNotIn(endpoint, source, endpoint)

    def test_list_models_is_read_only(self):
        with patch.dict("os.environ", {"MOPNG_API_KEY": "k"}), \
                patch.object(mopng_api, "_api_request", return_value={"data": {"models": []}}) as req, \
                patch("sys.stdout"):
            self.assertEqual(mopng_api.main(["list-models"]), 0)
        self.assertEqual(req.call_args.args[0], "GET")


if __name__ == "__main__":
    unittest.main(verbosity=2)