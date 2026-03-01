#!/usr/bin/env python3
"""FeaGPT CLI - Natural language driven FEA automation."""
import click
import logging
import sys
import json
from pathlib import Path


def setup_logging(level="INFO"):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("feagpt.log")],
    )


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, config, verbose):
    """FeaGPT: End-to-End Agentic AI for Finite Element Analysis."""
    setup_logging("DEBUG" if verbose else "INFO")
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.argument("description")
@click.option("--output", "-o", default="results", help="Output directory")
@click.pass_context
def run(ctx, description, output):
    """Run a single FEA analysis from natural language description."""
    from feagpt.config import FeaGPTConfig
    from feagpt.pipeline import GMSAPipeline

    config = FeaGPTConfig(ctx.obj["config_path"])
    pipeline = GMSAPipeline(config)
    result = pipeline.run(description, output)

    if result.success:
        click.echo(f"Analysis complete. Results saved to {output}/")
        click.echo(f"Max stress: {result.results_data.get('max_von_mises', 'N/A')} Pa")
        click.echo(f"Max displacement: {result.results_data.get('max_displacement', 'N/A')} m")
    else:
        click.echo(f"Pipeline failed at stage: {result.stage}", err=True)
        for err in result.errors:
            click.echo(f"  Error: {err}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("description")
@click.option("--output", "-o", default="results", help="Output directory")
@click.option("--workers", "-w", default=None, type=int, help="Max parallel workers")
@click.pass_context
def batch(ctx, description, output, workers):
    """Run a parametric batch study from natural language description."""
    from feagpt.config import FeaGPTConfig
    from feagpt.pipeline import GMSAPipeline

    config = FeaGPTConfig(ctx.obj["config_path"])
    if workers:
        config.batch.max_workers = workers
    pipeline = GMSAPipeline(config)
    results = pipeline.run_batch(description, output)

    success = sum(1 for r in results if r.success)
    click.echo(f"Batch complete: {success}/{len(results)} succeeded")


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start an interactive FEA session."""
    from feagpt.config import FeaGPTConfig
    from feagpt.pipeline import GMSAPipeline

    config = FeaGPTConfig(ctx.obj["config_path"])
    pipeline = GMSAPipeline(config)
    pipeline.initialize()

    click.echo("FeaGPT Interactive Mode. Type 'quit' to exit.")
    while True:
        try:
            desc = click.prompt("\nDescribe your analysis", prompt_suffix="> ")
            if desc.lower() in ("quit", "exit", "q"):
                break
            result = pipeline.run(desc)
            if result.success:
                click.echo(json.dumps(result.results_data, indent=2, default=str))
            else:
                click.echo(f"Failed: {result.errors}")
        except (KeyboardInterrupt, EOFError):
            break

    click.echo("Goodbye!")


if __name__ == "__main__":
    cli()
