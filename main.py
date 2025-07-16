import os
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from modules.content_discoverer import ContentDiscoverer
from utils.context import ScanContext

console = Console()

def print_banner():
    banner = """
██████   █████ ████████ ██   ██ ██    ██ ███    ██ ████████ ███████ ██████  
██   ██ ██   ██  ██     ██   ██ ██    ██ ████   ██    ██    ██      ██   ██ 
██████  ███████  ██     ███████ ██    ██ ██ ██  ██    ██    █████   ██████  
██      ██   ██  ██     ██   ██ ██    ██ ██  ██ ██    ██    ██      ██   ██ 
██      ██   ██  ██     ██   ██  ██████  ██   ████    ██    ███████ ██   ██ 
    Advanced Web Content Discovery Tool 
    """
    console.print(Panel(banner, style="bold cyan"))


def print_scan_summary(url, wordlist, threads, profile, recursion, include_regex, exclude_regex, delay):
    summary_table = Table(show_header=False, box=None)
    summary_table.add_row("🌍 Target", f"[yellow]{url}[/yellow]")
    summary_table.add_row("📂 Wordlist", wordlist)
    summary_table.add_row("⚙️ Threads", str(threads))
    summary_table.add_row("🚀 Profile", profile)
    summary_table.add_row("🔁 Recursion", str(recursion))
    summary_table.add_row("⏱ Delay", f"{delay}s")
    summary_table.add_row("✅ Include Regex", str(include_regex) if include_regex else "None")
    summary_table.add_row("❌ Exclude Regex", str(exclude_regex) if exclude_regex else "None")
    console.print(Panel(summary_table, title="[bold green]Scan Configuration[/bold green]", border_style="green"))


def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="Web Content Discovery Tool")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("-w", "--wordlist", help="Path to wordlist file (overrides --mode)")
    parser.add_argument("-t", "--threads", type=int, default=30, help="Number of threads")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests")
    parser.add_argument("--profile", choices=["stealth", "balanced", "aggressive"], default="balanced", help="Scan profile")
    parser.add_argument("--recursion", action="store_true", help="Enable recursion")
    parser.add_argument("--include-regex", help="Only include responses matching regex")
    parser.add_argument("--exclude-regex", help="Exclude responses matching regex")
    parser.add_argument("--mode", choices=["fast", "balanced", "stealth"], default="balanced", help="Scan mode to select wordlist automatically")
    args = parser.parse_args()

    # Map modes to wordlist files (absolute paths)
    wordlist_map = {
        "fast": os.path.join(BASE_DIR, "wordlists", "common.txt"),
        "balanced": os.path.join(BASE_DIR, "wordlists", "large.txt"),
        "stealth": os.path.join(BASE_DIR, "wordlists", "logger.txt"),
    }

    # Determine which wordlist to use
    if args.wordlist:
        wordlist_path = args.wordlist
        # If relative path, make absolute relative to BASE_DIR
        if not os.path.isabs(wordlist_path):
            wordlist_path = os.path.join(BASE_DIR, wordlist_path)
    else:
        wordlist_path = wordlist_map.get(args.mode, wordlist_map["balanced"])

    # Check if wordlist file exists
    if not os.path.isfile(wordlist_path):
        console.print(f"[bold red][ERROR][/bold red] Wordlist not found: {wordlist_path}")
        return

    print_banner()
    print_scan_summary(
        args.url,
        wordlist_path,
        args.threads,
        args.profile,
        args.recursion,
        args.include_regex,
        args.exclude_regex,
        args.delay,
    )

    context = ScanContext(target_url=args.url, wordlist_path=wordlist_path)
    discoverer = ContentDiscoverer(
        context=context,
        threads=args.threads,
        delay=args.delay,
        profile=args.profile,
        recursion=args.recursion,
        include_regex=args.include_regex,
        exclude_regex=args.exclude_regex,
    )

    console.print(f"\n🚀 Starting {args.mode.upper()} scan on: {args.url}")
    console.print(f"📂 Using wordlist: {wordlist_path}\n")

    discoverer.run(args.url, wordlist_path)

    console.print("\n✅ [bold green]Scan complete! Results saved to scan_results.json[/bold green]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n⚠️ [bold red]Scan interrupted by user. Exiting...[/bold red]")
