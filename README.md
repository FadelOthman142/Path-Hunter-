# PathHunter

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Status](https://img.shields.io/badge/status-beta-orange.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Made With Rich](https://img.shields.io/badge/made%20with-Rich-6f42c1.svg)

> **PathHunter** is an advanced, Feroxbuster-inspired **web content discovery tool** for penetration testers, bug bounty hunters, and security engineers. It aggressively (or stealthily—your call) fuzzes directories & files, detects interesting responses, attempts simple WAF / auth bypass tricks, and displays everything in a **live-updating Rich terminal UI**.

---

## ✨ Highlights

* ⚡ **Multi-threaded scanning** for speed
* 🎯 **Scan modes** that auto-pick wordlists: *fast*, *balanced*, *stealth*
* 🧠 **Regex include / exclude filters** (content-aware)
* 🔁 **Recursive directory discovery** (optional)
* 🛡 **Basic 403/401 bypass attempts** (header & path tricks)
* 🖥 **Feroxbuster-like Rich TUI**: live progress bar + result table
* 📤 **Export results** to JSON or CSV
* 🔌 (Planned) Proxy routing, rate shaping per-domain, resume support

---

## 📸 Demo

> *Coming soon.* Drop a GIF or screenshot of PathHunter running in your terminal here for instant credibility.

```
# placeholder preview (replace with real image)
$ python main.py https://target.tld --mode fast
```

You can capture a terminal session with **asciinema**:

```bash
asciinema rec demo.cast
python main.py https://target.tld --mode fast

```

---

## 📦 Installation

```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/pathhunter.git
cd pathhunter
pip install -r requirements.txt
```

**Recommended:** Use a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate     # Windows PowerShell
pip install -r requirements.txt
```

---

## 🔧 Requirements

* Python **3.9+**
* Internet access to your target(s)
* Wordlists (included: `common.txt`, `large.txt`, `logger.txt`)

Install deps manually:

```bash
pip install requests rich urllib3
```

---

## 🚀 Quick Start

Fast scan using built-in common wordlist:

```bash
python main.py https://target.tld --mode fast
```

Balanced scan (default):

```bash
python main.py https://target.tld --mode balanced
```

Stealth mode w/ slower pacing & logger wordlist:

```bash
python main.py https://target.tld --mode stealth --delay 1.5 --threads 5
```

Custom wordlist overrides mode:

```bash
python main.py https://target.tld -w /path/to/custom.txt
```

Exclude responses containing the string `logout`:

```bash
python main.py https://target.tld --exclude-regex logout
```

---

## 🧭 Command-Line Usage

```
usage: main.py [-h] [-w WORDLIST] [-t THREADS] [--delay DELAY]
              [--profile {stealth,balanced,aggressive}]
              [--recursion] [--include-regex INCLUDE_REGEX]
              [--exclude-regex EXCLUDE_REGEX] [--mode {fast,balanced,stealth}]
              url
```

### Positional Argument

| Arg   | Description                                    |
| ----- | ---------------------------------------------- |
| `url` | Target base URL (e.g., `https://example.com/`) |

### Options

| Flag               | Description                                             | Default        |
| ------------------ | ------------------------------------------------------- | -------------- |
| `-w`, `--wordlist` | Path to custom wordlist (overrides `--mode`)            | *auto by mode* |
| `-t`, `--threads`  | Worker threads                                          | `30`           |
| `--delay`          | Delay (seconds) between requests baseline               | `0.1`          |
| `--profile`        | Traffic behavior: `stealth`, `balanced`, `aggressive`   | `balanced`     |
| `--recursion`      | Enable recursive scanning into found dirs               | `False`        |
| `--include-regex`  | Only accept responses whose **body** matches regex      | `None`         |
| `--exclude-regex`  | Drop responses whose **body** matches regex             | `None`         |
| `--mode`           | Select built-in wordlist: `fast`, `balanced`, `stealth` | `balanced`     |

> **Note:** `--wordlist` always takes precedence over `--mode`.

---

## 📚 Scan Modes → Wordlists

Built-in mapping used in `main.py`:

| Mode       | Wordlist               | Intended Use                             |
| ---------- | ---------------------- | ---------------------------------------- |
| `fast`     | `wordlists/common.txt` | Quick recon / triage                     |
| `balanced` | `wordlists/large.txt`  | Deeper target coverage                   |
| `stealth`  | `wordlists/logger.txt` | Small, low-noise set for fragile targets |

---

## 🧵 Profiles vs. Performance

`profile` affects thread cap & minimum delay:

| Profile      | Max Threads Used        | Min Delay Applied | Notes                                             |
| ------------ | ----------------------- | ----------------- | ------------------------------------------------- |
| `stealth`    | min(user\_threads, 10)  | ≥ 1.5s            | Low & slow; try on fragile / rate-limited targets |
| `balanced`   | user\_threads           | user\_delay       | Good default                                      |
| `aggressive` | max(user\_threads, 100) | ≥ 0.01s           | Go brrrr; be careful!                             |

---

## 🕵️ Discovery Logic

For each word in the wordlist (`path`), PathHunter probes:

* `path/`
* `path.<ext>` for each extension (defaults include: php, html, bak, txt, zip, asp, aspx)

Responses whose status codes are in the **status filter** (`[200, 403, 401]` by default) and pass regex filters are logged & shown in the UI. You can customize extensions at construction time if you wire it through CLI (roadmap).

If a directory is discovered (trailing slash) and recursion is enabled, it’s queued for deeper scanning.

---

## 🔐 403/401 Bypass Attempts

When a response is *Forbidden* or *Unauthorized*, PathHunter will try:

* Suffix fuzz (`/.`, `//`, encoded slash, `..;/`, `;/`)
* Common header tricks (`X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-For`, etc.)

Successful bypasses are logged and shown in the results table as **Bypass Success** or **Header Bypass**.

---

## 📊 Output & Reporting

After scan completion (or graceful interrupt), results are written to:

* `scan_results.json` (default)
* CSV supported via internal call (future CLI flag)

**JSON schema example:**

```json
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

---

## 🧪 Example Runs

Fast mode, exclude anything with `logout` in body:

```bash
python main.py https://target.tld --mode fast --exclude-regex logout
```

Balanced mode, recursive:

```bash
python main.py https://target.tld --mode balanced --recursion
```

Aggressive profile + custom wordlist:

```bash
python main.py https://target.tld -w lists/bb-elite.txt --profile aggressive --threads 200 --delay 0.01
```

---

## 🧰 Development Setup

Install in editable mode for hacking:

```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/pathhunter.git
cd pathhunter
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Run in debug mode with verbose logging (add your own flags if extending logger):

```bash
python main.py https://localhost:8443 --mode fast
```

---

## 🧱 Project Layout

```
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
│   ├── large.txt            # Balanced/full list
│   └── logger.txt           # Small/stealth list
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🧭 Roadmap

* [ ] CLI flag for custom extensions (`--extensions php,asp,aspx`)
* [ ] Built-in extension presets (`--common-extensions`)
* [ ] Proxy support exposed via CLI
* [ ] Per-host rate shaping / jitter curves
* [ ] Resume from partial scans (state file)
* [ ] Output filtering by status class (2xx only, etc.)
* [ ] HTML report export w/ risk ranking
* [ ] CI pipeline + tests

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-idea`
3. Run lint + basic tests (coming soon)
4. Submit a PR with a clear description & sample output

Bug report? Open an issue with:

* Target type (public, test lab, localhost)
* Command used
* Python version & OS
* Stack trace or weird output screenshot

---

## ⚠️ Legal & Ethical Use

**Use PathHunter only on systems you own or have explicit permission to test.** Unauthorized scanning may be illegal.

The authors assume **no liability** for misuse.

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE).

---

## 🙌 Credits

* Inspired by: Feroxbuster, Dirsearch, Gobuster
* Rich TUI powered by: [Textualize Rich](https://github.com/Textualize/rich)
* HTTP by: `requests`

---

### ⭐ If you find PathHunter useful, star the repo! It helps others discover it.

---

**Happy Hunting!** 🔥
