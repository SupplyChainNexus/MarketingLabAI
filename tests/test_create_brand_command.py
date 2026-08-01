"""Tests for CreateBrandCommand."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.commands.brands import CreateBrandCommand
from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.events.brand_events import BrandCreatedEvent
from app.events.bus import EventBus
from app.events.publisher import EventPublisher
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class CreateBrandCommandTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()

        self.database = SQLiteDatabase(Path(self.temp.name) / "marketinglabai.db")

        self.database.initialise()

        self.tenants = TenantRepository(self.database)
        self.brands = BrandRepository(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_brand(self):

        command = CreateBrandCommand(
            payload={
                "brand_id": "brand-one",
                "name": "Brand One",
            },
            tenant_repository=self.tenants,
            brand_repository=self.brands,
        )

        brand = command.execute()

        self.assertEqual(
            brand["brand_id"],
            "brand-one",
        )

        self.assertEqual(
            brand["tenant_id"],
            "default",
        )

    def test_create_brand_for_explicit_tenant(self):

        self.tenants.save(
            Tenant(
                tenant_id="tenant-two",
                name="Tenant Two",
            )
        )

        command = CreateBrandCommand(
            payload={
                "brand_id": "brand-two",
                "name": "Brand Two",
                "tenant_id": "tenant-two",
            },
            tenant_repository=self.tenants,
            brand_repository=self.brands,
        )

        brand = command.execute()

        self.assertEqual(
            brand["tenant_id"],
            "tenant-two",
        )

    def test_unknown_tenant_is_rejected(self):

        with self.assertRaisesRegex(
            ValueError,
            "does not exist",
        ):

            CreateBrandCommand(
                payload={
                    "brand_id": "brand",
                    "name": "Brand",
                    "tenant_id": "missing",
                },
                tenant_repository=self.tenants,
                brand_repository=self.brands,
            ).execute()

    def test_command_publishes_brand_created_event(self) -> None:
        received: list[BrandCreatedEvent] = []
        event_bus = EventBus()

        event_bus.subscribe(
            "brand.created",
            received.append,
        )

        command = CreateBrandCommand(
            payload={
                "brand_id": "brand-one",
                "name": "Brand One",
            },
            tenant_repository=self.tenants,
            brand_repository=self.brands,
            event_publisher=EventPublisher(event_bus),
        )

        command.execute()

        self.assertEqual(len(received), 1)
        self.assertEqual(
            received[0].event_type,
            "brand.created",
        )
        self.assertEqual(
            received[0].tenant_id,
            "default",
        )
        self.assertEqual(
            received[0].brand_id,
            "brand-one",
        )
        self.assertEqual(
            received[0].brand_name,
            "Brand One",
        )


if __name__ == "__main__":
    unittest.main()
