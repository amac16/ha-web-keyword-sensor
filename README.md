# Web Keyword Sensor Home Assistant App

Web Keyword Sensor is a Home Assistant app that checks web pages on a schedule
and publishes the results as automatically discovered MQTT entities. It can
look for an exact phrase or use an AI model to interpret page content and find
relevant information.

## Features

- Multiple independent page checks.
- Exact, case-sensitive or case-insensitive phrase matching.
- AI context matching with OpenAI, Google Gemini, or Anthropic Claude.
- Binary sensors for yes/no results and text sensors for AI summaries.
- Weekday and daily time-window scheduling, including overnight windows.
- No-auth checks, username/password/TOTP login, and interactive Browser SSO.
- MQTT discovery, immediate per-check testing, and provider connection testing.
- Bounded concurrency, request sizes, browser sessions, and timeouts to protect
  Home Assistant from slow or unusually large pages.

## Add to Home Assistant

Publish this repository to GitHub, then in Home Assistant open:

**Settings → Apps → App Store → ⋮ → Repositories**

Add the GitHub repository URL. The app will then appear under **Local apps** or
as a custom repository app.

Install and configure **Web Keyword Sensor**, then open its Ingress panel to
create checks and AI provider profiles. The complete feature and configuration
guide is in [`web-keyword-sensor/README.md`](web-keyword-sensor/README.md).
