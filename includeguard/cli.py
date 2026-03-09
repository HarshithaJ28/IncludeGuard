"""
Command-line interface for IncludeGuard
"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn
from rich.panel import Panel
from rich.tree import Tree
from rich.align import Align
from rich import box
from rich.syntax import Syntax
import json
import sys
import time
import statistics
import subprocess
import tempfile
from datetime import datetime

from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator
from includeguard.analyzer.forward_declaration import ForwardDeclarationDetector
from includeguard.analyzer.pch_recommender import PCHRecommender
from includeguard.analyzer.build_profiler import BuildProfiler
from includeguard.ui.html_report import HTMLReportGenerator

# Configure console for cross-platform compatibility
console = Console(
    force_terminal=True,
    no_color=False,
    width=120
)

def print_banner():
    """Print application banner"""
    banner = """
    ___            __          __    ______                     __
   /  _/___  _____/ /_  ______/ /__ / ____/_  ______ __________/ /
   / // __ \/ ___/ / / / / __  / _ \/ / __/ / / / __ `/ ___/ __  / 
 _/ // / / / /__/ / /_/ / /_/ /  __/ /_/ / /_/ / /_/ / /  / /_/ /  
/___/_/ /_/\___/_/\__,_/\__,_/\___/\____/\__,_/\__,_/_/   \__,_/   
    """
    console.print("\n")
    console.print(Align.center(banner), style="bold magenta")
    console.print(Align.center(
        "[bold cyan]Fast C++ Include Analyzer[/bold cyan] [dim]|[/dim] "
        "[bold green]Build Cost Estimator[/bold green] [dim]|[/dim] "
        "[bold yellow]v0.1.0[/bold yellow]"
    ))
    console.print(Align.center("[dim]Optimize your C++ build times instantly[/dim]\n"))

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
    
    # Step 4: Forward declaration analysis
    console.print("[cyan]Analyzing forward declaration opportunities...[/cyan]")
    fwd_detector = ForwardDeclarationDetector()
    
    all_fwd_opportunities = []
    for analysis in analyses:
        opportunities = fwd_detector.analyze_file(analysis.filepath, analysis)
        if opportunities:
            all_fwd_opportunities.extend([
                {**opp, 'file': Path(analysis.filepath).name}
                for opp in opportunities
            ])
    
    # Step 5: PCH recommendations
    console.print("[cyan]Generating PCH recommendations...[/cyan]")
    pch_recommender = PCHRecommender()
    pch_recommendations = pch_recommender.recommend_pch_headers(
        analyses, graph, estimator, min_usage_count=3
    )
    
    console.print(f"[green]✓[/green] Analysis complete\n")
    
    # Display results
    _display_project_summary(summary)
    _display_top_opportunities(summary)
    
    if all_fwd_opportunities:
        _display_forward_declaration_opportunities(all_fwd_opportunities[:10])
    
    if pch_recommendations:
        _display_pch_recommendations(pch_recommendations[:10], pch_recommender)
    
    _display_top_wasteful_files(reports[:10])
    
    # Export HTML report
    if output:
        console.print(f"\n[cyan]Generating HTML report...[/cyan]")
        html_gen = HTMLReportGenerator()
        html_gen.generate(reports, summary, graph_stats, output,
                         forward_decls=all_fwd_opportunities,
                         pch_recommendations=pch_recommendations)
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
    """Display project cost summary with enhanced styling"""
    
    # Calculate savings visually
    waste_pct = summary['waste_percentage']
    efficiency = 100 - waste_pct
    
    # Color code based on waste
    if waste_pct < 10:
        waste_color = "green"
        status_emoji = "✨"
        status = "Excellent"
    elif waste_pct < 25:
        waste_color = "yellow"
        status_emoji = "✅"
        status = "Good"
    elif waste_pct < 50:
        waste_color = "orange1"
        status_emoji = "⚠️"
        status = "Needs Optimization"
    else:
        waste_color = "red"
        status_emoji = "🔥"
        status = "Critical"
    
    panel_content = f"""
[bold white on blue] 📊 BUILD COST ANALYSIS [/bold white on blue]

💰 [bold]Total Build Cost:[/bold]     [cyan]{summary['total_cost']:>12,.0f}[/cyan] units
🗑️  [bold]Wasted Cost:[/bold]        [{waste_color}]{summary['total_waste']:>12,.0f}[/{waste_color}] units ([{waste_color}]{waste_pct:.1f}%[/{waste_color}])
📈 [bold]Potential Savings:[/bold]   [green]{waste_pct:>12.1f}%[/green] of build time
⚡ [bold]Build Efficiency:[/bold]    [green]{efficiency:>12.1f}%[/green]

