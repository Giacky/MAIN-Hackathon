"""Reset helper kept for CLI: python -m scripts.seed_demo_db"""

from services.demo_seed import seed_demo_reports
from utils.config import DATABASE_PATH

if __name__ == "__main__":
    lost_reports, found_reports = seed_demo_reports()
    print(f"Database reset: {DATABASE_PATH}")
    print(f"Lost ({len(lost_reports)}):")
    for report in lost_reports:
        print(f"  - {report.id}  {report.description[:60]}")
    print(f"Found ({len(found_reports)}):")
    for report in found_reports:
        print(f"  - {report.id}  {report.description[:60]}")
