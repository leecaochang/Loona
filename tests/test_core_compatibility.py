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


def test_ci_exercises_minimum_baseline_and_representative_releases():
    import json
    import yaml

    from custom_components.loona.const import MIN_CORE_VERSION

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/compatibility.yml").read_text())
    rows = workflow["jobs"]["backend"]["strategy"]["matrix"]["include"]
    assert MIN_CORE_VERSION in {row["core"] for row in rows}
    assert len({row["core"].split(".")[0] for row in rows}) >= 3
    assert json.loads((root / "hacs.json").read_text())["homeassistant"] == MIN_CORE_VERSION
