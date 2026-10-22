#!/usr/bin/env python3
"""CSV Cleaner: tidy a messy CSV file using only the Python standard library.

What it does:
  * cleans the header names (trim, lowercase, spaces -> underscores)
  * trims every cell and collapses repeated spaces
  * turns placeholders such as "N/A", "null" or "-" into empty cells
  * removes rows that are completely empty
  * removes duplicate rows (or duplicates of chosen key columns)
  * fixes short rows and skips rows that have too many cells

Usage:
  python csv_cleaner.py input.csv
  python csv_cleaner.py input.csv -o clean.csv --dedupe-by email
"""
import argparse
import csv
import re
import sys
from pathlib import Path

EMPTY_MARKERS = {"", "n/a", "na", "null", "none", "nan", "-", "--"}


def clean_header(name, position):
    """Lowercase, trim and replace runs of non-alphanumeric characters with '_'."""
    cleaned = re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_")
    return cleaned or f"column_{position}"


def unique_headers(names):
    """Make header names unique by adding _2, _3, ... to repeats."""
    seen = {}
    result = []
    for name in names:
        count = seen.get(name, 0) + 1
        seen[name] = count
        result.append(name if count == 1 else f"{name}_{count}")
    return result


def clean_cell(value):
    """Trim, collapse inner whitespace and turn placeholder values into ''."""
    value = re.sub(r"\s+", " ", value).strip()
    return "" if value.lower() in EMPTY_MARKERS else value


def clean_rows(rows, dedupe_by=None):
    """Clean a list of rows (first row is the header).

    Returns (header, cleaned_rows, stats). `dedupe_by` is an optional list of
    cleaned column names; rows with the same values in those columns count as
    duplicates (the first one is kept). Without it, whole rows are compared.
    """
    stats = {"read": 0, "empty": 0, "malformed": 0, "duplicates": 0, "written": 0}
    if not rows:
        return [], [], stats

    header = unique_headers([clean_header(h, i + 1) for i, h in enumerate(rows[0])])

    key_positions = None
    if dedupe_by:
        missing = [c for c in dedupe_by if c not in header]
        if missing:
            raise ValueError(
                "Unknown column(s): " + ", ".join(missing) + ". Available: " + ", ".join(header)
            )
        key_positions = [header.index(c) for c in dedupe_by]

    seen = set()
    cleaned_rows = []
    for row in rows[1:]:
        stats["read"] += 1
        if len(row) > len(header):
            stats["malformed"] += 1
            continue
        row = [clean_cell(c) for c in row] + [""] * (len(header) - len(row))
        if not any(row):
            stats["empty"] += 1
            continue
        key = tuple(row[i].lower() for i in key_positions) if key_positions else tuple(row)
        if key in seen:
            stats["duplicates"] += 1
            continue
        seen.add(key)
        cleaned_rows.append(row)

    stats["written"] = len(cleaned_rows)
    return header, cleaned_rows, stats


def clean_file(source, destination, dedupe_by=None):
    """Read `source`, write the cleaned CSV to `destination`, return the stats."""
    with open(source, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    header, cleaned_rows, stats = clean_rows(rows, dedupe_by)
    with open(destination, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
        writer.writerows(cleaned_rows)
    return stats


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clean a messy CSV file.")
    parser.add_argument("input", help="path to the CSV file to clean")
    parser.add_argument("-o", "--output", help="output path (default: <input>_clean.csv)")
    parser.add_argument(
        "--dedupe-by", nargs="+", metavar="COLUMN",
        help="treat rows with the same value in these (cleaned) columns as duplicates",
    )
    args = parser.parse_args(argv)

    source = Path(args.input)
    if not source.is_file():
        print(f"Error: file not found: {source}", file=sys.stderr)
        return 1
    destination = Path(args.output) if args.output else source.with_name(source.stem + "_clean.csv")

    try:
        stats = clean_file(source, destination, args.dedupe_by)
    except (ValueError, csv.Error, UnicodeDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Rows read:               {stats['read']}")
    print(f"Empty rows removed:      {stats['empty']}")
    print(f"Duplicates removed:      {stats['duplicates']}")
    print(f"Malformed rows skipped:  {stats['malformed']}")
    print(f"Rows written:            {stats['written']}")
    print(f"Saved to: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
