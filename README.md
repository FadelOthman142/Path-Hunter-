# 🕵️ PathHunter

**Advanced Web Content Discovery Tool**

PathHunter is a Feroxbuster-inspired web content discovery tool for
penetration testers, bug bounty hunters, and security engineers.\
It aggressively (or stealthily---your call) fuzzes directories & files,
detects interesting responses, attempts simple WAF/auth bypass tricks,
and displays everything in a live-updating **Rich-powered TUI**.

------------------------------------------------------------------------

## ✨ Highlights

-   ⚡ **Multi-threaded scanning** for speed\
-   🎯 **Scan modes** with auto-selected wordlists: fast, balanced,
    stealth\
-   🧠 **Regex include/exclude filters** (content-aware)\
-   🔁 **Recursive directory discovery** (optional)\
-   🛡 **Basic 403/401 bypass attempts** (headers & path tricks)\
-   🖥 **Feroxbuster-like Rich TUI** with live progress bar + results
    table\
-   📤 **Export results** to JSON or CSV\
-   🔌 *(Planned)* Proxy routing, rate shaping per-domain, resume
    support

------------------------------------------------------------------------

## 📸 Demo

Coming soon -- a GIF or screenshot of PathHunter running in your
terminal.

``` bash
$ python main.py https://target.tld --mode fast
```

👉 Capture with asciinema:

``` bash
asciinema rec demo.cast
python main.py https://target.tld --mode fast
```

------------------------------------------------------------------------

## 📦 Installation

``` bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/pathhunter.git
cd pathhunter
pip install -r requirements.txt
```

Recommended: use a virtual environment.

``` bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scriptsctivate     # Windows PowerShell
pip install -r requirements.txt
```

------------------------------------------------------------------------

## 🔧 Requirements

-   Python 3.9+\
-   Internet access to your target(s)\
-   Wordlists (included: `common.txt`, `medium.txt`, `large.txt`)

Install deps manually:

``` bash
pip install requests rich urllib3
```

------------------------------------------------------------------------

## 🚀 Quick Start

**Fast scan (built-in common wordlist):**

``` bash
python main.py https://target.tld --mode fast
```

**Balanced scan (default):**

``` bash
python main.py https://target.tld --mode balanced
```

**Stealth scan (low-noise):**

``` bash
python main.py https://target.tld --profile stealth --mode stealth --delay 1.5 --threads 5
```

**Custom wordlist:**

``` bash
python main.py https://target.tld -w /path/to/custom.txt
```

**Exclude responses containing `logout`:**

``` bash
python main.py https://target.tld --exclude-regex logout
```

------------------------------------------------------------------------

## 🧭 Command-Line Usage

``` bash
usage: main.py [-h] [-w WORDLIST] [-t THREADS] [--delay DELAY]
               [--profile {stealth,balanced,aggressive}]
               [--recursion] [--include-regex INCLUDE_REGEX]
               [--exclude-regex EXCLUDE_REGEX] [--mode {fast,balanced,stealth}]
               url
```

