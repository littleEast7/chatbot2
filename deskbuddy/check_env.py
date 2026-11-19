"""Print dependency diagnostics and return a useful process status."""
import importlib
import importlib.metadata
import sys


def main():
    failed = False
    for module, package in (("PySide6", "PySide6"), ("yaml", "PyYAML"),
                            ("apscheduler", "APScheduler"), ("flask", "Flask"),
                            ("requests", "requests")):
        try:
            importlib.import_module(module)
            print(f"OK {package} {importlib.metadata.version(package)}")
        except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
            print(f"ERROR {package}: {exc}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
