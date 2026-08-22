#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.2.1",
#     "environs>=14.6.0",
#     "httpx>=0.28.1",
#     "pyyaml>=6.0.2",
# ]
# ///
"""Set up a new event on pretix by cloning an existing one.

Copies all settings from a source event and changes name, slug, dates and
location. Then creates vouchers for the internal and speaker tickets and makes
the event live.

Ported from the mkdocs repo's create_event.py. The one behavioral change: event
details come from the Hugo page front matter (content/events/<date>_<Sponsor>/
index.md) rather than events.yaml, so the website and the ticket shop cannot
disagree about the date, venue or name.

Required environment variable:
- PRETIX_API_TOKEN: a pretix API token allowed to create and edit events.

Example:
  uv run scripts/create_pretix_event.py --date 20270210
"""

import random
import string
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import click  # pyright: ignore[reportMissingImports]
import events as ev
import httpx  # pyright: ignore[reportMissingImports]
from environs import env  # pyright: ignore[reportMissingImports]

env.read_env()

ORGANIZER = ev.PRETIX_ORGANIZER
API_BASE_URL = f"{ev.PRETIX_BASE_URL}/api/v1/organizers/{ORGANIZER}/events"
CONTROL_URL = f"{ev.PRETIX_BASE_URL}/control/event/{ORGANIZER}"
DEFAULT_SOURCE_EVENT = "20260909-onezeroit"
SPEAKER_TICKET_AMOUNT = 3
INTERNAL_TICKET_AMOUNT = 10


class TicketType(StrEnum):
    INTERNAL = "Internal ticket"
    SPEAKER = "Speaker ticket"
    NLNAM = "NLNAM ticket"


def make_client() -> httpx.Client:
    return httpx.Client(
        headers=httpx.Headers(
            {
                "Content-Type": "application/json",
                "authorization": f"token {env('PRETIX_API_TOKEN')}",
            }
        )
    )


def event_payload(event: ev.Event, doors_open: str | None) -> dict[str, Any]:
    """Build the pretix clone payload from the Hugo page front matter."""
    hhmm = doors_open or event.doors_open
    date_admission = datetime.strptime(f"{event.date_compact}{hhmm}", "%Y%m%d%H%M")

    return {
        "name": {"en": f"NLNAM {event.event_number} @ {event.host}"},
        "slug": event.slug,
        "is_public": True,
        "testmode": False,
        # Doors open, then the programme starts 35 minutes later.
        "date_from": str(date_admission + timedelta(minutes=30)),
        "date_to": str(date_admission + timedelta(hours=4)),
        "date_admission": str(date_admission),
        "presale_start": str(
            datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            + timedelta(days=7)
        ),
        "presale_end": str(
            date_admission.replace(hour=10, minute=0, second=0, microsecond=0)
            - timedelta(days=1)
        ),
        "location": event.venue,
    }


def clone_event(client: httpx.Client, payload: dict, source_event: str) -> Any:
    response = client.post(f"{API_BASE_URL}/{source_event}/clone/", json=payload)
    if response.status_code >= 400:
        raise click.ClickException(
            f"Cloning {source_event} failed ({response.status_code}): {response.text}"
        )
    return response.json()


def make_live(client: httpx.Client, slug: str) -> Any:
    return client.patch(f"{API_BASE_URL}/{slug}/", json={"live": True}).json()


def get_items(client: httpx.Client, slug: str) -> dict[str, int]:
    response = client.get(f"{API_BASE_URL}/{slug}/items/")
    return {ticket["name"]["en"]: ticket["id"] for ticket in response.json()["results"]}


def create_voucher(
    client: httpx.Client, slug: str, ticket_id: int, max_usages: int
) -> Any:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    data = {"code": code, "max_usages": max_usages, "item": ticket_id}
    return client.post(f"{API_BASE_URL}/{slug}/vouchers/", json=data).json()


@click.command(context_settings={"max_content_width": 120})
@click.option(
    "-d",
    "--date",
    prompt="Date of the event (YYYYMMDD)",
    help="The date of the event in YYYYMMDD format.",
)
@click.option(
    "--doors-open",
    default=None,
    help="Override the doors-open time, HHMM. Defaults to the page's doorsOpen.",
)
@click.option(
    "--source-event",
    default=DEFAULT_SOURCE_EVENT,
    show_default=True,
    help="The slug of the event to clone.",
)
@click.option(
    "--dry-run", is_flag=True, help="Print the payload that would be sent and exit."
)
def main(date: str, doors_open: str | None, source_event: str, dry_run: bool) -> None:
    event = ev.by_date(date)
    payload = event_payload(event, doors_open)

    if dry_run:
        click.echo(f"Would clone {source_event} into:")
        for key, value in payload.items():
            click.echo(f"  {key}: {value}")
        return

    client = make_client()
    clone_event(client, payload, source_event)
    tickets = get_items(client, payload["slug"])

    code_internal = create_voucher(
        client, payload["slug"], tickets[TicketType.INTERNAL], INTERNAL_TICKET_AMOUNT
    )
    code_speaker = create_voucher(
        client, payload["slug"], tickets[TicketType.SPEAKER], SPEAKER_TICKET_AMOUNT
    )

    make_live(client, payload["slug"])

    shop = ev.shop_url(payload["slug"])

    click.echo(f"""
        Event created successfully:
        Admin page: {CONTROL_URL}/{payload["slug"]}/
        Ticket page: {shop}
        Start presale: {payload["presale_start"]}

        Page is live

        Vouchers created:
        - '{shop}redeem?voucher={code_internal["code"]}'
          - {INTERNAL_TICKET_AMOUNT} vouchers for internal use, send this to the sponsor for distribution
        - '{shop}redeem?voucher={code_speaker["code"]}'
          - {SPEAKER_TICKET_AMOUNT} vouchers for speakers
        """)


if __name__ == "__main__":
    main()
