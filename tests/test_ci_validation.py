"""Negative cases for the offline CI gates, without Azure or model access."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_ci.py"
SPEC = importlib.util.spec_from_file_location("validate_ci", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    services = {
        "ai-project": {
            "host": "azure.ai.project",
            "deployments": [{
                "name": "gpt-5.4-mini",
                "model": {"format": "OpenAI", "name": "gpt-5.4-mini", "version": "2026-03-17"},
            }],
        },
    }
    for name in sorted(validation.CORE_AGENTS):
        folder = tmp_path / "src" / name
        folder.mkdir(parents=True)
        (folder / "main.py").write_text("", encoding="utf-8")
        services[name] = {
            "host": "azure.ai.agent", "project": f"src/{name}",
            "uses": ["ai-project"], "codeConfiguration": {"entryPoint": "main.py"},
        }
    (tmp_path / "azure.yaml").write_text(yaml.safe_dump({"services": services}), encoding="utf-8")
    return tmp_path


def test_valid_manifest_requires_both_core_agents(project: Path) -> None:
    assert set(validation.validate_manifest(project)) == validation.CORE_AGENTS


@pytest.mark.parametrize("service", ["devops-triage", "docs-qa", "ai-project"])
def test_missing_service_is_rejected(project: Path, service: str) -> None:
    path = project / "azure.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    del manifest["services"][service]
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        validation.validate_manifest(project)


def test_missing_model_is_rejected(project: Path) -> None:
    path = project / "azure.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["services"]["ai-project"]["deployments"] = []
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="model deployments"):
        validation.validate_manifest(project)


def test_missing_entry_point_is_rejected(project: Path) -> None:
    (project / "src" / "docs-qa" / "main.py").unlink()
    with pytest.raises(ValueError, match="entryPoint"):
        validation.validate_manifest(project)


def test_missing_datasets_are_rejected(project: Path) -> None:
    with pytest.raises(ValueError, match="no evaluation datasets"):
        validation.validate_datasets(validation.validate_manifest(project))


@pytest.mark.parametrize("text", ["", " \n", "[]", "null", "{}", "{"])
def test_empty_or_invalid_dataset_is_rejected(tmp_path: Path, text: str) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        validation.validate_dataset(path)


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    row = json.dumps(dict.fromkeys(validation.REQUIRED_FIELDS, "example"))
    path = tmp_path / "cases.jsonl"
    path.write_text(f"{row}\n{row}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        validation.validate_dataset(path)


@pytest.mark.parametrize("identifier", [1, "example"])
def test_valid_dataset_reports_real_row_count(tmp_path: Path, identifier: int | str) -> None:
    path = tmp_path / "cases.jsonl"
    row = dict.fromkeys(validation.REQUIRED_FIELDS, "example") | {"id": identifier}
    path.write_text(json.dumps(row), encoding="utf-8")
    assert validation.validate_dataset(path) == 1
