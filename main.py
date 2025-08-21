import os
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from modules.content_discoverer import ContentDiscoverer
from utils.context import ScanContext

console = Console()


reports_dir = "reports"

if not os.path.exists(reports_dir):
    os.makedirs(reports_dir)


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


def print_scan_summary(url, wordlist, threads, profile, recursion, include_regex, exclude_regex, delay, output_path, formats):
    summary_table = Table(show_header=False, box=None)
    summary_table.add_row("🌍 Target", f"[yellow]{url}[/yellow]")
    summary_table.add_row("📂 Wordlist", wordlist)
    summary_table.add_row("⚙️ Threads", str(threads))
    summary_table.add_row("🚀 Profile", profile)
    summary_table.add_row("🔁 Recursion", str(recursion))
    summary_table.add_row("⏱ Delay", f"{delay}s")
    summary_table.add_row("✅ Include Regex", str(include_regex) if include_regex else "None")
    summary_table.add_row("❌ Exclude Regex", str(exclude_regex) if exclude_regex else "None")
    summary_table.add_row("💾 Output Base", output_path)
    summary_table.add_row("📄 Formats", ", ".join(formats))
    console.print(Panel(summary_table, title="[bold green]Scan Configuration[/bold green]", border_style="green"))


def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="PathHunter - Web Content Discovery Tool")
    parser.add_argument("url", help="Target URL (must start with http:// or https://)")
    parser.add_argument("-w", "--wordlist", help="Path to custom wordlist file (overrides --mode)")
    parser.add_argument("-t", "--threads", type=int, default=30, help="Number of threads")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests")
    parser.add_argument("--profile", choices=["stealth", "balanced", "aggressive"], default="balanced", help="Scan profile")
    parser.add_argument("--recursion", action="store_true", help="Enable recursion (experimental)")
    parser.add_argument("--include-regex", help="Only include responses whose body matches this regex")
    parser.add_argument("--exclude-regex", help="Exclude responses whose body matches this regex")
    parser.add_argument("--mode", choices=["fast", "balanced", "deep"], default="balanced", help="Scan mode to select wordlist automatically")
    parser.add_argument("-o", "--output", default="scan_results", help="Output base filename (extension auto-added per format)")
    parser.add_argument("--format", default="json", help="Comma-separated formats: json,csv,txt or 'all'")
    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith(("http://", "https://")):
        console.print("[bold red][ERROR][/bold red] Invalid URL. It must start with http:// or https://")
        exit(1)

    # Map modes to wordlist files
    wordlist_map = {
        "fast": os.path.join(BASE_DIR, "wordlists", "common.txt"),
        "balanced": os.path.join(BASE_DIR, "wordlists", "medium.txt"),
        "deep": os.path.join(BASE_DIR, "wordlists", "large.txt"),
    }

    # Determine wordlist
    if args.wordlist:
        wordlist_path = args.wordlist
        if not os.path.isabs(wordlist_path):
            wordlist_path = os.path.join(BASE_DIR, wordlist_path)
    else:
        wordlist_path = wordlist_map.get(args.mode, wordlist_map["balanced"])

    # Check wordlist exists
    if not os.path.isfile(wordlist_path):
        console.print(f"[bold red][ERROR][/bold red] Wordlist not found: {wordlist_path}")
        exit(1)

    # Normalize formats
    formats = [f.strip().lower() for f in args.format.split(",")]
    if "all" in formats:
        formats = ["json", "csv", "txt"]

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
        args.output,
        formats,
    )

    # Init scan context
    context = ScanContext(target_url=args.url, wordlist_path=wordlist_path)

    # Build discoverer
    discoverer = ContentDiscoverer(
        context=context,
        threads=args.threads,
        delay=args.delay,
        profile=args.profile,
        recursion=args.recursion,
        include_regex=args.include_regex,
        exclude_regex=args.exclude_regex,
        output_path=args.output,
        formats=formats,
        verify_ssl=True,  # adjust or expose flag
    )

    console.print(f"\n🚀 Starting {args.mode.upper()} scan on: {args.url}")
    console.print(f"📂 Using wordlist: {wordlist_path}\n")

    discoverer.run(args.url, wordlist_path)

    # Show where files went
    base = os.path.abspath(args.output)
    got = ", ".join(formats)
    console.print(f"\n✅ [bold green]Scan complete! Results saved (formats: {got}) with base: {base}[/bold green]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n⚠️ [bold red]Scan interrupted by user. Exiting...[/bold red]")
