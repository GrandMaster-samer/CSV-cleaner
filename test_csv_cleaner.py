import csv
import tempfile
import unittest
from pathlib import Path

import csv_cleaner as cc


class HeaderTests(unittest.TestCase):
    def test_clean_header(self):
        self.assertEqual(cc.clean_header("  First Name ", 1), "first_name")
        self.assertEqual(cc.clean_header("E-mail (work)", 2), "e_mail_work")

    def test_empty_header_gets_a_name(self):
        self.assertEqual(cc.clean_header("   ", 3), "column_3")

    def test_unique_headers(self):
        self.assertEqual(cc.unique_headers(["a", "a", "b", "a"]), ["a", "a_2", "b", "a_3"])


class CellTests(unittest.TestCase):
    def test_trims_and_collapses_spaces(self):
        self.assertEqual(cc.clean_cell("  Rami   Khoury "), "Rami Khoury")

    def test_placeholders_become_empty(self):
        for value in ["N/A", "null", " None ", "-", "NaN", ""]:
            self.assertEqual(cc.clean_cell(value), "", value)

    def test_real_values_are_kept(self):
        self.assertEqual(cc.clean_cell("0"), "0")
        self.assertEqual(cc.clean_cell("Beirut"), "Beirut")


class RowTests(unittest.TestCase):
    def test_removes_empty_rows_and_duplicates(self):
        rows = [
            ["Name", "City"],
            ["Layla", "Beirut"],
            [" layla ", "Beirut"],      # differs only by case -> not an exact duplicate
            ["Layla ", " Beirut"],      # exact duplicate after cleaning
            ["", "N/A"],               # empty after cleaning
        ]
        header, cleaned, stats = cc.clean_rows(rows)
        self.assertEqual(header, ["name", "city"])
        self.assertEqual(cleaned, [["Layla", "Beirut"], ["layla", "Beirut"]])
        self.assertEqual((stats["empty"], stats["duplicates"], stats["written"]), (1, 1, 2))

    def test_short_rows_are_padded_and_long_rows_skipped(self):
        rows = [["a", "b"], ["1"], ["1", "2", "3"]]
        _, cleaned, stats = cc.clean_rows(rows)
        self.assertEqual(cleaned, [["1", ""]])
        self.assertEqual(stats["malformed"], 1)

    def test_dedupe_by_column_ignores_case(self):
        rows = [["Email", "Name"], ["a@x.com", "A"], ["A@X.COM", "A2"], ["b@x.com", "B"]]
        _, cleaned, stats = cc.clean_rows(rows, dedupe_by=["email"])
        self.assertEqual([r[1] for r in cleaned], ["A", "B"])
        self.assertEqual(stats["duplicates"], 1)

    def test_unknown_dedupe_column_raises(self):
        with self.assertRaises(ValueError):
            cc.clean_rows([["a"], ["1"]], dedupe_by=["zzz"])

    def test_empty_input(self):
        self.assertEqual(cc.clean_rows([]), ([], [], {"read": 0, "empty": 0, "malformed": 0, "duplicates": 0, "written": 0}))


class FileTests(unittest.TestCase):
    def test_round_trip_with_bom_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp, "in.csv"), Path(tmp, "out.csv")
            src.write_text('\ufeffName,Note\n" Sam ","said ""hi"""\n,\n', encoding="utf-8")
            stats = cc.clean_file(src, dst)
            with open(dst, newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.reader(f)), [["name", "note"], ["Sam", 'said "hi"']])
            self.assertEqual(stats["written"], 1)

    def test_main_reports_missing_file(self):
        self.assertEqual(cc.main(["definitely_missing.csv"]), 1)


if __name__ == "__main__":
    unittest.main()
