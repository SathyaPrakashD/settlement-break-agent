"""Eval suite runner. Composes all layers into a single CLI-callable run."""
from rich.console import Console
from rich.table import Table

console = Console()


def run_all(layer: str = "all") -> None:
    """Run the specified eval layer(s)."""
    if layer in ("retrieval", "all"):
        _run_retrieval()
    if layer in ("synthesis", "all"):
        _run_synthesis_judge()
    if layer in ("deterministic", "all"):
        _note_deterministic()


def _run_retrieval() -> None:
    from evals.retrieval_metrics import run_retrieval_eval

    console.print("[bold cyan]── Layer 2: retrieval metrics ──[/bold cyan]")
    metrics = run_retrieval_eval()

    table = Table(border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Score", justify="right")
    for name, score in metrics.items():
        table.add_row(name, f"{score:.4f}")
    console.print(table)
    console.print()


def _run_synthesis_judge() -> None:
    from evals.synthesis_judge import run_synthesis_judge

    console.print("[bold cyan]── Layer 3: synthesis quality (LLM-as-judge) ──[/bold cyan]")
    results = run_synthesis_judge()

    table = Table(border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    for name, value in results.items():
        table.add_row(name, str(value))
    console.print(table)
    console.print()


def _note_deterministic() -> None:
    console.print("[bold cyan]── Layer 1: deterministic checks ──[/bold cyan]")
    console.print(
        "Layer 1 runs per-investigation inline. See evals/deterministic.py for the checks.\n"
    )


if __name__ == "__main__":
    run_all()
