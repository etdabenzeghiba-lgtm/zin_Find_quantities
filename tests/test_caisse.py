import csv
from datetime import date

import pytest

from find_quantity.models import Sale
from find_quantity.models.product import gen_test_product
from find_quantity.utils.caisse import (
    CCP,
    ESPECE,
    CaisseEntry,
    CaisseError,
    CaisseRules,
    cash_is_covered,
    days_before_encaissement,
    normalize_mode,
    order_days_for_cash,
    parse_amount,
    parse_entries,
    split_daily_sales_by_mode,
)


def row(mois="1", code="SH1", mode="CCP", d="2026-01-20", montant="1000"):
    return {
        "mois": mois,
        "showroom": "Alger",
        "Code-Showroom": code,
        "mode": mode,
        "date": d,
        "montant": montant,
    }


def group(total: int) -> list[Sale]:
    """A group of sales worth `total` (price 1 x total units)."""
    return [Sale(product=gen_test_product(stock_qt=total, prix=1), units_sold=total)]


def test_mode_spellings():
    assert normalize_mode("ccp") == CCP
    assert normalize_mode(" CCP ") == CCP
    assert normalize_mode("espèce") == ESPECE
    assert normalize_mode("Especes") == ESPECE
    with pytest.raises(CaisseError):
        normalize_mode("cheque")


def test_amount_formats():
    assert parse_amount("1234,50") == 1234.5
    assert parse_amount("1.234,50") == 1234.5
    assert parse_amount("12 000") == 12000
    assert parse_amount("") == 0


def test_mixed_modes_for_same_showroom_and_month_refused():
    with pytest.raises(CaisseError):
        parse_entries([row(mode="CCP"), row(mode="espece")])


def test_same_showroom_different_month_can_change_mode():
    entries = parse_entries([row(mois="1", mode="CCP"), row(mois="2", mode="espece")])
    rules = CaisseRules(entries)
    assert rules.mode_of(1, "SH1") == CCP
    assert rules.mode_of(2, "SH1") == ESPECE
    assert rules.mode_of(3, "SH1") is None


def test_bad_date_is_reported_with_line_number():
    with pytest.raises(CaisseError, match="line 2"):
        parse_entries([row(d="not a date")])


def test_ccp_only_days_strictly_before_encaissement():
    days = [date(2026, 1, d) for d in (1, 2, 3, 4, 5)]
    entries = parse_entries([row(d="2026-01-04")])
    allowed = days_before_encaissement(days, entries)
    assert allowed == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]


def test_ccp_encaissement_on_first_day_keeps_all_days():
    days = [date(2026, 1, d) for d in (1, 2, 3)]
    entries = parse_entries([row(d="2026-01-01")])
    assert days_before_encaissement(days, entries) == days


def test_espece_order_covers_expense():
    days = [date(2026, 1, d) for d in range(1, 6)]
    # One big day of 1000 and four small days of 10
    groups = [group(10), group(10), group(10), group(10), group(1000)]
    # Expense of 500 on day 1: the big day must go first
    entries = parse_entries([row(mode="espece", d="2026-01-01", montant="500")])
    ordered = order_days_for_cash(days, groups, entries)
    totals = [sum(s.sale_total_amount for s in g) for g in ordered]
    assert totals[0] == 1000
    assert cash_is_covered(days, totals, entries)


def test_espece_same_day_sales_can_pay_the_expense():
    days = [date(2026, 1, 1), date(2026, 1, 2)]
    entries = parse_entries([row(mode="espece", d="2026-01-01", montant="100")])
    assert cash_is_covered(days, [100, 0], entries)
    assert not cash_is_covered(days, [99, 1000], entries)


def test_espece_impossible_expense_raises():
    days = [date(2026, 1, d) for d in range(1, 4)]
    groups = [group(10), group(10), group(10)]
    entries = parse_entries([row(mode="espece", d="2026-01-02", montant="5000")])
    with pytest.raises(CaisseError, match="cannot be covered"):
        order_days_for_cash(days, groups, entries)

def test_split_daily_sales_by_mode(tmp_path):
    source = tmp_path / "daily_sales.csv"
    with open(source, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(["mois", "showroom", "Code-Showroom", "date"])
        w.writerow([1, "Alger", "SH1", "2026-01-02"])
        w.writerow([1, "Oran", "SH2", "2026-01-02"])
        w.writerow([1, "Blida", "SH3", "2026-01-02"])
    rules = CaisseRules(
        parse_entries(
            [row(code="SH1", mode="CCP"), row(code="SH2", mode="espece")]
        )
    )
    written = split_daily_sales_by_mode(source, rules, tmp_path)
    names = sorted(p.name for p in written)
    assert names == [
        "daily_sales_CCP.csv",
        "daily_sales_ESPECE.csv",
        "daily_sales_sans_mode.csv",
    ]
    assert "Alger" in (tmp_path / "daily_sales_CCP.csv").read_text()
    assert "Alger" not in (tmp_path / "daily_sales_ESPECE.csv").read_text()
    assert source.exists()
