"""Tests for Marketing Brief and Prompt Pack integration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.marketing_brief import (
    MarketingBrief,
    MarketingBriefEvidence,
    MarketingBriefPromptPackService,
    MarketingBriefPromptValuesMapper,
    RenderedMarketingBriefPrompt,
)
from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector
from app.prompts.service import RenderedPrompt


class MarketingBriefPromptValuesMapperTests(unittest.TestCase):
    """Validate deterministic Marketing Brief variable mapping."""

    def setUp(self) -> None:
        self.mapper = MarketingBriefPromptValuesMapper()

    @staticmethod
    def make_brief(
        **overrides: object,
    ) -> MarketingBrief:
        values: dict[str, object] = {
            "brief_id": "brief-one",
            "tenant_id": "default",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": "Increase qualified enquiries",
            "audience": "Independent repair workshops",
            "offer": "Priority parts sourcing",
            "key_message": "Dependable access to parts",
            "call_to_action": "Request a quote",
            "channels": ["Facebook", "Email"],
            "deliverables": ["Lead advert"],
            "constraints": ["No unsupported guarantees"],
            "success_metrics": ["Qualified enquiries"],
            "customer_segment_ids": ["segment-one"],
            "product_ids": ["product-one"],
            "evidence": [
                MarketingBriefEvidence(
                    source_type="customer_intelligence",
                    source_id="segment-one",
                    summary="Verified workshop segment",
                    confidence=0.9,
                )
            ],
            "assumptions": ["Budget remains available"],
            "notes": "Use direct language.",
        }
        values.update(overrides)

        return MarketingBrief(**values)

    def test_mapper_rejects_invalid_brief(self) -> None:
        with self.assertRaises(TypeError):
            self.mapper.map(  # type: ignore[arg-type]
                object(),
                ["objective"],
            )

    def test_mapper_rejects_string_as_variable_sequence(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            self.mapper.map(
                self.make_brief(),
                "objective",  # type: ignore[arg-type]
            )

    def test_mapper_returns_only_declared_variables(self) -> None:
        values = self.mapper.map(
            self.make_brief(),
            ["objective", "audience"],
        )

        self.assertEqual(
            values,
            {
                "objective": "Increase qualified enquiries",
                "audience": "Independent repair workshops",
            },
        )

    def test_mapper_formats_collection_values(self) -> None:
        values = self.mapper.map(
            self.make_brief(),
            [
                "channels",
                "deliverables",
                "constraints",
            ],
        )

        self.assertEqual(
            values["channels"],
            "Facebook, Email",
        )
        self.assertEqual(
            values["deliverables"],
            "- Lead advert",
        )
        self.assertEqual(
            values["constraints"],
            "- No unsupported guarantees",
        )

    def test_mapper_formats_evidence_with_audit_reference(
        self,
    ) -> None:
        values = self.mapper.map(
            self.make_brief(),
            ["evidence"],
        )

        self.assertIn(
            "[customer_intelligence:segment-one]",
            values["evidence"],
        )
        self.assertIn(
            "confidence: 0.90",
            values["evidence"],
        )

    def test_mapper_rejects_unsupported_variable(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported_variable",
        ):
            self.mapper.map(
                self.make_brief(),
                ["unsupported_variable"],
            )

    def test_mapper_rejects_empty_declared_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "offer",
        ):
            self.mapper.map(
                self.make_brief(offer=""),
                ["offer"],
            )

    def test_supported_variables_are_stable(self) -> None:
        supported = self.mapper.supported_variables()

        self.assertIn("objective", supported)
        self.assertIn("evidence", supported)
        self.assertIn("brief_version", supported)


class MarketingBriefPromptPackServiceTests(unittest.TestCase):
    """Validate Prompt Pack selection and rendering from a brief."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "marketinglabai.db"
        self.database = SQLiteDatabase(database_path)
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.brands.save(
            {
                "brand_id": "brand-one",
                "tenant_id": "default",
                "name": "Brand One",
            }
        )

        self.repository = PromptPackRepository(self.database)
        self.selector = PromptPackSelector(self.repository)
        self.service = MarketingBriefPromptPackService(self.selector)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_brief(
        **overrides: object,
    ) -> MarketingBrief:
        values: dict[str, object] = {
            "brief_id": "brief-one",
            "tenant_id": "default",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": "Increase qualified enquiries",
            "audience": "Independent repair workshops",
            "key_message": "Dependable access to parts",
            "call_to_action": "Request a quote",
            "channels": ["Facebook"],
            "deliverables": ["Lead advert"],
        }
        values.update(overrides)

        return MarketingBrief(**values)

    @staticmethod
    def make_pack(
        *,
        prompt_pack_id: str = "brief-social",
        version: int = 1,
        channel: str = "facebook",
        brand_id: str | None = "brand-one",
        template: str = (
            "Objective: {objective}\n"
            "Audience: {audience}\n"
            "Message: {key_message}\n"
            "CTA: {call_to_action}"
        ),
        variables: list[str] | None = None,
    ) -> PromptPack:
        return PromptPack(
            prompt_pack_id=prompt_pack_id,
            tenant_id="default",
            brand_id=brand_id,
            name="Brief Social Prompt",
            task_type="campaign_content",
            channel=channel,
            template=template,
            variables=variables
            or [
                "objective",
                "audience",
                "key_message",
                "call_to_action",
            ],
            system_instruction="Use only supplied facts.",
            version=version,
        )

    def test_service_rejects_invalid_dependencies(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "PromptPackSelector",
        ):
            MarketingBriefPromptPackService(object())  # type: ignore[arg-type]

        with self.assertRaisesRegex(
            TypeError,
            "PromptPackRenderer",
        ):
            MarketingBriefPromptPackService(
                self.selector,
                renderer=object(),  # type: ignore[arg-type]
            )

        with self.assertRaisesRegex(
            TypeError,
            "MarketingBriefPromptValuesMapper",
        ):
            MarketingBriefPromptPackService(
                self.selector,
                mapper=object(),  # type: ignore[arg-type]
            )

    def test_service_selects_and_renders_matching_pack(
        self,
    ) -> None:
        self.repository.save(self.make_pack())

        result = self.service.render(
            self.make_brief(),
            task_type="campaign_content",
            channel="facebook",
        )

        self.assertIsInstance(
            result,
            RenderedMarketingBriefPrompt,
        )
        self.assertIsInstance(
            result.prompt,
            RenderedPrompt,
        )
        self.assertIn(
            "Objective: Increase qualified enquiries",
            result.prompt.content,
        )
        self.assertEqual(
            result.prompt.prompt_pack_id,
            "brief-social",
        )

    def test_service_uses_latest_enabled_version(self) -> None:
        self.repository.save(self.make_pack(version=1))
        self.repository.save(
            self.make_pack(
                version=2,
                template="Version 2: {objective}",
                variables=["objective"],
            )
        )

        result = self.service.render(
            self.make_brief(),
            task_type="campaign_content",
            channel="facebook",
        )

        self.assertEqual(result.prompt.version, 2)
        self.assertEqual(
            result.prompt.content,
            "Version 2: Increase qualified enquiries",
        )

    def test_service_supports_exact_pack_selection(self) -> None:
        self.repository.save(
            self.make_pack(
                prompt_pack_id="pack-one",
            )
        )
        self.repository.save(
            self.make_pack(
                prompt_pack_id="pack-two",
            )
        )

        result = self.service.render(
            self.make_brief(),
            task_type="campaign_content",
            channel="facebook",
            prompt_pack_id="pack-two",
        )

        self.assertEqual(
            result.prompt.prompt_pack_id,
            "pack-two",
        )

    def test_result_contains_brief_and_pack_audit_data(
        self,
    ) -> None:
        self.repository.save(self.make_pack(version=3))

        brief = self.make_brief(version=2)

        result = self.service.render(
            brief,
            task_type="campaign_content",
            channel="facebook",
        )

        self.assertEqual(result.brief_id, "brief-one")
        self.assertEqual(result.brief_version, 2)
        self.assertEqual(result.brief_status, "draft")
        self.assertEqual(result.prompt.version, 3)
        self.assertEqual(
            result.mapped_variables,
            (
                "objective",
                "audience",
                "key_message",
                "call_to_action",
            ),
        )

    def test_service_rejects_pack_variable_not_supported_by_brief(
        self,
    ) -> None:
        self.repository.save(
            self.make_pack(
                template="{unsupported_variable}",
                variables=["unsupported_variable"],
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "unsupported_variable",
        ):
            self.service.render(
                self.make_brief(),
                task_type="campaign_content",
                channel="facebook",
            )

    def test_service_rejects_required_empty_brief_value(
        self,
    ) -> None:
        self.repository.save(
            self.make_pack(
                template="{offer}",
                variables=["offer"],
            )
        )

        with self.assertRaisesRegex(ValueError, "offer"):
            self.service.render(
                self.make_brief(offer=""),
                task_type="campaign_content",
                channel="facebook",
            )

    def test_service_preserves_system_instruction(self) -> None:
        self.repository.save(self.make_pack())

        result = self.service.render(
            self.make_brief(),
            task_type="campaign_content",
            channel="facebook",
        )

        self.assertEqual(
            result.prompt.system_instruction,
            "Use only supplied facts.",
        )


class RenderedMarketingBriefPromptTests(unittest.TestCase):
    """Validate integrated render result boundaries."""

    def test_result_is_immutable(self) -> None:
        result = RenderedMarketingBriefPrompt(
            prompt=RenderedPrompt(
                content="Rendered content",
                system_instruction="Be accurate.",
                prompt_pack_id="pack-one",
                version=1,
                tenant_id="default",
                brand_id="brand-one",
                task_type="campaign_content",
                channel="facebook",
            ),
            brief_id="brief-one",
            brief_version=1,
            brief_status="approved",
            mapped_variables=("objective",),
        )

        with self.assertRaises(
            (
                AttributeError,
                TypeError,
            )
        ):
            result.brief_id = "changed"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
