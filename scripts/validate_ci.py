"""Validate deployment inputs offline, including missing-coverage failures."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

CORE_AGENTS = {"devops-triage", "docs-qa"}
REQUIRED_FIELDS = {"id", "description", "query", "candidate_response"}
MODEL_DEPLOYMENT = "gpt-5.4-mini"


def validate_manifest(root: Path) -> dict[str, Path]:
    manifest = yaml.safe_load((root / "azure.yaml").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("services"), dict):
        raise ValueError("azure.yaml must declare a services mapping")
    services = manifest["services"]
    if any(not isinstance(service, dict) for service in services.values()):
        raise ValueError("Every service must be a mapping")
    agents = {name: service for name, service in services.items()
              if service.get("host") == "azure.ai.agent"}
    if not CORE_AGENTS.issubset(agents):
        raise ValueError(f"Missing required agents: {sorted(CORE_AGENTS - agents.keys())}")
    project = services.get("ai-project", {})
    if project.get("host") != "azure.ai.project":
        raise ValueError("ai-project must reference a real azure.ai.project service")
    deployments = project.get("deployments")
    if not isinstance(deployments, list) or not deployments:
        raise ValueError("ai-project must declare model deployments")
    for deployment in deployments:
        if not isinstance(deployment, dict) or not isinstance(deployment.get("model"), dict):
            raise ValueError("Each deployment must declare a model")
        if not all(deployment["model"].get(key) for key in ("format", "name", "version")):
            raise ValueError("Each model needs format, name and version")
    if MODEL_DEPLOYMENT not in {deployment.get("name") for deployment in deployments}:
        raise ValueError(f"Missing deployment used by the deployment workflow: {MODEL_DEPLOYMENT}")
    paths = {}
    for name, agent in agents.items():
        uses = agent.get("uses")
        if not isinstance(uses, list) or "ai-project" not in uses:
            raise ValueError(f"{name}: missing ai-project binding")
        if any(binding not in services for binding in uses):
            raise ValueError(f"{name}: references an undefined service")
        configuration = agent.get("codeConfiguration")
        if not isinstance(configuration, dict):
            raise ValueError(f"{name}: missing codeConfiguration")
        folder, entry = agent.get("project"), configuration.get("entryPoint")
        if not isinstance(folder, str) or not folder or not isinstance(entry, str) or not entry:
            raise ValueError(f"{name}: missing project or entryPoint")
        project_path = (root / folder).resolve()
        path = (project_path / entry).resolve()
        if (Path(folder).is_absolute() or Path(entry).is_absolute()
                or not project_path.is_relative_to(root.resolve())
                or not path.is_relative_to(project_path) or not path.is_file()):
            raise ValueError(f"{name}: entryPoint must be an existing file inside its repository project")
        paths[name] = project_path
    return paths


def validate_dataset(path: Path) -> int:
    identifiers: set[str | int] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number}: row must be an object")
        if not REQUIRED_FIELDS.issubset(row):
            raise ValueError(f"{path}:{number}: missing required fields")
        if any(not isinstance(row[field], str) or not row[field].strip()
               for field in REQUIRED_FIELDS - {"id"}):
            raise ValueError(f"{path}:{number}: text fields must be nonempty strings")
        identifier = row["id"]
        if (type(identifier) not in (str, int)
                or isinstance(identifier, str) and not identifier.strip()):
            raise ValueError(f"{path}:{number}: id must be an integer or nonempty string")
        if identifier in identifiers:
            raise ValueError(f"{path}:{number}: duplicate case ID")
        identifiers.add(identifier)
    if not identifiers:
        raise ValueError(f"{path}: dataset must not be empty")
    return len(identifiers)


def validate_datasets(agents: dict[str, Path]) -> dict[str, int]:
    counts = {}
    for name, folder in agents.items():
        paths = sorted((folder / "datasets").glob("*/*.jsonl"))
        if not paths:
            raise ValueError(f"{name}: no evaluation datasets found")
        counts[name] = sum(validate_dataset(path) for path in paths)
    return counts


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    for name, count in validate_datasets(validate_manifest(root)).items():
        print(f"{name}: entry point, model binding and {count} evaluation rows validated")


if __name__ == "__main__":
    main()