{status_emoji}  [bold]Status:[/bold] [{waste_color}]{status}[/{waste_color}]
[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]
[dim]📁 Average cost per file: {summary['avg_cost_per_file']:.1f} units[/dim]
"""
    
    console.print()
    console.print(Panel(
        panel_content,
        border_style="bright_cyan",
        padding=(1, 2)
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

def _display_forward_declaration_opportunities(opportunities: list):
    """Display forward declaration suggestions"""
    console.print("\n[bold green]💡 Forward Declaration Opportunities[/bold green]\n")
    console.print("[dim]Replace expensive includes with forward declarations when only using pointers/references[/dim]\n")
    
    table = Table(box=box.SIMPLE)
    table.add_column("File", style="cyan", no_wrap=True, max_width=25)
    table.add_column("Replace Include", style="yellow", max_width=35)
    table.add_column("With Forward Decl", style="green", max_width=30)
    table.add_column("Confidence", justify="center")
    
    for opp in opportunities:
        conf_color = "green" if opp['confidence'] > 0.7 else "yellow" if opp['confidence'] > 0.5 else "dim"
        table.add_row(
            opp['file'],
            f"#include \"{opp['header']}\"",
            opp['suggestion'],
            f"[{conf_color}]{opp['confidence']:.0%}[/{conf_color}]"
        )
    
    console.print(table)

def _display_pch_recommendations(recommendations: list, pch_recommender: PCHRecommender):
    """Display PCH recommendations"""
    console.print("\n[bold magenta]🔧 Precompiled Header Recommendations[/bold magenta]\n")
    console.print("[dim]Headers used frequently + expensive to compile → Good PCH candidates[/dim]\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("Header", style="cyan")
    table.add_column("Used By", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("PCH Score", justify="right", style="magenta")
    table.add_column("Est. Savings", justify="right", style="green")
    
    for rec in recommendations:
        score_color = "magenta bold" if rec['pch_score'] > 10000 else "magenta"
        table.add_row(
            rec['header'],
            f"{rec['usage_count']} files",
            f"{rec['cost']:.0f}",
            f"[{score_color}]{rec['pch_score']:.0f}[/{score_color}]",
            f"{rec['estimated_savings']:.0f}"
        )
    
    console.print(table)
    
    # Show benefit estimate
    benefit = pch_recommender.estimate_pch_benefit(recommendations)
    console.print(f"\n[bold]Estimated speedup with PCH:[/bold] [green]{benefit['estimated_speedup']:.1f}%[/green] ")
    console.print(f"[dim]({benefit['files_benefiting']} files would benefit)[/dim]")
    
    # Generate PCH file suggestion
    console.print("\n[bold]Suggested PCH file (pch.h):[/bold]\n")
    pch_content = pch_recommender.generate_pch_file_content(recommendations, max_headers=10)
    syntax = Syntax(
        pch_content,
        "cpp",
        theme="monokai",
        line_numbers=False
    )
    console.print(syntax)

@main.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Show detailed analysis')
@click.option('--json', '-j', is_flag=True, help='Output JSON for programmatic use')
def inspect(filepath, verbose, json):
    """Inspect a single file's includes"""
    
    if not json:
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
    
    # JSON output for programmatic use (e.g., VS Code extension)
    if json:
        import sys
        json_output = {
            'file': str(file_path),
            'includes': [
                {
                    'header': inc.header,
                    'line': inc.line_number,
                    'is_system': inc.is_system,
                    'cost': report['include_costs'].get(inc.header, {}).get('estimated_cost', 0),
                    'likely_used': report['include_costs'].get(inc.header, {}).get('likely_used', True),
                    'confidence': report['include_costs'].get(inc.header, {}).get('confidence', 0.0)
                }
                for inc in analysis.includes
            ],
            'summary': {
                'total_cost': report['total_estimated_cost'],
                'wasted_cost': report['wasted_cost'],
                'potential_savings_pct': report['potential_savings_pct']
            },
            'optimization_opportunities': report['optimization_opportunities']
        }
        console.print(json.dumps(json_output, indent=2))
        sys.exit(0)

@main.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--compiler', default='g++', help='Compiler to use (g++, clang++, cl)')
@click.option('--flags', '-f', multiple=True, help='Compiler flags (e.g., -std=c++17)')
def profile(filepath, compiler, flags):
    """Profile actual compilation time impact of headers"""
    
    print_banner()
    
    file_path = Path(filepath).resolve()
    
    console.print(f"\n[bold cyan]Profiling:[/bold cyan] {file_path.name}")
    console.print(f"[yellow]This requires a C++ compiler ({compiler})[/yellow]\n")
    
    # Parse file
    parser = IncludeParser(file_path.parent)
    analysis = parser.parse_file(file_path)
    
    if not analysis or not analysis.includes:
        console.print("[red]No includes found or file cannot be parsed[/red]")
        return
    
    # Setup profiler
    profiler = BuildProfiler(compiler)
    compile_flags = list(flags) if flags else ['-std=c++17']
    
    console.print("[cyan]Measuring baseline compilation time...[/cyan]")
    baseline = profiler.profile_file(str(file_path), compile_flags)
    
    if not baseline.success:
        console.print(f"[red]Compilation failed:[/red] {baseline.error_message}")
        console.print(f"[yellow]Check that the file compiles with:[/yellow]")
        console.print(f"  {compiler} -E {file_path} {' '.join(compile_flags)}")
        return
    
    console.print(f"[green]✓[/green] Baseline: {baseline.compilation_time_ms:.0f}ms "
                 f"({baseline.preprocessed_lines:,} preprocessed lines)\n")
    
    # Profile each header
    console.print("[cyan]Profiling individual headers (this may take a while)...[/cyan]\n")
    
    results = []
    with Progress(TextColumn("[progress.description]{task.description}"),
                 console=console) as progress:
        task = progress.add_task("Profiling headers...", total=len(analysis.includes))
        
        for inc in analysis.includes:
            result = profiler.profile_with_and_without_header(
                str(file_path),
                inc.header,
                compile_flags
            )
            results.append(result)
            progress.advance(task)
    
    # Filter out errors and sort by savings
    valid_results = [r for r in results if r.get('error') is None]
    valid_results.sort(key=lambda r: r['savings_ms'], reverse=True)
    
    if not valid_results:
        console.print("[red]Could not profile any headers successfully[/red]")
        return
    
    # Display results
    table = Table(title="Actual Build Impact Profile", box=box.ROUNDED)
    table.add_column("Header", style="yellow", max_width=40)
    table.add_column("Baseline", justify="right")
    table.add_column("Without", justify="right")
    table.add_column("Savings", justify="right", style="green")
    table.add_column("Lines Saved", justify="right")
    
    for result in valid_results[:15]:
        savings_pct = result['savings_pct']
        if savings_pct > 10:
            savings_color = "green bold"
        elif savings_pct > 5:
            savings_color = "green"
        else:
            savings_color = "dim"
        
        table.add_row(
            result['header'],
            f"{result['baseline_ms']:.0f}ms",
            f"{result['without_header_ms']:.0f}ms",
            f"[{savings_color}]{result['savings_ms']:.0f}ms ({result['savings_pct']:.1f}%)[/{savings_color}]",
            f"{result['lines_saved']:,}"
        )
    
    console.print(table)
    
    # Summary
    total_savings = sum(r['savings_ms'] for r in valid_results)
    total_savings_pct = (total_savings / baseline.compilation_time_ms * 100 
                        if baseline.compilation_time_ms > 0 else 0)
    
    console.print(f"\n[bold]Total potential savings:[/bold] "
                 f"[green]{total_savings:.0f}ms ({total_savings_pct:.1f}% of baseline)[/green]")
    
    # Show headers that broke compilation (likely necessary)
    error_results = [r for r in results if r.get('error') is not None]
    if error_results:
        console.print(f"\n[dim]{len(error_results)} headers appear to be necessary (removal breaks compilation)[/dim]")

