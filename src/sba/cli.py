"""Command-line interface.

Single entry point for: generating corpus, indexing, running an investigation,
running evals. Wired up via `[project.scripts] sba = "sba.cli:app"` in pyproject.toml.

Once installed:
    uv run sba generate-corpus --count 500
    uv run sba index
    uv run sba investigate --trade-id TRD-XXXXXX
    uv run sba eval
"""
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sba.config import settings

app = typer.Typer(
    name="sba",
    help="Settlement Break Investigation Agent — RAG-first, agent-later.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.command(name="generate-corpus")
def generate_corpus_cmd(
    count: int = typer.Option(500, "--count", "-n", help="Number of breaks to generate"),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed for reproducibility"),
    output: Path = typer.Option(
        None, "--output", "-o", help="Output JSONL path (default: data/breaks_corpus.jsonl)"
    ),
) -> None:
    """Generate a synthetic corpus of N historical breaks."""
    from sba.synthetic.generator import generate_corpus

    output_path = output or settings.corpus_path
    console.print(f"[bold cyan]Generating {count} synthetic breaks[/bold cyan]")
    console.print(f"  → {output_path}")
    console.print(f"  → seed: {seed}\n")

    generate_corpus(count=count, output_path=output_path, seed=seed)

    console.print(f"\n[bold green]✓[/bold green] Corpus written: {output_path}")


@app.command(name="index")
def index_cmd() -> None:
    """Index the corpus into Qdrant (dense) + BM25 (sparse)."""
    from sba.retrieval.indexer import index_corpus

    console.print("[bold cyan]Indexing corpus[/bold cyan]\n")
    index_corpus()


@app.command(name="investigate")
def investigate_cmd(
    trade_id: str = typer.Option(..., "--trade-id", "-t", help="Trade ID to investigate"),
    show_retrieval: bool = typer.Option(
        True, "--show-retrieval/--no-show-retrieval", help="Show retrieved cases"
    ),
) -> None:
    """Investigate a break by trade_id.

    For v0.1: pulls the break from the corpus (treating it as an unseen break)
    and runs it through the full retrieve → rerank → synthesise pipeline.
    """
    from sba.retrieval.hybrid import HybridRetriever
    from sba.retrieval.indexer import load_corpus
    from sba.retrieval.rerank import Reranker
    from sba.synthesis.synthesizer import Synthesizer
    from sba.synthetic.schemas import BreakNotification

    # Load the trade from the corpus (in v0.2+ this becomes an MCP tool call)
    breaks = load_corpus(settings.corpus_path)
    matching = [b for b in breaks if b.trade_id == trade_id]
    if not matching:
        console.print(f"[bold red]✗[/bold red] Trade ID {trade_id} not found in corpus")
        raise typer.Exit(code=1)

    brk = matching[0]
    notification = BreakNotification(
        trade_id=brk.trade_id,
        category_suspected=None,
        severity=brk.severity,
        product_type=brk.product_type,
        currency=brk.currency,
        counterparty_id=brk.counterparty_id,
        exception_code=brk.exception_code,
        trade_date=brk.trade_date,
        settlement_date=brk.settlement_date,
        notional_usd=brk.notional_usd,
        analyst_narrative=brk.analyst_narrative,
    )

    console.print(Panel(notification.analyst_narrative, title=f"Break: {trade_id}", border_style="yellow"))

    # ─── Retrieve ───
    console.print("\n[bold cyan]Retrieving similar cases...[/bold cyan]")
    retriever = HybridRetriever()
    candidates = retriever.search(notification.analyst_narrative)

    # ─── Rerank ───
    reranker = Reranker()
    top_cases = reranker.rerank(notification.analyst_narrative, candidates)

    if show_retrieval:
        table = Table(title=f"Top {len(top_cases)} retrieved cases", border_style="cyan")
        table.add_column("Rank", style="bold")
        table.add_column("Case ID")
        table.add_column("Category")
        table.add_column("Score")
        for i, case in enumerate(top_cases, start=1):
            table.add_row(
                str(i),
                case.case_id,
                case.payload.get("category", "?"),
                f"{case.score:.4f}",
            )
        console.print(table)

    # ─── Synthesise ───
    console.print("\n[bold cyan]Synthesising remediation...[/bold cyan]")
    synthesiser = Synthesizer()
    remediation = synthesiser.synthesize(notification, top_cases)

    # ─── Render ───
    console.print(
        Panel(
            f"[bold]Root cause:[/bold] {remediation.root_cause_category.value}\n"
            f"[bold]Confidence:[/bold] {remediation.confidence:.2f}\n\n"
            f"[bold]Explanation:[/bold]\n{remediation.root_cause_explanation}\n\n"
            f"[bold]Recommended actions:[/bold]\n"
            + "\n".join(f"  {i}. {a}" for i, a in enumerate(remediation.recommended_actions, 1))
            + f"\n\n[bold]Citations:[/bold] {', '.join(remediation.cited_case_ids)}",
            title="Drafted Remediation",
            border_style="green",
        )
    )


@app.command(name="eval")
def eval_cmd(
    layer: str = typer.Option(
        "all",
        "--layer",
        "-l",
        help="Which eval layer to run: deterministic | retrieval | synthesis | all",
    ),
) -> None:
    """Run the eval suite against the golden set."""
    from evals.run_evals import run_all

    console.print(f"[bold cyan]Running eval layer: {layer}[/bold cyan]\n")
    run_all(layer=layer)


if __name__ == "__main__":
    app()
