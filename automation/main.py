# Standard library imports.
from importlib import metadata
from pathlib import Path
import sys

# Third party imports.
import heather


def main() -> None:
    bootstrap_heather_flat_imports()

    from sync.run import run_heather
    from tools.freshness import wait_for_fresh_gl_issues

    print(f"[*] Heather package version: {metadata.version('heather')}")
    wait_for_fresh_gl_issues()
    run_heather()


def bootstrap_heather_flat_imports() -> None:
    heather_package_path = str(Path(heather.__file__).resolve().parent)

    if heather_package_path not in sys.path:
        sys.path.insert(0, heather_package_path)


if __name__ == "__main__":
    main()
