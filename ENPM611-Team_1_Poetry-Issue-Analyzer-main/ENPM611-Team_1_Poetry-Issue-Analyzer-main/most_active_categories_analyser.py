# most_active_categories_analyser.py
import json
from pathlib import Path
from textwrap import fill
from typing import Iterable, List, Dict, Optional
import re

from dateutil import parser
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate


class MostActiveCategoriesAnalyser:
    """
    Feature 1 output:
      1) Lollipop: Top-N Most Active Issues (normalized activity score)
      2) Pie: Category share (% of issues in the selected period)
      3) Grouped Bar: Open vs Closed issue counts per category
      4) CLI: Breakdown of what’s inside the 'Other' bucket (top labels + families)

    Filters:
      - filter_type:   high-level category (Bug, Feature, Docs, Dependency, Infra, Other; comma-separated)
      - filter_labels: substring match on raw labels (e.g., "kind/bug, area/cli")
    """

    CATEGORY_COLORS = {
        "Bug": "#d62728",          # red
        "Feature": "#2ca02c",      # green
        "Docs": "#9467bd",         # purple
        "Dependency": "#1f77b4",   # blue
        "Infra": "#ff7f0e",        # orange
        "Other": "#7f7f7f"         # gray
    }
    CATEGORY_ORDER = ["Bug", "Feature", "Docs", "Dependency", "Infra", "Other"]

    def __init__(self, data_path: str = "./poetry_issues.json"):
        self.data_path = Path(data_path)

    # --------- Helpers ---------
    def _load_issues(self) -> list:
        return json.loads(self.data_path.read_text(encoding="utf-8"))

    @staticmethod
    def _iid(issue) -> str:
        return str(issue.get("number") or issue.get("url", "").split("/")[-1])

    @staticmethod
    def _label_names(labels: Iterable) -> List[str]:
        """Convert labels to a list of plain strings (handles dicts from the GitHub API)."""
        out = []
        for l in labels or []:
            if isinstance(l, dict):
                name = l.get("name")
                if name:
                    out.append(str(name))
            else:
                out.append(str(l))
        return out

    def _flatten_events(self, issues: list) -> pd.DataFrame:
        """
        Build a long dataframe of events:
          issue_id, title, labels(list[str]), event_type, event_date, year
        """
        rows = []
        for iss in issues:
            iid = self._iid(iss)
            title = iss.get("title", "") or ""
            labels = self._label_names(iss.get("labels", []) or [])
            for ev in iss.get("events", []) or []:
                etype = ev.get("event_type") or ev.get("type") or ev.get("event")
                edate = ev.get("event_date") or ev.get("created_at") or ev.get("date")
                try:
                    dt = parser.parse(edate) if edate else None
                    year = dt.year if dt else None
                except Exception:
                    dt, year = None, None
                rows.append({
                    "issue_id": iid,
                    "title": title,
                    "labels": tuple(labels),
                    "event_type": etype,
                    "event_date": dt,
                    "year": year
                })
        return pd.DataFrame.from_records(rows)

    def _make_ylabels(self, df: pd.DataFrame, wrap_at: int = 60) -> list[str]:
        """Wrap long titles for y-axis labels: '#<id>: <title>'."""
        return [fill(f"#{iid}: {title}", width=wrap_at)
                for iid, title in zip(df["issue_id"], df["title"])]

    # ---------- Classification (refined to shrink "Other") ----------
    def _classify_type(self, labels: List[str], title: str = "") -> str:
        """
        Map labels/title to a general category.
        Goal: reduce "Other" by capturing common families explicitly.

        Priority order when multiple cues appear:
          Bug > Dependency > Infra > Feature > Docs > Other
        """
        ll = [str(l).lower() for l in (labels or [])]
        labset = set(ll)
        t = (title or "").lower()

        def has_any(substrs: List[str]) -> bool:
            if not labset:
                return False
            return any(any(s in lab for s in substrs) for lab in labset)

        def family_starts(prefix: str) -> bool:
            p = prefix.lower()
            if not labset:
                return False
            return any(lab.startswith(p + "/") or lab == p for lab in labset)

        # 1) BUG
        if (
            has_any(["kind/bug", "bug", "crash", "regression", "panic", "traceback", "segfault", "needs-reproduction"])
            or re.search(r"\bbug|crash|regression|error|fix(es)?\b", t)
        ):
            return "Bug"

        # 2) DEPENDENCY
        if (
            has_any(["dependency", "dependencies", "deps", "dependabot", "bump", "chore(deps)", "security(deps)"])
            or re.search(r"\bdependenc(y|ies)|deps|dependabot|bump|poetry\.lock\b", t)
        ):
            return "Dependency"

        # 3) INFRA (tooling/CI/build/CLI/core/config/installer/solver/refactor/tests)
        if (
            has_any(["ci", "cd", "workflow", "github actions", "pipeline", "build", "release", "refactor", "tooling", "flake8", "ruff"])
            or family_starts("area/ci")
            or family_starts("area/cli")
            or family_starts("area/core")
            or family_starts("area/config")
            or family_starts("area/installer")
            or family_starts("area/solver")
            or has_any(["test", "tests", "pytest", "unittest"])
            or re.search(r"\bci|cd|workflow|build|release|pipeline|test(s)?\b", t)
        ):
            return "Infra"

        # 4) FEATURE (enhancement/requests)
        if (
            has_any(["kind/feature", "kind/enhancement", "feature", "enhancement", "improvement"])
            or re.search(r"\b(feature|enhancement|improvement|proposal|request)\b", t)
        ):
            return "Feature"

        # 5) DOCS (include questions/FAQ/how-to)
        if (
            has_any(["docs", "documentation", "readme", "guide", "tutorial", "howto", "how-to", "faq", "kind/question"])
            or family_starts("area/docs")
            or family_starts("docs/faq")
            or re.search(r"\bdoc(s)?|readme|guide|tutorial|how[- ]?to|faq\b", t)
        ):
            return "Docs"

        # 6) OTHER (status/* etc. stay here; they're workflow, not type)
        return "Other"

    # --------- “Other” breakdown (CLI only) ----------
    def _print_other_breakdown(self, norm_period_df: pd.DataFrame, period_label: str, top_k: int = 10) -> None:
        """
        Print top raw labels and label families present in issues categorized as 'Other'
        (within the selected period; before user-applied filters).
        """
        # unique issues in period with their label lists & type
        uniq = norm_period_df[["issue_id", "labels", "type"]].drop_duplicates("issue_id")
        other = uniq[uniq["type"] == "Other"].copy()
        if other.empty:
            print(f"No 'Other' issues to break down for {period_label}.\n")
            return

        # ---- Top labels (count unique issues per label)
        # explode labels
        exploded = other.explode("labels")
        exploded["labels"] = exploded["labels"].fillna("").astype(str)
        exploded = exploded[exploded["labels"].str.len() > 0]
        if exploded.empty:
            print(f"No labels found inside 'Other' for {period_label}.\n")
            return

        top_labels = (exploded.groupby("labels")["issue_id"]
                      .nunique()
                      .sort_values(ascending=False)
                      .head(top_k)
                      .reset_index()
                      .rename(columns={"labels": "Label", "issue_id": "Issues"}))

        print("Top labels found in 'Other':")
        print(tabulate(top_labels, headers="keys", tablefmt="github"))
        print()

        # ---- Top families (prefix before '/'), with common sublabels
        def split_family(lbl: str) -> (str, str):
            parts = lbl.split("/", 1)
            return (parts[0], parts[1] if len(parts) > 1 else "")

        fam = exploded.assign(
            Family=exploded["labels"].apply(lambda s: split_family(s)[0]),
            Sublabel=exploded["labels"].apply(lambda s: split_family(s)[1]),
        )

        fam_counts = (fam.groupby("Family")["issue_id"]
                      .nunique()
                      .sort_values(ascending=False)
                      .head(top_k)
                      .reset_index()
                      .rename(columns={"issue_id": "Issues"}))

        # collect common sublabels for each family
        common_rows = []
        for family in fam_counts["Family"]:
            sub = fam[fam["Family"] == family]
            top_sub = (sub[sub["Sublabel"].str.len() > 0]
                       .groupby("Sublabel")["issue_id"]
                       .nunique()
                       .sort_values(ascending=False)
                       .head(3)
                       .reset_index())
            if not top_sub.empty:
                common = ", ".join(f"{r['Sublabel']} ({int(r['issue_id'])})" for _, r in top_sub.iterrows())
            else:
                common = "-"
            issues = int(fam_counts.loc[fam_counts["Family"] == family, "Issues"].iloc[0])
            common_rows.append({"Family": family, "Issues": issues, "Common sublabels": common})

        fam_table = pd.DataFrame(common_rows)

        print("Top label families in 'Other':")
        print(tabulate(fam_table, headers="keys", tablefmt="github"))
        print()

    # --------- Plot builders (return fig; show() later once for all) ---------
    def _build_plot_topn_lollipop(self, top_df: pd.DataFrame, period_label: str, wrap_at: int = 60):
        """Lollipop (hlines + dots) with value annotations + category colors."""
        top_sorted = top_df.sort_values("activity_score", ascending=True)
        ylabels = self._make_ylabels(top_sorted, wrap_at=wrap_at)

        n = len(top_sorted)
        height = max(6, 0.6 * n)
        fig, ax = plt.subplots(figsize=(12, height))

        colors = list(top_sorted["color"])
        for y, xmax, col in zip(range(n), top_sorted["activity_score"], colors):
            ax.hlines(y=y, xmin=0, xmax=xmax, linewidth=2, color=col)
        ax.plot(top_sorted["activity_score"], range(n), "o", markersize=8, color="black")
        ax.scatter(top_sorted["activity_score"], range(n), s=64, color=colors, zorder=3)

        ax.set_yticks(range(n), labels=ylabels)
        ax.set_xlabel("Activity Score (normalized)", fontsize=11)
        ax.set_title(f"Most Active Issues (Top {n}) — {period_label}", fontsize=14, weight="bold")

        for idx, val in enumerate(top_sorted["activity_score"]):
            ax.text(val + 0.02, idx, f"{val:.2f}", va="center", fontsize=9)

        handles = [plt.Line2D([0], [0], color=c, lw=6, label=t)
                   for t, c in self.CATEGORY_COLORS.items()]
        ax.legend(handles=handles, title="Issue Type", loc="lower right")

        fig.tight_layout()
        fig.subplots_adjust(left=0.35)
        return fig

    def _prepare_category_table(self, issues_unique: pd.DataFrame) -> pd.DataFrame:
        """
        Return a table indexed by category with absolute counts and percentage of total.
        Uses unique issue ids in the selected period (regardless of state).
        """
        counts = (issues_unique
                  .groupby(["type"])
                  .size()
                  .rename("count")
                  .reset_index())

        table = (counts
                 .set_index("type")
                 .reindex(self.CATEGORY_ORDER)
                 .fillna(0)
                 .astype(float))

        table["count"] = table["count"].fillna(0)
        total = table["count"].sum()
        table["pct"] = np.where(total > 0, table["count"] / total, 0.0)
        return table

    def _build_plot_category_pie(self, table: pd.DataFrame, period_label: str):
        """Pie chart of % share across categories for the selected period."""
        tbl = table[table["count"] > 0].copy()
        fig, ax = plt.subplots(figsize=(7, 7))
        if tbl.empty:
            ax.text(0.5, 0.5, "No issues in period", ha="center", va="center")
            ax.axis("off")
            return fig

        labels = list(tbl.index)
        sizes = list(tbl["pct"].values)
        colors = [self.CATEGORY_COLORS.get(t, "#aaaaaa") for t in labels]

        ax.pie(
            sizes,
            labels=labels,
            autopct=lambda p: f"{p:.0f}%" if p >= 3 else "",  # suppress tiny labels
            startangle=140,
            colors=colors,
            wedgeprops=dict(linewidth=1, edgecolor="white")
        )
        ax.set_title(f"Category Share (% of issues) — {period_label}", fontsize=13, weight="bold")
        ax.axis("equal")
        fig.tight_layout()
        return fig

    def _build_plot_category_state_bars(self, issues_unique_state: pd.DataFrame, period_label: str):
        """
        Grouped bar chart: Open vs Closed counts per category (absolute counts).
        Also prints a small CLI table of those counts.
        """
        # Normalize state to open/closed
        tmp = issues_unique_state.copy()
        tmp["state"] = tmp["state"].astype(str).str.lower().map(
            lambda s: "open" if "open" in s else ("closed" if "close" in s else "other")
        )

        cat_state = (tmp.groupby(["type", "state"])
                      .size()
                      .rename("count")
                      .reset_index())

        table = (cat_state
                 .pivot_table(index="type", columns="state", values="count", fill_value=0)
                 .reindex(self.CATEGORY_ORDER)
                 .fillna(0)
                 .astype(int))

        # Reorder columns to Open, Closed (and "other" if present)
        cols = [c for c in ["open", "closed", "other"] if c in table.columns]
        table = table[cols]

        # ---- CLI table
        print(f"Issue Counts by Category and State — {period_label}\n")
        print(tabulate(table.reset_index().rename(columns={"type": "Type"}),
                       headers="keys", tablefmt="github"))
        print()

        # ---- Plot grouped bars
        types = list(table.index)
        x = np.arange(len(types))
        width = 0.35 if len(cols) == 2 else 0.28

        fig, ax = plt.subplots(figsize=(10.5, 5.5))

        for i, st in enumerate(cols):
            ax.bar(x + (i - (len(cols)-1)/2) * width,
                   table[st].values,
                   width,
                   label=st.capitalize())

            # annotate counts on each bar
            for xi, yi in zip(x + (i - (len(cols)-1)/2) * width, table[st].values):
                ax.text(xi, yi + max(1, yi*0.02), str(int(yi)),
                        ha="center", va="bottom", fontsize=9)

        ax.set_title(f"Open vs Closed Issues by Category — {period_label}", fontsize=13, weight="bold")
        ax.set_xlabel("Issue Category")
        ax.set_ylabel("Count")
        ax.set_xticks(x, types)
        ax.legend()
        fig.tight_layout()
        return fig

    # --------- Main logic ---------
    def run(
        self,
        year: Optional[int] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        top_n: int = 5,
        plot: str = "lollipop",       # Top-N chart style (kept for compatibility)
        wrap_at: int = 60,            # characters per line for label wrapping
        filter_type: Optional[str] = None,     # e.g., "Bug,Feature"
        filter_labels: Optional[str] = None,   # e.g., "kind/bug, area/cli"
        show_category_pie: bool = True,
        show_category_state_bars: bool = True
    ):
        """
        :param year: Single year (used if range not provided). Defaults to latest year in data.
        :param start_year: Start of year range (used only if both start_year and end_year provided).
        :param end_year: End of year range (used only if both start_year and end_year provided).
        :param top_n: Number of top issues to display.
        :param plot: Lollipop style for Top-N (value kept for compatibility).
        :param wrap_at: Wrap width for axis labels.
        :param filter_type: Filter by category Type (comma-separated ok).
        :param filter_labels: Filter by raw label names (comma-separated; substring match).
        :param show_category_pie: Also render category % pie.
        :param show_category_state_bars: Also render Open vs Closed grouped bars.
        """
        issues = self._load_issues()
        ev = self._flatten_events(issues)

        if ev.empty:
            print("No events to analyze.")
            return

        years_available = sorted(ev["year"].dropna().unique())
        if not years_available:
            print("No years found in events.")
            return

        # ---- Period selection
        if start_year is not None and end_year is not None:
            ev_period = ev[(ev["year"] >= start_year) & (ev["year"] <= end_year)].copy()
            period_label = f"{start_year}-{end_year}"
        else:
            if year is None:
                year = int(years_available[-1])
            ev_period = ev[ev["year"] == year].copy()
            period_label = str(year)

        if ev_period.empty:
            print(f"No events found for selected period {period_label}.")
            return

        # ---- Maps (labels/state)
        id_to_labels: Dict[str, List[str]] = {}
        id_to_state: Dict[str, str] = {}
        for it in issues:
            iid = self._iid(it)
            id_to_labels[iid] = self._label_names(it.get("labels", []) or [])
            id_to_state[iid] = (it.get("state") or "").lower() or "-"

        # ---- Event counts (per issue, per event_type)
        counts = (ev_period.groupby(["issue_id", "title", "event_type"])
                  .size().rename("count").reset_index())

        pivot = (counts.pivot_table(index=["issue_id", "title"],
                                    columns="event_type",
                                    values="count",
                                    fill_value=0).reset_index())

        if "commented" not in pivot.columns:
            pivot["commented"] = 0

        # Normalize each event-type column across issues to [0,1]
        event_cols = [c for c in pivot.columns if c not in ["issue_id", "title"]]
        norm = pivot.copy()
        for c in event_cols:
            col = norm[c].astype(float)
            rng = col.max() - col.min()
            norm[c] = (col > 0).astype(float) if rng == 0 else (col - col.min()) / rng

        # ---- Metadata + classification
        norm["labels"] = norm["issue_id"].map(lambda iid: id_to_labels.get(iid, []))
        norm["state"] = norm["issue_id"].map(lambda iid: id_to_state.get(iid, "-"))
        title_map = dict(zip(pivot["issue_id"], pivot["title"]))
        norm["type"] = norm.apply(
            lambda r: self._classify_type(r["labels"], title_map.get(r["issue_id"], "")),
            axis=1
        )
        norm["color"] = norm["type"].apply(lambda t: self.CATEGORY_COLORS.get(t, "#7f7f7f"))

        # ---- Keep a copy BEFORE filters for "Other" breakdown
        norm_period_all = norm[["issue_id", "labels", "type"]].drop_duplicates("issue_id")

        # ---- Optional filters (for plots/top-n and counts)
        working = norm.copy()
        if filter_type:
            requested = [t.strip().capitalize() for t in filter_type.split(",") if t.strip()]
            working = working[working["type"].isin(requested)]
            if working.empty:
                print(f"No issues found for Type(s): {requested} in {period_label}")
                # Still show what's inside 'Other' for context
                self._print_other_breakdown(norm_period_all, period_label=period_label, top_k=10)
                return

        if filter_labels:
            needles = [s.strip().lower() for s in filter_labels.split(",") if s.strip()]

            def _match_labels(lbls: List[str]) -> bool:
                low = [x.lower() for x in (lbls or [])]
                return any(any(n in lab for lab in low) for n in needles)

            mask = working["labels"].apply(_match_labels)
            working = working[mask]
            if working.empty:
                print(f"No issues found for raw label(s): {needles} in {period_label}")
                self._print_other_breakdown(norm_period_all, period_label=period_label, top_k=10)
                return

        # ---- Score + rank (on filtered working set)
        working["activity_score"] = working[event_cols].sum(axis=1)
        top = working.sort_values("activity_score", ascending=False).head(top_n).reset_index(drop=True)

        # ---- CLI Top-N table
        suffix = []
        if filter_type:   suffix.append(f"Types: {filter_type}")
        if filter_labels: suffix.append(f'Labels like: {filter_labels}')
        header_suffix = (" — " + " | ".join(suffix)) if suffix else ""
        print(f"\nMost Active Issues ({period_label}) — Top {len(top)}{header_suffix}\n")

        table_data = []
        for rank, row in enumerate(top.itertuples(index=False), start=1):
            labels_list = list(row.labels) if isinstance(row.labels, (list, tuple)) else []
            labels_str = ", ".join(labels_list[:4]) if labels_list else "-"
            title_short = (row.title[:80] + "…") if len(row.title) > 80 else row.title
            table_data.append([
                rank,
                f"#{row.issue_id}",
                title_short,
                labels_str,
                row.type,
                str(row.state).capitalize() if isinstance(row.state, str) else "-",
                f"{row.activity_score:.2f}",
            ])
        headers = ["Rank", "Issue ID", "Title", "Labels", "Type", "State", "Score"]
        print(tabulate(table_data, headers=headers, tablefmt="github"))
        print()

        # ---- CLI breakdown of "Other" (always computed from the full period set)
        self._print_other_breakdown(norm_period_all, period_label=period_label, top_k=10)

        # ---- Category % PIE (filtered view)
        figs = []
        if show_category_pie:
            issues_unique_cat = working[["issue_id", "type"]].drop_duplicates("issue_id")
            cat_table = self._prepare_category_table(issues_unique_cat)

            # CLI category summary
            cat_cli = (cat_table[["count", "pct"]]
                       .reset_index()
                       .rename(columns={"type": "Type", "count": "Count", "pct": "Percent"}))
            cat_cli["Percent"] = (cat_cli["Percent"] * 100).round(1)
            print(f"Category Share (% of issues) — {period_label}\n")
            print(tabulate(cat_cli, headers="keys", tablefmt="github"))
            print()

            figs.append(self._build_plot_category_pie(cat_table, period_label=period_label))

        # ---- Open vs Closed grouped BAR (filtered view)
        if show_category_state_bars:
            issues_unique_state = working[["issue_id", "type", "state"]].drop_duplicates("issue_id")
            figs.append(self._build_plot_category_state_bars(issues_unique_state, period_label=period_label))

        # ---- Top-N LOLLIPOP (filtered view)
        figs.append(self._build_plot_topn_lollipop(top, period_label=period_label, wrap_at=wrap_at))

        # Render all figures (one call)
        plt.show()

        return top


# ---------- Standalone CLI (optional) ----------
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("MostActiveCategoriesAnalyser")
    ap.add_argument("--data", type=str, default="./poetry_issues.json", help="Path to issues JSON")
    ap.add_argument("--year", type=int, required=False)
    ap.add_argument("--start-year", type=int, required=False)
    ap.add_argument("--end-year", type=int, required=False)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--wrap", type=int, default=60, help="Axis label wrap width")
    ap.add_argument("--type", type=str, required=False,
                    help="Filter by Type (Bug, Feature, Docs, Dependency, Infra, Other). Comma-separated allowed.")
    ap.add_argument("--labels", type=str, required=False,
                    help="Filter by raw labels (comma-separated, case-insensitive substring match).")
    args = ap.parse_args()

    MostActiveCategoriesAnalyser(data_path=args.data).run(
        year=args.year,
        start_year=args.start_year,
        end_year=args.end_year,
        top_n=args.top,
        wrap_at=args.wrap,
        filter_type=args.type,
        filter_labels=args.labels,
        show_category_pie=True,
        show_category_state_bars=True,
    )
