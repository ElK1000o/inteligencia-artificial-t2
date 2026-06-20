"""Tests for file upload security validation."""
import pytest
import io
from fastapi import UploadFile
from pathlib import Path
import re

# Test the validation logic directly
ALLOWED_EXTENSIONS = {".csv"}
MAX_SIZE_BYTES = 50 * 1024 * 1024

def safe_filename(original: str) -> str:
    name = re.sub(r'[^\w\-_. ]', '', original)
    return name[:128] or "upload"

class TestFileNameSanitization:
    def test_normal_filename_preserved(self):
        assert "materials.csv" in safe_filename("materials.csv")

    def test_path_traversal_removed(self):
        result = safe_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_xss_in_filename_removed(self):
        result = safe_filename('<script>alert("xss")</script>.csv')
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result

    def test_null_bytes_removed(self):
        result = safe_filename("file\x00name.csv")
        assert "\x00" not in result

    def test_long_filename_truncated(self):
        long_name = "A" * 500 + ".csv"
        result = safe_filename(long_name)
        assert len(result) <= 128

    def test_empty_filename_has_default(self):
        result = safe_filename("")
        assert len(result) > 0

class TestFileExtensionValidation:
    def test_csv_allowed(self):
        suffix = Path("data.csv").suffix.lower()
        assert suffix in ALLOWED_EXTENSIONS

    def test_py_not_allowed(self):
        suffix = Path("malicious.py").suffix.lower()
        assert suffix not in ALLOWED_EXTENSIONS

    def test_exe_not_allowed(self):
        suffix = Path("virus.exe").suffix.lower()
        assert suffix not in ALLOWED_EXTENSIONS

    def test_csv_uppercase_normalized(self):
        suffix = Path("DATA.CSV").suffix.lower()
        assert suffix in ALLOWED_EXTENSIONS

    def test_double_extension_not_allowed(self):
        # .csv.exe should fail
        suffix = Path("file.csv.exe").suffix.lower()
        assert suffix not in ALLOWED_EXTENSIONS

class TestCSVEncoding:
    def test_utf8_accepted(self):
        content = "formula,energy\nLiFePO4,-3.5\n".encode("utf-8")
        content.decode("utf-8")  # should not raise

    def test_invalid_encoding_detected(self):
        # Simulate binary/non-utf8 content
        content = b"\xff\xfe\x00\x01"  # UTF-16 BOM — invalid UTF-8
        with pytest.raises(UnicodeDecodeError):
            content.decode("utf-8")
