# Local setup

## Requirements

- macOS or Linux with Python 3.13
- A Photon 2.0 beta project and project API key
- A shared iMessage line with one consenting test sender
- An OpenAI API key with access to the configured Responses model

Create an isolated environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cp .env.example .env
```

Put real values only in the ignored `.env`. Set `PHOTON_PROJECT_ID`,
`PHOTON_API_KEY`, `PHOTON_AGENT_HANDLE`, `PHOTON_ALLOWED_SENDER`,
`OPENAI_API_KEY`, and `VISION_MODEL=gpt-4.1-mini`. Do not paste keys into
issues, logs, fixtures, or chat.

Check configuration without making a model call:

```sh
.venv/bin/python -m src doctor
```

`photon_configuration: ready` means required names are present, not that
credentials or phone delivery have been proven.

## Run

Poll once:

```sh
.venv/bin/python -m src live --once
```

Run until SIGINT or SIGTERM:

```sh
.venv/bin/python -m src live
```

The service authenticates project-scoped REST reads, discovers only the
configured sender's verified direct space, persists its cursor and receipts in
SQLite, and uses that same space for replies. The model cannot choose routing.
The first poll reads the current received history when `PHOTON_LOOKBACK_SECONDS`
is zero. Later polls continue from the saved cursor. A missing model key does
not stop history polling; a sticker is recorded as `api_key_not_configured`
and is not sent.

## Supported media

Photon 2.0 beta did not surface a native iMessage sticker in the verified shared
thread. Send a static PNG, JPEG, or WebP with the iMessage photo button. The
service enforces a 5 MB encoded-file limit, a 16,777,216-pixel decode limit,
rejects animation/malformed bytes, and gives OpenAI a decoded PNG.

Native sticker bubbles and group chats are not claimed. Shared iMessage is a
direct-space test path; a dedicated line is required for the documented group
path.
