"""Load the repository-local harness for unittest discovery without installation."""
from pathlib import Path
import hashlib
import json
import sys

SOURCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / "tools/harness"))


def fixture_verification(task: dict) -> dict:
    """Known-answer fixture review only; never an automatic production sign-off."""
    from harness.completion_review import template
    value = template(task['kind'])
    value['scope'] = 'Isolated fixture acceptance and its linked evidence'
    for area in value['areas']:
        area.update(result='checked', reason='The authored fixture checks this boundary; no independent agent quality claim.')
    value['rounds'][0].update(outcome='no_new_findings', reason='Known-answer fixture reviewed against its stated acceptance.',
                              evidence=list(task['evidence']))
    return value


def fixture_security(root: Path, folder="docs/projects/demo") -> str:
    """Reviewed scope for routing fixtures, not an application security model."""
    from harness.security_profiles import AREAS
    path = root / folder / "security.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Fixture security scope\nOnly synthetic local command-selection metadata is processed.\n")
    text = '\n[security]\nstate="reviewed"\ndocument=' + json.dumps(f"{folder}/security.md") + '\n'
    text += 'document_sha256=' + json.dumps(hashlib.sha256(path.read_bytes()).hexdigest()) + '\n'
    text += 'assets=["Synthetic command-selection metadata"]\ntrust_boundaries=["Local temporary test workspace"]\n'
    for area in AREAS:
        text += '\n[[security.controls]]\narea=' + json.dumps(area) + '\nstatus="not_applicable"\n'
        text += 'description="This fixture exercises command selection only; no product implementation is tested."\n'
    return text
