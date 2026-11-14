from datetime import date

from find_quantity.utils.workdays import (
    FRIDAY,
    is_selling_day,
    load_holidays,
    selling_days,
)

HOLIDAYS = {date(2026, 7, 5), date(2026, 11, 1)}


def test_no_friday_in_selling_days():
    for month in range(1, 13):
        days = selling_days(2026, month, HOLIDAYS)
        assert all(d.weekday() != FRIDAY for d in days)


def test_holidays_are_excluded():
    days = selling_days(2026, 7, HOLIDAYS)
    assert date(2026, 7, 5) not in days


def test_month_is_filled_until_the_last_day():
    # November 2026: 30 days, 4 Fridays (6, 13, 20, 27), and 1 Nov is a holiday
    days = selling_days(2026, 11, HOLIDAYS)
    assert len(days) == 30 - 4 - 1
    assert max(days) == date(2026, 11, 30)


def test_february_leap_year_has_29_days_range():
    days = selling_days(2028, 2)
    assert max(days).day == 29


def test_is_selling_day():
    assert not is_selling_day(date(2026, 11, 13))  # Friday
    assert not is_selling_day(date(2026, 11, 1), HOLIDAYS)
    assert is_selling_day(date(2026, 11, 2), HOLIDAYS)


def test_load_holidays_template():
    from pathlib import Path

    path = Path(__file__).parent.parent / "src/find_quantity/templates/holidays.yml"
    holidays = load_holidays(path)
    assert date(2026, 1, 1) in holidays
    assert date(2027, 11, 1) in holidays
    assert {h.year for h in holidays} == {2026, 2027}


def test_load_holidays_missing_file(tmp_path):
    assert load_holidays(tmp_path / "nope.yml") == set()
