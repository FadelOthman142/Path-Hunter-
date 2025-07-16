import urllib3  # Place this at the top of the file
from utils.context import ScanContext

class ContentDiscoverer:
    def __init__(self, context: ScanContext, threads=30, delay=0.1,
                 status_filter=[200, 403, 401], extensions=None, recursion=True,
                 proxies=None, profile="balanced", include_regex=None, exclude_regex=None):
        self.context = context

        if not self.context.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # ... rest of your init logic
