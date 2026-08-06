# Google Cloud Identity Platform deployment

Google Cloud Identity Platform is the selected customer authentication service.
It does not own MarketingLabAI tenants, memberships, invitations, entitlements,
billing state, or authorization.

## Existing Google Workspace

Supply Chain Nexus Enterprise's Workspace administration can own the Google
Cloud organization and controlled project. Workspace users are staff
administrators only. Strand Auto Parts and Velani Wholesale must sign up through
Identity Platform and must not be provisioned as Workspace users.

Google Workspace billing and Google Cloud billing are separate. No Workspace
upgrade is required for Identity Platform.

## Free-first boundary

- Use email/password or Google sign-in and TOTP where MFA is required.
- Keep SMS, SAML/OIDC enterprise federation, Cloud Functions, and paid add-ons
  disabled.
- Configure Cloud Billing budget alerts before browser rehearsal, even when
  expected usage remains inside the free allowance.
- Enable Identity Platform audit/activity logging before invitations.
- Use one external identity configuration; MarketingLabAI remains the authority
  for SME tenant separation.

## Activation order

1. Validate the local adapter and complete repository synchronization.
2. Create a dedicated Google Cloud project under the controlled organization.
3. Enable Identity Platform and approved sign-in methods only.
4. Configure authorized domains and local secrets outside version control.
5. Rehearse synthetic signup, invalid tokens, recovery, and account revocation.
6. Request founder approval before sending invitations or processing real data.
