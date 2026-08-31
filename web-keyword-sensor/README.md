# Web Keyword Sensor

Release notes are maintained in [`CHANGELOG.md`](CHANGELOG.md) and should be
updated whenever the app version in `config.yaml` changes.

This Home Assistant app polls configured HTTP(S) pages and publishes MQTT
discovery entities. Each check has its own URL, matching mode, entity type,
interval, schedule, authentication, and TLS setting. Checks run independently,
so one unavailable page does not stop the others.

## How it works

1. Create one or more checks in the app's Ingress interface.
2. Choose **Exact phrase** or **AI context match**.
3. Choose the check's entity type, schedule, and authentication mode.
4. The app fetches the page, converts it to text, evaluates the match, and
   publishes the state and safe metadata over MQTT.
5. Home Assistant creates the entity automatically through MQTT discovery.

Use the **Test** button on any saved check to run it immediately and see the
same state and match result that would be published normally.

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

For exact matching, the phrase is required. HTML is reduced to plain text
before matching. The check is `ON`/`1` when the phrase is found and `OFF`/`0`
when it is not found.

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

The provider profile's model field is a provider-specific model ID, such as
`gpt-4.1-mini`, `gemini-2.5-flash`, or an available Claude model. The profile
dropdown on an AI check selects exactly one enabled profile. AI output is
required to contain a boolean match, a short summary, and optional findings.

Each saved check has a **Test** button. It runs the check immediately, publishes
the normal MQTT state, and displays the resulting state and match value in the
management page. A failed test reports an error instead of publishing a false
negative result.

AI binary sensors publish `ON`/`OFF`. AI text sensors publish the model's short
summary as their state and put bounded findings in MQTT attributes. Provider
errors mark the entity unavailable without replacing its last state. AI checks
are serialized and use the same request timeout and page-size limits as normal
checks, so model use should be scheduled at a reasonable interval. External
AI calls may incur provider charges and may disclose private page contents.

The app does not ask the AI provider to browse the web: it sends the text
retrieved from the configured page. JavaScript-rendered pages should use Browser
SSO when required.

## Authentication

Auth mode defaults to **None**, which hides all login controls. **Username/password/TOTP**
can define a login URL, username, password, TOTP secret, login form field names,
and login success text. Credentials are stored in
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

## MQTT entities and attributes

Each check receives a stable unique ID derived from its name and URL. The app
publishes the entity state, availability, and attributes including the URL,
match mode, match result, timestamp, and HTTP status. AI entities additionally
include the selected profile/model, summary, and bounded findings. API keys,
passwords, page contents, prompts, and model responses are never published.

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
