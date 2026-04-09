"""Click-based CLI entry point for pathy-svg."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import click


@click.group()
@click.version_option()
def main():
    """pathy-svg: Color SVG paths by data values."""


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
@click.argument("data_file", type=click.Path(exists=True))
@click.option("--id-col", required=True, help="Column name for path IDs")
@click.option("--value-col", required=True, help="Column name for values")
@click.option("--palette", default="viridis", help="Colormap name")
@click.option("--legend/--no-legend", default=False, help="Add legend")
@click.option("--legend-title", default=None, help="Legend title text")
@click.option("-o", "--output", required=True, help="Output SVG path")
def heatmap(
    svg_file, data_file, id_col, value_col, palette, legend, legend_title, output
):
    """Create a heatmap from SVG + data file."""
    from pathy_svg.document import SVGDocument

    doc = SVGDocument.from_file(svg_file)
    data = _read_data(data_file, id_col, value_col)

    result = doc.heatmap(data, palette=palette)
    if legend:
        result = result.legend(title=legend_title)
    result.save(output)
    click.echo(f"Saved to {output}")


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
def inspect(svg_file):
    """List path IDs and basic info about an SVG."""
    from pathy_svg.document import SVGDocument

    doc = SVGDocument.from_file(svg_file)
    vb = doc.viewbox
    w, h = doc.dimensions

    click.echo(f"File: {svg_file}")
    click.echo(f"ViewBox: {vb}")
    click.echo(f"Dimensions: {w} x {h}")
    click.echo(f"Paths ({len(doc.path_ids)}):")
    for pid in sorted(doc.path_ids):
        click.echo(f"  {pid}")
    click.echo(f"Groups ({len(doc.group_ids)}):")
    for gid in sorted(doc.group_ids):
        click.echo(f"  {gid}")


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
@click.argument("data_file", type=click.Path(exists=True))
@click.option("--id-col", required=True, help="Column name for path IDs")
def validate(svg_file, data_file, id_col):
    """Validate data IDs against SVG element IDs."""
    from pathy_svg.document import SVGDocument

    doc = SVGDocument.from_file(svg_file)
    ids = _read_ids(data_file, id_col)
    result = doc.validate_ids(ids)

    click.echo(f"Matched ({len(result.matched)}): {', '.join(result.matched)}")
    if result.unmatched:
        click.echo(
            f"Unmatched ({len(result.unmatched)}): {', '.join(result.unmatched)}"
        )
    if result.unused:
        click.echo(
            f"Unused SVG IDs ({len(result.unused)}): {', '.join(result.unused[:10])}"
        )
    if result.is_valid:
        click.echo("✓ All data IDs found in SVG")
    else:
        click.echo("✗ Some data IDs not found in SVG")
        sys.exit(1)


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, help="Output SVG path")
@click.option("--color", default="red", help="Grid color")
@click.option("--step", default=50, type=float, help="Grid step size")
def guide(svg_file, output, color, step):
    """Generate an XY coordinate guide overlay."""
    from pathy_svg.document import SVGDocument

    doc = SVGDocument.from_file(svg_file)
    result = doc.xy_guide(color=color, step=step)
    result.save(output)
    click.echo(f"Guide saved to {output}")


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
@click.option(
    "--format", "fmt", type=click.Choice(["png", "pdf", "jpeg"]), default="png"
)
@click.option("--width", type=int, default=None, help="Output width in pixels")
@click.option("--dpi", type=int, default=96, help="DPI for raster export")
@click.option("-o", "--output", required=True, help="Output file path")
def export(svg_file, fmt, width, dpi, output):
    """Export SVG to raster format (PNG, PDF, JPEG)."""
    from pathy_svg.document import SVGDocument

    doc = SVGDocument.from_file(svg_file)
    if fmt == "png":
        doc.to_png(output, width=width, dpi=dpi)
    elif fmt == "pdf":
        doc.to_pdf(output)
    elif fmt == "jpeg":
        doc.to_jpeg(output, width=width, dpi=dpi)
    click.echo(f"Exported to {output}")


@main.command()
@click.argument("svg_file", type=click.Path(exists=True))
@click.argument("baseline_file", type=click.Path(exists=True))
@click.argument("treatment_file", type=click.Path(exists=True))
@click.option("--id-col", required=True, help="Column name for path IDs")
@click.option("--value-col", required=True, help="Column name for values")
@click.option(
    "--mode",
    type=click.Choice(["delta", "ratio", "log2ratio", "percent_change"]),
    default="delta",
)
@click.option("--palette", default="coolwarm")
@click.option("-o", "--output", required=True, help="Output SVG path")
def diff(
    svg_file, baseline_file, treatment_file, id_col, value_col, mode, palette, output
):
    """Compare two datasets on the same SVG."""
    from pathy_svg.document import SVGDocument

    doc = SVGDocument.from_file(svg_file)
    baseline = _read_data(baseline_file, id_col, value_col)
    treatment = _read_data(treatment_file, id_col, value_col)

    result = doc.diff(baseline, treatment, mode=mode, palette=palette)
    result.legend(title=f"{mode.replace('_', ' ').title()}").save(output)
    click.echo(f"Diff saved to {output}")


def _read_data(path: str, id_col: str, value_col: str) -> dict[str, float]:
    """Read a CSV/TSV/Parquet/Excel file and return {id: value} dict."""
    p = Path(path)
    if p.suffix in (".csv", ".tsv", ".tab"):
        return _read_csv_data(p, id_col, value_col)
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            f"Reading {p.suffix} files requires pandas. Install with: pip install pandas"
        ) from None
    if p.suffix == ".parquet":
        df = pd.read_parquet(p)
    elif p.suffix in (".xls", ".xlsx"):
        df = pd.read_excel(p)
    else:
        return _read_csv_data(p, id_col, value_col)
    return _data_from_df(df, id_col, value_col)


def _read_csv_data(path: Path, id_col: str, value_col: str) -> dict[str, float]:
    """Read a CSV/TSV and return {id: value} dict."""
    delimiter = "\t" if path.suffix in (".tsv", ".tab") else ","
    data = {}
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            try:
                data[row[id_col]] = float(row[value_col])
            except (KeyError, ValueError):
                continue
    return data


def _data_from_df(df, id_col: str, value_col: str) -> dict[str, float]:
    """Extract {id: value} from a Pandas DataFrame."""
    from pathy_svg.data import dataframe_to_dict

    return dataframe_to_dict(df, id_col, value_col)


def _read_ids(path: str, id_col: str) -> list[str]:
    """Read a CSV/TSV and return list of IDs."""
    p = Path(path)
    delimiter = "\t" if p.suffix in (".tsv", ".tab") else ","
    ids = []
    with open(p) as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            if id_col in row:
                ids.append(row[id_col])
    return ids
