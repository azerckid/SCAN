"""Command-line entry point for the SCAN tool."""

from typing import Annotated

import typer

from scan_tool import __version__

app = typer.Typer(
    help="Evidence-first blockchain forensic tools for SCAN 2026.",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed package version and exit."),
    ] = False,
) -> None:
    """Run the SCAN command-line interface."""
    if version:
        typer.echo(__version__)
        raise typer.Exit
