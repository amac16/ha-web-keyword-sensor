# Web Keyword Sensor

Release notes are maintained in [`CHANGELOG.md`](CHANGELOG.md) and should be
updated whenever the app version in `config.yaml` changes.

This Home Assistant app polls configured HTTP(S) pages and publishes MQTT
discovery entities when a phrase is found. Each check has its own URL, phrase,
entity type, interval, time unit, matching mode, and TLS setting.

## Setup

1. Add this directory as a local add-on repository (or copy it into the local
   add-ons directory).
2. Install and configure the app.
3. Ensure the Home Assistant MQTT integration is connected to the same broker.
4. Add checks in the app configuration as a JSON array, for example:

```json
[
  {
    "name": "Example phrase",
    "url": "https://www.example.com",
    "phrase": "this string",
    "entity_type": "binary_sensor",
    "interval": 15,
    "unit": "minutes",
    "case_sensitive": false,
    "verify_ssl": true,
    "enabled": true
  }
]
```

The `binary_sensor` is `on` when the phrase occurs and `off` otherwise. A
`sensor` reports `1` for a match and `0` otherwise. Multiple checks can be
listed and run independently.

The form also supports selecting individual weekdays and a daily `From`/`To`
window in one-hour increments. The existing interval remains the polling
frequency while the time window controls when polling is allowed. Overnight
windows such as 22:00 to 06:00 are supported. The app uses MQTT discovery, so
no Home Assistant API token is required. The default MQTT host is
`homeassistant.local`; set broker credentials if needed.

## AI context matching

Use the **AI model integrations** section to save one or more provider profiles
with a provider (`openai`, `google`, or `anthropic`), model ID, and API key. Keys
are stored in `/data/ai-profiles.json` with mode `0600` and are never returned
to the browser. Use **Test provider** before saving or while editing to verify
the credentials and model. Each check can select `AI context match` and one enabled
profile, then describe the information to find. The page text and request are
sent to that provider; webpage text is treated as untrusted data.

AI binary sensors publish `ON`/`OFF`. AI text sensors publish the model's short
summary as their state and put bounded findings in MQTT attributes. Provider
errors mark the entity unavailable without replacing its last state. AI checks
are serialized and use the same request timeout and page-size limits as normal
checks, so model use should be scheduled at a reasonable interval. External
AI calls may incur provider charges and may disclose private page contents.

## Authentication

Each check can optionally define a login URL, username, password, TOTP secret,
the login form field names, and login success text. Credentials are stored in
`/data/checks.json` with mode `0600` and are never returned by the management
API. Leave secret fields blank while editing to preserve existing values. The
app reports successful authentication in the form and sends a persistent Home
Assistant notification when authentication fails or a protected page returns
HTTP 401/403. JavaScript login flows, CAPTCHA, passkeys, SMS, and email codes
require site-specific automation and are not supported by the generic login.

For JavaScript-based SSO, set `Auth mode` to `Browser SSO`, save the check, edit
it again, and use `Start browser`. The Ingress UI displays a Chromium
screenshot; click the screenshot and type into it to complete redirects, MFA,
or consent screens, then select `Finish authentication`. The browser context
and cookies remain in memory only and must be reauthenticated after an app
restart. Playwright and Chromium are included in the image. Browser operations
have hard timeouts and expired sessions are closed automatically.

## Security and limitations

Only HTTP and HTTPS URLs are accepted. Requests have a configurable timeout.
Checks use a bounded worker pool (two concurrent checks by default), and page
responses are capped at 2 MiB by default. Keeping these limits small prevents a
slow or unusually large page from consuming the host's memory.
Custom headers are supported for pages requiring them; do not put secrets in
headers if app logs or backups are shared. The page is reduced to plain text
before matching. Browser SSO requires an interactive Ingress session and does
not support CAPTCHA solving or native browser popups. Browser credentials and
cookies are not written to disk.
