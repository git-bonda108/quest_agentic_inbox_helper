"""Join the daily logs into one file for the quest page's single log slot."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
days = sorted((ROOT / "logs").glob("day-*.md"))
header = (
    "# Daily logs\n\n"
    "One short log per day of the quest, joined from `logs/`. "
    "Run-by-run detail is in `evals/README.md`.\n"
)
body = "\n---\n\n".join(path.read_text(encoding="utf-8").strip() + "\n" for path in days)
(ROOT / "submission" / "logs.md").write_text(f"{header}\n---\n\n{body}", encoding="utf-8")
print(f"joined {len(days)} logs into submission/logs.md")