@main.command('ci-comment')
@click.argument('analysis_json', type=click.Path(exists=True))
@click.option('--output', '-o', default='pr_comment.md', 
              help='Output markdown file for PR comment')
@click.option('--fail-on-threshold/--no-fail', default=False, 
              help='Exit with error code if quality thresholds exceeded')
def ci_comment(analysis_json, output, fail_on_threshold):
    """Generate CI/CD comment from analysis JSON for pull requests"""
    
    from includeguard.ci.github_action import generate_pr_comment, check_thresholds
    
    # Read analysis results
    with open(analysis_json) as f:
        analysis_data = json.load(f)
    
    # Generate PR comment
    comment = generate_pr_comment(analysis_data)
    
    # Write to file with UTF-8 encoding
    Path(output).write_text(comment, encoding='utf-8')
    
    console.print(f"[green]✓[/green] Generated PR comment: {output}")
    console.print("\n" + "="*80 + "\n")
    console.print(comment)
    console.print("\n" + "="*80 + "\n")
    
    # Check quality thresholds
    if fail_on_threshold:
        passing, messages = check_thresholds(analysis_data)
        
        console.print("[bold]Threshold Check Results:[/bold]")
        for msg in messages:
            if "FAIL" in msg:
                console.print(f"[red]{msg}[/red]")
            else:
                console.print(f"[green]{msg}[/green]")
        
        if not passing:
            console.print("\n[red]❌ Quality thresholds exceeded - failing build[/red]")
            sys.exit(1)
        else:
            console.print("\n[green]✅ All thresholds passed[/green]")
    
    console.print("[green]✅ CI comment generation complete[/green]")

@main.command('fix-generate')
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--output', '-o', default='includeguard_fixes.patch',
              help='Output patch file')
@click.option('--min-confidence', default=0.7, type=float,
              help='Minimum confidence for auto-fix (0-1, default: 0.7)')
@click.option('--json-input', '-j', type=click.Path(exists=True),
              help='Use existing JSON analysis instead of re-analyzing')
def fix_generate(project_path, output, min_confidence, json_input):
    """Generate Git patch to automatically fix include issues"""
    
    print_banner()
    
    console.print(f"[cyan]Generating auto-fix patch for:[/cyan] {project_path}")
    console.print(f"[cyan]Minimum confidence:[/cyan] {min_confidence:.0%}\n")
    
    # Either load existing analysis or run new analysis
    if json_input:
        console.print(f"[dim]Loading analysis from {json_input}...[/dim]")
        with open(json_input) as f:
            analysis_data = json.load(f)
        
        reports = analysis_data.get('reports', [])
        fwd_opportunities = analysis_data.get('forward_declarations', [])
    else:
        # Run full analysis
        console.print("[dim]Running analysis...[/dim]")
        
        project_path_obj = Path(project_path)
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing project...", total=None)
            
            # Parse project
            parser = IncludeParser(project_root=project_path_obj)
            analyses = parser.parse_project()
            
            progress.update(task, description="Building dependency graph...")
            graph = DependencyGraph()
            graph.build(analyses)
            
            progress.update(task, description="Estimating costs...")
            estimator = CostEstimator(graph)
            
            # Build reports for each file
            all_analyses = {a.filepath: a for a in analyses}
            reports = []
            for analysis in analyses:
                cost_results = estimator.analyze_file_costs(analysis, all_analyses)
                total_cost = sum(c['estimated_cost'] for c in cost_results)
                
                report = {
                    'file': analysis.filepath,
                    'optimization_opportunities': cost_results,
                    'total_estimated_cost': total_cost,
                    'total_includes': len(analysis.includes)
                }
                reports.append(report)
            
            progress.update(task, description="Finding forward declaration opportunities...")
            fwd_detector = ForwardDeclarationDetector()
            fwd_opportunities = []
            for analysis in analyses:
                try:
                    opportunities = fwd_detector.analyze_file(str(analysis.filepath), analysis)
                    fwd_opportunities.extend(opportunities)
                except Exception as e:
                    console.print(f"[dim]Warning: Could not analyze {analysis.filepath}: {e}[/dim]")
            
            progress.update(task, description="Complete!", completed=True)
        
        console.print(f"[green]✓[/green] Analyzed {len(analyses)} files\n")
    
    # Generate patch
    from includeguard.fixer.patch_generator import PatchGenerator
    
    generator = PatchGenerator(min_confidence=min_confidence)
    
    console.print("[cyan]Generating patch...[/cyan]")
    
    try:
        num_files = generator.generate_patch(reports, fwd_opportunities, output)
        stats = generator.get_stats()
        
        if num_files == 0:
            console.print("\n[yellow]⚠️  No fixes to apply![/yellow]")
            console.print("[dim]Either no issues found or confidence threshold too high[/dim]")
            return
        
        console.print(f"\n[green]✓[/green] Generated patch: {output}")
        console.print(f"[cyan]Files modified:[/cyan] {num_files}")
        console.print(f"[cyan]Fixes applied:[/cyan] {stats['fixes_applied']}\n")
        
        # Show how to apply
        panel_content = f"""[bold green]Patch generated successfully![/bold green]

[bold]To apply fixes:[/bold]
  git apply {output}

[bold]To review before applying:[/bold]
  git apply --check {output}
  cat {output}

[yellow]⚠️  Always review changes before committing![/yellow]"""
        
        console.print(Panel(panel_content, title="✅ Auto-Fix Ready", border_style="green"))
        
        # Summary of what was fixed
        console.print("\n[bold]Summary of fixes:[/bold]")
        
        unused_removed = sum(1 for r in reports 
                            for opp in r.get('optimization_opportunities', [])
                            if not opp.get('likely_used', True) and opp.get('cost', 0) > 500)
        
        fwd_added = sum(1 for fwd in fwd_opportunities 
                       if fwd.get('confidence', 0) >= min_confidence)
        
        if unused_removed > 0:
            console.print(f"  • Removed [red]{unused_removed}[/red] unused includes")
        if fwd_added > 0:
            console.print(f"  • Added [blue]{fwd_added}[/blue] forward declarations")
        
    except Exception as e:
        console.print(f"\n[red]❌ Error generating patch:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)

@main.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--compiler', '-c', default='g++', 
              help='Compiler to use (default: g++)')
