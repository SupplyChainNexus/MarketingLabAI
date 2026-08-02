"""Campaign persistence, including compliance reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.compliance.models import ComplianceReport
from app.config import Settings, load_settings
from app.models import CampaignBrief, GeneratedContent
from app.services.json_storage import JsonStorage


class CampaignService:
    """Store campaign briefs, generated content, and compliance reports."""

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.storage = JsonStorage(self.settings.database_folder / "campaigns")

        self.output_folder = self.settings.output_folder / "campaigns"
        self.output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.compliance_output_folder = self.settings.output_folder / "compliance"
        self.compliance_output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_brief(
        self,
        brief: CampaignBrief,
    ) -> CampaignBrief:
        """Persist a campaign brief."""

        record = {
            "record_type": "campaign_brief",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "data": brief.to_dict(),
        }

        self.storage.save(
            f"{brief.campaign_id}-brief",
            record,
        )

        return brief

    def save_generated_content(
        self,
        generated: GeneratedContent,
    ) -> Path:
        """Persist generated content and its AI audit trail."""

        if not isinstance(
            generated,
            GeneratedContent,
        ):
            raise TypeError("generated must be GeneratedContent.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")

        filename = f"{generated.campaign_id}-" f"{timestamp}.txt"
        path = self.output_folder / filename

        provider = generated.provider or "Not recorded"
        input_tokens = (
            str(generated.input_tokens)
            if generated.input_tokens is not None
            else "Unknown"
        )
        output_tokens = (
            str(generated.output_tokens)
            if generated.output_tokens is not None
            else "Unknown"
        )
        finish_reason = generated.finish_reason or "Not recorded"

        output = (
            f"Campaign ID: {generated.campaign_id}\n"
            f"Platform: {generated.platform}\n"
            f"Content type: {generated.content_type}\n"
            f"Provider: {provider}\n"
            f"Model: {generated.model}\n"
            f"Input tokens: {input_tokens}\n"
            f"Output tokens: {output_tokens}\n"
            f"Finish reason: {finish_reason}\n"
            f"Generated: {timestamp} UTC\n"
            f"\n"
            f"{generated.content.strip()}\n"
        )

        path.write_text(
            output,
            encoding="utf-8",
        )

        metadata: dict[str, Any] = {
            "record_type": "generated_content",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "output_file": str(path),
            "data": generated.to_dict(),
        }

        self.storage.save(
            (f"{generated.campaign_id}-" f"{timestamp}"),
            metadata,
        )

        return path

    def save_compliance_report(
        self,
        report: ComplianceReport,
    ) -> Path:
        """Persist a completed campaign compliance report."""

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        filename = f"{report.subject_id}-" f"{timestamp}-compliance.json"
        path = self.compliance_output_folder / filename

        report_data = report.to_dict()

        path.write_text(
            json.dumps(
                report_data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        metadata: dict[str, Any] = {
            "record_type": "compliance_report",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "output_file": str(path),
            "data": report_data,
        }

        self.storage.save(
            (f"{report.subject_id}-" f"{timestamp}-compliance"),
            metadata,
        )

        return path

    def list_campaign_records(
        self,
    ) -> list[str]:
        """Return saved campaign record identifiers."""

        return self.storage.list_records()
