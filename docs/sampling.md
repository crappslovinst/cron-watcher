# Event Sampling

Under high-volume conditions cron-watcher may generate a large number of
alert events.  The **sampling** feature lets you keep only a statistical
fraction of non-critical events while ensuring that important jobs are
never silently dropped.

## Configuration

Add a `[sampling]` section to your `cron_watcher.toml`:

```toml
[sampling]
enabled        = true
rate           = 0.25          # keep 25 % of events at random
always_include = ["backup", "cron\.daily"]   # regex patterns — always kept
```

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Master switch |
| `rate` | float 0–1 | `1.0` | Fraction of events to retain |
| `always_include` | list[str] | `[]` | Regex patterns for jobs that bypass sampling |

## How it works

1. For every failure event the daemon checks whether the job name matches
   any pattern in `always_include`.  Matching events are **always** kept.
2. All other events are kept with probability `rate` using a uniform
   random draw.
3. When `enabled = false` or `rate = 1.0` the list is returned unchanged
   (zero overhead).

## Integration point

The daemon calls `sampled_failures(events)` from
`cron_watcher.sampling_integration` after deduplication and before
dispatching alerts.  The singleton config is loaded once from the global
`Config` object and cached for the lifetime of the process.

## Notes

- Sampling is **non-deterministic** by design; use `always_include` for
  jobs where you need guaranteed visibility.
- The `rate` is applied per-event, not per-job, so a bursty job will
  still have some events surface even at low rates.
