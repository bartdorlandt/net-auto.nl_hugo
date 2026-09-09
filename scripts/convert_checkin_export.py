#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.2.1",
# ]
# ///
"""Trim a pretix check-in export down to the columns the door needs.

The export carries thirty-odd columns, most of them empty. Printing it or
pulling it into a check-in list means scrolling past price, seat zone and
address to find a name. This keeps only the order code, the name (whole, given
and family) and the product, in the export's own semicolon-separated format.

Example:
  uv run scripts/convert_checkin_export.py checkin.csv
  uv run scripts/convert_checkin_export.py checkin.csv -o door_list.csv
"""

import csv
from pathlib import Path

import click

COLUMNS = [
    "Attendee name",
    "Company",
    # "Attendee name: Given name",
    # "Attendee name: Family name",
    "Product",
    "Order code",
]
DELIMITER = ";"


def convert(source: Path, target: Path) -> int:
    """Copy the wanted columns from source to target, returning the row count."""
    with source.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=DELIMITER)
        if missing := [c for c in COLUMNS if c not in (reader.fieldnames or [])]:
            raise click.ClickException(
                f"{source} is missing column(s): {', '.join(missing)}"
            )
        rows = [{c: row[c] for c in COLUMNS} for row in reader if any(row.values())]

    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=COLUMNS, delimiter=DELIMITER, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


@click.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Where to write the trimmed CSV. Defaults to <source>_trimmed.csv.",
)
def main(source: Path, output: Path | None) -> None:
    """Reduce a pretix check-in export to the check-in columns."""
    target = output or source.with_name(f"{source.stem}_trimmed{source.suffix}")
    if target == source:
        raise click.ClickException("Refusing to overwrite the input file.")

    count = convert(source, target)
    click.echo(f"Wrote {count} attendees to {target}")


if __name__ == "__main__":
    main()
