# Minimal CMA Gateway Specification

## Goal

A minimal gateway that lets authorized users interact with the PI Coding Agent through:

* Telegram
* Email

No web UI.
No HTTP API.
Single daemon process.

## Core Session Model

Session identity mapping:

* Telegram chat/user ID -> active PI session
* notmuch thread ID -> PI session

This avoids weak subject-based threading and uses proper mail thread metadata.

## Stack

* Node.js
* PI SDK
* SQLite
* mbsync
* notmuch
* msmtp
* systemd

## Persistence

SQLite database.

### sessions

* local_id
* channel (`telegram`, `email`)
* channel_key
* pi_session_id
* updated_at

Rules:

* Telegram: `channel_key = telegram chat id`
* Email: `channel_key = notmuch thread id`

### seen_messages

* message_id
* processed_at

Used for deduplication.

## Email Flow

```bash
mbsync -a
notmuch new
```

For each unprocessed message:

1. Read message ID
2. Resolve notmuch thread ID
3. Validate sender authentication
4. Check whitelist
5. Load or create PI session bound to thread ID
6. Extract plain text body
7. Send prompt to PI
8. Send reply via msmtp
9. Mark processed

All replies in the same email thread resume the same PI session.

## Telegram Flow

Whitelist Telegram user IDs.

Commands:

* `/new` create fresh session
* `/list` list sessions
* `/switch <id>` switch active session

Plain text messages are sent to the active session.

## Authentication

### Telegram

* Bot token
* Allowed user ID whitelist

### Email

Accept only messages that were successfully delivered by the trusted mail provider, and whose sender address is whitelisted.

Do not trust visible `From:` header alone.
Use trusted provider authentication headers.

## PI Integration

Use PI SDK directly.

Docs: https://raw.githubusercontent.com/badlogic/pi-mono/refs/heads/main/packages/coding-agent/docs/sdk.md

## Service Model

Single systemd service.

Telegram should use polling mode for minimal setup.

Mail processing runs on interval loop, e.g. every 60 seconds.

## Filesystem Layout

```text
/opt/cma/
  dist/

/var/lib/cma/
  gateway.db
  sessions/

/etc/cma.env
```

## Configuration

```env
TELEGRAM_TOKEN=...
TELEGRAM_ALLOWED_IDS=12345,67890

EMAIL_ALLOWED=me@example.com,you@example.com
MAIL_FROM=bot@example.com

POLL_SECONDS=60
```

## systemd Unit

```ini
[Unit]
Description=CMA Gateway
After=network.target

[Service]
User=cma
WorkingDirectory=/opt/cma
EnvironmentFile=/etc/cma.env
ExecStart=/usr/bin/node /opt/cma/dist/index.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Design Principle

Keep the gateway focused on identity-aware multi-channel session orchestration while PI handles agent execution.
Implement only the most essential features to minimize complexity and maintenance overhead.
