#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.2.1",
#     "pyyaml>=6.0.2",
# ]
# ///
"""Generate the LinkedIn posts and the posting schedule for an event.

Replaces the old `reminders:create:*` Taskfile tasks. Same three files, same
cadence; the event details now come from the Hugo page front matter.

Example:
  uv run scripts/reminders.py --date 20270210
  uv run scripts/reminders.py            # the next upcoming event
"""

from datetime import timedelta

import click
import events as ev

REMINDERS_DIR = "reminders"

# Days before the event, and what to post on each. Mirrors the old schedule.
SCHEDULE: list[tuple[int, str]] = [
    (
        90,
        "Send out reminder about Event -- Schedule in LinkedIn\ncat {rfp_dir}/{date}_event_linkedin.txt",
    ),
    (
        70,
        "Send out reminder about RfP -- Schedule in LinkedIn\ncat {rfp_dir}/{date}_rfp_linkedin.txt",
    ),
    (
        56,
        "Send out reminder about RfP -- Schedule in LinkedIn\ncat {rfp_dir}/{date}_rfp_linkedin.txt",
    ),
    (
        49,
        "Send out reminder about RfP -- Schedule in LinkedIn\ncat {rfp_dir}/{date}_rfp_linkedin.txt",
    ),
    (
        42,
        "Send out reminder about Event -- Schedule in LinkedIn\ncat {rfp_dir}/{date}_event_linkedin.txt",
    ),
    (
        35,
        "Send out reminder about Event -- Schedule in LinkedIn\ncat {rfp_dir}/{date}_event_linkedin.txt",
    ),
    (30, "Send out reminder about First external speaker -- put in Reminders app"),
    (23, "Send out reminder about Second external speaker -- put in Reminders app"),
]


def hashtag(host: str) -> str:
    """LinkedIn hashtags break at the first space, so '#One Zero IT' would post
    as '#One' followed by loose text. Collapse the host name instead."""
    return "#" + "".join(c for c in host if c.isalnum())


def rfp_post(event: ev.Event, site: str, cfp: str) -> str:
    return f"""\
Hi #NLNAM community!

We have the next meetup scheduled on {event.date_formatted} with the help of {hashtag(event.host)}.
We are looking for speakers to present at the event.

If you have a nice topic you'd like to share with the community, please submit a presentation proposal using:
{cfp}

We especially welcome new speakers.

If you know someone that should give a talk, please share this message with them!

See you at the meetup!

More info at {site}{event.url_path}
"""


def event_post(event: ev.Event, site: str, cfp: str) -> str:
    return f"""\
Hi #NLNAM community!

We have the next meetup scheduled on {event.date_formatted} with the help of {hashtag(event.host)}.
If you haven't registered yet, you can at: {event.pretix_url}

At the same time we are always looking for speakers to present at the event.
If you have a nice topic you'd like to share with the community, please submit a presentation proposal using:

{cfp}

If you know someone that should give a talk, please share this message with them!

See you at the meetup!

More info at {site}{event.url_path}
"""


def schedule(event: ev.Event, site: str) -> str:
    date = event.date_compact
    lines = [
        f'Now: post on linkedIn about the new event. "cat {REMINDERS_DIR}/{date}_event_linkedin.txt"',
        "",
    ]

    for days, note in SCHEDULE:
        when = event.date - timedelta(days=days)
        lines.append(str(when))
        lines.append(f"{days}d - {note.format(rfp_dir=REMINDERS_DIR, date=date)}")
        lines.append("")

    lines += [
        str(event.date - timedelta(days=14)),
        "14d - Send out reminder about Event -- Schedule in LinkedIn",
        "Hi #NLNAM community!",
        "",
        f"We have the next meetup scheduled on {event.date_formatted} with the help of {hashtag(event.host)}.",
        f"If you haven't registered yet, you can at: {event.pretix_url}",
        "",
        "See you at the meetup!",
        "",
        f"More info at {site}{event.url_path}",
        "",
        str(event.date - timedelta(days=2)),
        "2d - Send out last reminder about Event -- Schedule in LinkedIn",
        "Hi #NLNAM community!",
        "",
        f"We have the next meetup scheduled on {event.date_formatted} with the help of {hashtag(event.host)}.",
        "That is only 2 days from now 😎",
        "",
        "See you at the meetup!",
        "",
        f"More info at {site}{event.url_path}",
        "",
    ]
    return "\n".join(lines)


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "-d",
    "--date",
    default=None,
    help="Event date in YYYYMMDD format. Defaults to the next upcoming event.",
)
def main(date: str | None) -> None:
    if date:
        event = ev.by_date(date)
    else:
        event = ev.upcoming()
        if event is None:
            raise click.ClickException("No upcoming events found.")
        click.echo(f"No date given, using the next upcoming event: {event.dirname}")

    root = ev.repo_root()
    site = ev.site_url(root)
    cfp = ev.cfp_url(root)
    out_dir = root / REMINDERS_DIR
    out_dir.mkdir(exist_ok=True)

    written = {
        f"{event.date_compact}_rfp_linkedin.txt": rfp_post(event, site, cfp),
        f"{event.date_compact}_event_linkedin.txt": event_post(event, site, cfp),
        f"{event.date_compact}_schedule.txt": schedule(event, site),
    }
    for name, content in written.items():
        (out_dir / name).write_text(content)
        click.echo(f"Wrote {REMINDERS_DIR}/{name}")


if __name__ == "__main__":
    main()
