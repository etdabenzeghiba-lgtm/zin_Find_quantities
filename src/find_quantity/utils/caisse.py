"""Cash rules read from ``caisse.csv``.

Each showroom, for a given month, is either:

* ``CCP``    : all the tickets de caisse must be dated BEFORE the date of the
               encaissement (strictly before).
* ``ESPECE`` : the cash expenses (depenses journalieres de la caisse) must always
               be covered by the cash already sold. On the date of an expense,
               the sales up to and including that day must cover all the
               expenses up to and including that day.

The mode is set once per showroom and per month. Mixing CCP and ESPECE for the
same showroom in the same month is refused.
"""

import csv
import logging
import random
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from find_quantity.models import Sale

logger = logging.getLogger("find_quantity.cli")

CCP = "CCP"
ESPECE = "ESPECE"

CAISSE_HEADER = ["mois", "showroom", "Code-Showroom", "mode", "date", "montant"]

# How many random orders we try before using the "biggest days first" order
MAX_SHUFFLE_ATTEMPTS = 300


class CaisseError(ValueError):
    """Problem in the caisse.csv file."""


@dataclass(frozen=True)
class CaisseEntry:
    month: int
    code_showroom: str
    mode: str
    date: date
    amount: float


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def normalize_mode(value: str) -> str:
    """'ccp', 'CCP', 'espece', 'Espèce', 'especes' ... -> 'CCP' or 'ESPECE'."""
    clean = _strip_accents(str(value or "")).strip().upper()
    if clean == "CCP":
        return CCP
    if clean in ("ESPECE", "ESPECES"):
        return ESPECE
    raise CaisseError(f'Mode "{value}" is not valid. Write CCP or espece.')


def parse_amount(value: str) -> float:
    text = str(value or "").strip().replace(" ", "").replace("\u00a0", "")
    if text == "":
        return 0.0
    # "1.234,50" (French) or "1234,50" or "1234.50"
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    return float(text)


def parse_date(value: str) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    try:  # also accept DD/MM/YYYY
        d, m, y = text.split("/")
        return date(int(y), int(m), int(d))
    except ValueError:
        raise CaisseError(f'Date "{value}" is not valid. Use YYYY-MM-DD.')


