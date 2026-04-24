"""
Eval runner — tests all models against all 30 cases.

Usage:
    cd D:/Workspace/nl2gh
    python -m evals.run
    python -m evals.run --model claude
    python -m evals.run --model gemini --model gemma
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Force UTF-8 and disable legacy Windows renderer (which can't handle non-ASCII)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Make src importable when run as script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2gh.providers.anthropic_provider import AnthropicProvider
from nl2gh.providers.google_provider import GoogleProvider
from nl2gh.providers.groq_provider import GroqProvider
from nl2gh.schemas import GitHubSearchArgs
from evals.metrics import score_case

load_dotenv()
app = typer.Typer()
console = Console(legacy_windows=False)

CASES_FILE = Path(__file__).parent / "cases.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"

ALL_MODELS = {
    "claude": lambda: AnthropicProvider(os.environ["ANTHROPIC_API_KEY"]),
    "gemini": lambda: GoogleProvider(os.environ["GOOGLE_API_KEY"], "gemini-2.5-pro"),
    "llama": lambda: GroqProvider(os.environ["GROQ_API_KEY"]),
}


def load_cases() -> list[dict]:
    cases = []
    with open(CASES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_model(model_name: str, cases: list[dict]) -> list[dict]:
    provider = ALL_MODELS[model_name]()
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]{model_name}[/cyan]", total=len(cases))

        for case in cases:
            predicted: GitHubSearchArgs | None = None
            error: str | None = None

            try:
                predicted = provider.query(case["nl"])
            except Exception as e:
                error = str(e)

            scored = score_case(case, predicted, error)
            scored["model"] = model_name
            results.append(scored)

            status = "[green]PASS[/green]" if scored["pass"] else "[red]FAIL[/red]"
            progress.console.print(f"  {status} {case['id']} — {case['nl'][:60]}")
            progress.advance(task)
            # Groq free tier: 6,000 TPM (~750 tokens/call → max 8 calls/min)
            sleep = 10.0 if model_name == "llama" else 0.3
            time.sleep(sleep)

    return results


def save_results(model_name: str, results: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{model_name}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    return out


@app.command()
def main(
    model: list[str] = typer.Option(
        list(ALL_MODELS.keys()), "--model", "-m", help="Model(s) to evaluate"
    ),
):
    cases = load_cases()
    console.print(f"[bold]Loaded {len(cases)} cases[/bold]")

    summary: dict[str, float] = {}

    for m in model:
        if m not in ALL_MODELS:
            console.print(f"[red]Unknown model: {m}[/red]")
            continue

        console.rule(f"[bold blue]{m}[/bold blue]")
        results = run_model(m, cases)
        out_path = save_results(m, results)

        passed = sum(1 for r in results if r["pass"])
        accuracy = passed / len(results) * 100
        summary[m] = accuracy
        console.print(
            f"\n[bold]{m}[/bold]: {passed}/{len(results)} passed — "
            f"[{'green' if accuracy >= 85 else 'red'}]{accuracy:.1f}%[/]\n"
        )
        console.print(f"[dim]Results saved to {out_path}[/dim]\n")

    if len(summary) > 1:
        console.rule("[bold]Summary[/bold]")
        for m, acc in summary.items():
            bar = "█" * int(acc / 5)
            color = "green" if acc >= 85 else "red"
            console.print(f"  {m:10s} [{color}]{bar:<20} {acc:.1f}%[/]")


if __name__ == "__main__":
    app()
