"""Keep the complete native acceptance runner exercised by the regular suite."""

from pathlib import Path
import subprocess
import sys


def test_native_backend_acceptance_runner():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("core_compatibility.py"))],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Passed full native backend acceptance" in result.stdout


def test_ci_matrix_covers_every_admitted_core():
    import yaml

    from custom_components.loona.const import (
        FRONTEND_CORE_VERSIONS, REGISTRY_CORE_VERSIONS, SUPPORTED_CORE_VERSIONS,
    )

    path = Path(__file__).resolve().parents[1] / ".github/workflows/compatibility.yml"
    workflow = yaml.safe_load(path.read_text())
    rows = workflow["jobs"]["backend"]["strategy"]["matrix"]["include"]
    assert {row["core"] for row in rows} == SUPPORTED_CORE_VERSIONS
    assert FRONTEND_CORE_VERSIONS <= SUPPORTED_CORE_VERSIONS
    assert REGISTRY_CORE_VERSIONS <= SUPPORTED_CORE_VERSIONS
