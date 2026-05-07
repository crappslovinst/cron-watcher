"""Job label/tag support — attach metadata tags to cron events for richer filtering and reporting."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cron_watcher.log_parser import CronEvent


@dataclass
class LabelRule:
    """Maps a job-name pattern to a set of tags."""
    pattern: str
    tags: List[str]
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def matches(self, job: str) -> bool:
        return bool(self._compiled.search(job))


@dataclass
class LabelConfig:
    rules: List[LabelRule] = field(default_factory=list)


def label_config_from_dict(raw: dict) -> LabelConfig:
    """Build a LabelConfig from the parsed TOML/YAML config dict."""
    rules: List[LabelRule] = []
    for entry in raw.get("label_rules", []):
        pattern = entry.get("pattern", "")
        tags = entry.get("tags", [])
        if pattern and tags:
            rules.append(LabelRule(pattern=pattern, tags=tags))
    return LabelConfig(rules=rules)


def resolve_tags(event: CronEvent, config: LabelConfig) -> List[str]:
    """Return all tags that apply to *event* according to *config* rules."""
    job = event.job or ""
    seen: Dict[str, None] = {}  # preserve insertion order, deduplicate
    for rule in config.rules:
        if rule.matches(job):
            for tag in rule.tags:
                seen[tag] = None
    return list(seen)


def annotate_events(
    events: List[CronEvent],
    config: LabelConfig,
) -> List[Dict]:
    """Return a list of dicts, each being the event dict with a 'tags' key added."""
    from cron_watcher.log_parser import to_dict  # local import avoids circularity

    result = []
    for ev in events:
        d = to_dict(ev)
        d["tags"] = resolve_tags(ev, config)
        result.append(d)
    return result
