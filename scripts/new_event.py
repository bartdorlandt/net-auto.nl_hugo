#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.2.1",
#     "pyyaml>=6.0.2",
# ]
# ///
"""Create a new NLNAM event page under content/events/.

Replaces the old `task event:yaml:create` + `task event:webpage` pair. There is
no events.yaml any more: this writes the Hugo page, and the page front matter is
what every later step (pretix, reminders) reads back.

Event numbering, slug, directory name and the registration URL are all derived
here so they cannot drift apart.

Example:
  uv run scripts/new_event.py -d 20270210 -s "Foo Bar" \
      -w https://foobar.nl/ -a "Street 1, 1234 AB, Amsterdam"
"""

from datetime import datetime
from pathlib import Path

import click

import events as ev

ARCHETYPE = Path("archetypes/event.md")


def load_template(root: Path) -> str:
    """The archetype is the one copy of the page template.

    `hugo new --kind event` cannot fill in the sponsor, the meetup number or the
    event date -- it only knows the path and today's date -- so the archetype is
    read and formatted here instead. Keeping it in the usual Hugo location means
    there is still exactly one file to edit when the page layout changes.
    """
    template = root / ARCHETYPE
    if not template.is_file():
        raise click.ClickException(f"Missing template: {ARCHETYPE}")
    return template.read_text()


def realign_tables(text: str) -> str:
    """Re-pad markdown table pipes after substitution.

    Placeholders like {sponsor} are rarely the width of the value replacing
    them, so a table that lined up in the archetype comes out ragged. Markdown
    does not care, but the author opening the file to fill in the talks does.
    """
    lines = text.split("\n")
    start = None

    def flush(end: int) -> None:
        rows = [
            [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
            for i in range(start, end)
        ]
        if len({len(r) for r in rows}) != 1:
            return
        widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]
        for offset, row in enumerate(rows):
            cells = [
                "-" * widths[c] if set(cell) == {"-"} else cell.ljust(widths[c])
                for c, cell in enumerate(row)
            ]
            lines[start + offset] = "| " + " | ".join(cells) + " |"

    for index, line in enumerate(lines + [""]):
        if line.strip().startswith("|"):
            start = index if start is None else start
        elif start is not None:
            flush(index)
            start = None
    return "\n".join(lines)


def city_from(address: str) -> str:
    """Best-effort city for the meta description; the author can fix it up."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    return parts[-1] if parts else "the Netherlands"


@click.command(context_settings={"max_content_width": 120})
@click.option("-d", "--date", prompt="Date of the event (YYYYMMDD)",
              help="Event date in YYYYMMDD format.")
@click.option("-s", "--sponsor", prompt="Sponsor (multiple separated by ' & ')",
              help="Host/sponsor name, in the casing you want displayed.")
@click.option("-w", "--website", prompt="Sponsor website (https://...)",
              help="Sponsor website URL.")
@click.option("-a", "--address", prompt="Full address (used for the map link)",
              help="Venue address.")
@click.option("--doors-open", default="18:00", show_default=True,
              help="Time the doors open, HH:MM.")
@click.option("--ends-at", default="22:00", show_default=True,
              help="Time the venue closes, HH:MM.")
@click.option("--force", is_flag=True, help="Overwrite an existing event page.")
def main(date: str, sponsor: str, website: str, address: str,
         doors_open: str, ends_at: str, force: bool) -> None:
    try:
        parsed = datetime.strptime(date, "%Y%m%d")
    except ValueError as exc:
        raise click.BadParameter(f"{date!r} is not a valid YYYYMMDD date") from exc

    root = ev.repo_root()
    dirname = ev.dirname_for(date, sponsor)
    target = root / ev.CONTENT_EVENTS / dirname / "index.md"

    if target.exists() and not force:
        raise click.ClickException(
            f"{target.relative_to(root)} already exists. Pass --force to overwrite."
        )

    number = ev.next_event_number(root)
    slug = ev.slug_for(date, sponsor)

    target.parent.mkdir(parents=True, exist_ok=True)
    page = load_template(root).format(
        number=number,
        sponsor=sponsor,
        website=website,
        address=address,
        city=city_from(address),
        slug=slug,
        date_iso=parsed.strftime("%Y-%m-%d"),
        date_long=parsed.strftime("%-d %B %Y"),
        today=datetime.now().strftime("%Y-%m-%d"),
        doors_open=doors_open,
        ends_at=ends_at,
    )
    target.write_text(realign_tables(page))

    click.echo(f"""
Created {target.relative_to(root)}

  Meetup number : {number}
  Pretix slug   : {slug}
  Page URL      : /events/{dirname.lower()}/

Next:
  1. Edit the page: fill in the agenda, parking details and description.
  2. task event:pretix DATE={date}     # clone the pretix event
  3. task reminders DATE={date}        # LinkedIn posts + schedule
""")


if __name__ == "__main__":
    main()
