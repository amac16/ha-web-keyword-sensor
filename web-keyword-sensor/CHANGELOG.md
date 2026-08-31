# Changelog

## 1.4.2

- Use Playwright's Async API on a dedicated event loop for browser SSO.

## 1.3.3

- Updated Playwright for the Python 3.14 runtime.
- Retained Chromium-based browser SSO support.

## 1.3.2

- Added browser-based SSO authentication through the app ingress UI.
- Added persistent browser sessions for authenticated checks.

## 1.3.1

- Added Playwright and Chromium support for browser-authenticated pages.
- Added authentication status and persistent Home Assistant notifications.

## 1.3.0

- Added the interactive web form for managing checks.
- Added browser SSO controls and basic login fields.

## 1.2.0

- Added optional username/password/TOTP authentication.
- Added authentication failure notifications.

## 1.1.0

- Added weekday and daily time-window scheduling.
- Added persistent check storage.

## 1.0.0

- Initial release.
- Added MQTT discovery sensors for webpage phrase matching.
## 1.5.0

- Bound concurrent checks with a small worker pool instead of creating an
  unbounded thread per check.
- Keep MQTT and the ingress UI available while the broker is unavailable.
- Bound HTTP response memory, close HTTP sessions, and harden invalid intervals.
- Add browser-operation timeouts, expired-session cleanup, and graceful browser
  shutdown so Chromium cannot accumulate across retries.
