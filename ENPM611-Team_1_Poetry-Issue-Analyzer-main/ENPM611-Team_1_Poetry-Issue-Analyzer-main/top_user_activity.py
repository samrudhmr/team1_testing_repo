from typing import List, Tuple, Dict
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from collections import Counter

import config
from data_loader import DataLoader
from model import Issue, Event


class TopUserActivityAnalyser:
    """
    Feature: Top Users Activity

    Analyze  GitHub contributors' activity levels based on issues opened,
    issues closed, and comments made. Ranks contributors by a combined activity score.
    
    Total Activity Score per contributor =
        (# issues opened) + (# issues closed) + (# comments made)

    Data sources:
      - ISSUE.creator_login (or creator/user.login)  -> opened
      - EVENT.actor_login where event_type in {'closed','commented'} -> closed/commented
    """

    def __init__(self) -> None:
        """Initialize configuration, data loader, and issue list."""
        config._init_config()
        self.issues: List[Issue] = DataLoader().get_issues()

    def run(self,
            top_n: int = 5,
            credit_creator_when_closed_unknown: bool = True) -> None:
        """
        Entry point. Computes activity, prints the top list, and plots the bar chart.
        """
        df = self._compute_activity_dataframe(
            credit_creator_when_closed_unknown=credit_creator_when_closed_unknown
        )

        # Rank & take Top-N
        top_df = (df.sort_values("score", ascending=False)
                    .head(top_n)
                    .reset_index(drop=True))

        # Console output
        print("\nTop contributors:")
        for i, row in top_df.iterrows():
            print(f"{i+1:>2}. {row['user']:<20s}  "
                  f"score={int(row['score']):3d}  "
                  f"(opened={int(row['opened'])}, "
                  f"closed={int(row['closed'])}, "
                  f"commented={int(row['commented'])})")

        # Visual
        self._plot_top_users(top_df, title=f"Top {len(top_df)} Active Contributors")

    
    def _compute_activity_dataframe(
        self, credit_creator_when_closed_unknown: bool
    ) -> pd.DataFrame:
        """
        Build a DataFrame with columns:
            user | opened | closed | commented | score
        """
        opened = Counter()
        closed = Counter()
        commented = Counter()

        # 1) Opened (from issues' creators)
        for iss in self.issues:
            creator = self._issue_creator(iss)
            if creator:
                opened[creator] += 1

        # 2) Closed / Commented (prefer per-issue events if present)
        for iss in self.issues:
            has_any_events = hasattr(iss, "events") and isinstance(iss.events, list)

            if has_any_events and iss.events:
                for ev in iss.events:
                    actor = self._event_actor(ev)
                    etype = self._event_type(ev)
                    if not actor or not etype:
                        continue
                    if etype == "closed":
                        closed[actor] += 1
                    elif etype == "commented":
                        commented[actor] += 1
            else:
                if credit_creator_when_closed_unknown and self._issue_state(iss) == "closed":
                    creator = self._issue_creator(iss)
                    if creator:
                        closed[creator] += 1

        # 3) Merge into a DataFrame
        contributors = set(opened) | set(closed) | set(commented)
        rows: List[Dict[str, int | str]] = []
        for u in contributors:
            row = {
                "user": u,
                "opened": opened[u],
                "closed": closed[u],
                "commented": commented[u],
            }
            row["score"] = row["opened"] + row["closed"] + row["commented"]
            rows.append(row)

        if not rows:
            return pd.DataFrame(columns=["user", "opened", "closed", "commented", "score"])

        return pd.DataFrame(rows)

    def _plot_top_users(self, top_df: pd.DataFrame, title: str) -> None:
        """
        Bar chart without badges. Shows total score and a compact (o/c/cm) breakdown above each bar.
        """
        if top_df.empty:
            print("No data to plot.")
            return

        users = top_df["user"].tolist()
        scores = top_df["score"].tolist()
        opened = top_df["opened"].tolist()
        closed = top_df["closed"].tolist()
        commented = top_df["commented"].tolist()

        plt.figure(figsize=(9, 5))
        bars = plt.bar(users, scores)

        plt.title(f"{title}\n(opened + closed + commented)")
        plt.xlabel("Contributor")
        plt.ylabel("Total Activity Score")

        y_off = max(scores) * 0.03 if scores else 0.5

        for i, bar in enumerate(bars):
            label = f"{int(scores[i])} (o:{int(opened[i])} c:{int(closed[i])} cm:{int(commented[i])})"
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + y_off,
                label,
                ha="center",
                va="bottom",
                fontsize=9,
            )

        plt.tight_layout()
        plt.show()


# -- Helper methods to tolerate schema differences --
    @staticmethod
    def _issue_creator(issue: Issue) -> str | None:
        """
        Support multiple shapes:
          issue.creator_login | issue.creator | issue.user.login
        """
        # dataclass/obj + dict hybrid tolerance:
        val = getattr(issue, "creator_login", None) or getattr(issue, "creator", None)
        if val:
            return val
        user = getattr(issue, "user", None) or {}
        return getattr(user, "login", None) if hasattr(user, "login") else user.get("login") if isinstance(user, dict) else None

    @staticmethod
    def _issue_state(issue: Issue) -> str:
        state = getattr(issue, "state", None)
        if not state and isinstance(issue, dict):
            state = issue.get("state")
        return (state or "").lower()

    @staticmethod
    def _event_type(ev: Event) -> str:
        et = getattr(ev, "event_type", None) or getattr(ev, "type", None)
        if not et and isinstance(ev, dict):
            et = ev.get("event_type") or ev.get("type")
        return (et or "").lower()

    @staticmethod
    def _event_actor(ev: Event) -> str | None:
        # actor_login | actor.login
        actor = getattr(ev, "actor_login", None)
        if actor:
            return actor
        # nested actor object
        act = getattr(ev, "actor", None) or {}
        if hasattr(act, "login"):
            return act.login
        if isinstance(act, dict):
            return act.get("login")
        # dict shape
        if isinstance(ev, dict):
            return ev.get("actor_login") or ((ev.get("actor") or {}).get("login"))
        return None


if __name__ == "__main__":
    TopUserActivityAnalyser().run()
