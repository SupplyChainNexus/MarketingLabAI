"""Microsoft Entra External ID adapter security tests."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import jwt

from app.identity.entra import (
    EntraAuthenticationError,
    EntraExternalIdAdapter,
    EntraExternalIdSettings,
)


class EntraExternalIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = EntraExternalIdSettings(
            tenant_id="11111111-2222-3333-4444-555555555555",
            tenant_subdomain="marketinglabai-test",
            client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        )
        self.jwk = Mock()
        self.jwk.get_signing_key_from_jwt.return_value.key = "public-key"
        self.adapter = EntraExternalIdAdapter(
            self.settings, jwk_client_factory=lambda _: self.jwk
        )

    def test_valid_token_maps_only_verified_identity_claims(self) -> None:
        claims = {"sub": "entra-subject", "name": "Founder Owner"}
        with patch("app.identity.entra.jwt.decode", return_value=claims) as decode:
            principal = self.adapter.authenticate("signed-token")
        self.assertEqual(principal.subject_id, "entra-subject")
        self.assertEqual(principal.provider, "microsoft-entra-external-id")
        self.assertEqual(principal.display_name, "Founder Owner")
        decode.assert_called_once_with(
            "signed-token",
            "public-key",
            algorithms=["RS256"],
            audience=self.settings.client_id,
            issuer=self.settings.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )

    def test_invalid_signature_expiry_issuer_and_audience_are_denied(self) -> None:
        for error in (
            jwt.InvalidSignatureError(),
            jwt.ExpiredSignatureError(),
            jwt.InvalidIssuerError(),
            jwt.InvalidAudienceError(),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("app.identity.entra.jwt.decode", side_effect=error):
                    with self.assertRaises(EntraAuthenticationError):
                        self.adapter.authenticate("untrusted-token")

    def test_missing_subject_and_empty_credential_are_denied(self) -> None:
        with patch("app.identity.entra.jwt.decode", return_value={"sub": ""}):
            with self.assertRaises(EntraAuthenticationError):
                self.adapter.authenticate("signed-token")
        with self.assertRaises(EntraAuthenticationError):
            self.adapter.authenticate(" ")

    def test_settings_pin_external_tenant_endpoints(self) -> None:
        self.assertEqual(
            self.settings.issuer,
            "https://marketinglabai-test.ciamlogin.com/"
            "11111111-2222-3333-4444-555555555555/v2.0",
        )
        self.assertTrue(self.settings.jwks_uri.endswith("/discovery/v2.0/keys"))


if __name__ == "__main__":
    unittest.main()