@click.option('--timeout', '-t', default=30, type=int,
              help='Timeout per file in seconds (default: 30)')
def benchmark(project_path, compiler, timeout):
    """Validate accuracy by comparing estimated vs actual compilation times"""
    
    print_banner()
    
    import time
    import subprocess
    import tempfile
    from pathlib import Path
    import statistics
    
    project = Path(project_path).resolve()
    
    console.print(f"[bold cyan]>> Benchmarking: {project}[/bold cyan]")
    console.print(f"[dim]Compiler: {compiler} | Timeout: {timeout}s[/dim]\n")
    
    # Step 1: Run analysis
    console.print("[cyan]Step 1: Running IncludeGuard analysis...[/cyan]")
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Parsing files...", total=None)
        
        parser = IncludeParser(project)
        analyses = parser.parse_project()
        
        progress.update(task, description="Building dependency graph...")
        graph = DependencyGraph()
        graph.build(analyses)
        
        progress.update(task, description="Estimating costs...")
        estimator = CostEstimator(graph)
        
        all_analyses = {a.filepath: a for a in analyses}
        estimated_costs = {}
        
        for analysis in analyses:
            cost_results = estimator.analyze_file_costs(analysis, all_analyses)
            total_cost = sum(c['estimated_cost'] for c in cost_results)
            estimated_costs[str(analysis.filepath)] = total_cost
        
        progress.update(task, completed=True)
    
    console.print(f"[green][OK][/green] Estimated costs for {len(analyses)} files\n")
    
    # Step 2: Compile files and measure time
    console.print("[cyan]Step 2: Measuring actual compilation times...[/cyan]")
    
    actual_times = {}
    compilation_errors = []
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Compiling 0/{len(analyses)} files...", total=len(analyses))
        
        for i, filepath in enumerate(estimated_costs.keys()):
            file_path = Path(filepath)
            
            try:
                # Create temporary output file
                with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as tmp:
                    tmp_output = tmp.name
                
                # Compile and time
                start_time = time.time()
                result = subprocess.run(
                    [compiler, '-c', str(file_path), '-o', tmp_output],
                    capture_output=True,
                    timeout=timeout,
                    text=True
                )
                actual_time = time.time() - start_time
                
                # Clean up
                Path(tmp_output).unlink(missing_ok=True)
                
                if result.returncode == 0:
                    actual_times[str(filepath)] = actual_time
                else:
                    compilation_errors.append({
                        'file': str(file_path.name),
                        'error': result.stderr[:200] if result.stderr else 'Unknown error'
                    })
                
            except subprocess.TimeoutExpired:
                compilation_errors.append({
                    'file': str(file_path.name),
                    'error': f'Timeout after {timeout}s'
                })
            except Exception as e:
                compilation_errors.append({
                    'file': str(file_path.name),
                    'error': str(e)
                })
            
            progress.update(task, advance=1, description=f"Compiling {i+1}/{len(analyses)} files...")
    
    if not actual_times:
        console.print(f"\n[red][ERROR] Failed to compile any files![/red]")
        if compilation_errors:
            console.print("\n[dim]Errors:[/dim]")
            for err in compilation_errors[:5]:
                console.print(f"  • {err['file']}: {err['error']}")
        sys.exit(1)
    
    console.print(f"[green][OK][/green] Successfully compiled {len(actual_times)} files")
    if compilation_errors:
        console.print(f"[yellow][WARN][/yellow] {len(compilation_errors)} files failed to compile\n")
    
    # Step 3: Calculate correlation
    console.print("[cyan]Step 3: Analyzing correlation...[/cyan]\n")
    
    # Only compare files that compiled successfully
    matched_pairs = []
    for filepath, actual_time in actual_times.items():
        if filepath in estimated_costs:
            matched_pairs.append((estimated_costs[filepath], actual_time))
    
    if len(matched_pairs) < 2:
        console.print("[red][ERROR] Not enough successful compilations for correlation analysis[/red]")
        sys.exit(1)
    
    estimated_vals = [p[0] for p in matched_pairs]
    actual_vals = [p[1] for p in matched_pairs]
    
    # Calculate correlation coefficient
    mean_est = statistics.mean(estimated_vals)
    mean_act = statistics.mean(actual_vals)
    
    numerator = sum((e - mean_est) * (a - mean_act) for e, a in matched_pairs)
    denom1 = sum((e - mean_est) ** 2 for e in estimated_vals)
    denom2 = sum((a - mean_act) ** 2 for a in actual_vals)
    
    if denom1 > 0 and denom2 > 0:
        correlation = numerator / ((denom1 * denom2) ** 0.5)
        r_squared = correlation ** 2
    else:
        correlation = 0
        r_squared = 0
    
    # Display results table
    table = Table(title="Compilation Time Analysis", box=box.ROUNDED)
    table.add_column("File", style="cyan")
    table.add_column("Estimated (units)", justify="right", style="green")
    table.add_column("Actual (sec)", justify="right", style="blue")
    table.add_column("Ratio (units/sec)", justify="right", style="yellow")
    
    ratios = []
    for filepath, actual_time in list(actual_times.items())[:10]:  # Show top 10
        if actual_time > 0:
            ratio = estimated_costs[filepath] / actual_time
            ratios.append(ratio)
            table.add_row(
                Path(filepath).name,
                f"{estimated_costs[filepath]:,}",
                f"{actual_time:.3f}",
                f"{ratio:.2f}"
            )
    
    console.print(table)
    
    # Summary panel
    avg_ratio = statistics.mean(ratios) if ratios else 0
    
    summary = f"""[bold]Accuracy Metrics:[/bold]

[cyan]Correlation Coefficient:[/cyan]  {correlation:+.4f}
[cyan]R² (coefficient of determination):[/cyan] {r_squared:.4f} ({r_squared:.1%} variance explained)

[cyan]Average Ratio:[/cyan] {avg_ratio:.2f} units/sec
[cyan]Files Analyzed:[/cyan] {len(actual_times)}/{len(analyses)}

[bold]Interpretation:[/bold]
"""
    
    if correlation >= 0.90:
        summary += "[green][EXCELLENT] Excellent correlation[/green] - Estimates are highly accurate"
    elif correlation >= 0.75:
        summary += "[yellow][GOOD] Good correlation[/yellow] - Estimates are reasonably accurate"
    elif correlation >= 0.50:
        summary += "[yellow][MODERATE] Moderate correlation[/yellow] - Estimates have room for improvement"
    else:
        summary += "[red][POOR] Poor correlation[/red] - Model needs recalibration"
    
    console.print(Panel(summary, title="Benchmark Results", border_style="cyan"))
    
    # Confidence assessment
    if correlation >= 0.90:
        console.print("[green][OK][/green] Model is production-ready")
    elif correlation >= 0.75:
        console.print("[yellow][WARN][/yellow] Model is usable but could be improved")
    else:
        console.print("[red][FAIL][/red] Model needs significant improvement")


