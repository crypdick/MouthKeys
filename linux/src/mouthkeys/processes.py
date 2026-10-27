"""Launch installed Python modules without importing from the caller's directory."""

import sys


def python_command(module="mouthkeys", *args):
    return [sys.executable, "-P", "-m", module, *args]
