from pathlib import Path

import click

from .manifest import load_manifest
from .materialx import generate_mtlx
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


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None,
              help="Output path for .mtlx file (default: materials/master.mtlx)")
def material(path: Path, output: Path | None):
    """Generate a MaterialX file from manifest material_zones."""
    manifest = load_manifest(path)
    zones = manifest.get("material_zones")

    if not zones:
        click.echo(click.style("  FAIL  No material_zones defined in manifest.", fg="red"))
        raise SystemExit(1)

    asset_dir = path if path.is_dir() else path.parent
    if output is None:
        output = asset_dir / "materials" / "master.mtlx"

    generate_mtlx(zones, output)

    click.echo(f"Generated {len(zones)} material zone(s):")
    for name in zones:
        click.echo(click.style(f"  MAT_{name}", fg="cyan"))
    click.echo()
    click.echo(click.style(f"Written to: {output}", fg="green", bold=True))
