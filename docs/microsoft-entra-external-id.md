# Microsoft Entra External ID — superseded deployment option

ADR-0021 selected Microsoft Entra External ID, but ADR-0022 superseded that
decision before any live external tenant or customer deployment. The adapter is
retained as a tested portability option. Google Cloud Identity Platform is the
current provider selection while retaining
MarketingLabAI-owned tenant authorization.

## Free-first boundary

- use the core free MAU allowance;
- use the default `ciamlogin.com` domain;
- avoid SMS, Front Door, WAF and premium governance;
- keep real customer data founder-frozen;
- never place secrets or invitation plaintext in source control.

## Signup timing

Create the Microsoft account and external tenant only after MLAI-030.2 installs
and validates. Record the tenant ID, tenant subdomain and application client ID
in the local `.env`; do not commit them. Configure a web application using the
authorization-code flow with PKCE and exact local callback/logout URLs. No client
secret is required in the browser.

Before invitations are sent, verify signup, login, logout, account recovery,
invalid-token rejection, tenant isolation and operational recovery with
synthetic data.
