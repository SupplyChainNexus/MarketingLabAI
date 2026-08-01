"""Tests for brand domain events."""

from __future__ import annotations

import unittest

from app.events.brand_events import BrandCreatedEvent


class BrandCreatedEventTests(unittest.TestCase):
    def test_event_contains_expected_data(self) -> None:
        event = BrandCreatedEvent(
            event_id="event-1",
            tenant_id="default",
            brand_id="brand-1",
            brand_name="Brand One",
        )

        self.assertEqual(event.event_type, "brand.created")
        self.assertEqual(event.source, "CreateBrandCommand")
        self.assertEqual(event.tenant_id, "default")
        self.assertEqual(event.brand_id, "brand-1")
        self.assertEqual(event.brand_name, "Brand One")
        self.assertEqual(
            event.summary,
            "Brand 'Brand One' was created.",
        )
        self.assertEqual(
            dict(event.payload),
            {
                "tenant_id": "default",
                "brand_name": "Brand One",
            },
        )

    def test_event_cleans_values(self) -> None:
        event = BrandCreatedEvent(
            tenant_id=" default ",
            brand_id=" brand-1 ",
            brand_name=" Brand One ",
        )

        self.assertEqual(event.tenant_id, "default")
        self.assertEqual(event.brand_id, "brand-1")
        self.assertEqual(event.brand_name, "Brand One")

    def test_event_rejects_blank_tenant(self) -> None:
        with self.assertRaisesRegex(ValueError, "tenant_id"):
            BrandCreatedEvent(
                tenant_id=" ",
                brand_id="brand-1",
                brand_name="Brand One",
            )

    def test_event_rejects_blank_brand_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "brand_name"):
            BrandCreatedEvent(
                tenant_id="default",
                brand_id="brand-1",
                brand_name=" ",
            )


if __name__ == "__main__":
    unittest.main()
