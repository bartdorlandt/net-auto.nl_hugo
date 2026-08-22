"""Read NLNAM events straight out of the Hugo content tree.

Imported by the scripts next to it rather than run on its own, so it carries no
PEP 723 metadata block; its one third-party dependency (pyyaml) is declared by
each entry point. uv puts a script's own directory on sys.path, which is what
makes `import events` resolve from those scripts.

The old mkdocs site kept an events.yaml alongside the pages, which meant every
event existed twice: once as data and once as the page rendered from it. Here
the page front matter *is* the data. Everything the Taskfile and the pretix
script need is derived from content/events/<YYYYMMDD>_<Sponsor>/index.md.
"""

import re
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

CONTENT_EVENTS = Path("content/events")
HUGO_CONFIG = Path("config/_default/hugo.toml")
DIRNAME_RE = re.compile(r"^(\d{8})_(.+)$")

# Pretix lives under one organizer; every pretix URL is built from these.
PRETIX_ORGANIZER = "nlnam"
PRETIX_BASE_URL = "https://pretix.eu"

FALLBACK_SITE_URL = "https://net-auto.nl"
FALLBACK_CFP_URL = "https://forms.gle/qmjaMqcHLuJV3rTy8"


def repo_root() -> Path:
    """Walk up from this file until we find the Hugo content directory."""
    for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (candidate / CONTENT_EVENTS).is_dir():
            return candidate
    raise FileNotFoundError(
        f"Could not locate {CONTENT_EVENTS}/ - run this from the repo root."
    )


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Hugo page into its YAML front matter and its body."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}, text
    return yaml.safe_load(parts[1]) or {}, parts[2]


def slugify(sponsor: str) -> str:
    """'One Zero IT' -> 'onezeroit'; 'Adyen & Netpicker' -> 'adyen-netpicker'."""
    return re.sub(r"\s+", "", sponsor.lower().replace(" & ", "-"))


def slug_for(date: str, sponsor: str) -> str:
    """'20270210', 'Adyen & Netpicker' -> '20270210-adyen-netpicker'."""
    return f"{date}-{slugify(sponsor)}"


def shop_url(slug: str) -> str:
    """Public ticket-shop URL for a pretix slug."""
    return f"{PRETIX_BASE_URL}/{PRETIX_ORGANIZER}/{slug}/"


def site_url(root: Path | None = None) -> str:
    """The site's baseURL, read from the Hugo config.

    Hard-coding it here once meant the reminder posts pointed at
    https://net-auto.nl while the site was actually building for
    https://new.net-auto.nl/ -- links in a LinkedIn post nobody would notice
    were wrong until someone clicked one.
    """
    config = (root or repo_root()) / HUGO_CONFIG
    if config.is_file():
        for line in config.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "baseURL":
                return value.strip().strip("\"'").rstrip("/")
    return FALLBACK_SITE_URL


def cfp_url(root: Path | None = None) -> str:
    """The call-for-papers form, read from the events section front matter.

    content/events/_index.md cascades cfpURL onto every event page, so the site
    already has the value; reading it here keeps the LinkedIn posts pointing at
    the same form the "Propose a talk" button does.
    """
    index = (root or repo_root()) / CONTENT_EVENTS / "_index.md"
    if index.is_file():
        front_matter, _ = split_front_matter(index.read_text())
        cascade = front_matter.get("cascade") or {}
        found = cascade.get("cfpURL") or front_matter.get("cfpURL")
        if found:
            return str(found)
    return FALLBACK_CFP_URL


def dirname_for(date: str, sponsor: str) -> str:
    """'20270210', 'Adyen & Netpicker' -> '20270210_Adyen__Netpicker'."""
    return f"{date}_{sponsor.replace(' & ', '__').replace(' ', '_')}"


@dataclass(frozen=True)
class Event:
    path: Path
    front_matter: dict[str, Any]
    body: str

    @property
    def dirname(self) -> str:
        return self.path.parent.name

    @property
    def date_compact(self) -> str:
        """YYYYMMDD, taken from the directory name."""
        match = DIRNAME_RE.match(self.dirname)
        if not match:
            raise ValueError(f"Event directory is not YYYYMMDD_Sponsor: {self.dirname}")
        return match.group(1)

    @property
    def date(self) -> Date:
        value = self.front_matter.get("date")
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, Date):
            return value
        return datetime.strptime(self.date_compact, "%Y%m%d").date()

    @property
    def date_formatted(self) -> str:
        return self.date.isoformat()

    @property
    def host(self) -> str:
        return self.front_matter.get("host", "")

    @property
    def venue(self) -> str:
        return self.front_matter.get("venue", "")

    @property
    def event_number(self) -> int:
        return int(self.front_matter["eventNumber"])

    @property
    def slug(self) -> str:
        """The pretix ticket-shop slug.

        Deliberately *not* called `slug` in front matter: Hugo treats that key
        as the page's own URL, and setting it would silently move every event
        page off the /events/YYYYMMDD_Sponsor/ path the site already publishes.
        """
        return (
            self.front_matter.get("pretixSlug")
            or slug_for(self.date_compact, self.host)
        )

    @property
    def doors_open(self) -> str:
        """'18:00' -> '1800', the format the pretix script wants."""
        return str(self.front_matter.get("doorsOpen", "18:00")).replace(":", "")

    @property
    def url_path(self) -> str:
        return f"/events/{self.dirname.lower()}/"

    @property
    def pretix_url(self) -> str:
        return shop_url(self.slug)


def load(path: Path) -> Event:
    front_matter, body = split_front_matter(path.read_text())
    return Event(path=path, front_matter=front_matter, body=body)


def all_events(root: Path | None = None) -> list[Event]:
    """Every event page, oldest first."""
    root = root or repo_root()
    events = [
        load(index)
        for index in sorted((root / CONTENT_EVENTS).glob("*/index.md"))
        if DIRNAME_RE.match(index.parent.name)
    ]
    return sorted(events, key=lambda e: e.date_compact)


def by_date(date: str, root: Path | None = None) -> Event:
    """Look up a single event by its YYYYMMDD date."""
    for event in all_events(root):
        if event.date_compact == date:
            return event
    known = ", ".join(e.date_compact for e in all_events(root)) or "none"
    raise KeyError(f"No event for {date}. Known events: {known}")


def next_event_number(root: Path | None = None) -> int:
    """One past the highest number in use, so numbering survives out-of-order adds."""
    numbers = [
        int(e.front_matter["eventNumber"])
        for e in all_events(root)
        if e.front_matter.get("eventNumber") is not None
    ]
    return max(numbers, default=0) + 1


def upcoming(root: Path | None = None) -> Event | None:
    """The closest event still in the future."""
    today = Date.today()
    future = [e for e in all_events(root) if e.date >= today]
    return future[0] if future else None