@main.command()
@click.argument('header')
@click.argument('filepath', type=click.Path(exists=True))
def explain(header, filepath):
    """Explain why a header was flagged as used/unused"""
    
    print_banner()
    
    filepath_obj = Path(filepath).resolve()
    
    if not filepath_obj.exists():
        console.print(f"[red]Error: File not found: {filepath}[/red]")
        sys.exit(1)
    
    console.print(f"[bold cyan]Analyzing:[/bold cyan] {header} in {filepath_obj.name}\n")
    
    # Parse the file
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing file...", total=None)
        
        parser = IncludeParser(filepath_obj.parent)
        file_analysis = parser.parse_file(filepath_obj)
        
        progress.update(task, completed=True)
    
    if not file_analysis:
        console.print("[red][ERROR] Could not parse file[/red]")
        sys.exit(1)
    
    # Find the header in includes
    header_found = None
    header_line = None
    
    for inc in file_analysis.includes:
        if header.lower() in inc.header.lower() or inc.header.lower() in header.lower():
            header_found = inc
            header_line = inc.line_number
            break
    
    if not header_found:
        console.print(f"[yellow][WARN][/yellow] Header '{header}' not found in includes")
        console.print(f"[dim]Available includes:[/dim]")
        for inc in file_analysis.includes[:5]:
            console.print(f"  • {inc.header} (line {inc.line_number})")
        return
    
    # Analyze patterns
    file_content = filepath_obj.read_text(errors='replace')
    lines = file_content.split('\n')
    
    # Pattern matching
    patterns = {
        'namespace_usage': {
            'name': 'Namespace usage (std::, boost::, etc)',
            'found': False,
            'examples': []
        },
        'direct_symbols': {
            'name': 'Direct symbol usage (cout, vector, etc)',
            'found': False,
            'examples': []
        },
        'type_usage': {
            'name': 'Type/class usage',
            'found': False,
            'examples': []
        }
    }
    
    # Get namespace hint from header
    namespace_hints = ['std', 'boost']
    
    for line_num, line in enumerate(lines, 1):
        if line_num == header_line:
            continue  # Skip include line itself
        
        # Check for namespace usage
        for ns in namespace_hints:
            if f'{ns}::' in line and not line.strip().startswith('//'):
                patterns['namespace_usage']['found'] = True
                patterns['namespace_usage']['examples'].append(
                    (line_num, line.strip()[:80])
                )
                break
        
        # Check for known stdlib symbols
        stdlib_symbols = ['cout', 'cin', 'vector', 'map', 'string', 'algorithm', 'unique_ptr']
        for symbol in stdlib_symbols:
            if symbol in line and not line.strip().startswith('//'):
                patterns['direct_symbols']['found'] = True
                patterns['direct_symbols']['examples'].append(
                    (line_num, line.strip()[:80])
                )
    
    # Calculate confidence
    found_patterns = sum(1 for p in patterns.values() if p['found'])
    total_patterns = len(patterns)
    confidence = (found_patterns / total_patterns) * 100 if total_patterns > 0 else 0
    
    # Display results
    console.print("[bold]Pattern Analysis:[/bold]\n")
    
    for pattern_key, pattern_info in patterns.items():
        status = "[green][OK][/green]" if pattern_info['found'] else "[red][FAIL][/red]"
        console.print(f"{status} {pattern_info['name']}")
        
        if pattern_info['examples']:
            for line_num, example in pattern_info['examples'][:2]:
                console.print(f"    [dim]line {line_num}: {example}[/dim]")
    
    console.print()
    
    # Verdict
    verdict_panel = f"""[bold]Header Usage Analysis:[/bold]

[cyan]Header:[/cyan] {header_found.header}
[cyan]Declared at:[/cyan] line {header_line}
[cyan]Patterns matched:[/cyan] {found_patterns}/{total_patterns}

[bold]Confidence Score:[/bold] {confidence:.0f}%

[bold]Verdict:[/bold]
"""
    
    if confidence >= 60:
        verdict_panel += "[green][OK] LIKELY USED[/green] in file"
    elif confidence >= 30:
        verdict_panel += "[yellow][?] UNCERTAIN[/yellow] - manual review recommended"
    else:
        verdict_panel += "[red][X] LIKELY UNUSED[/red] - consider removing"
    
    verdict_panel += f"""

[bold]Recommendation:[/bold]
[dim]This is an algorithmic estimate. Always:
1. Verify with grep/search
2. Check compilation without header
3. Run tests to confirm[/dim]"""
    
    console.print(Panel(verdict_panel, title="Analysis Result", border_style="cyan"))


