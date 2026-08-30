# Web Keyword Sensor

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

The app uses MQTT discovery, so no Home Assistant API token is required. The
default MQTT host is `homeassistant.local`; set broker credentials if needed.

## Security and limitations

Only HTTP and HTTPS URLs are accepted. Requests have a configurable timeout.
Custom headers are supported for pages requiring them; do not put secrets in
headers if app logs or backups are shared. The page is reduced to plain text
before matching, and JavaScript-rendered content is not available to this
lightweight scraper.
