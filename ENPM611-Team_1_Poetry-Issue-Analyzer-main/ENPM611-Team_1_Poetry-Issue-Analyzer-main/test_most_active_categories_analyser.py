import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

import pandas as pd
import numpy as np

import most_active_categories_analyser


class TestMostActiveCategoriesAnalyser(unittest.TestCase):
    """Clean and aligned tests for MostActiveCategoriesAnalyser."""

    def setUp(self):
        self.analyzer = most_active_categories_analyser.MostActiveCategoriesAnalyser(
            data_path="./test_data.json"
        )

    # ------------------------------------------------------------------
    # _load_issues
    # ------------------------------------------------------------------
    @patch("most_active_categories_analyser.Path.read_text")
    def test_load_issues_reads_json(self, mock_read_text):
        mock_read_text.return_value = '[{"number": 1, "title": "Issue 1"}]'
        res = self.analyzer._load_issues()
        self.assertEqual(res, [{"number": 1, "title": "Issue 1"}])

    # ------------------------------------------------------------------
    # _iid
    # ------------------------------------------------------------------
    def test_iid_with_number(self):
        issue = {"number": 10}
        self.assertEqual(self.analyzer._iid(issue), "10")

    def test_iid_with_url(self):
        issue = {"url": "http://x/y/33"}
        self.assertEqual(self.analyzer._iid(issue), "33")

    def test_iid_missing(self):
        self.assertEqual(self.analyzer._iid({}), "")

    # ------------------------------------------------------------------
    # _label_names
    # ------------------------------------------------------------------
    def test_label_names(self):
        labels = ["bug", {"name": "feature"}, None, {"name": ""}]
        expected = ["bug", "feature", "None"]
        self.assertEqual(self.analyzer._label_names(labels), expected)

    def test_label_names_empty(self):
        self.assertEqual(self.analyzer._label_names([]), [])
        self.assertEqual(self.analyzer._label_names(None), [])

    # ------------------------------------------------------------------
    # _flatten_events
    # ------------------------------------------------------------------
    @patch("most_active_categories_analyser.parser.parse")
    def test_flatten_events(self, mock_parse):
        mock_parse.return_value = datetime(2023, 1, 1)

        issues = [{
            "number": 1,
            "title": "T",
            "labels": ["bug"],
            "events": [{"event_type": "opened", "event_date": "2023-01-01"}]
        }]

        df = self.analyzer._flatten_events(issues)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "issue_id"], "1")

    @patch("most_active_categories_analyser.parser.parse", side_effect=Exception("err"))
    def test_flatten_events_bad_date(self, mock_parse):
        issues = [{
            "number": 1,
            "title": "T",
            "labels": ["bug"],
            "events": [{"event_type": "opened", "event_date": "xxx"}]
        }]

        df = self.analyzer._flatten_events(issues)
        self.assertEqual(len(df), 1)
        self.assertIsNone(df.loc[0, "event_date"])

    # ------------------------------------------------------------------
    # _make_ylabels
    # ------------------------------------------------------------------
    def test_make_ylabels(self):
        df = pd.DataFrame({
            "issue_id": ["1", "2"],
            "title": ["Short", "Long long long long long title"]
        })
        out = self.analyzer._make_ylabels(df, wrap_at=20)
        self.assertEqual(len(out), 2)
        self.assertTrue(out[0].startswith("#1:"))

    # ------------------------------------------------------------------
    # _classify_type
    # ------------------------------------------------------------------
    def test_classify_bug_label(self):
        self.assertEqual(self.analyzer._classify_type(["bug"], ""), "Bug")

    def test_classify_bug_title(self):
        self.assertEqual(self.analyzer._classify_type([], "Crash occurred"), "Bug")

    def test_classify_dependency_label(self):
        self.assertEqual(self.analyzer._classify_type(["dependency"], ""), "Dependency")

    def test_classify_infra_title(self):
        self.assertEqual(self.analyzer._classify_type([], "Improve CI pipeline"), "Infra")

    def test_classify_feature(self):
        self.assertEqual(self.analyzer._classify_type(["kind/feature"], ""), "Feature")

    def test_classify_docs(self):
        self.assertEqual(self.analyzer._classify_type([], "Readme update"), "Docs")

    def test_classify_other(self):
        self.assertEqual(self.analyzer._classify_type(["random"], ""), "Other")

    # ------------------------------------------------------------------
    # _prepare_category_table (real pandas, FIXED)
    # ------------------------------------------------------------------
    def test_prepare_category_table_real(self):
        df = pd.DataFrame({
            "issue_id": ["1", "2", "3", "4"],
            "type": ["Bug", "Bug", "Feature", "Other"]
        })

        table = self.analyzer._prepare_category_table(df)

        # check proper summation
        self.assertEqual(table.loc["Bug", "count"], 2.0)
        self.assertEqual(table.loc["Feature", "count"], 1.0)
        self.assertEqual(table.loc["Other", "count"], 1.0)

        # pct should sum to 1 over non-zero entries
        self.assertAlmostEqual(table["pct"].sum(), 1.0, places=6)

    # ------------------------------------------------------------------
    # Plot functions — only patch plt
    # ------------------------------------------------------------------
    @patch("most_active_categories_analyser.plt")
    def test_plot_lollipop(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        df = pd.DataFrame({
            "issue_id": ["1"],
            "title": ["A"],
            "activity_score": [0.5],
            "color": ["#000"],
        })
        res = self.analyzer._build_plot_topn_lollipop(df, "2023")
        self.assertIs(res, mock_fig)

    @patch("most_active_categories_analyser.plt")
    def test_plot_pie_empty(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        table = pd.DataFrame({"count": [0, 0], "pct": [0.0, 0.0]}, index=["Bug", "Feature"])
        res = self.analyzer._build_plot_category_pie(table, "2023")
        self.assertIs(res, mock_fig)

    @patch("most_active_categories_analyser.plt")
    def test_plot_pie_nonempty(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        table = pd.DataFrame({"count": [3, 1], "pct": [0.75, 0.25]}, index=["Bug", "Feature"])
        res = self.analyzer._build_plot_category_pie(table, "2023")
        self.assertIs(res, mock_fig)

    @patch("most_active_categories_analyser.plt")
    @patch("most_active_categories_analyser.tabulate")
    @patch("builtins.print")
    def test_plot_state_bars(self, mock_print, mock_tab, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        df = pd.DataFrame({
            "type": ["Bug", "Bug", "Feature"],
            "state": ["open", "closed", "open"],
            "issue_id": ["1", "2", "3"]
        })

        res = self.analyzer._build_plot_category_state_bars(df, "2023")
        self.assertIs(res, mock_fig)
        mock_tab.tabulate.assert_called()

    # ------------------------------------------------------------------
    # run()
    # ------------------------------------------------------------------
    @patch("most_active_categories_analyser.MostActiveCategoriesAnalyser._load_issues")
    @patch("most_active_categories_analyser.MostActiveCategoriesAnalyser._flatten_events")
    def test_run_no_events(self, mock_flatten, mock_load):
        mock_flatten.return_value = pd.DataFrame()
        with patch("builtins.print") as p:
            res = self.analyzer.run()
            self.assertIsNone(res)
            p.assert_any_call("No events to analyze.")

    @patch("most_active_categories_analyser.MostActiveCategoriesAnalyser._load_issues")
    @patch("most_active_categories_analyser.MostActiveCategoriesAnalyser._flatten_events")
    def test_run_full_flow(self, mock_flatten, mock_load):
        mock_load.return_value = [
            {"number": 1, "title": "A", "labels": ["bug"], "state": "open"},
            {"number": 2, "title": "B", "labels": ["feature"], "state": "closed"}
        ]

        ev = pd.DataFrame({
            "issue_id": ["1", "1", "2"],
            "title": ["A", "A", "B"],
            "event_type": ["opened", "commented", "opened"],
            "year": [2023, 2023, 2023],
        })
        mock_flatten.return_value = ev

        with patch("most_active_categories_analyser.plt.show"):
            res = self.analyzer.run(year=2023, top_n=2)
            self.assertIsNotNone(res)


if __name__ == "__main__":
    unittest.main()