@main.command()
@click.argument('project_path', type=click.Path(exists=True))
def stats(project_path):
    """Display project statistics and optimization priorities"""
    
    print_banner()
    
    project = Path(project_path).resolve()
    console.print(f"[bold cyan]Project Stats:[/bold cyan] {project}\n")
    
    # Run analysis
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scanning project...", total=None)
        
        parser = IncludeParser(project)
        analyses = parser.parse_project()
        
        progress.update(task, description="Building dependency graph...")
        graph = DependencyGraph()
        graph.build(analyses)
        
        progress.update(task, description="Calculating costs...")
        estimator = CostEstimator(graph)
        
        all_analyses = {a.filepath: a for a in analyses}
        file_costs = {}
        file_unused = {}
        
        for analysis in analyses:
            cost_results = estimator.analyze_file_costs(analysis, all_analyses)
            total_cost = sum(c['estimated_cost'] for c in cost_results)
            unused_count = sum(1 for c in cost_results if c.get('is_unused', False))
            
            file_costs[str(analysis.filepath)] = total_cost
            file_unused[str(analysis.filepath)] = unused_count
        
        progress.update(task, completed=True)
    
    # Calculate statistics
    total_files = len(analyses)
    total_includes = sum(len(a.includes) for a in analyses)
    total_cost = sum(file_costs.values())
    system_includes = sum(
        sum(1 for inc in a.includes if inc.is_system)
        for a in analyses
    )
    user_includes = total_includes - system_includes
    
    avg_includes = total_includes / total_files if total_files > 0 else 0
    avg_cost = total_cost / total_files if total_files > 0 else 0
    
    # Display overview
    console.print("[bold]Project Overview:[/bold]\n")
    
    overview_table = Table(box=box.ROUNDED)
    overview_table.add_column("Metric", style="cyan")
    overview_table.add_column("Value", justify="right", style="green")
    
    overview_table.add_row("Total Files", str(total_files))
    overview_table.add_row("Total Includes", f"{total_includes:,}")
    overview_table.add_row("  System Includes", f"{system_includes:,}")
    overview_table.add_row("  User Includes", f"{user_includes:,}")
    overview_table.add_row("Total Build Cost", f"{total_cost:,} units")
    overview_table.add_row("Avg Cost/File", f"{avg_cost:,.0f} units")
    overview_table.add_row("Avg Includes/File", f"{avg_includes:.1f}")
    
    console.print(overview_table)
    
    # Most problematic files
    console.print("\n[bold]Most Problematic Files (High Cost):[/bold]\n")
    
    sorted_files = sorted(file_costs.items(), key=lambda x: x[1], reverse=True)
    
    file_table = Table(box=box.ROUNDED)
    file_table.add_column("File", style="cyan")
    file_table.add_column("Cost", justify="right", style="yellow")
    file_table.add_column("% of Total", justify="right")
    file_table.add_column("Issues", justify="right", style="red")
    
    for filepath, cost in sorted_files[:10]:
        filename = Path(filepath).name
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0
        issues = file_unused.get(filepath, 0)
        
        file_table.add_row(
            filename,
            f"{cost:,}",
            f"{percentage:.1f}%",
            str(issues)
        )
    
    console.print(file_table)
    
    # Recommendations
    if sorted_files:
        top_file = Path(sorted_files[0][0]).name
        top_cost = sorted_files[0][1]
        top_pct = (top_cost / total_cost * 100) if total_cost > 0 else 0
        
        console.print(f"\n[bold]Optimization Priority:[/bold]")
        console.print(f"[cyan]Start with:[/cyan] {top_file} ({top_cost:,} units, {top_pct:.1f}% of total)")
        console.print(f"[dim]Removing unnecessary includes from this file would have the biggest impact.[/dim]")
    
    console.print(f"\n[bold]Next Steps:[/bold]")
    console.print("[dim]1. Run 'includeguard explain <header> <file>' to analyze specific headers")
    console.print("2. Use 'includeguard benchmark' to validate accuracy")
    console.print("3. Use 'includeguard watch' for real-time monitoring[/dim]")


@main.command()
@click.argument('json_file1', type=click.Path(exists=True))
@click.argument('json_file2', type=click.Path(exists=True))
@click.option('--threshold', '-t', default=10, type=float,
              help='Show changes greater than this percentage (default: 10%)')