def parse_entries(rows: list[dict]) -> list[CaisseEntry]:
    entries = []
    for line_no, row in enumerate(rows, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue  # empty line
        try:
            entries.append(
                CaisseEntry(
                    month=int(str(row["mois"]).strip()),
                    code_showroom=str(row["Code-Showroom"]).strip(),
                    mode=normalize_mode(row["mode"]),
                    date=parse_date(row["date"]),
                    amount=parse_amount(row["montant"]),
                )
            )
        except (CaisseError, ValueError, KeyError) as e:
            raise CaisseError(f"caisse.csv line {line_no}: {e}") from e
    _check_single_mode(entries)
    return entries


def _check_single_mode(entries: list[CaisseEntry]) -> None:
    modes: dict[tuple[int, str], str] = {}
    for e in entries:
        key = (e.month, e.code_showroom)
        if modes.setdefault(key, e.mode) != e.mode:
            raise CaisseError(
                f"Showroom {e.code_showroom}, month {e.month}: CCP and espece are mixed. "
                "Use only one mode per showroom and per month."
            )


def read_caisse(path: Path, encoding: str, separator: str) -> list[CaisseEntry]:
    """Read caisse.csv. Returns an empty list if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        logger.warning(f"{path.name} not found. Cash rules (CCP / espece) not applied.")
        return []
    with open(path, "r", encoding=encoding, newline="") as f:
        header = [h.strip() for h in next(f).split(separator)]
        missing = [h for h in CAISSE_HEADER if h not in header]
        if missing:
            raise CaisseError(f"caisse.csv is missing the columns: {', '.join(missing)}")
        rows = list(csv.DictReader(f, fieldnames=header, delimiter=separator))
    return parse_entries(rows)


class CaisseRules:
    """Quick access to the rules of one showroom for one month."""

    def __init__(self, entries: list[CaisseEntry]):
        self.entries = entries

    def mode_of(self, month: int, code_showroom: str) -> str | None:
        for e in self.entries:
            if e.month == int(month) and e.code_showroom == code_showroom:
                return e.mode
        return None

    def movements(self, month: int, code_showroom: str) -> list[CaisseEntry]:
        found = [
            e
            for e in self.entries
            if e.month == int(month) and e.code_showroom == code_showroom
        ]
        return sorted(found, key=lambda e: e.date)


def days_before_encaissement(days: list[date], movements: list[CaisseEntry]) -> list[date]:
    """CCP rule: keep only the selling days strictly before the first encaissement."""
    if not movements:
        return list(days)
    first = min(m.date for m in movements)
    allowed = [d for d in days if d < first]
    if not allowed:
        logger.warning(
            f"CCP encaissement on {first}: no selling day before it. Rule not applied."
        )
        return list(days)
    return allowed


def _day_total(sales: list[Sale]) -> float:
    return sum(s.sale_total_amount for s in sales)


def cash_is_covered(
    days: list[date], day_totals: list[float], movements: list[CaisseEntry]
) -> bool:
    """True if on every expense date, the cumulative sales (that day included)
    cover the cumulative expenses (that day included)."""
    for m in movements:
        sold = sum(t for d, t in zip(days, day_totals) if d <= m.date)
        spent = sum(x.amount for x in movements if x.date <= m.date)
        if sold + 1e-9 < spent:
            return False
    return True


def order_days_for_cash(
    days: list[date],
    daily_sales: list[list[Sale]],
    movements: list[CaisseEntry],
) -> list[list[Sale]]:
    """ESPECE rule: choose which group of sales goes to which date.

    The groups are interchangeable (they hold similar quantities), so we try
    random orders first (natural look). If none respects the cash rule, the
    biggest groups are put first, which is the best possible order. If even that
    fails, the expenses are higher than the sales and a warning is logged.
    """
    if not movements:
        return daily_sales

    groups = list(daily_sales)

    def totals(order: list[list[Sale]]) -> list[float]:
        return [_day_total(g) for g in order]

    if cash_is_covered(days, totals(groups), movements):
        return groups

    for _ in range(MAX_SHUFFLE_ATTEMPTS):
        candidate = random.sample(groups, k=len(groups))
        if cash_is_covered(days, totals(candidate), movements):
            return candidate

    best = sorted(groups, key=_day_total, reverse=True)
    if not cash_is_covered(days, totals(best), movements):
        total_sales = sum(totals(best))
        total_spent = sum(m.amount for m in movements)
        logger.warning(
            f"Cash expenses ({total_spent:,.2f}) cannot be covered by the sales "
            f"({total_sales:,.2f}) at the requested dates. Best order used."
        )
    return best


def split_daily_sales_by_mode(
    source: Path,
    rules: CaisseRules,
    output_folder: Path,
    separator: str = ";",
) -> list[Path]:
    """Split the finished daily_sales.csv in one file per mode.

    Creates ``daily_sales_CCP.csv`` and ``daily_sales_ESPECE.csv`` (only the ones
    that have rows). Rows of showrooms that are not in caisse.csv go to
    ``daily_sales_sans_mode.csv``. The original file is left untouched.
    """
    source = Path(source)
    if not source.exists() or not rules.entries:
        return []

    buckets: dict[str, list[list[str]]] = {CCP: [], ESPECE: [], "sans_mode": []}
    with open(source, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=separator)
        header = next(reader)
        i_month = header.index("mois")
        i_code = header.index("Code-Showroom")
        for row in reader:
            mode = rules.mode_of(int(row[i_month]), row[i_code].strip())
            buckets[mode or "sans_mode"].append(row)

    written = []
    for name, rows in buckets.items():
        if not rows:
            continue
        path = Path(output_folder) / f"daily_sales_{name}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=separator, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        written.append(path)
    return written
