"""Google Cloud Identity Platform adapter security tests."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import jwt

from app.identity.google_cloud import (
    GoogleCloudAuthenticationError,
    GoogleCloudIdentityAdapter,
    GoogleCloudIdentitySettings,
)


class GoogleCloudIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GoogleCloudIdentitySettings("marketinglabai-dev")
        self.jwk = Mock()
        self.jwk.get_signing_key_from_jwt.return_value.key = "public-key"
        self.adapter = GoogleCloudIdentityAdapter(
            self.settings, jwk_client_factory=lambda _: self.jwk
        )

    def test_valid_token_maps_only_verified_claims(self) -> None:
        claims = {
            "sub": "google-subject",
            "email": "owner@example.test",
            "email_verified": True,
            "firebase": {"sign_in_provider": "google.com"},
        }
        with patch("app.identity.google_cloud.jwt.decode", return_value=claims) as call:
            principal = self.adapter.authenticate("signed-token")
        self.assertEqual(principal.subject_id, "google-subject")
        self.assertEqual(principal.provider, "google-cloud-identity-platform")
        call.assert_called_once_with(
            "signed-token",
            "public-key",
            algorithms=["RS256"],
            audience="marketinglabai-dev",
            issuer="https://securetoken.google.com/marketinglabai-dev",
            options={"require": ["exp", "iat", "iss", "aud", "sub", "auth_time"]},
        )

    def test_untrusted_token_conditions_are_denied(self) -> None:
        for error in (
            jwt.InvalidSignatureError(),
            jwt.ExpiredSignatureError(),
            jwt.InvalidIssuerError(),
            jwt.InvalidAudienceError(),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("app.identity.google_cloud.jwt.decode", side_effect=error):
                    with self.assertRaises(GoogleCloudAuthenticationError):
                        self.adapter.authenticate("untrusted-token")

    def test_empty_or_oversized_subject_is_denied(self) -> None:
        for subject in ("", "x" * 129):
            with patch(
                "app.identity.google_cloud.jwt.decode", return_value={"sub": subject}
            ):
                with self.assertRaises(GoogleCloudAuthenticationError):
                    self.adapter.authenticate("signed-token")

    def test_unverified_or_non_google_identity_is_denied(self) -> None:
        claims = {
            "sub": "subject",
            "email": "owner@example.test",
            "email_verified": True,
            "firebase": {"sign_in_provider": "google.com"},
        }
        invalid = (
            {**claims, "email_verified": False},
            {**claims, "email": ""},
            {**claims, "firebase": {"sign_in_provider": "password"}},
        )
        for selected in invalid:
            with self.subTest(claims=selected):
                with patch(
                    "app.identity.google_cloud.jwt.decode", return_value=selected
                ):
                    with self.assertRaises(GoogleCloudAuthenticationError):
                        self.adapter.authenticate("signed-token")

    def test_settings_pin_google_project_endpoints(self) -> None:
        self.assertEqual(
            self.settings.issuer,
            "https://securetoken.google.com/marketinglabai-dev",
        )
        self.assertIn("googleapis.com", self.settings.jwks_uri)


if __name__ == "__main__":
    unittest.main()
