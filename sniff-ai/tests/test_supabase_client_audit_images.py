"""Tests for SupabaseUploader's audit-screenshot persistence and read-back.

Regression tests for a real production gap found live: audit screenshots
were never uploaded to Supabase Storage - AuditReport.images.* stayed as
local filesystem paths, which only ever existed on the ephemeral Cloud Run
instance that captured them. A real seeded audit became unviewable (report
and screenshots both) after nothing more than a routine backend redeploy.

Mocks the underlying `supabase` client - no real network/Supabase project
needed.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.supabase_client import SupabaseUploader


@pytest.fixture
def uploader():
    with patch("src.integrations.supabase_client.create_client"):
        u = SupabaseUploader(supabase_url="https://project.supabase.co", supabase_key="test-key")
    u.client = MagicMock()
    return u


class TestUploadAuditImages:
    def test_uploads_each_existing_file_and_returns_public_urls(self, uploader, tmp_path):
        above_fold = tmp_path / "above_fold.png"
        above_fold.write_bytes(b"fake-png-bytes")
        full_page = tmp_path / "full_page.png"
        full_page.write_bytes(b"fake-png-bytes")

        uploader.client.storage.from_.return_value.get_public_url.side_effect = (
            lambda path: f"https://project.supabase.co/storage/v1/object/public/sniff-screenshots/{path}"
        )

        result = uploader._upload_audit_images(
            "audit_123", {"above_fold": str(above_fold), "full_page": str(full_page)}
        )

        assert result == {
            "above_fold": "https://project.supabase.co/storage/v1/object/public/sniff-screenshots/audit_123/above_fold.png",
            "full_page": "https://project.supabase.co/storage/v1/object/public/sniff-screenshots/audit_123/full_page.png",
        }
        assert uploader.client.storage.from_.return_value.upload.call_count == 2

    def test_leaves_path_unchanged_when_file_does_not_exist(self, uploader):
        result = uploader._upload_audit_images("audit_123", {"above_fold": "/does/not/exist.png"})

        assert result == {"above_fold": "/does/not/exist.png"}
        uploader.client.storage.from_.return_value.upload.assert_not_called()

    def test_leaves_path_unchanged_when_upload_raises(self, uploader, tmp_path):
        image = tmp_path / "annotated.png"
        image.write_bytes(b"fake-png-bytes")
        uploader.client.storage.from_.return_value.upload.side_effect = RuntimeError("storage is down")

        result = uploader._upload_audit_images("audit_123", {"annotated": str(image)})

        assert result == {"annotated": str(image)}

    def test_upload_audit_rewrites_report_images_before_inserting(self, uploader, tmp_path):
        image = tmp_path / "above_fold.png"
        image.write_bytes(b"fake-png-bytes")
        uploader.client.storage.from_.return_value.get_public_url.return_value = "https://cdn.example/above_fold.png"

        report = MagicMock()
        report.model_dump.return_value = {
            "overall_score": 7.0,
            "label": "Great",
            "verdict": "Solid",
            "core_web_vitals": {},
            "images": {"above_fold": str(image)},
        }

        uploader.upload_audit(audit_id="audit_123", url="https://example.com", persona=None, report=report)

        inserted = uploader.client.table.return_value.insert.call_args.args[0]
        assert inserted["report_json"]["images"]["above_fold"] == "https://cdn.example/above_fold.png"


class TestGetAudit:
    def test_returns_the_row_when_found(self, uploader):
        uploader.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"audit_id": "audit_123", "report_json": {"overall_score": 5.0}}
        ]

        row = uploader.get_audit("audit_123")

        assert row == {"audit_id": "audit_123", "report_json": {"overall_score": 5.0}}

    def test_returns_none_when_not_found(self, uploader):
        uploader.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        assert uploader.get_audit("audit_never_existed") is None
