#!/usr/bin/env python3
"""Unit tests for mopng_api.py"""

import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import _http

# Add repo root and scripts to path: entry points resolve their sibling helpers
# (`_http`) on the scripts dir, tests patch third-party modules (urllib) as loaded.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import mopng_api as api


class TestApiBaseUrlConfig(unittest.TestCase):
    """BASE_URL / UPSCALE_URL have a single configurable default."""

    def _reload(self, **env):
        import importlib

        with patch.dict(os.environ, env, clear=False):
            for key in ("MOPNG_API_BASE_URL", "MOPNG_UPSCALE_BASE_URL"):
                if key not in env:
                    os.environ.pop(key, None)
            return importlib.reload(api)

    def tearDown(self):
        self._reload()

    def test_defaults_are_identical_and_trimmed(self):
        mod = self._reload()
        self.assertEqual(mod.BASE_URL, "https://mo-api.mopng.cn")
        self.assertEqual(mod.UPSCALE_URL, mod.BASE_URL)

    def test_env_overrides_base_url(self):
        mod = self._reload(MOPNG_API_BASE_URL="https://staging.example/")
        self.assertEqual(mod.BASE_URL, "https://staging.example")
        self.assertEqual(mod.UPSCALE_URL, "https://staging.example")

    def test_upscale_can_override_independently(self):
        mod = self._reload(
            MOPNG_API_BASE_URL="https://api.example",
            MOPNG_UPSCALE_BASE_URL="https://upscale.example/",
        )
        self.assertEqual(mod.BASE_URL, "https://api.example")
        self.assertEqual(mod.UPSCALE_URL, "https://upscale.example")


class TestAPIRequest(unittest.TestCase):
    """Test API request functionality"""
    
    @patch('_http.request.urlopen')
    def test_api_request_success(self, mock_urlopen):
        """Test successful API request"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 0, "data": {"result": "ok"}}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = api._api_request("GET", "/test", "test_key")
        self.assertEqual(result["code"], 0)
    
    @patch('_http.request.urlopen')
    def test_api_request_error(self, mock_urlopen):
        """Test API request error"""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 400, "Bad Request", {}, None
        )
        
        with self.assertRaises(RuntimeError):
            api._api_request("GET", "/test", "test_key")

    @patch('_http.request.urlopen')
    def test_api_request_network_error_is_runtime_error(self, mock_urlopen):
        """Network failures must surface as RuntimeError, not leak URLError."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("timed out")

        with self.assertRaises(RuntimeError) as ctx:
            api._api_request("GET", "/test", "test_key")
        self.assertIn("unavailable", str(ctx.exception))

    @patch('_http.request.urlopen')
    def test_api_request_http_error_message_from_json(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 400, "Bad Request", {},
            io.BytesIO(b'{"message": "invalid key"}'),
        )

        with self.assertRaises(RuntimeError) as ctx:
            api._api_request("GET", "/test", "test_key")
        self.assertEqual(str(ctx.exception), "MoPNG API API error: invalid key")

    @patch('_http.request.urlopen')
    def test_api_request_http_error_non_json_body(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 503, "Unavailable", {}, io.BytesIO(b"boom")
        )

        with self.assertRaises(RuntimeError) as ctx:
            api._api_request("GET", "/test", "test_key")
        self.assertEqual(str(ctx.exception), "MoPNG API HTTP 503: boom")

    @patch('_http.request.urlopen')
    def test_api_request_non_json_success_body(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.assertRaises(RuntimeError) as ctx:
            api._api_request("GET", "/test", "test_key")
        self.assertIn("non-JSON", str(ctx.exception))

    @patch('_http.request.urlopen')
    def test_api_request_sends_bearer_auth_to_given_base_url(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 0}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        api._api_request("GET", "/test", "secret", base_url="https://alt.example")

        req = mock_urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://alt.example/test")
        self.assertEqual(req.get_header("Authorization"), "Bearer secret")

    @patch('_http.request.urlopen')
    def test_api_request_uploads_multipart_file(self, mock_urlopen):
        import tempfile

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 0}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "pic.png"
            image.write_bytes(b"PNGDATA")
            api._api_request("POST", "/upload", "k", files={"file": (image, b"PNGDATA")})

        req = mock_urlopen.call_args.args[0]
        self.assertTrue(req.get_header("Content-type").startswith("multipart/form-data"))
        self.assertIn(b'filename="pic.png"', req.data)


class TestEnvironment(unittest.TestCase):
    """Test environment setup"""
    
    def test_api_key_required(self):
        """Test that API key is required"""
        # Save original env
        original_key = os.environ.get("MOPNG_API_KEY")
        
        try:
            # Remove API key
            if "MOPNG_API_KEY" in os.environ:
                del os.environ["MOPNG_API_KEY"]
            
            # Import should work, but main should fail
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "scripts.mopng_api", "list-models"],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent.parent)
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("MOPNG_API_KEY", result.stderr)
        finally:
            # Restore original env
            if original_key:
                os.environ["MOPNG_API_KEY"] = original_key


if __name__ == "__main__":
    unittest.main(verbosity=2)
