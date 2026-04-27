# cron-watcher

> Lightweight daemon that monitors cron job execution, logs failures, and sends configurable alerts via webhook or email.

---

## Installation

```bash
pip install cron-watcher
```

Or install from source:

```bash
git clone https://github.com/yourname/cron-watcher.git && cd cron-watcher && pip install .
```

---

## Usage

Define your monitored jobs in `config.yaml`:

```yaml
jobs:
  - name: daily-backup
    schedule: "0 2 * * *"
    command: /usr/local/bin/backup.sh
    timeout: 300
    alerts:
      webhook: https://hooks.slack.com/services/your/webhook/url
      email: ops@example.com

settings:
  log_file: /var/log/cron-watcher.log
  retry_attempts: 3
```

Start the daemon:

```bash
cron-watcher start --config config.yaml
```

Check status or view recent failures:

```bash
cron-watcher status
cron-watcher logs --failed --last 10
```

Stop the daemon:

```bash
cron-watcher stop
```

---

## Features

- Monitors cron job exit codes and execution duration
- Logs failures with timestamps and captured output
- Sends alerts via **webhook** (Slack, Discord, custom) or **SMTP email**
- Configurable retry attempts before alerting
- Zero external dependencies beyond the standard library

---

## License

MIT © 2024 [yourname](https://github.com/yourname)