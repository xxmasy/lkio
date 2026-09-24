"""LKIO Ingestion CLI Tool
Provides command-line commands for scanning projects, viewing runs, and checking diffs.
"""

from datetime import datetime
from pathlib import Path
import sys
import uuid

# Ensure root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.table import Table
from sqlalchemy import select
import typer
from core.db.session import SessionLocal
from core.models.ingestion_run import IngestionRun
from core.models.project import Project
from ingestion.pipeline import run_all_projects_ingestion, run_project_ingestion

app = typer.Typer(help="LKIO Ingestion Command Line Interface")
console = Console()


@app.command("scan")
def scan_project(
    project: str = typer.Option(..., "--project", "-p", help="Project Key or UUID to scan"),
):
    """Scan a single registered project into the Knowledge Core."""
    console.print(f"[bold blue]Starting ingestion scan for project:[/bold blue] {project}")
    try:
        run = run_project_ingestion(project)
        console.print(f"[bold green]Scan completed successfully![/bold green] (Run ID: {run.id})")
        table = Table(title=f"Scan Summary: {project}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Status", run.status)
        table.add_row("HEAD After", run.head_after or "N/A")
        table.add_row("Files Seen", str(run.files_seen))
        table.add_row("Files Created / Updated", f"+{run.files_created} / ~{run.files_updated}")
        table.add_row("Files Deleted", str(run.files_deleted))
        table.add_row("Entities Created", str(run.entities_created))
        table.add_row("Relations Created", str(run.relations_created))
        table.add_row("Warnings", str(len(run.warnings)))
        table.add_row("Errors", str(len(run.errors)))
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Scan failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("scan-all")
def scan_all():
    """Scan all active registered projects with partial failure isolation."""
    console.print("[bold blue]Starting scan for all active projects...[/bold blue]")
    summary = run_all_projects_ingestion()
    table = Table(title="Batch Ingestion Summary")
    table.add_column("Project", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Files", style="green")
    table.add_column("Entities", style="magenta")
    table.add_column("Duration", style="yellow")

    for p_key, res in summary["runs"].items():
        st_color = "green" if res["status"] == "COMPLETED" else "red"
        table.add_row(
            p_key,
            f"[{st_color}]{res['status']}[/{st_color}]",
            str(res.get("files_seen", 0)),
            str(res.get("entities_created", 0)),
            f"{res.get('duration_s', 0):.2f}s",
        )

    console.print(table)
    console.print(f"Overall Status: [bold]{summary['status']}[/bold] ({summary['succeeded']}/{summary['total']} succeeded)")


@app.command("list-runs")
def list_runs(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of runs to list"),
):
    """List recent ingestion runs."""
    with SessionLocal() as db:
        runs = db.scalars(
            select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
        ).all()

        table = Table(title="Recent Ingestion Runs")
        table.add_column("Run ID", style="dim")
        table.add_column("Project", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Started", style="blue")
        table.add_column("HEAD After", style="yellow")
        table.add_column("Files", style="green")

        for r in runs:
            p_name = r.project.key if r.project else "Unknown"
            st_color = "green" if r.status == "COMPLETED" else ("yellow" if r.status == "RUNNING" else "red")
            table.add_row(
                str(r.id)[:8],
                p_name,
                f"[{st_color}]{r.status}[/{st_color}]",
                r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "",
                r.head_after[:8] if r.head_after else "N/A",
                str(r.files_seen),
            )
        console.print(table)


if __name__ == "__main__":
    app()
