#entry point for running cURLmONKEY as a module

import sys
from .app import run_application

if __name__ == "__main__":
    sys.exit(run_application())

