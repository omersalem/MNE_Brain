"""Acceptance and unit tests for P11 multimodal image and file upload endpoints."""

from __future__ import annotations

import base64
import json
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import pytest
from core.api.server import MNEBrainAPIHandler


def test_upload_image_and_retrieve(tmp_path):
    """Verify that valid base64 image data is stored and retrievable via GET."""
    handler = MNEBrainAPIHandler.__new__(MNEBrainAPIHandler)
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []

    # 1x1 transparent PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    b64_content = base64.b64encode(png_bytes).decode("ascii")

    payload = {
        "filename": "screenshot test.png",
        "mime_type": "image/png",
        "content_base64": b64_content,
    }

    responses = []
    def mock_json_response(status, data, extra_headers=None):
        responses.append((status, data))

    handler._json_response = mock_json_response

    handler._handle_upload_post(payload, owner_session={"username": "admin"})

    assert len(responses) == 1
    status, data = responses[0]
    assert status == 201
    assert data["is_image"] is True
    assert data["filename"] == "screenshot test.png"
    assert data["mime_type"] == "image/png"
    assert data["size"] == len(png_bytes)
    assert data["safe_name"].startswith("upl_")
    assert data["safe_name"].endswith("screenshot_test.png")

    # Now verify GET serving
    uploaded_file = Path(data["absolute_path"])
    assert uploaded_file.is_file()
    assert uploaded_file.read_bytes() == png_bytes

    # Clean up test artifact
    uploaded_file.unlink(missing_ok=True)


def test_upload_text_file_preview():
    """Verify that text configuration files are stored and text_content is decoded."""
    handler = MNEBrainAPIHandler.__new__(MNEBrainAPIHandler)
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []

    conf_text = "config firewall address\nedit FQDN_test\nset type fqdn\nend"
    b64_content = base64.b64encode(conf_text.encode("utf-8")).decode("ascii")

    payload = {
        "filename": "fortigate.conf",
        "mime_type": "text/plain",
        "content_base64": b64_content,
    }

    responses = []
    handler._json_response = lambda status, data, extra_headers=None: responses.append((status, data))

    handler._handle_upload_post(payload, owner_session={"username": "admin"})

    assert len(responses) == 1
    status, data = responses[0]
    assert status == 201
    assert data["is_image"] is False
    assert data["text_content"] == conf_text

    Path(data["absolute_path"]).unlink(missing_ok=True)


def test_upload_path_traversal_sanitization():
    """Verify that path traversal attempts are safely stripped from the filename."""
    handler = MNEBrainAPIHandler.__new__(MNEBrainAPIHandler)
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []

    payload = {
        "filename": "../../../etc/passwd.txt",
        "mime_type": "text/plain",
        "content_base64": base64.b64encode(b"test").decode("ascii"),
    }

    responses = []
    handler._json_response = lambda status, data, extra_headers=None: responses.append((status, data))

    handler._handle_upload_post(payload, owner_session={"username": "admin"})

    assert len(responses) == 1
    status, data = responses[0]
    assert status == 201
    assert ".." not in data["safe_name"]
    assert "/" not in data["safe_name"]
    assert "\\" not in data["safe_name"]
    assert data["safe_name"].endswith("passwd.txt")

    Path(data["absolute_path"]).unlink(missing_ok=True)


def test_upload_validation_errors():
    """Verify that invalid base64 and empty payloads are rejected."""
    handler = MNEBrainAPIHandler.__new__(MNEBrainAPIHandler)

    with pytest.raises(ValueError, match="content.*required"):
        handler._handle_upload_post({"filename": "test.png", "content_base64": ""}, None)

    with pytest.raises(ValueError, match="Invalid base64"):
        handler._handle_upload_post({"filename": "test.png", "content_base64": "not_valid_b64!!!"}, None)
