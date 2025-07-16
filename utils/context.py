# utils/context.py
class ScanContext:
    def __init__(self, target_url, wordlist_path, verify_ssl=True,
                 threads=30, delay=0.1, proxy=None, include_regex=None, exclude_regex=None):
        self.target_url = target_url
        self.wordlist_path = wordlist_path
        self.verify_ssl = verify_ssl
        self.threads = threads
        self.delay = delay
        self.proxy = proxy
        self.include_regex = include_regex
        self.exclude_regex = exclude_regex

        self.found_paths = set()
        self.discovery_results = []
        self.discoveries = [] 

    def add_discovery_result(self, result):
        self.discovery_results.append(result)

    def get_all_discoveries(self):
        return self.discovery_results


    def add_discovery_result(self, result):
        self.discoveries.append(result)

    def get_all_discoveries(self):
        return self.discoveries
