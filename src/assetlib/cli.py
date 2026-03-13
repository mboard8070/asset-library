from pathlib import Path

import click

from .validator import run_full_validation


@click.group()
@click.version_option()
def cli():
    """Digital Twin Asset Library — pipeline tools."""


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def ingest(path: Path):
    """Validate and ingest an asset directory into the library."""
    click.echo(f"Ingesting: {path}")
    click.echo()

    errors, warnings = run_full_validation(path)

    if warnings:
        for w in warnings:
            click.echo(click.style(f"  WARN  {w}", fg="yellow"))
        click.echo()

    if errors:
        for e in errors:
            click.echo(click.style(f"  FAIL  {e}", fg="red"))
        click.echo()
        click.echo(click.style("Ingest failed — fix errors above.", fg="red", bold=True))
        raise SystemExit(1)

    click.echo(click.style("  PASS  Directory structure valid", fg="green"))
    click.echo(click.style("  PASS  Manifest schema valid", fg="green"))

    if warnings:
        click.echo()
        click.echo(f"  {len(warnings)} warning(s) — missing asset files (expected during scaffolding)")

    click.echo()
    click.echo(click.style("Asset ingested successfully.", fg="green", bold=True))
