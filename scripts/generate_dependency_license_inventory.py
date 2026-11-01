"""Collect declared dependency license metadata without making legal claims."""

from __future__ import annotations

from importlib import metadata
import json
from pathlib import Path
import sys
from typing import Any


def declared_python(component: dict[str, Any]) -> dict[str, Any]:
    name = str(component["name"])
    expected_version = str(component.get("version", "unknown"))
    installed_version = metadata.version(name)
    if installed_version != expected_version:
        raise RuntimeError(
            f"Installed {name} {installed_version} does not match lock {expected_version}."
        )
    record = metadata.metadata(name)
    license_value = record.get("License")
    if license_value and len(license_value) > 500:
        license_value = "Declared metadata contains embedded text; inspect the package metadata."
    return {
        "name": name,
        "version": expected_version,
        "license_expression": record.get("License-Expression"),
        "license": license_value,
        "license_classifiers": sorted(
            classifier
            for classifier in record.get_all("Classifier", [])
            if classifier.startswith("License ::")
        ),
    }


def declared_web(component: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(component["name"]),
        "version": str(component.get("version", "unknown")),
        "licenses": component.get("licenses", []),
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Use: python-script PYTHON_SBOM WEB_SBOM OUTPUT")
    python_sbom = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    web_sbom = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    result = {
        "format": "updatarr-declared-license-inventory-v1",
        "notice": (
            "Values are dependency-publisher declarations, not a legal "
            "compatibility opinion. Missing values remain null or empty."
        ),
        "python_runtime": sorted(
            (declared_python(item) for item in python_sbom["components"]),
            key=lambda item: item["name"].lower(),
        ),
        "browser_runtime": sorted(
            (declared_web(item) for item in web_sbom["components"]),
            key=lambda item: item["name"].lower(),
        ),
    }
    Path(sys.argv[3]).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
