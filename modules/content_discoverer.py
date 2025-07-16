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
from utils.logger import log_error
from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table

console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)",
]

DEFAULT_EXTENSIONS = ["php", "html", "bak", "txt", "zip", "asp", "aspx"]

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def format_status(status_code):
    if 200 <= status_code < 300:
        return f"[bold green]{status_code}[/bold green] ✅"
    elif 300 <= status_code < 400:
        return f"[bold blue]{status_code}[/bold blue] 🔵"
    elif 400 <= status_code < 500:
        return f"[bold yellow]{status_code}[/bold yellow] ⚠️"
    else:
        return f"[bold red]{status_code}[/bold red] 🔥"


def get_severity(path):
    high_risk = [".bak", ".sql", ".env", ".config", ".php", ".ini"]
    medium_risk = [".log", ".txt", ".zip"]
    path = path.lower()
    for ext in high_risk:
        if path.endswith(ext):
            return "🔥 High Risk"
    for ext in medium_risk:
        if path.endswith(ext):
            return "⚠️ Medium Risk"
    return "ℹ️ Low Risk"


class ContentDiscoverer:
    def __init__(self, context: ScanContext, threads=30, delay=0.1,
                 status_filter=[200, 403, 401], extensions=None, recursion=True,
                 proxies=None, profile="balanced", include_regex=None, exclude_regex=None):
        self.context = context
        self.profile = profile.lower()

        if self.profile == "stealth":
            self.threads = min(threads, 10)
            self.base_delay = max(delay, 1.5)
        elif self.profile == "aggressive":
            self.threads = max(threads, 100)
            self.base_delay = max(delay, 0.01)
        else:
            self.threads = threads
            self.base_delay = delay

        self.delay = self.base_delay
        self.visited_lock = threading.Lock()
        self.visited = set()
        self.status_filter = status_filter
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.recursion = recursion
        self.proxies = proxies

        self.include_regex = re.compile(include_regex, re.IGNORECASE) if include_regex else None
        self.exclude_regex = re.compile(exclude_regex, re.IGNORECASE) if exclude_regex else None

        self.task_queue = queue.Queue()
        self.shutdown_event = threading.Event()

        self.total_tasks_lock = threading.Lock()
        self.total_tasks = 0
        self.completed_tasks = 0

        self.progress_bar = Progress(
            TextColumn("[cyan]Scanning...[/cyan]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}")
        )

        self.result_table = Table(show_header=True, header_style="bold magenta")
        self.result_table.add_column("Status", style="cyan", width=10)
        self.result_table.add_column("URL", style="white")
        self.result_table.add_column("Severity", style="yellow")

        self.ui_lock = threading.Lock()
        self.displayed_urls = set()  # Track which URLs have been displayed to avoid duplicates

    def load_wordlist(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Wordlist not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip().strip('/') for line in f if line.strip()]

    def send_request(self, url, extra_headers=None):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Connection": "close"
        }
        if extra_headers:
            headers.update(extra_headers)
        try:
            response = requests.get(url, headers=headers, timeout=10,
                                    allow_redirects=True,
                                    proxies=self.proxies,
                                    verify=self.context.verify_ssl)
            return response.status_code, response.text, url
        except requests.RequestException:
            return None, None, url

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

        for trick_url in bypass_paths:
            time.sleep(random.uniform(self.base_delay, self.base_delay + 0.5))
            status, content, _ = self.send_request(trick_url)
            if status and status not in [403, 401]:
                if self._content_filter(content):
                    with self.ui_lock:
                        if trick_url not in self.displayed_urls:
                            self.result_table.add_row(format_status(status), trick_url, "Bypass Success")
                            self.displayed_urls.add(trick_url)
                    self.context.add_discovery_result({"url": trick_url, "status": status, "bypass": "path"})
                    bypasses.append((trick_url, status))

        for headers in header_payloads:
            headers["User-Agent"] = random.choice(USER_AGENTS)
            try:
                time.sleep(random.uniform(self.base_delay, self.base_delay + 0.5))
                response = requests.get(url, headers=headers, timeout=10,
                                        verify=False, proxies=self.proxies)
                if response.status_code not in [403, 401] and self._content_filter(response.text):
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
            except requests.RequestException:
                continue

        return bypasses

    def _content_filter(self, content):
        if content is None:
            return False
        if self.include_regex and not self.include_regex.search(content):
            return False
        if self.exclude_regex and self.exclude_regex.search(content):
            return False
        return True

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

    def _process_path(self, base_url, path):
        targets = [path + "/"] + [f"{path}.{ext}" for ext in self.extensions]

        for target in targets:
            full_url = urljoin(base_url, target)

            with self.visited_lock:
                if full_url in self.visited:
                    continue
                self.visited.add(full_url)

            time.sleep(random.uniform(self.base_delay, self.base_delay + 0.5))
            status, content, url = self.send_request(full_url)

            if status in self.status_filter and self._content_filter(content):
                severity = get_severity(target)
                with self.ui_lock:
                    if full_url not in self.displayed_urls:
                        self.result_table.add_row(format_status(status), full_url, severity)
                        self.displayed_urls.add(full_url)

                if status in [403, 401]:
                    self.try_bypass(full_url, status)

                self.context.add_discovery_result({"url": full_url, "status": status, "severity": severity})

                if self.recursion and target.endswith("/") and status != 404:
                    with self.total_tasks_lock:
                        self.total_tasks += 1
                    self.task_queue.put((full_url, ""))

    def _render_ui(self, task_id):
        return Panel(
            Group(self.progress_bar, self.result_table),
            title=f"✅ Found: {len(self.context.get_all_discoveries())} | Progress",
            border_style="cyan"
        )

    def run(self, base_url, wordlist_path):
        try:
            paths = self.load_wordlist(wordlist_path)
        except FileNotFoundError as e:
            log_error(str(e))
            return

        for path in paths:
            with self.total_tasks_lock:
                self.total_tasks += 1
            self.task_queue.put((base_url, path))

        # Create progress task
        task_id = self.progress_bar.add_task("Scanning", total=self.total_tasks)

        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            threads.append(t)

        # Use Live to manage the UI with limited refresh rate for smoothness
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

        for t in threads:
            t.join()

        self.save_results("scan_results.json", format='json')

    def save_results(self, filepath, format='json'):
        try:
            data = self.context.get_all_discoveries()
        except Exception as e:
            log_error(f"Failed to get discoveries from context: {e}")
            return

        if not data:
            return

        try:
            if format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            elif format == 'csv':
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        except Exception as e:
            log_error(f"Failed to save results: {e}")


