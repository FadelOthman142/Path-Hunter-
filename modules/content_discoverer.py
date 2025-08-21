import os
import time
import random
import threading
import queue
import requests
import re
import json
import csv
import urllib3
from urllib.parse import urljoin

from utils.context import ScanContext
from utils.logger import log_error, log_info

from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table

console = Console()

# --------------------------------------------------------------------------- #
# Globals / Defaults
# --------------------------------------------------------------------------- #
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)",
]

DEFAULT_EXTENSIONS = ["php", "html", "bak", "txt", "zip", "asp", "aspx"]
DEFAULT_INTERESTING_CODES = {200, 204, 301, 302, 307, 308, 401, 403, 405}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# --------------------------------------------------------------------------- #
# UI helpers
# --------------------------------------------------------------------------- #
def format_status(status_code: int) -> str:
    if 200 <= status_code < 300:
        return f"[bold green]{status_code}[/bold green] ✅"
    elif 300 <= status_code < 400:
        return f"[bold blue]{status_code}[/bold blue] 🔵"
    elif 400 <= status_code < 500:
        return f"[bold yellow]{status_code}[/bold yellow] ⚠️"
    else:
        return f"[bold red]{status_code}[/bold red] 🔥"


def get_severity(path: str) -> str:
    high_risk = [".bak", ".sql", ".env", ".config", ".php", ".ini"]
    medium_risk = [".log", ".txt", ".zip"]
    lower = path.lower()
    for ext in high_risk:
        if lower.endswith(ext):
            return "🔥 High Risk"
    for ext in medium_risk:
        if lower.endswith(ext):
            return "⚠️ Medium Risk"
    return "ℹ️ Low Risk"


