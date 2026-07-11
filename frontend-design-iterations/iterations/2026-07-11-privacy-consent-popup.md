# 2026-07-11 Privacy Consent Popup

## Direction

The privacy experience uses the existing warm ivory and orange product language,
with mint green and pale lilac accents to communicate trust without becoming
cold or legalistic.

The first screen answers three questions:

- What is protected.
- What is collected.
- What control the user keeps.

The primary login action stays disabled until the agreement control is selected.
The complete policy opens in a scrollable detail layer. Rejecting closes the
dialog and does not start login.

## Assets

- Design preview:
  `frontend-design-iterations/assets/privacy-consent/privacy-consent-popup-design.png`
- Generated source on magenta key:
  `frontend-design-iterations/assets/privacy-consent/privacy-shield-source-magenta.png`
- Transparent generated master:
  `frontend-design-iterations/assets/privacy-consent/privacy-shield-v2.png`
- Optimized mini program asset:
  `AImental_frontend/images/privacy/privacy-shield.png`

The final asset was generated through the project Images API using
`openai/gpt-image-2`, then locally keyed to alpha and resized to 512 x 512.

## Implementation

- Reusable component: `components/privacy-consent/`
- Shared policy and consent storage: `utils/privacy.js`
- Login payload integration: `utils/auth.js`
- First-login entry points: `components/login-prompt/` and `pages/profile/`
- Persistent privacy page and withdrawal flow: `pkgProfile/privacy.*`