if __name__ == "__main__":
    import argparse
    from utils.context import ScanContext

    parser = argparse.ArgumentParser(description="Advanced Web Content Discovery Tool")
    parser.add_argument("url", help="Base URL to scan")
    parser.add_argument("--wordlist", default="wordlists/common.txt", help="Path to wordlist file")
    parser.add_argument("--threads", type=int, default=30, help="Number of concurrent threads")
    parser.add_argument("--delay", type=float, default=0.1, help="Base delay between requests")
    parser.add_argument("--profile", default="balanced", choices=["stealth", "balanced", "aggressive"], help="Scan profile")
    parser.add_argument("--recursion", action="store_true", help="Enable recursive scanning")
    parser.add_argument("--include-regex", default=None, help="Regex to include in response content")
    parser.add_argument("--exclude-regex", default=None, help="Regex to exclude in response content")
    parser.add_argument("--proxy", default=None, help="Proxy URL to use for requests")
    args = parser.parse_args()

    context = ScanContext(verify_ssl=True)
    discoverer = ContentDiscoverer(
        context,
        threads=args.threads,
        delay=args.delay,
        recursion=args.recursion,
        proxies={"http": args.proxy, "https": args.proxy} if args.proxy else None,
        profile=args.profile,
        include_regex=args.include_regex,
        exclude_regex=args.exclude_regex,
    )

    console.print(f"[bold cyan]🚀 Starting {args.profile.upper()} scan on: {args.url}[/bold cyan]")
    console.print(f"[bold green]📂 Using wordlist: {os.path.abspath(args.wordlist)}[/bold green]")

    discoverer.run(args.url, args.wordlist)
