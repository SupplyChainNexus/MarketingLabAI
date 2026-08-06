"""Authenticated Founder Design Partner signup and atomic tenant claiming."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Mapping

from app.database.connection import SQLiteDatabase
from app.design_partner.privacy import PilotPrivacyPolicy
from app.design_partner.registry import FounderDesignPartnerRegistry
from app.identity import AuthenticatedPrincipal, IdentityProviderAdapter


class SignupConflictError(RuntimeError):
    """Raised when an approved tenant was already claimed by another identity."""


@dataclass(frozen=True, slots=True)
class FounderSignupResult:
    partner_name: str
    tenant_id: str
    owner_subject_id: str
    owner_provider: str
    replayed: bool
    privacy_notice_version: str
    data_boundary_version: str

    def to_dict(self) -> dict:
        return {
            "partner_name": self.partner_name,
            "tenant_id": self.tenant_id,
            "owner_subject_id": self.owner_subject_id,
            "owner_provider": self.owner_provider,
            "role": "admin",
            "commercial_tier": "founder_design_partner_free",
            "full_feature_access": True,
            "billing_enabled": False,
            "pilot_status": "real_data_activation_frozen",
            "synthetic_only": True,
            "real_data_activation_authorized": False,
            "privacy_acceptance_recorded": True,
            "privacy_notice_version": self.privacy_notice_version,
            "data_boundary_version": self.data_boundary_version,
            "replayed": self.replayed,
        }


class FounderDesignPartnerSignupService:
    """Claim an approved invitation only after trusted authentication."""

    def __init__(
        self,
        database: SQLiteDatabase,
        identity_provider: IdentityProviderAdapter,
        invitation_hashes: Mapping[str, str],
    ) -> None:
        if not isinstance(database, SQLiteDatabase):
            raise TypeError("database must be a SQLiteDatabase.")
        if not isinstance(identity_provider, IdentityProviderAdapter):
            raise TypeError("identity_provider must be an IdentityProviderAdapter.")
        self.database = database
        self.identity_provider = identity_provider
        self.invitation_hashes = dict(invitation_hashes)

    def signup(
        self,
        *,
        credential: str,
        partner_name: str,
        invitation_code: str,
        privacy_notice_accepted: bool,
        synthetic_data_boundary_accepted: bool,
        privacy_notice_version: str = PilotPrivacyPolicy.NOTICE_VERSION,
        data_boundary_version: str = PilotPrivacyPolicy.BOUNDARY_VERSION,
    ) -> FounderSignupResult:
        if privacy_notice_accepted is not True:
            raise ValueError("The privacy notice must be accepted.")
        if synthetic_data_boundary_accepted is not True:
            raise ValueError("The synthetic-data boundary must be accepted.")
        if privacy_notice_version != PilotPrivacyPolicy.NOTICE_VERSION:
            raise ValueError("The current privacy notice version must be accepted.")
        if data_boundary_version != PilotPrivacyPolicy.BOUNDARY_VERSION:
            raise ValueError("The current synthetic-data boundary must be accepted.")
        partner = FounderDesignPartnerRegistry().get_by_name(partner_name)
        expected = self.invitation_hashes.get(partner.tenant_id, "")
        supplied = self.hash_invitation(invitation_code)
        if not expected or not hmac.compare_digest(expected, supplied):
            raise PermissionError("The Founder Design Partner invitation is invalid.")
        principal = self.identity_provider.authenticate(credential)
        return self._claim(
            partner.partner_name,
            partner.tenant_id,
            principal,
            privacy_notice_version,
            data_boundary_version,
        )

    def _claim(
        self,
        partner_name: str,
        tenant_id: str,
        principal: AuthenticatedPrincipal,
        privacy_notice_version: str,
        data_boundary_version: str,
    ) -> FounderSignupResult:
        with self.database.transaction() as connection:
            owner = connection.execute(
                """
                SELECT provider, subject_id FROM tenant_memberships
                WHERE tenant_id = ? AND role = 'admin' AND active = 1
                ORDER BY created_at LIMIT 1
                """,
                (tenant_id,),
            ).fetchone()
            if owner is not None:
                same_owner = (
                    str(owner["provider"]) == principal.provider
                    and str(owner["subject_id"]) == principal.subject_id
                )
                if not same_owner:
                    raise SignupConflictError(
                        "The Founder Design Partner invitation was already claimed."
                    )
                self._record_acceptance(
                    connection,
                    tenant_id,
                    principal,
                    privacy_notice_version,
                    data_boundary_version,
                )
                return self._result(
                    partner_name,
                    tenant_id,
                    principal,
                    privacy_notice_version,
                    data_boundary_version,
                    replayed=True,
                )
            connection.execute(
                """
                INSERT INTO tenants (tenant_id, name, status, created_at, updated_at)
                VALUES (?, ?, 'active',
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                """,
                (tenant_id, partner_name),
            )
            connection.execute(
                """
                INSERT INTO tenant_memberships
                    (provider, subject_id, tenant_id, role, active,
                     created_at, updated_at)
                VALUES (?, ?, ?, 'admin', 1,
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                """,
                (principal.provider, principal.subject_id, tenant_id),
            )
            self._record_acceptance(
                connection,
                tenant_id,
                principal,
                privacy_notice_version,
                data_boundary_version,
            )
        return self._result(
            partner_name,
            tenant_id,
            principal,
            privacy_notice_version,
            data_boundary_version,
            replayed=False,
        )

    @staticmethod
    def _record_acceptance(
        connection,
        tenant_id: str,
        principal: AuthenticatedPrincipal,
        privacy_notice_version: str,
        data_boundary_version: str,
    ) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO pilot_privacy_acceptances
                (tenant_id, provider, subject_id, notice_version,
                 boundary_version, accepted_at)
            VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (
                tenant_id,
                principal.provider,
                principal.subject_id,
                privacy_notice_version,
                data_boundary_version,
            ),
        )

    @staticmethod
    def hash_invitation(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            return ""
        return hashlib.sha256(value.strip().encode()).hexdigest()

    @staticmethod
    def _result(
        partner_name: str,
        tenant_id: str,
        principal: AuthenticatedPrincipal,
        privacy_notice_version: str,
        data_boundary_version: str,
        *,
        replayed: bool,
    ) -> FounderSignupResult:
        return FounderSignupResult(
            partner_name=partner_name,
            tenant_id=tenant_id,
            owner_subject_id=principal.subject_id,
            owner_provider=principal.provider,
            privacy_notice_version=privacy_notice_version,
            data_boundary_version=data_boundary_version,
            replayed=replayed,
        )
