"""Make both agent source directories importable from the test suite.

Each agent directory is a self-contained deployment unit (Foundry zips it and
runs `main.py` from inside it), so the modules are top-level rather than a
package. Adding both directories to `sys.path` mirrors that runtime layout.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

for agent_dir in ("devops-triage", "docs-qa"):
    path = REPO_ROOT / "src" / agent_dir
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
