"""
Enhanced UI formatting for IncludeGuard with Rich.

Provides beautiful, modern terminal output.
"""
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, DownloadColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.box import ROUNDED, HEAVY_HEAD
from rich.align import Align
from rich.tree import Tree
from rich.text import Text
from rich.syntax import Syntax
from rich.columns import Columns
import json
from typing import List, Dict, Optional
from pathlib import Path


class RichFormatter:
    """Enhanced Rich-based formatter for IncludeGuard output."""
    
    def __init__(self, width: int = 120, no_color: bool = False):
        """
        Initialize formatter.
        
        Args:
            width: Console width
            no_color: Disable colored output
        """
        self.console = Console(width=width, no_color=no_color, force_terminal=True)
        self.width = width
    
    def print_banner(self, version: str = "2.0.0"):
        """Print IncludeGuard banner."""
        banner = """
        ___            __          __    ______                     __
       /  _/___  _____/ /_  ______/ /__ / ____/_  ______ __________/ /
       / // __ \/ ___/ / / / / __  / _ \/ / __/ / / / __ `/ ___/ __  / 
     _/ // / / / /__/ / /_/ / /_/ /  __/ /_/ / /_/ / /_/ / /  / /_/ /  
    /___/_/ /_/\___/_/\__,_/\__,_/\___/\____/\__,_/\__,_/_/   \__,_/   
        """
        self.console.print()
        self.console.print(banner, style="bold magenta")
        self.console.print(
            Align.center(
                f"[bold cyan]IncludeGuard[/bold cyan] [dim]v{version}[/dim] - "
                "[green]C++ Include Analyzer[/green]"
            )
        )
        self.console.print()
    
    def print_analysis_summary(self, summary: Dict) -> None:
        """Print analysis summary with metrics."""
        metrics = [
            ("Files Analyzed", str(summary.get('total_files', 0)), "blue"),
            ("Includes Found", str(summary.get('total_includes', 0)), "cyan"),
            ("Unused Includes", str(sum(u['unused'] for u in summary.get('reports', []))), "yellow"),
            ("Build Cost", f"{summary.get('total_cost', 0):.1f}MB", "magenta"),
            ("Wasted Cost", f"{summary.get('total_waste', 0):.1f}MB", "red"),
        ]
        
        # Create metric display
        metric_panels = []
        for label, value, color in metrics:
            panel = Panel(
                Align.center(f"[bold {color}]{value}[/bold {color}]"),
                title=f"[bold {color}]{label}[/bold {color}]",
                expand=False,
                padding=(1, 2)
            )
            metric_panels.append(panel)
        
        # Display in columns
        if len(metric_panels) <= 3:
            self.console.print(Columns(metric_panels))
        else:
            for i in range(0, len(metric_panels), 3):
                self.console.print(Columns(metric_panels[i:i+3]))
    
    def print_unused_includes_table(self, unused: List[Dict], limit: int = 20) -> None:
        """Print table of unused includes."""
        table = Table(
            title="[bold red]UNUSED INCLUDES[/bold red]",
            box=HEAVY_HEAD,
            show_header=True,
            header_style="bold white on dark_blue"
        )
        
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")
        table.add_column("Header", style="magenta")
        table.add_column("Cost", style="red")
        table.add_column("Confidence", style="green")
        
        for i, inc in enumerate(unused[:limit]):
            confidence_pct = f"{inc.get('confidence', 0) * 100:.0f}%"
            confidence_style = "green" if inc.get('confidence', 0) > 0.8 else "yellow"
            
            table.add_row(
                str(Path(inc.get('file', '')).name),
                str(inc.get('line', '')),
                inc.get('header', ''),
                f"{inc.get('cost', 0):.1f}MB",
                Text(confidence_pct, style=confidence_style)
            )
        
        self.console.print(table)
        
        if len(unused) > limit:
            self.console.print(
                f"[dim]... and {len(unused) - limit} more[/dim]"
            )
    
    def print_file_report(self, filepath: str, report: Dict) -> None:
        """Print detailed report for single file."""
        title = f"[bold blue]Analysis: {Path(filepath).name}[/bold blue]"
        
        table = Table(title=title, box=ROUNDED)
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="cyan")
        
        table.add_row("Path", str(filepath))
        table.add_row("Total Includes", str(report.get('total_includes', 0)))
        table.add_row("Used Includes", str(report.get('used_includes', 0)))
        table.add_row("Unused Includes", str(report.get('unused_includes', 0)))
        table.add_row("Total Cost", f"{report.get('total_cost', 0):.1f}MB")
        table.add_row("Wasted Cost", f"{report.get('wasted_cost', 0):.1f}MB")
        
        self.console.print(table)
    
    def print_dependency_tree(self, tree_data: Dict) -> None:
        """Print include dependency tree."""
        tree = Tree("[bold magenta]Include Dependencies[/bold magenta]")
        
        def add_nodes(parent_node, data: Dict, depth: int = 0):
            if depth > 5:  # Limit depth to avoid huge trees
                return
            
            for key, value in data.items():
                if isinstance(value, dict):
                    node = parent_node.add(f"[cyan]{key}[/cyan]")
                    add_nodes(node, value, depth + 1)
                else:
                    parent_node.add(f"[yellow]{key}[/yellow]: {value}")
        
        add_nodes(tree, tree_data)
        self.console.print(tree)
    
    def print_recommendations(self, recommendations: List[str]) -> None:
        """Print recommendations panel."""
        if not recommendations:
            return
        
        recommendations_text = "\n".join(
            f"• {rec}" for rec in recommendations
        )
        
        panel = Panel(
            recommendations_text,
            title="[bold green]RECOMMENDATIONS[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def print_error(self, error: str, details: str = None) -> None:
        """Print error in prominent way."""
        error_panel = Panel(
            error,
            title="[bold white on red]ERROR[/bold white on red]",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(error_panel)
        
        if details:
            self.console.print(f"[dim]{details}[/dim]")
    
    def print_warning(self, warning: str) -> None:
        """Print warning message."""
        self.console.print(f"[bold yellow]⚠  WARNING:[/bold yellow] {warning}")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[bold green]✓[/bold green] {message}")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"[bold cyan]ℹ[/bold cyan] {message}")
    
    def create_progress_bar(self, description: str, total: int = 100):
        """Create a progress bar for long operations."""
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
    
    def print_code_snippet(self, code: str, language: str = "cpp", 
                          theme: str = "monokai", line_numbers: bool = True) -> None:
        """Print code with syntax highlighting."""
        syntax = Syntax(
            code,
            language,
            theme=theme,
            line_numbers=line_numbers,
            background_color="default"
        )
        self.console.print(syntax)
    
    def print_json_report(self, data: Dict) -> None:
        """Print JSON report with formatting."""
        json_str = json.dumps(data, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai")
        self.console.print(syntax)
    
    def print_horizontal_rule(self, title: str = "") -> None:
        """Print horizontal rule."""
        if title:
            self.console.rule(f"[bold cyan]{title}[/bold cyan]")
        else:
            self.console.rule()


class ProgressIndicator:
    """Smart progress indication for analysis operations."""
    
    def __init__(self, formatter: RichFormatter):
        """
        Initialize progress indicator.
        
        Args:
            formatter: RichFormatter instance
        """
        self.formatter = formatter
        self.progress = None
    
    def start_parsing(self, file_count: int):
        """Start progress bar for parsing."""
        self.progress = self.formatter.create_progress_bar("Parsing files...")
        return self.progress.add_task("[cyan]Parsing...", total=file_count)
    
    def start_analysis(self):
        """Start progress bar for analysis."""
        self.progress = self.formatter.create_progress_bar("Analyzing includes...")
        return self.progress.add_task("[magenta]Analyzing...", total=100)
    
    def finish(self):
        """Finish progress tracking."""
        if self.progress:
            self.progress.stop()


# Global formatter instance
_global_formatter: Optional[RichFormatter] = None
_formatter_lock = None


def _get_formatter_lock():
    """Get thread lock for formatter singleton (lazy init)."""
    global _formatter_lock
    if _formatter_lock is None:
        import threading
        _formatter_lock = threading.Lock()
    return _formatter_lock


def get_formatter(width: int = 120, no_color: bool = False) -> RichFormatter:
    """Get or create global formatter instance.
    
    Thread-safe singleton pattern.
    """
    global _global_formatter
    
    # Fast path check (no lock needed if already initialized)
    if _global_formatter is not None:
        return _global_formatter
    
    # Acquire lock for initialization
    with _get_formatter_lock():
        # Double-check pattern
        if _global_formatter is None:
            _global_formatter = RichFormatter(width=width, no_color=no_color)
        return _global_formatter
