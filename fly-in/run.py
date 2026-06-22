"""Root entry point — delegates to fly_in.main."""

import sys
from fly_in.main import run

if __name__ == "__main__":
    sys.exit(run())