def compare(json_file1, json_file2, threshold):
    """Compare two analysis results to track optimization progress"""
    
    print_banner()
    
    console.print("[bold cyan]Comparing Analysis Results[/bold cyan]\n")
    
    # Load results
    with open(json_file1) as f:
        result1 = json.load(f)
    with open(json_file2) as f:
        result2 = json.load(f)
    
    # Compare overall metrics
    console.print("[bold]Overall Metrics Comparison:[/bold]\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Change", justify="right")
    
    metrics_to_compare = [
        ('total_cost', 'Total Build Cost', lambda x: f"{x:,}"),
        ('wasted_cost', 'Wasted Cost', lambda x: f"{x:,}"),
        ('waste_percentage', 'Waste %', lambda x: f"{x:.1f}%"),
    ]
    
    improvements = 0
    regressions = 0
    
    for key, label, formatter in metrics_to_compare:
        val1 = result1.get(key, 0)
        val2 = result2.get(key, 0)
        
        if val1 == 0:
            change_str = "N/A"
        else:
            change_pct = ((val2 - val1) / val1) * 100
            change_str = f"{change_pct:+.1f}%"
            
            if key == 'waste_percentage':
                if change_pct < -threshold:
                    improvements += 1
                elif change_pct > threshold:
                    regressions += 1
        
        val1_str = formatter(val1)
        val2_str = formatter(val2)
        
        style = "red" if ("+" in change_str and "-" not in change_str and key != 'waste_percentage') else "green"
        
        table.add_row(label, val1_str, val2_str, f"[{style}]{change_str}[/{style}]")
    
    console.print(table)
    
    # File-by-file comparison
    console.print("\n[bold]File-by-File Changes:[/bold]\n")
    
    file_changes = []
    
    reports1 = {r['file']: r for r in result1.get('reports', [])}
    reports2 = {r['file']: r for r in result2.get('reports', [])}
    
    all_files = set(reports1.keys()) | set(reports2.keys())
    
    for filepath in sorted(all_files):
        cost1 = reports1.get(filepath, {}).get('total_estimated_cost', 0)
        cost2 = reports2.get(filepath, {}).get('total_estimated_cost', 0)
        
        if cost1 == 0:
            continue
        
        change_pct = ((cost2 - cost1) / cost1) * 100
        
        if abs(change_pct) >= threshold:
            file_changes.append({
                'file': filepath,
                'before': cost1,
                'after': cost2,
                'change': change_pct
            })
    
    # Sort by improvement
    file_changes.sort(key=lambda x: x['change'])
    
    if file_changes:
        # Show improvements
        improvements_list = [c for c in file_changes if c['change'] < 0]
        if improvements_list:
            console.print("[green][IMPROVEMENTS][/green]")
            for change in improvements_list[:5]:
                console.print(f"  {Path(change['file']).name}: {change['change']:+.1f}% "
                            f"({change['before']:,} -> {change['after']:,} units)")
        
        # Show regressions
        regressions_list = [c for c in file_changes if c['change'] > 0]
        if regressions_list:
            console.print("\n[red][REGRESSIONS][/red]")
            for change in regressions_list[:5]:
                console.print(f"  {Path(change['file']).name}: {change['change']:+.1f}% "
                            f"({change['before']:,} -> {change['after']:,} units)")
    else:
        console.print("[yellow][WARN][/yellow] No significant changes detected")
    
    # Summary
    overall_waste1 = result1.get('waste_percentage', 0)
    overall_waste2 = result2.get('waste_percentage', 0)
    overall_change = overall_waste2 - overall_waste1
    
    summary = f"""[bold]Summary:[/bold]

Overall waste: {overall_waste1:.1f}% → {overall_waste2:.1f}% ({overall_change:+.1f}%)
"""
    
    if overall_change < 0:
        summary += "[green][IMPROVING] Project is getting BETTER[/green]"
    elif overall_change > 0:
        summary += "[red][DECLINING] Project is getting WORSE[/red]"
    else:
        summary += "[blue][STABLE] No change[/blue]"
    
    console.print(Panel(summary, title="📈 Overall Trend", border_style="cyan"))


@main.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--interval', '-i', default=2, type=int,
              help='Poll interval in seconds (default: 2)')
