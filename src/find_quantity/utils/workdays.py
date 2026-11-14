"""Selling days: every day of a month except Fridays and the holidays
listed in the user's ``holidays.yml`` file."""

import calendar
import logging
from datetime import date, datetime
from pathlib import Path

import yaml

logger = logging.getLogger("find_quantity.cli")

FRIDAY = 4


def load_holidays(path: Path) -> set[date]:
    """Read the holidays file. Returns an empty set if it doesn't exist."""
    path = Path(path)
    if not path.exists():
        logger.warning(f"Holidays file {path} not found. Only Fridays are skipped.")
        return set()

    with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f) or {}

    holidays: set[date] = set()
    for item in content.get("holidays") or []:
        if isinstance(item, datetime):
            item = item.date()
        if isinstance(item, date):
            holidays.add(item)
            continue
        try:
            holidays.add(date.fromisoformat(str(item).strip()))
        except ValueError:
            logger.error(
                f'"{item}" is not a valid date in {path.name}. Use YYYY-MM-DD.'
            )
    return holidays


def is_selling_day(dt: date, holidays: set[date] | frozenset[date] = frozenset()) -> bool:
    return dt.weekday() != FRIDAY and dt not in holidays


def selling_days(
    year: int, month: int, holidays: set[date] | frozenset[date] = frozenset()
) -> list[date]:
    """All the days of the month where sales are allowed, up to the last day."""
    last_day = calendar.monthrange(int(year), int(month))[1]
    days = (date(int(year), int(month), d) for d in range(1, last_day + 1))
    return [d for d in days if is_selling_day(d, holidays)]
