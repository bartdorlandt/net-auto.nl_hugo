#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pyyaml>=6.0.2",
# ]
# ///
"""List every event with its number, pretix slug and host.

A quick way to see the current numbering before adding an event, and to check
that a pretix slug matches what the ticket shop expects.
"""

import events as ev


def main() -> None:
    for event in ev.all_events():
        print(f"{event.date_compact}  #{event.event_number:<3} {event.slug:<32} {event.host}")


if __name__ == "__main__":
    main()
