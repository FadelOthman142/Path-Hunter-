from rich.live import Live
from rich.table import Table
from rich.console import Console
from time import sleep

console = Console()

def live_scan_display(get_status_func, total_tasks):
    """
    Displays a live updating table for scan progress.

    Args:
        get_status_func: A callback function that returns a list of dicts with keys:
                         'status', 'url', 'severity' representing current scan results.
        total_tasks: Total number of scan tasks (for progress).
    """
    with Live(refresh_per_second=4, console=console, transient=False) as live:
        while True:
            data = get_status_func()  # Get latest scan results

            table = Table(title=f"Scanning... {len(data)}/{total_tasks} tasks completed")
            table.add_column("Status", justify="center")
            table.add_column("URL", overflow="fold")
            table.add_column("Severity", justify="center")

            for item in data:
                table.add_row(str(item["status"]), item["url"], item["severity"])

            live.update(table)

            # Break condition when scanning done (can be controlled externally)
            if len(data) >= total_tasks:
                break

            sleep(0.25)  # refresh interval