def watch(project_path, interval):
    """Monitor project files and automatically re-analyze on changes"""
    
    print_banner()
    
    import time
    from pathlib import Path
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    
    project = Path(project_path).resolve()
    
    console.print(f"[bold cyan]>> Watching:[/bold cyan] {project}")
    console.print(f"[dim]Polling interval: {interval}s[/dim]\n")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    # Track file modification times
    file_timestamps = {}
    last_analysis_time = {}
    
    def get_cpp_files():
        """Get all C++ files in project"""
        extensions = {'.cpp', '.h', '.hpp', '.c', '.cc', '.cxx'}
        files = []
        for ext in extensions:
            files.extend(project.rglob(f'*{ext}'))
        return [f for f in files if '.git' not in f.parts and 'build' not in f.parts]
    
    def analyze_and_report(filepath):
        """Analyze a single file and report changes"""
        try:
            parser = IncludeParser(filepath.parent)
            analysis = parser.parse_file(filepath)
            
            if not analysis:
                return None
            
            graph = DependencyGraph()
            graph.build([analysis])
            
            estimator = CostEstimator(graph)
            cost_results = estimator.analyze_file_costs(analysis, {str(filepath): analysis})
            total_cost = sum(c['estimated_cost'] for c in cost_results)
            
            return {
                'file': str(filepath),
                'cost': total_cost,
                'includes': len(analysis.includes),
                'timestamp': time.time()
            }
        except Exception as e:
            return None
    
    # Initial scan
    cpp_files = get_cpp_files()
    console.print(f"[dim]Found {len(cpp_files)} C++ files[/dim]\n")
    
    for filepath in cpp_files:
        file_timestamps[str(filepath)] = filepath.stat().st_mtime
    
    try:
        iteration = 0
        while True:
            iteration += 1
            time.sleep(interval)
            
            changes = []
            
            # Check for modified files
            for filepath in cpp_files:
                filepath_str = str(filepath)
                current_mtime = filepath.stat().st_mtime
                
                if filepath_str not in file_timestamps:
                    file_timestamps[filepath_str] = current_mtime
                    changes.append(('new', filepath))
                elif file_timestamps[filepath_str] != current_mtime:
                    file_timestamps[filepath_str] = current_mtime
                    changes.append(('modified', filepath))
            
            # Check for deleted files
            for filepath_str in list(file_timestamps.keys()):
                if not Path(filepath_str).exists():
                    del file_timestamps[filepath_str]
                    changes.append(('deleted', Path(filepath_str)))
            
            # Check for new files
            current_files = set(str(f) for f in get_cpp_files())
            for new_file in current_files - set(file_timestamps.keys()):
                file_timestamps[new_file] = Path(new_file).stat().st_mtime
                changes.append(('new', Path(new_file)))
            
            if changes:
                timestamp = time.strftime('%H:%M:%S')
                console.print(f"\n[cyan][{timestamp}][/cyan] Detected {len(changes)} change(s)")
                
                for change_type, filepath in changes:
                    symbol = {'new': '[NEW]', 'modified': '[CHNG]', 'deleted': '[DEL]'}[change_type]
                    console.print(f"  {symbol} {change_type.upper()}: {filepath.name}")
                
                # Analyze modified files
                for change_type, filepath in changes:
                    if change_type != 'deleted':
                        start = time.time()
                        result = analyze_and_report(filepath)
                        duration = time.time() - start
                        
                        if result:
                            console.print(f"  [green][OK][/green] Analyzed in {duration:.2f}s")
                            console.print(f"    Cost: {result['cost']:,} units | Includes: {result['includes']}")
                            
                            # Compare with previous
                            if str(filepath) in last_analysis_time:
                                prev_result = last_analysis_time[str(filepath)]
                                cost_change = result['cost'] - prev_result['cost']
                                
                                if cost_change < 0:
                                    console.print(f"    [green][OK] Cost improved: {abs(cost_change):,} units saved[/green]")
                                elif cost_change > 0:
                                    console.print(f"    [red][!] Cost increased: {cost_change:,} units added[/red]")
                            
                            last_analysis_time[str(filepath)] = result
                        else:
                            console.print(f"  [red][FAIL][/red] Analysis failed")
                
                console.print(f"[dim]Watching... (next check in {interval}s)[/dim]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]\nWatch stopped (interrupted by user)[/yellow]")


@main.command()
@click.argument('project_path', type=click.Path(exists=True), required=False)
@click.option('--force', '-f', is_flag=True, help='Overwrite existing config')
def init(project_path, force):
    """Initialize IncludeGuard configuration for a project"""
    
    print_banner()
    
    project = Path(project_path or '.').resolve()
    config_file = project / '.includeguard.yml'
    
    if config_file.exists() and not force:
        console.print(f"[yellow][WARN][/yellow] Configuration already exists: {config_file}")
        console.print("[dim]Use --force to overwrite[/dim]")
        return
    
    console.print(f"[bold cyan]Setting up IncludeGuard for:[/bold cyan] {project}\n")
    
    # Ask configuration questions
    config = {
        'project_name': project.name,
        'max_files': 500,
        'extensions': ['.cpp', '.h', '.hpp', '.c', '.cc', '.cxx'],
        'exclude_patterns': [
            '*/third_party/*',
            '*/build/*',
            '*/dist/*',
            '*/.venv/*',
            '*/node_modules/*'
        ],
        'thresholds': {
            'warning': 30,
            'error': 50
        },
        'compilation': {
            'compiler': 'g++',
            'timeout': 30
        },
        'output': {
            'formats': ['html', 'json'],
            'directory': 'includeguard_reports'
        }
    }
    
    console.print("[bold]Configuration Template:[/bold]\n")
    
    config_yaml = f"""# IncludeGuard Configuration
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

project_name: {config['project_name']}

# Maximum files to analyze (use for large projects)
max_files: {config['max_files']}

# File extensions to include in analysis
extensions:
  - .cpp
  - .h
  - .hpp
  - .c
  - .cc
  - .cxx

# Patterns to exclude from analysis
exclude_patterns:
  - '*/third_party/*'
  - '*/build/*'
  - '*/dist/*'
  - '*/.venv/*'
  - '*/node_modules/*'

# Waste percentage thresholds
thresholds:
  warning: 30  # Warn if waste > 30%
  error: 50    # Error if waste > 50%

# Compilation benchmarking settings
compilation:
  compiler: g++       # Compiler to use for benchmarking
  timeout: 30         # Timeout in seconds per file
  
# Output settings
output:
  formats:            # Output formats to generate
    - html
    - json
  directory: includeguard_reports  # Where to save reports

# CI/CD integration
ci:
  enabled: false
  fail_on_error: true
  comment_on_pr: true
  min_confidence: 0.7
"""
    
    console.print("[dim]" + config_yaml + "[/dim]\n")
    
    # Write config file
    config_file.write_text(config_yaml)
    
    console.print(f"[green]✓[/green] Configuration created: [cyan]{config_file}[/cyan]")
    console.print(f"[green]✓[/green] Edit this file to customize settings")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. Review [cyan].includeguard.yml[/cyan]")
    console.print(f"  2. Run [cyan]includeguard analyze .[/cyan] to analyze project")
    console.print(f"  3. Run [cyan]includeguard benchmark .[/cyan] to validate estimates")
    console.print(f"  4. Run [cyan]includeguard watch .[/cyan] to monitor changes")


if __name__ == '__main__':
    main()
