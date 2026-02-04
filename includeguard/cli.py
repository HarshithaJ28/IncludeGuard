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
from includeguard.analyzer.forward_declaration import ForwardDeclarationDetector
from includeguard.analyzer.pch_recommender import PCHRecommender
from includeguard.analyzer.build_profiler import BuildProfiler
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
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
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
            SpinnerColumn(),
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

if __name__ == '__main__':
    main()
