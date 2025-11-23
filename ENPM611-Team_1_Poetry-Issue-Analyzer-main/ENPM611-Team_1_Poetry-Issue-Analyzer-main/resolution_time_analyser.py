from typing import List
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from collections import Counter

import config
from data_loader import DataLoader
from model import Issue, Event


class ResolutionTimeAnalyser:
    """
    Analyzes how specific GitHub issue events (like labeling or assignment)
    affect the time taken to resolve issues. Produces visual correlations
    between event timing and resolution duration.
    """

    def __init__(self):
        """Initialize configuration, data loader, and issue list."""
        config._init_config()
        self.issues: List[Issue] = DataLoader().get_issues()

    def run(self):
        """Entry point for the analysis."""
        self.analyze_event_impact_on_resolution_time()
 
    def analyze_event_impact_on_resolution_time(self):
        """
        Analyze how early or late key events (like 'labeled' or 'assigned')
        occur in an issue's lifecycle and visualize their impact on resolution time.
        """
        event_impact_data = []

        for issue in self.issues:
            if issue.state not in ("open", "closed"):
                continue

            event_types = [e.event_type for e in issue.events if e.event_type]
            event_dates = [e.event_date for e in issue.events if e.event_date]

            if len(event_types) != len(event_dates) or not issue.created_date:
                continue

            resolution_time = (
                (issue.updated_date - issue.created_date).days
                if issue.updated_date
                else np.nan
            )

            labeled_time, assigned_time = self._extract_event_times(
                issue, event_types, event_dates
            )

            event_impact_data.append(
                {
                    "resolution_time": resolution_time,
                    "labeled_time": labeled_time,
                    "assigned_time": assigned_time,
                }
            )

        # Convert to DataFrame for analysis
        event_impact_df = pd.DataFrame(event_impact_data)

        # Plot and analyze
        self._plot_event_impact(
            event_impact_df,
            event_col="labeled_time",
            color="darkorange",
            title="Impact of Labeling Time on Issue Resolution Time",
        )
        self._plot_event_impact(
            event_impact_df,
            event_col="assigned_time",
            color="seagreen",
            title="Impact of Assignment Time on Issue Resolution Time",
        )
 
    def _extract_event_times(self, issue: Issue, event_types: List[str], event_dates: List):
        """
        Extracts the first occurrence time (in days since creation) for 'labeled'
        and 'assigned' events in the issue's lifecycle.
        """
        labeled_time = np.nan
        assigned_time = np.nan

        for e_type, e_date in zip(event_types, event_dates):
            days_since_creation = (e_date - issue.created_date).days
            if e_type == "labeled" and np.isnan(labeled_time):
                labeled_time = days_since_creation
            elif e_type == "assigned" and np.isnan(assigned_time):
                assigned_time = days_since_creation

        return labeled_time, assigned_time

    def _plot_event_impact(self, df: pd.DataFrame, event_col: str, color: str, title: str):
        """
        Generates a scatter plot showing how the timing of a specific event
        (e.g., labeled/assigned) affects issue resolution time.
        """
        if event_col not in df.columns:
            print(f"No column '{event_col}' found in data.")
            return

        filtered_df = df.dropna(subset=[event_col, "resolution_time"])
        if filtered_df.empty:
            print(f"No valid data for '{event_col}' to plot.")
            return

        plt.style.use("seaborn-v0_8-whitegrid")
        plt.figure(figsize=(10, 6))
        plt.scatter(
            filtered_df[event_col],
            filtered_df["resolution_time"],
            color=color,
            alpha=0.65,
            edgecolors="black",
            linewidths=0.5,
            label=f"{event_col.replace('_', ' ').title()} vs Resolution Time",
        )
 
        try:
            m, b = np.polyfit(
                filtered_df[event_col], filtered_df["resolution_time"], 1
            )
            plt.plot(
                filtered_df[event_col],
                m * filtered_df[event_col] + b,
                color="gray",
                linestyle="--",
                linewidth=1.2,
                label="Trendline",
            )
        except Exception:
            pass

        plt.title(title, fontsize=14, fontweight="bold", pad=15)
        plt.xlabel("Days Since Creation to Event", fontsize=12)
        plt.ylabel("Resolution Time (Days)", fontsize=12)
        plt.legend()
        plt.tight_layout()
        plt.show()

 
if __name__ == "__main__":
    ResolutionTimeAnalyser().run()
