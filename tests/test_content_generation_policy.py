"""Tests for immutable C5 policy-pack behavior."""

from __future__ import annotations

import unittest

from app.content_generation.policy import (
    ChannelRule,
    PolicyError,
    PolicyPack,
    PolicyPackRegistry,
    TransformationRule,
)


class PolicyPackTests(unittest.TestCase):
    def test_v1_is_deterministic_and_versioned(self) -> None:
        first = PolicyPack.v1(effective_date="2026-08-25")
        second = PolicyPack.v1(effective_date="2026-08-25")
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(
            (first.version, first.anchor_floor, first.category_floor), (1, 3, 2)
        )

    def test_channel_and_transformation_rules_are_canonical(self) -> None:
        pack = PolicyPack.v1(
            channel_rules=(
                ChannelRule(
                    channel="Email",
                    content_type="Campaign Email",
                    required_markers=("subject",),
                    required_anchor_categories=("product",),
                ),
            ),
            transformations=(
                TransformationRule(
                    transformation_id="approved_ratio",
                    input_units=("count", "count"),
                    output_unit="ratio",
                ),
            ),
        )
        self.assertIsNotNone(pack.channel_rule("email", "campaign email"))
        self.assertIsNotNone(pack.transformation("approved_ratio"))
        self.assertNotEqual(pack.digest, PolicyPack.v1().digest)

    def test_policy_versions_are_append_only_and_rollback_selects_old_pack(
        self,
    ) -> None:
        registry = PolicyPackRegistry()
        pack = PolicyPack.v1(effective_date="2026-08-25")
        registry.register(pack)
        self.assertIs(registry.rollback(pack.name, 1), pack)
        with self.assertRaises(PolicyError):
            registry.register(
                PolicyPack(
                    name=pack.name,
                    version=pack.version,
                    effective_date="different",
                )
            )
        with self.assertRaises(PolicyError):
            registry.get(pack.name, 2)

    def test_incompatible_grounding_contract_is_rejected(self) -> None:
        with self.assertRaises(PolicyError):
            PolicyPack(
                name="c5-content-validation",
                version=1,
                effective_date="2026-08-25",
                grounding_schema_version=2,
            )

    def test_anchor_floor_cannot_be_weakened(self) -> None:
        with self.assertRaises(PolicyError):
            PolicyPack(
                name="c5-content-validation",
                version=1,
                effective_date="2026-08-25",
                anchor_floor=2,
            )


if __name__ == "__main__":
    unittest.main()
