"""
Command-line interface for IncludeGuard
"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.tree import Tree
from rich import box
from rich.syntax import Syntax
import json
import sys

from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator
from includeguard.ui.html_report import HTMLReportGenerator

console = Console()

def print_banner():
    """Print application banner"""
    banner = """
    ___            __          __    ______                     __
   /  _/___  _____/ /_  ______/ /__ / ____/_  ______ __________/ /
   / // __ \\/ ___/ / / / / __  / _ \\/ / __/ / / / __ `/ ___/ __  / 
 _/ // / / / /__/ / /_/ / /_/ /  __/ /_/ / /_/ / /_/ / /  / /_/ /  
/___/_/ /_/\\___/_/\\__,_/\\__,_/\\___/\\____/\\__,_/\\__,_/_/   \\__,_/   
    """
    console.print(banner, style="cyan bold")
    console.print("Fast C++ Include Analyzer with Build Cost Estimation\\n", style="dim")

@click.group()
@click.version_option(version='0.1.0')
def main():
    """IncludeGuard - Intelligent C++ Include Analysis"""
    pass

@main.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--output', '-o', default='includeguard_report.html', 
              help='Output HTML report file')
@click.option('--json-output', '-j', help='JSON output file')
@click.option('--dot-output', '-d', help='DOT graph output file')
@click.option('--max-files', '-m', default=None, type=int,
              help='Maximum files to analyze (for large projects)')
@click.option('--extensions', '-e', multiple=True,
              help='File extensions to analyze (e.g., .cpp .h)')
def analyze(project_path, output, json_output, dot_output, max_files, extensions):
    """Analyze a C++ project for include dependencies and costs"""
    
    print_banner()
    
    project = Path(project_path).resolve()
    
    if not project.exists():
        console.print(f"[red]Error: Project path does not exist: {project}[/red]")
        sys.exit(1)
    
    # Step 1: Parse files
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Parsing C++ files...", total=None)
        
        parser = IncludeParser(project)
        
        # Use custom extensions if provided
        ext_list = list(extensions) if extensions else None
        analyses = parser.parse_project(extensions=ext_list)
        
        # Limit files if requested
        if max_files and len(analyses) > max_files:
            console.print(f"[yellow]Warning: Limiting analysis to {max_files} files[/yellow]")
            analyses = analyses[:max_files]
        
        progress.update(task, completed=True)
    
    if not analyses:
        console.print("[red]No C++ files found in project![/red]")
        sys.exit(1)
    
    console.print(f"[green]✓[/green] Found {len(analyses)} C++ files\\n")
    
    # Display parser statistics
    stats = parser.get_statistics(analyses)
    _display_parser_stats(stats)
    
    # Step 2: Build dependency graph
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Building dependency graph...", total=None)
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        progress.update(task, completed=True)
    
    graph_stats = graph.get_node_stats()
    console.print(f"[green]✓[/green] Graph built: {graph_stats['total_nodes']} nodes, "
                 f"{graph_stats['total_edges']} edges\\n")
    
    _display_graph_stats(graph_stats, graph)
    
    # Step 3: Estimate costs
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]Estimating build costs for {len(analyses)} files...",
            total=len(analyses)
        )
        
        estimator = CostEstimator(graph)
        analysis_dict = {a.filepath: a for a in analyses}
        
        reports = []
        for analysis in analyses:
            report = estimator.generate_report(analysis, analysis_dict)
            reports.append(report)
            progress.advance(task)
    
    console.print(f"[green]✓[/green] Cost estimation complete\\n")
    
    # Sort reports by waste (most wasteful first)
    reports.sort(key=lambda r: r['wasted_cost'], reverse=True)
    
    # Generate project summary
    summary = estimator.generate_project_summary(reports)
    
    # Display results
    _display_project_summary(summary)
    _display_top_opportunities(summary)
    _display_top_wasteful_files(reports[:10])
    
    # Export HTML report
    if output:
        console.print(f"\n[cyan]Generating HTML report...[/cyan]")
        html_gen = HTMLReportGenerator()
        html_gen.generate(reports, summary, graph_stats, output)
        console.print(f"[green]✓[/green] HTML report saved to: [bold]{output}[/bold]")
    
    # Export JSON
    if json_output:
        console.print(f"[cyan]Exporting JSON data...[/cyan]")
        export_data = {
            'summary': summary,
            'reports': reports,
            'graph_stats': graph_stats
        }
        Path(json_output).write_text(json.dumps(export_data, indent=2))
        console.print(f"[green]✓[/green] JSON data saved to: [bold]{json_output}[/bold]")
    
    # Export DOT graph
    if dot_output:
        console.print(f"[cyan]Exporting dependency graph...[/cyan]")
        graph.export_dot(Path(dot_output))
    
    console.print()

def _display_parser_stats(stats: dict):
    """Display parser statistics"""
    table = Table(title="Parse Statistics", box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("Total Files", f"{stats['total_files']:,}")
    table.add_row("Total Includes", f"{stats['total_includes']:,}")
    table.add_row("System Includes", f"{stats['system_includes']:,}")
    table.add_row("User Includes", f"{stats['user_includes']:,}")
    table.add_row("Total Lines of Code", f"{stats['total_code_lines']:,}")
    table.add_row("Avg Includes/File", f"{stats['avg_includes_per_file']:.1f}")
    table.add_row("Files with Templates", f"{stats['files_with_templates']}")
    table.add_row("Files with Macros", f"{stats['files_with_macros']}")
    
    console.print(table)
    console.print()

def _display_graph_stats(stats: dict, graph: DependencyGraph):
    """Display graph statistics"""
    table = Table(title="Dependency Graph", box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("Total Nodes", f"{stats['total_nodes']:,}")
    table.add_row("Internal Nodes", f"{stats['internal_nodes']:,}")
    table.add_row("External Nodes", f"{stats['external_nodes']:,}")
    table.add_row("Total Edges", f"{stats['total_edges']:,}")
    table.add_row("Avg Dependencies/File", f"{stats['avg_degree']:.1f}")
    table.add_row("Max Dependency Depth", f"{stats['max_depth']}")
    table.add_row("Circular Dependencies", 
                 f"[red]{stats['cycles']}[/red]" if stats['cycles'] > 0 else "[green]0[/green]")
    
    console.print(table)
    
    # Show most included headers
    top_headers = graph.get_most_included_headers(5)
    if top_headers:
        console.print("\\n[bold]Most Included Headers:[/bold]")
        for header, count in top_headers:
            header_name = Path(header).name if not header.startswith('<') else header
            console.print(f"  • {header_name}: [green]{count}[/green] times")

def _display_project_summary(summary: dict):
    """Display project cost summary"""
    panel_content = f"""
