"""Waitress application factory for the configured controlled pilot."""

from __future__ import annotations

from importlib import import_module

from app.application import CanonicalApplication
from app.database.factory import create_database
from app.design_partner import DesignPartnerAcceptanceEvaluator
from app.identity import IdentityProviderAdapter
from app.operations.configuration import PilotConfiguration
from app.operations.sessions import PilotSessionProvider
from app.operations.wsgi import OperationalPilotApplication
from app.pilot_api import PilotApiService
from app.pilot_workspace import PilotWorkspaceApplication


def _factory(reference: str):
    module_name, separator, attribute = reference.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("Factory references must use module:function syntax.")
    selected = getattr(import_module(module_name), attribute)
    if not callable(selected):
        raise TypeError(f"Configured factory is not callable: {reference}")
    return selected


def create_application() -> OperationalPilotApplication:
    """Compose the deployable WSGI application exclusively from environment."""

    config = PilotConfiguration.from_environment()
    canonical = CanonicalApplication.build(
        create_database(
            backend=config.persistence_backend,
            database_path=config.database_path,
            database_url=config.database_url,
        ),
        initialise_schema=False,
    )
    upstream = _factory(config.identity_adapter_factory)(config)
    if not isinstance(upstream, IdentityProviderAdapter):
        raise TypeError("Identity factory must return IdentityProviderAdapter.")
    registry = _factory(config.provider_registry_factory)(config)
    sessions = PilotSessionProvider(
        canonical,
        upstream,
        config.session_secret,
        idle_ttl_seconds=config.session_idle_ttl_seconds,
        absolute_ttl_seconds=config.session_absolute_ttl_seconds,
    )
    service = PilotApiService(
        canonical,
        sessions,
        registry,
        signup_identity_provider=upstream,
        founder_invitation_hashes=config.founder_invitation_hashes,
        acceptance_evaluator=DesignPartnerAcceptanceEvaluator(
            config, canonical.database
        ),
    )
    workspace = PilotWorkspaceApplication(service)
    return OperationalPilotApplication(workspace, sessions, config)
