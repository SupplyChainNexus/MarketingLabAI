"""Tests for tenant domain models."""

from __future__ import annotations

import unittest

from app.tenants.models import (
    ACTIVE_TENANT_STATUS,
    DEFAULT_TENANT_ID,
    INACTIVE_TENANT_STATUS,
    Tenant,
)


class TenantModelTests(unittest.TestCase):
    def test_tenant_cleans_values(self) -> None:
        tenant = Tenant(
            tenant_id=" tenant-one ",
            name=" Tenant One ",
            status=" ACTIVE ",
            created_at=" created ",
            updated_at=" updated ",
        )

        self.assertEqual(tenant.tenant_id, "tenant-one")
        self.assertEqual(tenant.name, "Tenant One")
        self.assertEqual(tenant.status, ACTIVE_TENANT_STATUS)
        self.assertEqual(tenant.created_at, "created")
        self.assertEqual(tenant.updated_at, "updated")

    def test_tenant_defaults_to_active(self) -> None:
        tenant = Tenant(
            tenant_id="tenant-one",
            name="Tenant One",
        )

        self.assertEqual(tenant.status, ACTIVE_TENANT_STATUS)
        self.assertTrue(tenant.is_active)

    def test_inactive_tenant_reports_not_active(self) -> None:
        tenant = Tenant(
            tenant_id="tenant-one",
            name="Tenant One",
            status=INACTIVE_TENANT_STATUS,
        )

        self.assertFalse(tenant.is_active)

    def test_tenant_requires_identifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "tenant_id"):
            Tenant(
                tenant_id=" ",
                name="Tenant One",
            )

    def test_tenant_requires_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "name"):
            Tenant(
                tenant_id="tenant-one",
                name=" ",
            )

    def test_tenant_rejects_invalid_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "status"):
            Tenant(
                tenant_id="tenant-one",
                name="Tenant One",
                status="suspended",
            )

    def test_tenant_round_trip_dictionary_conversion(self) -> None:
        tenant = Tenant(
            tenant_id="tenant-one",
            name="Tenant One",
            status=INACTIVE_TENANT_STATUS,
            created_at="2026-07-31T10:00:00+00:00",
            updated_at="2026-07-31T11:00:00+00:00",
        )

        restored = Tenant.from_dict(tenant.to_dict())

        self.assertEqual(restored, tenant)

    def test_from_dict_rejects_non_dictionary(self) -> None:
        with self.assertRaisesRegex(TypeError, "dictionary"):
            Tenant.from_dict([])  # type: ignore[arg-type]

    def test_default_tenant_identifier_is_stable(self) -> None:
        self.assertEqual(DEFAULT_TENANT_ID, "default")


if __name__ == "__main__":
    unittest.main()
