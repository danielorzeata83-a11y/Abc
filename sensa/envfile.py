"""Read the project's .env (KEY=VALUE lines) so every entry point finds the same settings."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=None):
    """KEY=VALUE lines into os.environ; values already set in the real environment win."""
    try:
        lines = open(path or os.path.join(ROOT, ".env"), encoding="utf-8").read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k.replace("_", "").isalnum():
            os.environ.setdefault(k, v)
