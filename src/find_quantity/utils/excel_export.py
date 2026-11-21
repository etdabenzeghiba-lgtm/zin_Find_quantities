"""Big daily sales files: continue on another sheet when a sheet is full.

Excel cannot show more than 1,048,576 rows per sheet. When a daily sales file
has more data rows than ``max_rows``, it is written as an Excel file (.xlsx)
with several sheets (Feuil1, Feuil2, ...), each one with the header line.
The .csv file is then removed, because it would be cut when opened in Excel.
Files with fewer rows are left as they are (.csv).
"""

import csv
import logging
import re
from pathlib import Path

logger = logging.getLogger("find_quantity.cli")

# Numbers like 12, -3, 1250.50 ; not "007" (a code with leading zeros stays text)
_NUMBER = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?$")


def count_data_rows(source: Path, separator: str = ";") -> int:
    with open(source, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=separator)
        next(reader, None)  # header
        return sum(1 for _ in reader)


def csv_to_excel_sheets(
    source: Path,
    destination: Path,
    max_rows: int,
    separator: str = ";",
) -> int:
    """Write `source` in `destination` (.xlsx), `max_rows` data rows per sheet.
    Returns the number of sheets."""
    import xlsxwriter  # imported here: only needed for big files

    workbook = xlsxwriter.Workbook(str(destination), {"constant_memory": True})
    sheets = 0
    try:
        with open(source, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=separator)
            header = next(reader)
            sheet = None
            row_in_sheet = 0
            for row in reader:
                if sheet is None or row_in_sheet >= max_rows:
                    sheets += 1
                    sheet = workbook.add_worksheet(f"Feuil{sheets}")
                    for col, name in enumerate(header):
                        sheet.write_string(0, col, name)
                    sheet.freeze_panes(1, 0)
                    row_in_sheet = 0
                row_in_sheet += 1
                for col, value in enumerate(row):
                    if _NUMBER.match(value):
                        sheet.write_number(row_in_sheet, col, float(value))
                    else:
                        sheet.write_string(row_in_sheet, col, value)
    finally:
        workbook.close()
    return sheets


def convert_big_csv_files(folder: Path, max_rows: int, separator: str = ";") -> list[Path]:
    """Convert the daily_sales*.csv files that have more than `max_rows` data rows."""
    created = []
    for source in sorted(Path(folder).glob("daily_sales*.csv")):
        total = count_data_rows(source, separator)
        if total <= max_rows:
            continue
        try:
            import xlsxwriter  # noqa: F401
        except ImportError:
            logger.warning(
                f"{source.name} has {total:,} rows (more than one Excel sheet) but the "
                "package xlsxwriter is missing. Run: pip install xlsxwriter. CSV kept."
            )
            continue
        destination = source.with_suffix(".xlsx")
        sheets = csv_to_excel_sheets(source, destination, max_rows, separator)
        source.unlink()
        logger.info(f"{source.name}: {total:,} rows -> {destination.name} ({sheets} sheets)")
        created.append(destination)
    return created
