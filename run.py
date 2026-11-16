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


REQUIRED = ("numpy", "pandas")
OPTIONAL = ("pypdf",)          # only the House trades page needs it


def missing_modules(names, find=None):
    import importlib.util
    find = find or importlib.util.find_spec
    return [n for n in names if find(n) is None]


def plan(missing, pip_ok=None, offline_ok=None):
    """What to do about missing packages: run as is, use the venv after a good pip, run without optional ones, or fail."""
    if not missing:
        return "run"
    if pip_ok:
        return "venv-ok"
    return "run-without-optional" if all(m in OPTIONAL for m in missing) else "fail"


def venv_python():
    return os.path.join(VENV, "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")


def main(argv):
    inside = os.path.abspath(sys.prefix) == os.path.abspath(VENV)
    if not inside:
        missing = missing_modules(REQUIRED + OPTIONAL)
        if not missing:
            pass                                               # this Python already has everything: no venv, no download
        else:
            print("Missing packages: " + ", ".join(missing) + ". Trying to install them in .venv ...", flush=True)
            try:
                if not os.path.exists(venv_python()):
                    subprocess.check_call([sys.executable, "-m", "venv", VENV])
                subprocess.check_call([venv_python(), "-m", "pip", "install", "-q", "-r", os.path.join(HERE, "requirements.txt")])
                ok = True
            except (subprocess.CalledProcessError, OSError):
                ok = False
            what = plan(missing, pip_ok=ok)
            if what == "venv-ok":
                if os.name != "nt":
                    os.execv(venv_python(), [venv_python(), os.path.join(HERE, "run.py"), *argv])
                sys.exit(subprocess.call([venv_python(), os.path.join(HERE, "run.py"), *argv]))
            if what == "fail":
                sys.exit("Could not install " + ", ".join(m for m in missing if m in REQUIRED) +
                         " (no internet to PyPI?). Install them once with:  pip install numpy pandas   "
                         "(on a computer with internet, or ask IT for a proxy), then run again.")
            print("Optional package(s) missing (" + ", ".join(missing) + "): the House trades page will not read PDFs. Continuing.", flush=True)
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