# --------------------------------------------------------------------------- #
# ContentDiscoverer
# --------------------------------------------------------------------------- #
class ContentDiscoverer:
    """
    Rich-enabled, threaded web content discoverer.

    Scans a target URL using a wordlist (and per-extension permutations),
    displays live progress, collects interesting responses, attempts simple
    bypasses on 403/401, and saves results in JSON / CSV / TXT formats.
    """

    def __init__(
        self,
        context: ScanContext,
        threads: int = 30,
        delay: float = 0.1,
        status_filter=None,
        extensions=None,
        recursion: bool = True,
        proxies=None,
        profile: str = "balanced",
        include_regex: str = None,
        exclude_regex: str = None,
        output_path: str = "scan_results",  # base filename, ext auto-added per format
        formats=None,
        verify_ssl: bool = True,
        timeout: int = 10,
        interesting_codes=None,
    ):
        self.context = context

        # --- profile tuning ---
        profile = (profile or "balanced").lower()
        if profile == "stealth":
            self.threads = min(threads, 10)
            self.base_delay = max(delay, 1.5)
        elif profile == "aggressive":
            self.threads = max(threads, 100)
            self.base_delay = max(delay, 0.01)
        else:  # balanced
            self.threads = threads
            self.base_delay = delay

        self.delay = self.base_delay
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.proxies = proxies
        self.recursion = recursion

        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.status_filter = status_filter or DEFAULT_INTERESTING_CODES
        self.interesting_codes = interesting_codes or DEFAULT_INTERESTING_CODES

        # Regex filters on response *content* (body)
        self.include_regex = re.compile(include_regex, re.IGNORECASE) if include_regex else None
        self.exclude_regex = re.compile(exclude_regex, re.IGNORECASE) if exclude_regex else None

        # Work queue
        self.task_queue = queue.Queue()
        self.shutdown_event = threading.Event()

        # Progress tracking
        self.total_tasks_lock = threading.Lock()
        self.total_tasks = 0
        self.completed_tasks = 0

        # For recursion and duplicate suppression
        self.visited_lock = threading.Lock()
        self.visited = set()

        # UI state
        self.ui_lock = threading.Lock()
        self.displayed_urls = set()  # Track which URLs have been displayed

        # Rich progress + table
        self.progress_bar = Progress(
            TextColumn("[cyan]Scanning...[/cyan]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}")
        )
        self.result_table = Table(show_header=True, header_style="bold magenta")
        self.result_table.add_column("Status", style="cyan", width=10)
        self.result_table.add_column("URL", style="white")
        self.result_table.add_column("Severity", style="yellow")

        # Output selection
        self.output_base = output_path  # may include extension; extensions added per format
        if formats is None:
            formats = ["json"]
        if isinstance(formats, str):
            formats = [fmt.strip().lower() for fmt in formats.split(",")]
        self.formats = [f.lower() for f in formats]
        if "all" in self.formats:
            self.formats = ["json", "csv", "txt"]

    # ------------------------------------------------------------------ #
    # Wordlist
    # ------------------------------------------------------------------ #
    def load_wordlist(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Wordlist not found: {path}")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return [line.strip().strip('/') for line in f if line.strip()]

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def send_request(self, url, extra_headers=None):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Connection": "close"
        }
        if extra_headers:
            headers.update(extra_headers)
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
                proxies=self.proxies,
                verify=self.verify_ssl,
            )
            return response.status_code, response.text, url
        except requests.RequestException as e:
            log_error(f"Request error for {url}: {e}")
            return None, None, url

    # ------------------------------------------------------------------ #
    # Bypass attempts (simple)
    # ------------------------------------------------------------------ #
    def try_bypass(self, url, status_code):
        bypasses = []
        base_path = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]

        bypass_paths = [
            url + ".",
            url + "/",
            url.replace(base_path, f"{base_path}%2f"),
            url.replace(base_path, f"{base_path}/"),
            url.replace(base_path, f"{base_path}..;/"),
            url.replace(base_path, f"{base_path};/"),
        ]

        header_payloads = [
            {"X-Original-URL": url},
            {"X-Rewrite-URL": url},
            {"X-Custom-IP-Authorization": "127.0.0.1"},
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Forwarded-Host": "127.0.0.1"},
            {"Referer": url}
        ]

        # Path tricks
        for trick_url in bypass_paths:
            time.sleep(random.uniform(self.base_delay, self.base_delay + 0.5))
            status, content, _ = self.send_request(trick_url)
            if status and status not in (403, 401):
                if self._content_filter(content):
                    with self.ui_lock:
                        if trick_url not in self.displayed_urls:
                            self.result_table.add_row(format_status(status), trick_url, "Bypass Success")
                            self.displayed_urls.add(trick_url)
                    self.context.add_discovery_result({"url": trick_url, "status": status, "bypass": "path"})
                    bypasses.append((trick_url, status))

        # Header tricks
        for headers in header_payloads:
            headers["User-Agent"] = random.choice(USER_AGENTS)
            try:
                time.sleep(random.uniform(self.base_delay, self.base_delay + 0.5))
                response = requests.get(url, headers=headers, timeout=self.timeout, verify=False, proxies=self.proxies)
                if response.status_code not in (403, 401) and self._content_filter(response.text):
                    with self.ui_lock:
                        if url not in self.displayed_urls:
                            self.result_table.add_row(format_status(response.status_code), url, "Header Bypass")
                            self.displayed_urls.add(url)
                    self.context.add_discovery_result({
                        "url": url,
                        "status": response.status_code,
                        "bypass": list(headers.keys())[0]
                    })
                    bypasses.append((url, response.status_code))
            except requests.RequestException as e:
                log_error(f"Bypass header error for {url}: {e}")
                continue

        return bypasses

    # ------------------------------------------------------------------ #
    # Content filters
    # ------------------------------------------------------------------ #
    def _content_filter(self, content):
        if content is None:
            return False
        if self.include_regex and not self.include_regex.search(content):
            return False
        if self.exclude_regex and self.exclude_regex.search(content):
            return False
        return True

    # ------------------------------------------------------------------ #
    # Worker thread
    # ------------------------------------------------------------------ #
    def _worker(self):
        while not self.shutdown_event.is_set():
            try:
                base_url, path = self.task_queue.get(timeout=1)
            except queue.Empty:
                if self.shutdown_event.is_set():
                    break
                continue

            try:
                self._process_path(base_url, path)
            except Exception as e:
                log_error(f"Error processing {path}: {e}")
            finally:
                with self.total_tasks_lock:
                    self.completed_tasks += 1
                self.task_queue.task_done()

    # ------------------------------------------------------------------ #
    # Process a single path (plus extension fuzzing)
    # ------------------------------------------------------------------ #
    def _process_path(self, base_url, path):
        targets = [path + "/"] + [f"{path}.{ext}" for ext in self.extensions]

        for target in targets:
            full_url = urljoin(base_url, target)

            # skip if already scanned
            with self.visited_lock:
                if full_url in self.visited:
                    continue
                self.visited.add(full_url)

            # request
            time.sleep(random.uniform(self.base_delay, self.base_delay + 0.5))
            status, content, url = self.send_request(full_url)

            if status in self.status_filter and self._content_filter(content):
                severity = get_severity(target)
                with self.ui_lock:
                    if full_url not in self.displayed_urls:
                        self.result_table.add_row(format_status(status), full_url, severity)
                        self.displayed_urls.add(full_url)

                if status in (403, 401):
                    self.try_bypass(full_url, status)

                self.context.add_discovery_result({"url": full_url, "status": status, "severity": severity})

                # recursion into directories
                if self.recursion and target.endswith("/") and status != 404:
                    with self.total_tasks_lock:
                        self.total_tasks += 1
                    self.task_queue.put((full_url, ""))

    # ------------------------------------------------------------------ #
    # Render current UI state
    # ------------------------------------------------------------------ #
    def _render_ui(self, task_id):
        return Panel(
            Group(self.progress_bar, self.result_table),
            title=f"✅ Found: {len(self.context.get_all_discoveries())} | Progress",
            border_style="cyan"
        )

    # ------------------------------------------------------------------ #
    # Run scan
    # ------------------------------------------------------------------ #
    def run(self, base_url, wordlist_path):
        try:
            paths = self.load_wordlist(wordlist_path)
        except FileNotFoundError as e:
            log_error(str(e))
            return

        # enqueue tasks
        for path in paths:
            with self.total_tasks_lock:
                self.total_tasks += 1
            self.task_queue.put((base_url, path))

        # create progress task
        task_id = self.progress_bar.add_task("Scanning", total=self.total_tasks)

        # start workers
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            threads.append(t)

        # live UI
        with Live(self._render_ui(task_id), refresh_per_second=5, console=console):
            try:
                while True:
                    with self.total_tasks_lock:
                        completed = self.completed_tasks
                        total = self.total_tasks
                    self.progress_bar.update(task_id, completed=completed, total=total)

                    if completed >= total and self.task_queue.empty():
                        break
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.shutdown_event.set()

        # join workers
        for t in threads:
            t.join()

        # save data
        self._save_all_formats()

    # ------------------------------------------------------------------ #
    # Output filename helper
    # ------------------------------------------------------------------ #
    def _normalized_output_paths(self):
        """
        Build path per format. If output_base has an extension matching fmt, use it.
        Else append .fmt
        """
        paths = {}
        base = self.output_base
        lower = base.lower()
        for fmt in self.formats:
            ext = f".{fmt}"
            if lower.endswith(ext):
                paths[fmt] = base
            else:
                paths[fmt] = base + ext
        return paths

    # ------------------------------------------------------------------ #
    # Save results (multi-format)
    # ------------------------------------------------------------------ #
    def _save_all_formats(self):
        try:
            data = self.context.get_all_discoveries()
        except Exception as e:
            log_error(f"Failed to get discoveries from context: {e}")
            return

        if not data:
            log_info("No results to save.")
            return

        paths = self._normalized_output_paths()

        # JSON
        if "json" in self.formats:
            try:
                with open(paths["json"], "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                log_info(f"JSON results saved to {paths['json']}")
            except Exception as e:
                log_error(f"Failed to save JSON: {e}")

        # CSV
        if "csv" in self.formats:
            try:
                fieldnames = sorted({k for r in data for k in r.keys()})
                with open(paths["csv"], "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                log_info(f"CSV results saved to {paths['csv']}")
            except Exception as e:
                log_error(f"Failed to save CSV: {e}")

        # TXT
        if "txt" in self.formats:
            try:
                with open(paths["txt"], "w", encoding="utf-8") as f:
                    for r in data:
                        status = r.get("status", "?")
                        url = r.get("url", "")
                        severity = r.get("severity", "")
                        f.write(f"{status}\t{url}\t{severity}\n")
                log_info(f"TXT results saved to {paths['txt']}")
            except Exception as e:
                log_error(f"Failed to save TXT: {e}")


# --------------------------------------------------------------------------- #
# Standalone CLI (for quick testing of module directly)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ContentDiscoverer (module test)")
    parser.add_argument("url", help="Base URL to scan")
    parser.add_argument("--wordlist", default="wordlists/common.txt", help="Path to wordlist file")
    parser.add_argument("--threads", type=int, default=30, help="Number of concurrent threads")
    parser.add_argument("--delay", type=float, default=0.1, help="Base delay between requests")
    parser.add_argument("--profile", default="balanced", choices=["stealth", "balanced", "aggressive"], help="Scan profile")
    parser.add_argument("--recursion", action="store_true", help="Enable recursive scanning")
    parser.add_argument("--include-regex", default=None, help="Regex to include in response content")
    parser.add_argument("--exclude-regex", default=None, help="Regex to exclude in response content")
    parser.add_argument("--proxy", default=None, help="Proxy URL to use for requests")
    parser.add_argument("-o", "--output", default="scan_results", help="Output base filename")
    parser.add_argument("--format", default="json", help="Comma-separated formats: json,csv,txt or 'all'")
    parser.add_argument("--no-verify", action="store_true", help="Disable SSL verification")
    args = parser.parse_args()

    # Build formats list
    formats = [f.strip().lower() for f in args.format.split(",")]
    if "all" in formats:
        formats = ["json", "csv", "txt"]

    # Build context (minimal)
    ctx = ScanContext(target_url=args.url, wordlist_path=args.wordlist)
    ctx.verify_ssl = not args.no_verify

    discoverer = ContentDiscoverer(
        context=ctx,
        threads=args.threads,
        delay=args.delay,
        recursion=args.recursion,
        proxies={"http": args.proxy, "https": args.proxy} if args.proxy else None,
        profile=args.profile,
        include_regex=args.include_regex,
        exclude_regex=args.exclude_regex,
        output_path=args.output,
        formats=formats,
        verify_ssl=ctx.verify_ssl,
    )

    console.print(f"[bold cyan]🚀 Starting {args.profile.upper()} scan on: {args.url}[/bold cyan]")
    console.print(f"[bold green]📂 Using wordlist: {os.path.abspath(args.wordlist)}[/bold green]")

    discoverer.run(args.url, args.wordlist)
