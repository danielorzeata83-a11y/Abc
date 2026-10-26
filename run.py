"""One-command launcher: sets up a virtualenv, installs requirements, loads .env and starts the dashboard.

Every start also brings the data up to date: the server looks for a newer SEC 13F quarter, rebuilds the Smart Money
overview and the investors index, and refreshes insiders and House trades in the background."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, ".env")
VENV = os.path.join(HERE, ".venv")


def load_env(path):
    """KEY=VALUE lines into os.environ; values already set in the real environment win."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
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


def save_env_value(path, key, value):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        lines = []
    new = f"{key}={value}"
    if any(x.split("=", 1)[0].strip() == key for x in lines):
        lines = [new if x.split("=", 1)[0].strip() == key else x for x in lines]
    else:
        lines.append(new)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def venv_python():
    return os.path.join(VENV, "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")


def main(argv):
    if os.path.abspath(sys.prefix) != os.path.abspath(VENV):
        if not os.path.exists(venv_python()):
            print("Creating virtual environment (first run only)...", flush=True)
            subprocess.check_call([sys.executable, "-m", "venv", VENV])
        print("Checking requirements...", flush=True)
        subprocess.check_call([venv_python(), "-m", "pip", "install", "-q", "-r", os.path.join(HERE, "requirements.txt")])
        os.execv(venv_python(), [venv_python(), os.path.join(HERE, "run.py"), *argv]) if os.name != "nt" else sys.exit(
            subprocess.call([venv_python(), os.path.join(HERE, "run.py"), *argv]))
    load_env(ENV_FILE)
    if not os.environ.get("SEC_CONTACT"):
        print("SEC requires a contact e-mail in requests (used for the free SEC data). It stays on this computer.")
        v = input("Your e-mail: ").strip()
        if "@" in v:
            save_env_value(ENV_FILE, "SEC_CONTACT", v)
            os.environ["SEC_CONTACT"] = v
    sys.path.insert(0, HERE)
    sys.argv = [os.path.join(HERE, "sensa_server.py"), *argv]
    import sensa_server
    sensa_server.main()


if __name__ == "__main__":
    main(sys.argv[1:])
