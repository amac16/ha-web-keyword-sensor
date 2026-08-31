# Changelog

## 1.6.9

- Increased OpenAI Responses output budget and set low reasoning effort for
  reasoning models, preventing short classification results from ending with
  `max_output_tokens` before JSON is returned.

## 1.6.8

- Added a `None` authentication mode, selected by default for new checks.
- Authentication-specific fields now appear only for the selected mode.

## 1.6.7

- Hid the AI profile form by default and added a compact **Add** button to
  reveal it. Editing an existing profile still opens the form automatically.

## 1.6.6

- Displayed each check's selected weekdays and daily start/end time in the
  saved-entry list.

## 1.6.5

- Increased OpenAI Responses output headroom to avoid empty results when
  reasoning consumes the smaller output budget.
- Reported safe provider response status/reason details when an AI check has no
  usable output.

## 1.6.4

- Added a **Test** button beside each saved check to run it immediately.
- Test results return the same entity state and safe attributes that MQTT
  discovery receives, while failures are reported without fabricating a state.

## 1.6.3

- Fixed editing existing checks by replacing fragile inline JSON click handlers
  with safe event listeners and an in-memory check cache.

## 1.6.2

- Updated OpenAI AI checks to use the current Responses API at
  `https://api.openai.com/v1/responses` with structured JSON output.
- Added provider error details so invalid model or request settings are easier
  to diagnose without exposing API keys.

## 1.6.1

- Added a **Test provider** button to verify an AI profile's provider, model,
  and API key without saving or exposing the key.

## 1.6.0

- Added AI context matching with OpenAI, Google Gemini, and Anthropic Claude
  profiles.
- Added protected multi-profile storage, model selection per check, bounded AI
  input/output, and unavailable-on-error behavior that preserves the last state.
- AI text sensors publish a short summary with structured findings as attributes.

## 1.5.0

- Bound concurrent checks with a small worker pool instead of creating an
  unbounded thread per check.
- Keep MQTT and the ingress UI available while the broker is unavailable.
- Bound HTTP response memory, close HTTP sessions, and harden invalid intervals.
- Add browser-operation timeouts, expired-session cleanup, and graceful browser
  shutdown so Chromium cannot accumulate across retries.

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
