# utils/logger.py

import datetime

def log_info(message):
    print(f"[INFO] {datetime.datetime.now().isoformat()} - {message}")

def log_success(message):
    print(f"[SUCCESS] {datetime.datetime.now().isoformat()} - {message}")

def log_error(message):
    print(f"[ERROR] {datetime.datetime.now().isoformat()} - {message}")
