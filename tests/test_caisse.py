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


def test_espece_impossible_expense_does_not_crash(caplog):
    days = [date(2026, 1, d) for d in range(1, 4)]
    groups = [group(10), group(10), group(10)]
    entries = parse_entries([row(mode="espece", d="2026-01-02", montant="5000")])
    ordered = order_days_for_cash(days, groups, entries)
    assert len(ordered) == 3
    assert "cannot be covered" in caplog.text


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


def test_espece_warning_names_the_date_and_totals(caplog):
    days = [date(2026, 1, d) for d in range(1, 4)]
    groups = [group(100), group(100), group(100)]
    # Total sales 300 > expense 250, but on January 1st only 100 can be sold
    entries = parse_entries([row(mode="espece", d="2026-01-01", montant="250")])
    order_days_for_cash(days, groups, entries)
    assert "2026-01-01" in caplog.text
    assert "100.00" in caplog.text and "250.00" in caplog.text


def test_espece_rounding_error_is_not_a_problem():
    days = [date(2026, 1, 1), date(2026, 1, 2)]
    entries = parse_entries([row(mode="espece", d="2026-01-02", montant="123949500")])
    # sum of the days is a hair under the expense because of float rounding
    assert cash_is_covered(days, [123949499.999999, 0.0], entries)


# ---- real distribution with the cash rule ----
from find_quantity.models import Inventory
from find_quantity.solver import Solver
from find_quantity.utils.caisse import (
    cash_weights,
    distribute_for_cash,
    weighted_quantities,
)


def month_days(n=25):
    return [date(2026, 6, d) for d in range(1, n + 1)]


def showroom_sales():
    return [
        Sale(
            product=gen_test_product(n_article=f"A{i}", stock_qt=200 + i, prix=100 + i * 7),
            units_sold=200 + i,
        )
        for i in range(8)
    ]


def make_inventory():
    inv = Inventory(merge_rules=[])
    inv.add_products_from_sales(showroom_sales())
    return inv


def totals_of(groups):
    return [sum(s.sale_total_amount for s in g) for g in groups]


def test_weighted_quantities_keep_the_total():
    for qty in (0, 1, 7, 200, 1001):
        parts = weighted_quantities([5.0, 1.0, 1.0, 0.0, 3.0], qty)
        assert sum(parts) == qty
        assert parts[3] == 0


def test_cash_weights_impossible_cases():
    days = month_days()
    too_early = parse_entries([row(mode="espece", d="2026-05-01", montant="10")])
    assert cash_weights(days, too_early, 1000, 0.02) is None
    too_big = parse_entries([row(mode="espece", d="2026-06-30", montant="5000")])
    assert cash_weights(days, too_big, 1000, 0.02) is None


def test_big_early_expense_is_really_covered():
    """The bug seen in real use: total sales > expenses, but the expense is early."""
    days = month_days()
    solver = Solver()
    total = sum(totals_of(solver.distrubute_products_equally(make_inventory(), len(days))))
    amount = round(total * 0.42)  # 42% of the month's sales needed by June 3rd
    entries = parse_entries([row(mode="espece", d="2026-06-03", montant=str(amount))])
    for _ in range(10):  # random: try several times
        groups = distribute_for_cash(solver, make_inventory, days, entries)
        assert len(groups) == len(days)
        day_totals = totals_of(groups)
        assert cash_is_covered(days, day_totals, entries)
        assert abs(sum(day_totals) - total) < 1e-6  # all the sales are still used


def test_two_expenses_are_both_covered():
    days = month_days()
    solver = Solver()
    total = sum(totals_of(solver.distrubute_products_equally(make_inventory(), len(days))))
    entries = parse_entries(
        [
            row(mode="espece", d="2026-06-02", montant=str(round(total * 0.2))),
            row(mode="espece", d="2026-06-08", montant=str(round(total * 0.3))),
        ]
    )
    groups = distribute_for_cash(solver, make_inventory, days, entries)
    assert cash_is_covered(days, totals_of(groups), entries)


def test_easy_expense_keeps_an_equal_looking_split():
    days = month_days()
    solver = Solver()
    entries = parse_entries([row(mode="espece", d="2026-06-25", montant="100")])
    groups = distribute_for_cash(solver, make_inventory, days, entries)
    day_totals = totals_of(groups)
    assert max(day_totals) < 2 * (sum(day_totals) / len(days))  # no concentration


def test_expense_bigger_than_all_sales_warns_but_works(caplog):
    days = month_days()
    solver = Solver()
    entries = parse_entries([row(mode="espece", d="2026-06-10", montant="999999999")])
    groups = distribute_for_cash(solver, make_inventory, days, entries)
    assert len(groups) == len(days)
    assert "cannot be covered" in caplog.text
