"""
Generate a markdown comparison report from eval results.

Usage:
    python -m evals.report
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

RESULTS_DIR = Path(__file__).parent / "results"


def load_results(model: str) -> list[dict]:
    path = RESULTS_DIR / f"{model}.jsonl"
    if not path.exists():
        return []
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def generate_report(models: list[str]) -> str:
    all_results: dict[str, list[dict]] = {}
    for m in models:
        all_results[m] = load_results(m)
        if not all_results[m]:
            print(f"Warning: no results found for {m}")

    lines = ["# nl2gh Eval Report\n"]

    # Overall accuracy table
    lines.append("## Overall Accuracy\n")
    lines.append("| Model | Passed | Total | Accuracy |")
    lines.append("|-------|--------|-------|----------|")
    for m, results in all_results.items():
        if not results:
            continue
        passed = sum(1 for r in results if r["pass"])
        acc = passed / len(results) * 100
        threshold = "✅" if acc >= 85 else "❌"
        lines.append(f"| {m} | {passed} | {len(results)} | {acc:.1f}% {threshold} |")

    # Per-category breakdown
    lines.append("\n## Per-Category Accuracy\n")
    categories = sorted(set(r.get("category", "unknown") for rlist in all_results.values() for r in rlist))
    header = "| Category | " + " | ".join(models) + " |"
    sep = "|----------|" + "---------|" * len(models)
    lines.append(header)
    lines.append(sep)

    for cat in categories:
        row = f"| {cat} |"
        for m in models:
            cat_results = [r for r in all_results.get(m, []) if r.get("category") == cat]
            if not cat_results:
                row += " — |"
            else:
                passed = sum(1 for r in cat_results if r["pass"])
                row += f" {passed}/{len(cat_results)} ({passed/len(cat_results)*100:.0f}%) |"
        lines.append(row)

    # Per-difficulty breakdown
    lines.append("\n## Per-Difficulty Accuracy\n")
    difficulties = sorted(set(r.get("difficulty", 0) for rlist in all_results.values() for r in rlist))
    header = "| Difficulty | " + " | ".join(models) + " |"
    sep = "|------------|" + "---------|" * len(models)
    lines.append(header)
    lines.append(sep)

    for diff in difficulties:
        row = f"| {diff} |"
        for m in models:
            diff_results = [r for r in all_results.get(m, []) if r.get("difficulty") == diff]
            if not diff_results:
                row += " — |"
            else:
                passed = sum(1 for r in diff_results if r["pass"])
                row += f" {passed}/{len(diff_results)} |"
        lines.append(row)

    # Failure analysis
    lines.append("\n## Common Failure Patterns\n")
    for m, results in all_results.items():
        failures = [r for r in results if not r["pass"]]
        if not failures:
            lines.append(f"### {m}: no failures 🎉\n")
            continue
        lines.append(f"### {m} — {len(failures)} failures\n")
        for r in failures:
            details_failed = [k for k, v in r.get("details", {}).items() if not v]
            lines.append(
                f"- **{r['id']}** ({r.get('category')}) — "
                f"failed fields: `{', '.join(details_failed)}`  \n"
                f"  NL: *{r.get('nl', '')}*"
            )
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    models = ["claude", "gemini", "llama"]
    report = generate_report(models)
    out = RESULTS_DIR / "report.md"
    out.write_text(report, encoding="utf-8")
    print(f"Report written to {out}")
    print(report)
