"""Founder Design Partner registry tests."""

import unittest

from app.design_partner import (
    DesignPartnerReadinessEvaluator,
    FounderDesignPartnerRegistry,
)


class FounderDesignPartnerRegistryTests(unittest.TestCase):
    def test_registers_two_isolated_synthetic_tenants(self) -> None:
        partners = FounderDesignPartnerRegistry().list()
        self.assertEqual(len(partners), 2)
        self.assertEqual(len({item.tenant_id for item in partners}), 2)
        self.assertEqual(
            {item.tenant_id for item in partners},
            {"strand-auto-parts-pilot", "velani-wholesale-pilot"},
        )
        self.assertTrue(all(item.synthetic_only for item in partners))
        self.assertFalse(any(item.real_data_activation_authorized for item in partners))

    def test_both_partners_receive_free_full_access_without_activation(self) -> None:
        evaluator = DesignPartnerReadinessEvaluator()
        for name in ("Strand Auto Parts", "Velani Wholesale"):
            report = evaluator.evaluate(partner_name=name, evidence={})
            self.assertTrue(report["account_entitlement"]["full_feature_access"])
            self.assertFalse(report["account_entitlement"]["billing_enabled"])
            self.assertFalse(report["real_data_activation_authorized"])
            self.assertTrue(report["synthetic_rehearsal_authorized"])
            self.assertEqual(report["pilot_status"], "real_data_activation_frozen")

    def test_unapproved_partner_and_tenant_are_rejected(self) -> None:
        registry = FounderDesignPartnerRegistry()
        with self.assertRaisesRegex(ValueError, "candidate is not approved"):
            registry.get_by_name("Unapproved Business")
        with self.assertRaisesRegex(ValueError, "tenant is not approved"):
            registry.get_by_tenant("strand-auto-parts-pilot-copy")


if __name__ == "__main__":
    unittest.main()
