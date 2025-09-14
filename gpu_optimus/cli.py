#!/usr/bin/env python3
# gpu_optimus/cli.py
import click
import subprocess
import sys
from gpu_optimus.profiler import GPUProfiler
from gpu_optimus.analyzer import analyze_run
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

@click.group()
def cli():
    """GPU Optimus - Find wasted GPU compute in your ML training runs."""
    pass

@cli.command()
@click.argument('command', nargs=-1)
@click.option('--instance-type', default='p3.2xlarge', help='Cloud instance type (e.g., p3.2xlarge)')
@click.option('--cloud', default='aws', help='Cloud provider (aws, azure, gcp)')
def run(command, instance_type, cloud):
    """Run a command and profile its GPU usage."""
    if not command:
        console.print("[red]Error: No command provided to run.[/red]")
        return

    # Start the profiler
    profiler = GPUProfiler()
    console.print("🔍 [bold green]Starting GPU Profiler...[/bold green]")
    profiler.start()

    # Run the user's command
    try:
        cmd_str = " ".join(command)
        console.print(f"🚀 [bold]Running:[/bold] {cmd_str}")
        result = subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed with exit code {e.returncode}[/red]")
        profiler.stop()
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        console.print("[yellow]Command interrupted by user.[/yellow]")
        profiler.stop()
        sys.exit(1)
    finally:
        profiler.stop()

    # Analyze the results
    console.print("\n📊 [bold green]Analysis Complete! Generating report...[/bold green]")
    stats = profiler.calculate_stats()
    analysis = analyze_run(stats, instance_type, cloud)

    # Print the report with Rich
    console.print(Panel.fit(
        f"[bold]Job Duration:[/bold] {stats['duration_sec']:.0f} seconds ({stats['duration_sec']/3600:.2f} hours)\n"
        f"[bold]GPU Compute:[/bold] {stats['avg_compute_util']:.1f}% avg, [red]{stats['idle_percent']:.1f}% idle[/red]\n"
        f"[bold]GPU Memory:[/bold] {stats['avg_mem_util']:.1f}% avg, {stats['peak_mem_util_gb']:.1f}GB peak",
        title="📈 GPU Utilization Summary",
        border_style="green"
    ))

    cost = analysis['cost_analysis']
    console.print(Panel.fit(
        f"[bold]Instance:[/bold] {cost['instance_type']} ({cost['cloud_provider']}) @ ${cost['hourly_rate']}/hr\n"
        f"[bold]Total Cost:[/bold] ${cost['total_cost']:.2f}\n"
        f"[red]Wasted Cost (Idle):[/red] ${cost['wasted_cost']:.2f}",
        title="💸 Cost Analysis",
        border_style="red"
    ))

    if analysis['recommendations']:
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Priority", width=8)
        table.add_column("Category", width=15)
        table.add_column("Message", width=50)
        table.add_column("Suggestion")

        for rec in analysis['recommendations']:
            priority_color = "red" if rec['priority'] == 'HIGH' else "yellow"
            table.add_row(
                f"[{priority_color}]{rec['priority']}[/{priority_color}]",
                rec['category'],
                rec['message'],
                rec['suggestion']
            )
        console.print(Panel.fit(table, title="🚀 Recommendations", border_style="blue"))
    else:
        console.print("✅ [green]No major optimization opportunities found. Great job![/green]")

if __name__ == '__main__':
    cli()