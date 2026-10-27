"""File helpers."""

import os
import time


def replace_file(src, dst, attempts=20, wait=0.5, sleep=time.sleep):
    """os.replace that waits out a short lock: on Windows an antivirus scan or the indexer often holds a freshly
    downloaded file for a few seconds and the rename fails with PermissionError."""
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            sleep(wait)