[bold]Total Cost:[/bold] {summary['total_cost']:,.0f} units
[bold]Wasted Cost:[/bold] [red]{summary['total_waste']:,.0f}[/red] units ([red]{summary['waste_percentage']:.1f}%[/red])
[bold]Potential Savings:[/bold] [green]{summary['waste_percentage']:.1f}%[/green] of build time

[dim]Average cost per file: {summary['avg_cost_per_file']:.1f} units[/dim]
"""
    
    console.print(Panel(
        panel_content,
        title="[bold cyan]💰 Project Cost Summary[/bold cyan]",
        border_style="cyan"
    ))

def _display_top_opportunities(summary: dict):
    """Display top optimization opportunities"""
    if not summary['top_opportunities']:
        return
    
    console.print("\\n[bold yellow]🎯 Top Optimization Opportunities[/bold yellow]\\n")
    
    table = Table(box=box.SIMPLE)
    table.add_column("File", style="cyan", no_wrap=True, max_width=30)
    table.add_column("Unused Header", style="yellow", max_width=40)
    table.add_column("Est. Cost", justify="right", style="red")
    table.add_column("Line", justify="right", style="dim")
    
    for opp in summary['top_opportunities'][:15]:
        cost_style = "red bold" if opp['cost'] > 2000 else "red"
        table.add_row(
            opp['file'],
            opp['header'],
            f"[{cost_style}]{opp['cost']:.0f}[/{cost_style}]",
            str(opp['line'])
        )
    
    console.print(table)

def _display_top_wasteful_files(reports: list):
    """Display files with most waste"""
    if not reports:
        return
    
    console.print("\\n[bold red]📊 Most Wasteful Files[/bold red]\\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("Rank", justify="right", style="dim")
    table.add_column("File", style="cyan")
    table.add_column("Includes", justify="right")
    table.add_column("Total Cost", justify="right")
    table.add_column("Wasted", justify="right", style="red")
    table.add_column("Waste %", justify="right", style="yellow")
    
    for i, report in enumerate(reports, 1):
        filename = Path(report['file']).name
        waste_pct = report['potential_savings_pct']
        
        # Color code waste percentage
        if waste_pct > 50:
            waste_style = "red bold"
        elif waste_pct > 25:
            waste_style = "yellow"
        else:
            waste_style = "green"
        
        table.add_row(
            str(i),
            filename,
            str(report['total_includes']),
            f"{report['total_estimated_cost']:.0f}",
            f"{report['wasted_cost']:.0f}",
            f"[{waste_style}]{waste_pct:.1f}%[/{waste_style}]"
        )
    
    console.print(table)

@main.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Show detailed analysis')
def inspect(filepath, verbose):
    """Inspect a single file's includes"""
    
    print_banner()
    
    file_path = Path(filepath).resolve()
    
    if not file_path.exists():
        console.print(f"[red]Error: File does not exist: {file_path}[/red]")
        sys.exit(1)
    
    # Parse file
    parser = IncludeParser(file_path.parent)
    analysis = parser.parse_file(file_path)
    
    if not analysis:
        console.print("[red]Error parsing file[/red]")
        sys.exit(1)
    
    # Build minimal graph
    graph = DependencyGraph()
    graph.build([analysis])
    
    # Estimate costs
    estimator = CostEstimator(graph)
    report = estimator.generate_report(analysis, {analysis.filepath: analysis})
    
    # Display file info
    console.print(f"\\n[bold cyan]File:[/bold cyan] {file_path.name}")
    console.print(f"[bold cyan]Path:[/bold cyan] {file_path}")
    console.print(f"[dim]Lines: {analysis.total_lines} | "
                 f"Code: {analysis.code_lines} | "
                 f"Includes: {len(analysis.includes)}[/dim]\\n")
    
    # Include analysis
    table = Table(title="Include Analysis", box=box.ROUNDED)
    table.add_column("Header", style="yellow", max_width=50)
    table.add_column("Cost", justify="right", style="red")
    table.add_column("Used?", justify="center")
    table.add_column("Confidence", justify="center", style="dim")
    table.add_column("Line", justify="right", style="dim")
    
    for inc in report['all_includes']:
        # Determine cost color
        cost = inc['estimated_cost']
        if cost > 2000:
            cost_str = f"[red bold]{cost:.0f}[/red bold]"
        elif cost > 1000:
            cost_str = f"[red]{cost:.0f}[/red]"
        elif cost > 500:
            cost_str = f"[yellow]{cost:.0f}[/yellow]"
        else:
            cost_str = f"[green]{cost:.0f}[/green]"
        
        # Used indicator
        if inc['likely_used']:
            used_icon = "[green]✓[/green]"
        else:
            used_icon = "[red]✗[/red]"
        
        # Confidence bar
        conf = inc['usage_confidence']
        conf_str = f"{conf:.0%}"
        
        table.add_row(
            inc['header'],
            cost_str,
            used_icon,
            conf_str,
            str(inc['line'])
        )
    
    console.print(table)
    
    # Summary
    console.print()
    summary_panel = f"""
[bold]Total Estimated Cost:[/bold] {report['total_estimated_cost']:.0f} units
[bold]Wasted Cost:[/bold] [red]{report['wasted_cost']:.0f}[/red] units
[bold]Potential Savings:[/bold] [yellow]{report['potential_savings_pct']:.1f}%[/yellow]
"""
    console.print(Panel(
        summary_panel,
        title="[bold]Cost Summary[/bold]",
        border_style="cyan"
    ))
    
    # Show optimization recommendations
    if report['optimization_opportunities']:
        console.print("\\n[bold yellow]💡 Optimization Recommendations:[/bold yellow]\\n")
        for i, opp in enumerate(report['optimization_opportunities'][:5], 1):
            console.print(
                f"{i}. Remove [yellow]{opp['header']}[/yellow] "
                f"at line [dim]{opp['line']}[/dim] "
                f"(saves [red]{opp['estimated_cost']:.0f}[/red] units)"
            )
    else:
        console.print("\\n[green]✓ No obvious optimization opportunities found![/green]")

if __name__ == '__main__':
    main()
