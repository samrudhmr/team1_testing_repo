

"""
Starting point of the application. This module is invoked from
the command line to run the analyses.
"""

import argparse

import config
from example_analysis import ExampleAnalysis
from resolution_time_analyser import ResolutionTimeAnalyser
from top_user_activity import TopUserActivityAnalyser
from most_active_categories_analyser import MostActiveCategoriesAnalyser
from multi_area_impact import MultiAreaImpactAnalyzer

def parse_args():
    """
    Parses the command line arguments that were provided along
    with the python command. The --feature flag must be provided as
    that determines what analysis to run. Optionally, you can pass in
    a user and/or a label to run analysis focusing on specific issues.
    
    You can also add more command line arguments following the pattern
    below.
    """
    ap = argparse.ArgumentParser("run.py")
    
    # Required parameter specifying what analysis to run
    ap.add_argument('--feature', '-f', type=int, required=True,
                    help='Which of the three features to run')
    
    # Optional parameter for analyses focusing on a specific user (i.e., contributor)
    ap.add_argument('--user', '-u', type=str, required=False,
                    help='Optional parameter for analyses focusing on a specific user')
    
    # Optional parameter for analyses focusing on a specific label
    ap.add_argument('--label', '-l', type=str, required=False,
                    help='Optional parameter for analyses focusing on a specific label')
    
    ap.add_argument("--year", type=int, default=None,
                    help="Single year to analyze (e.g., 2024). Defaults to latest year in data.")
    ap.add_argument("--start-year", type=int, required=False,
                    help="Start of year range (use with --end-year).")
    ap.add_argument("--end-year", type=int, required=False,
                    help="End of year range (use with --start-year).")
    ap.add_argument("--top", type=int, default=5,
                    help="How many top issues to show (default: 5).")
    ap.add_argument("--type", type=str, required=False,
                    help="Filter by issue type: Bug, Feature, Docs, Dependency, Infra, Other. Comma-separated allowed.")
    ap.add_argument("--labels", type=str, required=False,
                    help="Filter by raw labels (comma-separated, case-insensitive substring).")

    
    return ap.parse_args()




# Parse feature to call from command line arguments
args = parse_args()
# Add arguments to config so that they can be accessed in other parts of the application
config.overwrite_from_args(args)
    
# Run the feature specified in the --feature flag
if args.feature == 0:
    ExampleAnalysis().run()
elif args.feature == 1:
    MostActiveCategoriesAnalyser().run(
       year=args.year,
        start_year=args.start_year,
        end_year=args.end_year,
        top_n=args.top,
        filter_type=args.type,
        filter_labels=args.labels,
    )
elif args.feature == 2:
    MultiAreaImpactAnalyzer().run()
elif args.feature == 3:
    TopUserActivityAnalyser().run()
elif args.feature == 4:
    ResolutionTimeAnalyser().run()
else:
    print('Need to specify which feature to run with --feature flag.')
