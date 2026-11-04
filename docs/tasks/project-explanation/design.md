# Project explanation workflow design

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "behavioral",
  "requirements": [
    "R1",
    "R2",
    "R3",
    "R4"
  ],
  "operations": [
    {
      "id": "O1",
      "requirements": [
        "R1",
        "R2",
        "R3",
        "R4"
      ],
      "paths": [
        "AGENTS.md",
        ".agents/context.toml",
        ".agents/skills/plan-project/**",
        ".agents/skills/verify-work/SKILL.md",
        ".agents/skills/verify-work/references/acceptance.md",
        ".agents/skills/verify-work/routes.toml",
        ".agents/skills/docs-maintenance/references/synchronization.md",
        "tools/harness/tests/test_project_explanation.py",
        "docs/tasks/project-explanation/**",
        "docs/tasks/index.md"
      ],
      "depends_on": [],
      "verification": "Actual context/flow reads and project-scoped selection plus source-linked scenario review; doctor and related regression checks."
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "User authorized implementation in current checkout; progressive explanations and final-only generic question derivation."
    }
  ]
}
```

## Requirements
R1: Accumulate explanations during work and derive questions only at final review. R2: One source-linked guide with scoped read and resume. R3: Existing plan/implementation/review entry points consume instructions without altering approval gates. R4: Generic guidance, template and verified selection with no supplied example content.

## Entities
Project guide, source/decision records, observed verification evidence and final study questions have different responsibilities.

## Approach
Extend the existing planning owner with one reference/template; connect existing handoff, document sync and verification. An independent generator would duplicate agent judgment.

## Structure
Project content lives in architecture/explanation-guide.md; reusable rules live in the planning skill. Existing runtime and task contracts stay authoritative.

## Operations
### O1
Add generic instructions, discovery and route reads; test actual selection, project rules and preserved gates.

## Norms
Current user scope, existing AGENTS and skill contracts apply. Preserve concurrent edits.

## Safeguards
No copied example questions or subject matter. No speculative reasons or invented execution. Keep step review and no blanket guide requirement for small requests. UI E2E is inapplicable; exercise actual context and flow behavior instead.