### Positional Argument

  Arg     Description
  ------- ----------------------------------------------
  `url`   Target base URL (e.g., https://example.com/)

### Options

  ---------------------------------------------------------------------------
  Flag                Description                      Default
  ------------------- -------------------------------- ----------------------
  `-w, --wordlist`    Path to custom wordlist          auto by mode
                      (overrides --mode)               

  `-t, --threads`     Worker threads                   30

  `--delay`           Delay (seconds) between requests 0.1

  `--profile`         Traffic profile: stealth,        balanced
                      balanced, aggressive             

  `--recursion`       Enable recursive scanning        False

  `--include-regex`   Only accept responses matching   None
                      regex                            

  `--exclude-regex`   Drop responses matching regex    None

  `--mode`            Select built-in wordlist: fast,  balanced
                      balanced, stealth                
  ---------------------------------------------------------------------------

------------------------------------------------------------------------

## 📚 Scan Modes → Wordlists

  -------------------------------------------------------------------------
  Mode           Wordlist                 Intended Use
  -------------- ------------------------ ---------------------------------
  fast           `wordlists/common.txt`   Quick recon / triage

  balanced       `wordlists/medium.txt`   Deeper target coverage

  stealth        `wordlists/large.txt`    Low-noise scans for fragile
                                          targets
  -------------------------------------------------------------------------

------------------------------------------------------------------------

## 🧵 Profiles vs. Performance

  Profile      Max Threads Used         Min Delay Applied   Notes
  ------------ ------------------------ ------------------- ---------------
  stealth      min(user_threads, 10)    ≥ 1.5s              Low & slow
  balanced     user_threads             user_delay          Default
  aggressive   max(user_threads, 100)   ≥ 0.01s             Very noisy ⚠️

------------------------------------------------------------------------

## 🕵️ Discovery Logic

For each word in the wordlist:

-   `path/`\
-   `path.<ext>` for common extensions
    (`php, html, bak, txt, zip, asp, aspx`)

Responses with interesting status codes (`200, 403, 401`) that pass
regex filters are logged.\
If a directory is discovered (`/`), recursion can queue deeper scanning.

------------------------------------------------------------------------

## 🔐 403/401 Bypass Attempts

On **Forbidden/Unauthorized responses**, PathHunter will try:

-   Suffix fuzzing: `/.`, `//`, encoded slash, `..;/`, `;/`\
-   Header tricks: `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-For`,
    etc.

Successful bypasses are shown as **Bypass Success** or **Header
Bypass**.

------------------------------------------------------------------------

## 📊 Output & Reporting

-   Results saved as `scan_results.json` by default\
-   CSV support planned via CLI flag

Example JSON:

``` json
[
  {
    "url": "https://target.tld/admin/",
    "status": 200,
    "severity": "🔥 High Risk"
  },
  {
    "url": "https://target.tld/.htaccess",
    "status": 403,
    "bypass": "path",
    "severity": "ℹ️ Low Risk"
  }
]
```

------------------------------------------------------------------------

## 🧪 Example Runs

**Fast mode, exclude `logout`:**

``` bash
python main.py https://target.tld --mode fast --exclude-regex logout
```

**Balanced mode, recursive:**

``` bash
python main.py https://target.tld --mode balanced --recursion
```

**Aggressive + custom wordlist:**

``` bash
python main.py https://target.tld -w lists/bb-elite.txt --profile aggressive --threads 200 --delay 0.01
```

------------------------------------------------------------------------

## 🧰 Development Setup

``` bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/pathhunter.git
cd pathhunter
python -m venv .venv
source .venv/bin/activate  # or .venv\Scriptsctivate on Windows
pip install -r requirements.txt
```

Run in debug mode:

``` bash
python main.py https://localhost:8443 --mode fast
```

------------------------------------------------------------------------

## 🧱 Project Layout

    pathhunter/
    ├── main.py                  # CLI entrypoint
    ├── modules/
    │   ├── __init__.py
    │   └── content_discover.py  # Scanning engine + Rich UI
    ├── utils/
    │   ├── __init__.py
    │   ├── context.py           # ScanContext (target, results store, SSL prefs)
    │   └── logger.py            # Minimal logger helpers
    ├── wordlists/
    │   ├── common.txt           # Fast list
    │   ├── medium.txt           # Balanced/full list
    │   └── large.txt            # Big/stealthy list
    ├── requirements.txt
    ├── LICENSE
    └── README.md

------------------------------------------------------------------------

## 🧭 Roadmap

-   CLI flag for custom extensions (`--extensions php,asp,aspx`)\
-   Built-in extension presets (`--common-extensions`)\
-   Proxy support via CLI\
-   Per-host rate shaping & jitter curves\
-   Resume from partial scans (state file)\
-   Output filtering (e.g., 2xx only)\
-   HTML report export with risk ranking\
-   CI pipeline + tests

------------------------------------------------------------------------

## 🤝 Contributing

Contributions welcome!

1.  Fork the repo\

2.  Create a feature branch:

    ``` bash
    git checkout -b feature/your-idea
    ```

3.  Run lint/tests (coming soon)\

4.  Submit a PR with a clear description & sample output

Bug report? Open an issue with:\
- Target type (public, lab, localhost)\
- Command used\
- Python version & OS\
- Stack trace / screenshot

------------------------------------------------------------------------

## ⚠️ Legal & Ethical Use

Use **PathHunter** only on systems you own or have explicit permission
to test.\
Unauthorized scanning may be illegal.

The authors assume **no liability for misuse**.

------------------------------------------------------------------------

## 📄 License

This project is licensed under the **MIT License**. See
[LICENSE](LICENSE).

------------------------------------------------------------------------

## 🙌 Credits

-   Inspired by: **Feroxbuster, Dirsearch, Gobuster**\
-   TUI powered by: **Rich (Textualize)**\
-   HTTP by: **requests**

------------------------------------------------------------------------

⭐ If you find PathHunter useful, **star the repo** to help others
discover it.\
🔥 Happy Hunting!
