#!/usr/bin/env python3
"""Unit tests for mopng_api.py"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import mopng_api as api


class TestImageValidation(unittest.TestCase):
    """Test image validation functions"""
    
    def test_detect_png(self):
        """Test PNG format detection"""
        png_header = b"\x89PNG\r\n\x1a\n"
        self.assertEqual(api._detect_image_format(png_header), "png")
    
    def test_detect_jpeg(self):
        """Test JPEG format detection"""
        jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        self.assertEqual(api._detect_image_format(jpeg_header), "jpeg")
    
    def test_detect_webp(self):
        """Test WEBP format detection"""
        webp_header = b"RIFF\x00\x00\x00\x00WEBPVP8 "
        self.assertEqual(api._detect_image_format(webp_header), "webp")
    
    def test_detect_unknown(self):
        """Test unknown format detection"""
        self.assertIsNone(api._detect_image_format(b"NOTANIMAGE"))


class TestWorkspaceUtils(unittest.TestCase):
    """Test workspace utilities"""
    
    def test_ensure_within_valid(self):
        """Test path within workspace"""
        root = Path("/workspace")
        path = Path("/workspace/subdir/file.txt")
        # Should not raise
        api._ensure_within(path, root, "test path")
    
    def test_ensure_within_invalid(self):
        """Test path outside workspace"""
        root = Path("/workspace")
        path = Path("/other/file.txt")
        with self.assertRaises(ValueError):
            api._ensure_within(path, root, "test path")


class TestAPIRequest(unittest.TestCase):
    """Test API request functionality"""
    
    @patch('mopng_api.request.urlopen')
    def test_api_request_success(self, mock_urlopen):
        """Test successful API request"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 0, "data": {"result": "ok"}}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = api._api_request("GET", "/test", "test_key")
        self.assertEqual(result["code"], 0)
    
    @patch('mopng_api.request.urlopen')
    def test_api_request_error(self, mock_urlopen):
        """Test API request error"""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 400, "Bad Request", {}, None
        )
        
        with self.assertRaises(RuntimeError):
            api._api_request("GET", "/test", "test_key")


class TestPollTask(unittest.TestCase):
    """Test task polling functionality"""
    
    @patch('mopng_api._api_request')
    def test_poll_task_completed(self, mock_request):
        """Test polling until completed"""
        mock_request.return_value = {
            "data": {"status": "completed", "result": {"imageUrl": "https://example.com/img.png"}}
        }
        
        result = api._poll_task("/tasks", "task-123", "test_key", max_retries=1)
        self.assertEqual(result["status"], "completed")
    
    @patch('mopng_api._api_request')
    def test_poll_task_failed(self, mock_request):
        """Test polling task failed"""
        mock_request.return_value = {
            "data": {"status": "failed", "message": "Processing error"}
        }
        
        with self.assertRaises(RuntimeError) as ctx:
            api._poll_task("/tasks", "task-123", "test_key", max_retries=1, interval=0)
        self.assertIn("failed", str(ctx.exception))


class TestDownloadImage(unittest.TestCase):
    """Test image download functionality"""
    
    @patch('mopng_api.request.urlopen')
    def test_download_image(self, mock_urlopen):
        """Test image download"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_image_data"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.png"
            api._download_image("https://example.com/img.png", output_path)
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"fake_image_data")


class TestCommandArguments(unittest.TestCase):
    """Test command argument parsing"""
    
    def test_remove_bg_args(self):
        """Test remove-bg argument parsing"""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        cmd = sub.add_parser("remove-bg")
        cmd.add_argument("--input", "-i", required=True)
        cmd.add_argument("--output", "-o", required=True)
        cmd.add_argument("--output-format", default="png")
        cmd.add_argument("--async-mode", action="store_true")
        cmd.add_argument("--return-mask", action="store_true")
        cmd.add_argument("--only-mask", action="store_true")
        
        args = parser.parse_args(["remove-bg", "-i", "test.jpg", "-o", "out.png"])
        self.assertEqual(args.input, "test.jpg")
        self.assertEqual(args.output, "out.png")
        self.assertEqual(args.output_format, "png")
    
    def test_upscale_args(self):
        """Test upscale argument parsing"""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        cmd = sub.add_parser("upscale")
        cmd.add_argument("--input", "-i", required=True)
        cmd.add_argument("--output", "-o", required=True)
        cmd.add_argument("--scale", type=int, default=2)
        
        args = parser.parse_args(["upscale", "-i", "test.jpg", "-o", "out.png", "--scale", "4"])
        self.assertEqual(args.scale, 4)
    
    def test_text_to_image_args(self):
        """Test text-to-image argument parsing"""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        cmd = sub.add_parser("text-to-image")
        cmd.add_argument("--prompt", "-p", required=True)
        cmd.add_argument("--output", "-o", required=True)
        cmd.add_argument("--model", default="wanx-v2.5")
        
        args = parser.parse_args([
            "text-to-image", 
            "-p", "a cat", 
            "-o", "out.png",
            "--model", "wanx-v2"
        ])
        self.assertEqual(args.prompt, "a cat")
        self.assertEqual(args.model, "wanx-v2")


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
