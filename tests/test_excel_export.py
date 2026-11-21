import csv

import pytest

from find_quantity.utils.excel_export import (
    convert_big_csv_files,
    count_data_rows,
    csv_to_excel_sheets,
)

openpyxl = pytest.importorskip("openpyxl")


def write_csv(path, n_rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(["mois", "Code-Showroom", "montant"])
        for i in range(1, n_rows + 1):
            w.writerow([6, "007", i * 10.5])


def test_count_rows(tmp_path):
    write_csv(tmp_path / "daily_sales_CCP.csv", 7)
    assert count_data_rows(tmp_path / "daily_sales_CCP.csv") == 7


def test_sheets_are_filled_one_after_the_other(tmp_path):
    src = tmp_path / "daily_sales_CCP.csv"
    write_csv(src, 7)
    out = tmp_path / "out.xlsx"
    sheets = csv_to_excel_sheets(src, out, max_rows=3)
    assert sheets == 3  # 3 + 3 + 1
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Feuil1", "Feuil2", "Feuil3"]
    sizes = [ws.max_row - 1 for ws in wb.worksheets]  # without header
    assert sizes == [3, 3, 1]
    for ws in wb.worksheets:
        assert [c.value for c in ws[1]] == ["mois", "Code-Showroom", "montant"]
    # nothing lost, order kept
    amounts = [ws.cell(r, 3).value for ws in wb.worksheets for r in range(2, ws.max_row + 1)]
    assert amounts == [i * 10.5 for i in range(1, 8)]


def test_numbers_are_numbers_and_codes_keep_their_zeros(tmp_path):
    src = tmp_path / "daily_sales_CCP.csv"
    write_csv(src, 2)
    out = tmp_path / "out.xlsx"
    csv_to_excel_sheets(src, out, max_rows=10)
    ws = openpyxl.load_workbook(out).worksheets[0]
    assert ws.cell(2, 1).value == 6
    assert ws.cell(2, 2).value == "007"
    assert ws.cell(2, 3).value == 10.5


def test_only_big_files_are_converted(tmp_path):
    write_csv(tmp_path / "daily_sales_CCP.csv", 5)
    write_csv(tmp_path / "daily_sales_ESPECE.csv", 2)
    created = convert_big_csv_files(tmp_path, max_rows=3)
    assert [p.name for p in created] == ["daily_sales_CCP.xlsx"]
    assert not (tmp_path / "daily_sales_CCP.csv").exists()  # replaced
    assert (tmp_path / "daily_sales_ESPECE.csv").exists()  # small one untouched


def test_file_with_exactly_max_rows_stays_csv(tmp_path):
    write_csv(tmp_path / "daily_sales_CCP.csv", 3)
    assert convert_big_csv_files(tmp_path, max_rows=3) == []
