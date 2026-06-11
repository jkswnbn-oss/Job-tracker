#!/usr/bin/env python3
"""Job application tracker CLI."""

import sqlite3
import os
from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

DB_PATH = Path(os.environ.get("JOBS_DB", Path.home() / ".jobs.db"))

STAGES = [
    "wishlist",
    "applied",
    "phone_screen",
    "interview",
    "offer",
    "rejected",
    "accepted",
    "withdrawn",
]

STAGE_COLORS = {
    "wishlist": "dim",
    "applied": "cyan",
    "phone_screen": "blue",
    "interview": "yellow",
    "offer": "green",
    "rejected": "red",
    "accepted": "bold green",
    "withdrawn": "dim",
}

console = Console()


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company     TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            stage       TEXT    NOT NULL DEFAULT 'applied',
            applied_on  TEXT,
            updated_on  TEXT    NOT NULL,
            url         TEXT,
            notes       TEXT
        )
    """)
    conn.commit()
    return conn


@click.group()
def cli():
    """Track your job applications."""


@cli.command("add")
@click.option("--company", "-c", required=True, help="Company name")
@click.option("--role", "-r", required=True, help="Role / job title")
@click.option("--stage", "-s", default="applied",
              type=click.Choice(STAGES, case_sensitive=False),
              show_default=True, help="Application stage")
@click.option("--applied-on", "-d", default=None,
              help="Date applied (YYYY-MM-DD). Defaults to today.")
@click.option("--url", "-u", default=None, help="Job posting URL")
@click.option("--notes", "-n", default=None, help="Free-form notes")
def add_cmd(company, role, stage, applied_on, url, notes):
    """Add a new job application."""
    today = str(date.today())
    applied_on = applied_on or today
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO applications (company, role, stage, applied_on, updated_on, url, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (company, role, stage.lower(), applied_on, today, url, notes),
        )
        app_id = cur.lastrowid
    console.print(f"[green]Added[/green] [bold]{company}[/bold] — {role} "
                  f"(id [cyan]{app_id}[/cyan], stage: {stage})")


@cli.command("update")
@click.argument("app_id", type=int)
@click.option("--stage", "-s", default=None,
              type=click.Choice(STAGES, case_sensitive=False), help="New stage")
@click.option("--company", "-c", default=None, help="Update company name")
@click.option("--role", "-r", default=None, help="Update role")
@click.option("--notes", "-n", default=None, help="Replace notes")
@click.option("--url", "-u", default=None, help="Update URL")
def update_cmd(app_id, stage, company, role, notes, url):
    """Update an existing application by ID."""
    fields = {}
    if stage:
        fields["stage"] = stage.lower()
    if company:
        fields["company"] = company
    if role:
        fields["role"] = role
    if notes is not None:
        fields["notes"] = notes
    if url is not None:
        fields["url"] = url

    if not fields:
        console.print("[yellow]Nothing to update — pass at least one option.[/yellow]")
        raise SystemExit(1)

    fields["updated_on"] = str(date.today())
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [app_id]

    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE applications SET {set_clause} WHERE id = ?", values
        )
        if cur.rowcount == 0:
            console.print(f"[red]No application found with id {app_id}[/red]")
            raise SystemExit(1)

    console.print(f"[green]Updated[/green] application [cyan]{app_id}[/cyan]: "
                  + ", ".join(f"{k}={v}" for k, v in fields.items() if k != "updated_on"))


@cli.command("list")
@click.option("--stage", "-s", default=None,
              type=click.Choice(STAGES, case_sensitive=False), help="Filter by stage")
@click.option("--company", "-c", default=None, help="Filter by company (partial match)")
@click.option("--all", "show_all", is_flag=True,
              help="Include rejected/withdrawn (hidden by default)")
def list_cmd(stage, company, show_all):
    """List applications, newest first."""
    with get_db() as conn:
        query = "SELECT * FROM applications WHERE 1=1"
        params: list = []

        if stage:
            query += " AND stage = ?"
            params.append(stage.lower())
        elif not show_all:
            query += " AND stage NOT IN ('rejected', 'withdrawn')"

        if company:
            query += " AND company LIKE ?"
            params.append(f"%{company}%")

        query += " ORDER BY updated_on DESC, id DESC"
        rows = conn.execute(query, params).fetchall()

    if not rows:
        console.print("[dim]No applications found.[/dim]")
        return

    t = Table(box=box.SIMPLE_HEAVY, show_lines=False)
    t.add_column("ID", style="dim", width=4, justify="right")
    t.add_column("Company", style="bold")
    t.add_column("Role")
    t.add_column("Stage", width=14)
    t.add_column("Applied", width=11)
    t.add_column("Updated", width=11)
    t.add_column("Notes", max_width=40, no_wrap=False)

    for row in rows:
        stage_val = row["stage"]
        color = STAGE_COLORS.get(stage_val, "white")
        t.add_row(
            str(row["id"]),
            row["company"],
            row["role"],
            f"[{color}]{stage_val}[/{color}]",
            row["applied_on"] or "—",
            row["updated_on"],
            (row["notes"] or "")[:80],
        )

    console.print(t)
    console.print(f"[dim]{len(rows)} application(s)[/dim]")


@cli.command("show")
@click.argument("app_id", type=int)
def show_cmd(app_id):
    """Show full details for one application."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()

    if not row:
        console.print(f"[red]No application with id {app_id}[/red]")
        raise SystemExit(1)

    stage_val = row["stage"]
    color = STAGE_COLORS.get(stage_val, "white")

    t = Table(box=box.ROUNDED, show_header=False)
    t.add_column("Field", style="dim", width=12)
    t.add_column("Value")
    t.add_row("ID", str(row["id"]))
    t.add_row("Company", f"[bold]{row['company']}[/bold]")
    t.add_row("Role", row["role"])
    t.add_row("Stage", f"[{color}]{stage_val}[/{color}]")
    t.add_row("Applied", row["applied_on"] or "—")
    t.add_row("Updated", row["updated_on"])
    t.add_row("URL", row["url"] or "—")
    t.add_row("Notes", row["notes"] or "—")

    console.print(t)


