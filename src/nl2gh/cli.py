import json
import os
import sys
from enum import Enum
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Windows terminals often default to cp1252; force UTF-8 so non-ASCII output is readable.
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .executor import GitHubAPIError, GitHubExecutor
from .providers.anthropic_provider import AnthropicProvider
from .providers.google_provider import GoogleProvider
from .schemas import GitHubSearchResult

load_dotenv()

app = typer.Typer(help="Natural language GitHub search — powered by LLMs")
console = Console()


class ModelChoice(str, Enum):
    claude = "claude"
    gemini = "gemini"
    gemma = "gemma"


class OutputFormat(str, Enum):
    table = "table"
    json = "json"


def _get_provider(model: ModelChoice):
    if model == ModelChoice.claude:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            typer.echo("ANTHROPIC_API_KEY not set", err=True)
            raise typer.Exit(1)
        return AnthropicProvider(key)

    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        typer.echo("GOOGLE_API_KEY not set", err=True)
        raise typer.Exit(1)

    model_id = "gemini-2.5-pro" if model == ModelChoice.gemini else "gemma-3-27b-it"
    return GoogleProvider(key, model_id)


@app.command()
def main(
    query: Annotated[str, typer.Argument(help="Natural language search query")],
    model: Annotated[ModelChoice, typer.Option("--model", "-m", help="LLM to use")] = ModelChoice.claude,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=30, help="Max results")] = 10,
    output: Annotated[OutputFormat, typer.Option("--output", "-o", help="Output format")] = OutputFormat.table,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show query without executing")] = False,
):
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token and not dry_run:
        typer.echo("GITHUB_TOKEN not set", err=True)
        raise typer.Exit(1)

    provider = _get_provider(model)

    with console.status(f"[bold blue]Building query with {provider.model_id}..."):
        try:
            args = provider.query(query)
        except Exception as e:
            console.print(f"[red]LLM error:[/red] {e}")
            raise typer.Exit(1)

    args.limit = limit

    if args.clarification_needed:
        console.print(f"[yellow]Clarification needed:[/yellow] {args.clarification_needed}")
        console.print("[dim]Proceeding with best-effort defaults...[/dim]")
        if not args.sort:
            args.sort = "stars"

    executor = GitHubExecutor(github_token)
    warnings = executor.validate(args)
    for w in warnings:
        console.print(f"[yellow]Warning:[/yellow] {w}")

    q_str = executor.build_query_string(args)
    if not q_str:
        # GitHub Search API requires a non-empty q; use a catch-all minimum qualifier.
        args.stars = args.stars or ">0"
        q_str = executor.build_query_string(args)

    console.print(f"[dim]type:[/dim] {args.search_type}  [dim]query:[/dim] [cyan]{q_str}[/cyan]")

    if dry_run:
        return

    with console.status("[bold blue]Fetching results from GitHub..."):
        try:
            result = executor.search(args)
        except GitHubAPIError as e:
            console.print(f"[red]GitHub API error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Request failed:[/red] {e}")
            raise typer.Exit(1)

    console.print(
        f"[bold]Found [green]{result.total_count:,}[/green] total results "
        f"(showing {len(result.items)})[/bold]"
    )

    if output == OutputFormat.json:
        rprint(json.dumps(result.items, indent=2, ensure_ascii=False))
    else:
        _render_table(result)


def _render_table(result: GitHubSearchResult) -> None:
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)

    if result.search_type == "repositories":
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Stars", justify="right")
        table.add_column("Language")
        table.add_column("Description", max_width=55)
        for item in result.items:
            table.add_row(
                item.get("full_name", ""),
                f"{item.get('stargazers_count', 0):,}",
                item.get("language") or "—",
                item.get("description") or "—",
            )

    elif result.search_type == "issues":
        table.add_column("Title", style="cyan", max_width=45)
        table.add_column("Repo")
        table.add_column("State")
        table.add_column("Created")
        for item in result.items:
            repo_url = item.get("repository_url", "")
            repo = "/".join(repo_url.split("/")[-2:]) if repo_url else "—"
            table.add_row(
                item.get("title", ""),
                repo,
                item.get("state", ""),
                (item.get("created_at") or "")[:10],
            )

    elif result.search_type == "users":
        table.add_column("Username", style="cyan")
        table.add_column("Type")
        table.add_column("URL")
        for item in result.items:
            table.add_row(
                item.get("login", ""),
                item.get("type", ""),
                item.get("html_url", ""),
            )

    else:  # code
        table.add_column("File", style="cyan")
        table.add_column("Repository")
        table.add_column("URL")
        for item in result.items:
            table.add_row(
                item.get("name", ""),
                item.get("repository", {}).get("full_name", ""),
                item.get("html_url", ""),
            )

    console.print(table)


if __name__ == "__main__":
    app()
