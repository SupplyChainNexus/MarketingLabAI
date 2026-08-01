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
from app.events.models import DomainEvent
from app.events.publisher import EventPublisher
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class CreateBrandCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.tenants = TenantRepository(self.database)
        self.brands = BrandRepository(self.database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_create_brand(self) -> None:
        command = CreateBrandCommand(
            payload={
                "brand_id": "brand-one",
                "name": "Brand One",
            },
            tenant_repository=self.tenants,
            brand_repository=self.brands,
        )

        brand = command.execute()

        self.assertEqual(brand["brand_id"], "brand-one")
        self.assertEqual(brand["tenant_id"], "default")

    def test_create_brand_for_explicit_tenant(self) -> None:
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

        self.assertEqual(brand["tenant_id"], "tenant-two")

    def test_unknown_tenant_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not exist"):
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
        received: list[DomainEvent] = []
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

        event = received[0]
        self.assertIsInstance(event, BrandCreatedEvent)
        assert isinstance(event, BrandCreatedEvent)

        self.assertEqual(event.event_type, "brand.created")
        self.assertEqual(event.tenant_id, "default")
        self.assertEqual(event.brand_id, "brand-one")
        self.assertEqual(event.brand_name, "Brand One")


if __name__ == "__main__":
    unittest.main()