@cli.command("pipeline")
def pipeline_cmd():
    """Show a stage-by-stage pipeline summary."""
    with get_db() as conn:
        counts = conn.execute(
            "SELECT stage, COUNT(*) as n FROM applications GROUP BY stage"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        recent = conn.execute(
            """SELECT company, role, stage, updated_on FROM applications
               ORDER BY updated_on DESC LIMIT 5"""
        ).fetchall()

    count_map = {r["stage"]: r["n"] for r in counts}

    console.rule("[bold]Job Application Pipeline[/bold]")

    t = Table(box=box.SIMPLE, show_header=True)
    t.add_column("Stage", width=14)
    t.add_column("Count", justify="right", width=7)
    t.add_column("Bar")

    active_stages = [s for s in STAGES if s not in ("rejected", "withdrawn")]
    for s in active_stages:
        n = count_map.get(s, 0)
        color = STAGE_COLORS.get(s, "white")
        bar = f"[{color}]{'█' * n}[/{color}]" if n else "[dim]·[/dim]"
        t.add_row(f"[{color}]{s}[/{color}]", str(n) if n else "—", bar)

    # Show rejected/withdrawn as a single summary row
    dead = sum(count_map.get(s, 0) for s in ("rejected", "withdrawn"))
    if dead:
        t.add_row("[dim]rejected/withdrawn[/dim]", str(dead), "[dim]" + "█" * dead + "[/dim]")

    console.print(t)
    console.print(f"[dim]Total: {total} application(s)[/dim]\n")

    if recent:
        console.rule("[dim]Recently updated[/dim]")
        rt = Table(box=box.SIMPLE, show_header=True)
        rt.add_column("Company", style="bold")
        rt.add_column("Role")
        rt.add_column("Stage", width=14)
        rt.add_column("Updated", width=11)
        for r in recent:
            color = STAGE_COLORS.get(r["stage"], "white")
            rt.add_row(r["company"], r["role"],
                       f"[{color}]{r['stage']}[/{color}]", r["updated_on"])
        console.print(rt)


@cli.command("delete")
@click.argument("app_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def delete_cmd(app_id, yes):
    """Delete an application by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT company, role FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
        if not row:
            console.print(f"[red]No application with id {app_id}[/red]")
            raise SystemExit(1)

        if not yes:
            click.confirm(
                f"Delete '{row['company']} — {row['role']}'?", abort=True
            )

        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))

    console.print(f"[red]Deleted[/red] application [cyan]{app_id}[/cyan] "
                  f"({row['company']} — {row['role']})")


if __name__ == "__main__":
    cli()
