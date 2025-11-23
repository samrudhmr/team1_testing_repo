import json
from datetime import datetime, timedelta
from dateutil import parser
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

from data_loader import DataLoader


class MultiAreaImpactAnalyzer:
    def __init__(self):
        self.data_loader = DataLoader()
        
    # Get all lables who start with "area/"
    def _get_area_labels(self, labels: List[str]) -> List[str]:
        area_labels = []
        for label in labels:
            if isinstance(label, str) and label.lower().startswith('area/'):
                area_labels.append(label)
        return area_labels
    
    # Timeline input from user
    def _get_timeline_selection(self) -> int:
        print("\n" + "="*50)
        print("MULTI-AREA IMPACT ANALYZER")
        print("="*50)
        print("\nSelect timeline for analysis:")
        print("1. Last 3 months")
        print("2. Last 6 months") 
        print("3. Last 12 months")
        print("4. Last 18 months")
        print("5. Last 24 months")
        print("6. All time")
        
        while True:
            try:
                choice = input("\nEnter your choice (1-6): ").strip()
                timeline_map = {
                    '1': 3,
                    '2': 6, 
                    '3': 12,
                    '4': 18,
                    '5': 24,
                    '6': 0  # 0 means all time
                }
                
                if choice in timeline_map:
                    return timeline_map[choice]
                else:
                    print("Invalid choice. Please enter a number between 1-6.")
            # handling ctrl + c
            except KeyboardInterrupt:
                print("\nAnalysis cancelled.")
                return None
            # If the input is not between
            except Exception as e:
                print(f"Invalid input. Please enter a number between 1-6.")
    
    # filter based on input
    def _filter_issues_by_timeline(self, issues: List, months: int) -> List:
        
        # All issues
        if months == 0:
            return issues
            
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        filtered_issues = []
        
        for issue in issues:
            try:
                if issue.created_date and issue.created_date >= cutoff_date:
                    filtered_issues.append(issue)
            except:
                # If date parsing fails, include the issue to be safe
                filtered_issues.append(issue)
                
        return filtered_issues
    
    def _analyze_multi_area_issues(self, issues: List) -> Tuple[List[Dict], Dict[str, int]]:
        multi_area_issues = []
        area_impact_count = {}
        
        for issue in issues:
            area_labels = self._get_area_labels(issue.labels)
            
            if len(area_labels) > 1:  # Multi-area impact
                issue_data = {
                    'number': issue.number,
                    'title': issue.title,
                    'area_labels': area_labels,
                    'area_count': len(area_labels),
                    'state': issue.state.value if issue.state else 'unknown',
                    'created_date': issue.created_date,
                    'creator': issue.creator
                }
                multi_area_issues.append(issue_data)
                
                # Count impact per area
                for area in area_labels:
                    area_impact_count[area] = area_impact_count.get(area, 0) + 1
        
        # Sort by number of areas impacted (highest first)
        multi_area_issues.sort(key=lambda x: x['area_count'], reverse=True)
        
        return multi_area_issues, area_impact_count
    
    def _create_charts(self, multi_area_issues: List[Dict], area_impact_count: Dict[str, int], timeline_months: int):
        """
        Create matplotlib charts for visualization.
        """
        if not multi_area_issues:
            return
            
        timeline_text = f"Last {timeline_months} months" if timeline_months > 0 else "All time"
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Multi-Area Impact Analysis - {timeline_text}', fontsize=16, fontweight='bold')
        
        # 1. Top 10 Areas by Multi-Area Impact Count
        sorted_areas = sorted(area_impact_count.items(), key=lambda x: x[1], reverse=True)[:10]
        if sorted_areas:
            areas, counts = zip(*sorted_areas)
            areas = [area.replace('area/', '') for area in areas]  # Clean up labels
            
            ax1.barh(range(len(areas)), counts, color='skyblue', edgecolor='navy', alpha=0.7)
            ax1.set_yticks(range(len(areas)))
            ax1.set_yticklabels(areas)
            ax1.set_xlabel('Number of Multi-Area Issues')
            ax1.set_title('Top 10 Most Impacted Areas')
            ax1.grid(axis='x', alpha=0.3)
            
            # Add value labels on bars
            for i, count in enumerate(counts):
                ax1.text(count + 0.1, i, str(count), va='center', fontweight='bold')
        
        # 2. Distribution of Area Count per Issue
        area_counts = [issue['area_count'] for issue in multi_area_issues]
        if area_counts:
            ax2.hist(area_counts, bins=range(2, max(area_counts) + 2), 
                    color='lightcoral', edgecolor='darkred', alpha=0.7)
            ax2.set_xlabel('Number of Areas per Issue')
            ax2.set_ylabel('Number of Issues')
            ax2.set_title('Distribution of Multi-Area Impact')
            ax2.grid(axis='y', alpha=0.3)
        
        # 3. Issue State Distribution
        states = [issue['state'] for issue in multi_area_issues]
        if states:
            state_counts = pd.Series(states).value_counts()
            colors = ['lightgreen' if state == 'closed' else 'orange' for state in state_counts.index]
            
            ax3.pie(state_counts.values, labels=[s.capitalize() for s in state_counts.index], 
                   autopct='%1.1f%%', colors=colors, startangle=90)
            ax3.set_title('Multi-Area Issues by State')
        
        # 4. Timeline of Multi-Area Issues
        issues_with_dates = [issue for issue in multi_area_issues if issue['created_date']]
        if issues_with_dates:
            dates = [issue['created_date'] for issue in issues_with_dates]
            df = pd.DataFrame({'date': dates})
            df['month'] = df['date'].dt.to_period('M')
            monthly_counts = df['month'].value_counts().sort_index()
            
            ax4.plot(monthly_counts.index.astype(str), monthly_counts.values, 
                    marker='o', linewidth=2, markersize=6, color='purple')
            ax4.set_xlabel('Month')
            ax4.set_ylabel('Number of Multi-Area Issues')
            ax4.set_title('Multi-Area Issues Over Time')
            ax4.tick_params(axis='x', rotation=45)
            ax4.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def run(self):
        # Get timeline selection from user
        timeline_months = self._get_timeline_selection()
        if timeline_months is None:
            return
        
        print(f"\nLoading issues data...")
        
        all_issues = self.data_loader.get_issues()
        filtered_issues = self._filter_issues_by_timeline(all_issues, timeline_months)
        
        timeline_text = f"last {timeline_months} months" if timeline_months > 0 else "all time"
        print(f"Analyzing {len(filtered_issues)} issues from the {timeline_text}...")
        
        multi_area_issues, area_impact_count = self._analyze_multi_area_issues(filtered_issues)
        self._create_charts(multi_area_issues, area_impact_count, timeline_months)
        
        return multi_area_issues, area_impact_count


if __name__ == "__main__":
    analyzer = MultiAreaImpactAnalyzer()
    analyzer.run()