"""Local maintenance CLI; model work dispatches to the routing entrypoints."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

from . import agent_config, check_snapshots, checks, context, doctor, environment, evidence, evaluation, experiments, knowledge, mcp, pilot, security, skills, tasks, workflows, workspaces
from .provenance import load, local_file
from .core import changed_paths, source_paths

ROOT = Path(__file__).resolve().parents[3]


def setup(root: Path, browser=False) -> dict:
    result = {**doctor.inspect(root), "skills": "native_repository", "browser": "not_requested",
              "note": "Codex reads .agents/skills directly; client trust, login and MCP connectivity are separate checks."}
    result["environment"] = environment.inspect(root)
    if result["status"] != "passed":
        return result
    if browser:
        npm = shutil.which("npm")
        if not npm:
            raise ValueError("Node.js/npm required for optional browser tools")
        command = [npm, "ci", "--prefix", "tools/harness/browser", "--cache", str(root / ".cache/npm"), "--no-audit", "--no-fund"]
        installed = subprocess.run(command, cwd=root, timeout=180, check=False, stdout=sys.stderr, stderr=sys.stderr)
        if installed.returncode:
            return {**result, "status": "failed", "browser": "dependency_install_failed"}
        cli = root / "tools/harness/browser/node_modules/playwright/cli.js"
        node = shutil.which("node")
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(root / ".cache/playwright")
        installed = subprocess.run([node, str(cli), "install", "chromium"], cwd=root, env=env, timeout=300, check=False, stdout=sys.stderr, stderr=sys.stderr)
        if installed.returncode:
            return {**result, "status": "failed", "browser": "browser_install_failed"}
        # Register only after both package and browser installation succeed.
        codex = root / ".codex/config.toml"
        if "[mcp_servers.playwright]" not in codex.read_text():
            with codex.open("a") as stream:
                stream.write('\n[mcp_servers.playwright]\ncommand = "node"\nargs = ["tools/harness/scripts/mcp-browser.mjs"]\n')
        result["browser"] = "installed_and_registered"
    return result


def main(argv=None, *, root: Path = ROOT) -> int:
    root = root.resolve()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"catalog", "route", "run", "chat"}:
        from .routing.cli import main as routing_main
        return routing_main(argv)
    parser = argparse.ArgumentParser(description="Portable harness setup, doctor, checks and task records")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("catalog", add_help=False, help="List supported model/reasoning combinations")
    commands.add_parser("route", add_help=False, help="Recommend a model/reasoning pair; does not execute tasks")
    commands.add_parser("run", add_help=False, help="Route a task, then execute using the selected model/effort")
    commands.add_parser("chat", add_help=False, help="Route and execute every prompt, retaining conversation context")
    p = commands.add_parser("setup")
    p.add_argument("--browser", action="store_true", help="Install locked browser tools and Chromium locally (network required)")
    p = commands.add_parser("knowledge", help="Review, retrieve and share portable lessons; no background models or global settings")
    knowledge_commands = p.add_subparsers(dest="knowledge_action", required=True)
    p = knowledge_commands.add_parser("add")
    p.add_argument("spec", help="Repository-relative JSON lesson specification")
    for name in ("list", "search"):
        p = knowledge_commands.add_parser(name)
        if name == "search":
            p.add_argument("query")
        p.add_argument("--project")
        p.add_argument("--state", choices=sorted(knowledge.STATES))
    p = knowledge_commands.add_parser("show")
    p.add_argument("id")
    p = knowledge_commands.add_parser("review")
    p.add_argument("id")
    p.add_argument("--state", choices=["evaluated", "adopted", "superseded"], required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--replacement")
    p = knowledge_commands.add_parser("promote")
    p.add_argument("id")
    p.add_argument("new_id")
    p.add_argument("--reason", required=True)
    p = knowledge_commands.add_parser("export")
    p.add_argument("output")
    p.add_argument("--project")
    p = knowledge_commands.add_parser("import")
    p.add_argument("bundle")
    p.add_argument("--dry-run", action="store_true")
    p = commands.add_parser("skill", help="Create and validate native repository skills without global installation")
    skill_commands = p.add_subparsers(dest="skill_action", required=True)
    p = skill_commands.add_parser("create")
    p.add_argument("name")
    p.add_argument("--description", required=True)
    p.add_argument("--instructions", required=True, help="Repository-relative Markdown body")
    p.add_argument("--topic", action="append", default=[])
    p.add_argument("--kind", action="append", default=[])
    p.add_argument("--path", action="append", default=[])
    p = skill_commands.add_parser("from-knowledge")
    p.add_argument("id")
    p.add_argument("name")
    p.add_argument("--description", required=True)
    p = skill_commands.add_parser("validate")
    p.add_argument("name")
    p = commands.add_parser("environment", help="Inspect project package managers or explicitly install locked local dependencies")
    environment_commands = p.add_subparsers(dest="environment_action", required=True)
    for name in ("inspect", "install"):
        p = environment_commands.add_parser(name)
        p.add_argument("--path", default=".")
        if name == "install":
            p.add_argument("--offline", action="store_true")
            p.add_argument("--allow-scripts", action="store_true", help="Allow reviewed dependency lifecycle/build scripts")
    commands.add_parser("doctor", help="Read-only offline configuration and link checks")
    commands.add_parser("mcp-check", help="Opt-in HTTP MCP initialize/tools-list check (network; no model)")
    p = commands.add_parser("security", help="Local secret-pattern candidates or explicit dependency advisory lookup; no fixes")
    security_commands = p.add_subparsers(dest="security_action", required=True)
    p = security_commands.add_parser("secrets", help="Offline text-pattern scan; never prints matching values")
    p.add_argument("--paths", nargs="+", help="Explicit local files; otherwise Git sources including untracked files")
    p = security_commands.add_parser("config", help="Audit Codex settings; external AgentShield is optional and must be installed separately")
    p.add_argument("--engine", choices=["builtin", "agentshield"], default="builtin")
    p = security_commands.add_parser("dependencies", help="Audit explicit public npm locks or flattened pinned Python requirements")
    p.add_argument("--npm-lock", action="append", default=[])
    p.add_argument("--requirements", action="append", default=[])
    p.add_argument("--allow-network", action="store_true", help="Allow sending dependency names/versions to advisory services")
    p = commands.add_parser("check")
    p.add_argument("--paths", nargs="+", help="Explicit repository-relative changed paths")
    p.add_argument("--full", action="store_true", help="Run all registered checks; not a guarantee of product acceptance")
    p.add_argument("--staged", action="store_true", help="Export and verify the exact Git index")
    p.add_argument("--snapshot", action="store_true", help="Capture current sources into an isolated local workspace before checks")
    p.add_argument("--reuse", action="store_true", help="Reuse eligible deterministic results on an unchanged snapshot")
    p.add_argument("--plan", action="store_true", help="Show scope selection without running commands")
    p.add_argument("--checkpoint", choices=['edit', 'feature', 'integration', 'final'], default='feature', help="Verification boundary; default is one meaningful user outcome")
    p.add_argument("--report-dir", type=Path, help=argparse.SUPPRESS)
    p.add_argument("--project", help="Repository-relative project workflow.toml; overrides [project].workflow")
    p = commands.add_parser("context", help="Select relevant skills/references/project documents before work")
    p.add_argument("--kind", choices=(*tasks.KINDS, "plan"), required=True)
    p.add_argument("--paths", nargs="*", default=[])
    p.add_argument("--topic", action="append", default=[], help="A topic from .agents/context.toml; repeatable")
    p.add_argument("--project")
    p.add_argument("--read", action="store_true", help="Include the selected files' actual contents")
    p = commands.add_parser("project", help="Create a draft project brief/workflow without choosing tools or commands")
    p.add_argument("slug")
    p.add_argument("--goal", required=True)
    p = commands.add_parser("task")
    p.add_argument("slug")
    p.add_argument("--kind", choices=tasks.KINDS, required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--acceptance", action="append", required=True)
    p = commands.add_parser('evidence', help='Attach content-bound task evidence, review and close locally')
    evidence_commands = p.add_subparsers(dest='evidence_action', required=True)
    p = evidence_commands.add_parser('add')
    p.add_argument('slug')
    p.add_argument('--id', required=True)
    p.add_argument('--type', choices=sorted(evidence.TYPES), required=True)
    p.add_argument('--path', required=True)
    p.add_argument('--criterion', required=True)
    p.add_argument('--method', required=True)
    p.add_argument('--description', required=True)
    p.add_argument('--check')
    p.add_argument('--origin')
    p.add_argument('--accessed-at', help='Actual source access date/time in ISO format; defaults to now')
    for name in ('review-template', 'verify', 'complete'):
        p = evidence_commands.add_parser(name)
        p.add_argument('slug')
        if name != 'review-template':
            p.add_argument('--review', help='Repository-relative reviewed JSON record')
    p = commands.add_parser('evaluate', help='Assess saved task outcomes; no model calls or fabricated token statistics')
    p.add_argument('suite')
    p.add_argument('--label', required=True)
    commands.add_parser('evaluate-pilot', help='Replay six known-answer local workflows in a new ignored workspace; no models/browser')
    p = commands.add_parser('experiment', help='Run or compare explicit, bounded local experiment protocols')
    experiment_commands = p.add_subparsers(dest='experiment_action', required=True)
    p = experiment_commands.add_parser('run')
    p.add_argument('recipe')
    p.add_argument('--variant', required=True)
    p = experiment_commands.add_parser('compare')
    p.add_argument('baseline')
    p.add_argument('candidate')
    p = commands.add_parser("session", help="Inspect isolation or create a work-unit Git worktree; no staging/commit/install")
    session_commands = p.add_subparsers(dest="session_action", required=True)
    session_commands.add_parser("status")
    p = session_commands.add_parser("start")
    p.add_argument("slug")
    p.add_argument("--base", default="HEAD")
    p.add_argument("--goal", required=True)
    p.add_argument("--scope", action="append", required=True)
    p = commands.add_parser("integration", help="Prepare and check a separate two-work-unit integration rehearsal")
    integration_commands = p.add_subparsers(dest="integration_action", required=True)
    p = integration_commands.add_parser("prepare")
    p.add_argument("slug")
    p.add_argument("--source", required=True)
    p.add_argument("--target", default="HEAD")
    p.add_argument("--goal", required=True)
    p.add_argument("--acceptance", action="append", required=True)
    p = integration_commands.add_parser("status")
    p.add_argument("slug")
    p = integration_commands.add_parser("check")
    p.add_argument("slug")
    p.add_argument("--plan", action="store_true")
    p.add_argument("--full", action="store_true")
    p.add_argument("--project")
    args = parser.parse_args(argv)
    try:
        if args.action == "doctor":
            result = doctor.inspect(root)
        elif args.action == "knowledge":
            action = args.knowledge_action
            if action == "add":
                result = knowledge.add(root, load(local_file(root, args.spec), knowledge.LIMIT))
            elif action in {"list", "search"}:
                result = knowledge.listing(root, project=args.project, state=args.state, query=getattr(args, "query", None))
            elif action == "show":
                result = knowledge.show(root, args.id)
            elif action == "review":
                result = knowledge.review(root, args.id, args.state, args.reason, args.evidence, args.replacement)
            elif action == "promote":
                result = knowledge.promote(root, args.id, args.new_id, args.reason)
            elif action == "export":
                result = knowledge.export(root, args.output, project=args.project)
            else:
                result = knowledge.import_bundle(root, args.bundle, dry_run=args.dry_run)
        elif args.action == "skill":
            if args.skill_action == "create":
                body = local_file(root, args.instructions).read_text(encoding="utf-8")
                result = skills.create(root, args.name, args.description, body, topics=args.topic, kinds=args.kind, paths=args.path)
            elif args.skill_action == "from-knowledge":
                result = skills.from_knowledge(root, args.id, args.name, args.description)
            else:
                result = skills.validate(local_file(root, f".agents/skills/{knowledge.slug(args.name)}/SKILL.md"))
        elif args.action == "environment":
            result = (environment.inspect(root, args.path) if args.environment_action == "inspect" else
                      environment.install(root, args.path, offline=args.offline, allow_scripts=args.allow_scripts))
        elif args.action == "security":
            if args.security_action == "config":
                result = agent_config.inspect(root) if args.engine == "builtin" else agent_config.agentshield(root)
            else:
                result = (security.secrets(root, args.paths) if args.security_action == "secrets" else
                          security.dependencies(root, npm_locks=args.npm_lock, requirements=args.requirements,
                                                allow_network=args.allow_network))
        elif args.action == "mcp-check":
            config = tomllib.loads((root / ".codex/config.toml").read_text())
            results = {name: mcp.probe(s["url"]) for name, s in config.get("mcp_servers", {}).items()
                       if "url" in s and s.get("enabled", True)}
            result = {"status": "passed" if results and all(r["status"] == "passed" for r in results.values()) else "unavailable", "servers": results,
                      "note": "Protocol reachability only; client trust/loading and tool-call correctness are separate."}
        elif args.action == "setup":
            result = setup(root, args.browser)
        elif args.action == "task":
            path = tasks.create(root, args.slug, args.kind, args.goal, args.acceptance)
            result = {"status": "created", "task": str(path.relative_to(root))}
        elif args.action == 'evidence':
            if args.evidence_action == 'add':
                result = evidence.add(root, args.slug, args.id, args.type, args.path, args.criterion,
                                      args.method, args.description, check=args.check, origin=args.origin, accessed_at=args.accessed_at)
            elif args.evidence_action == 'review-template':
                result = evidence.review_template(root, args.slug)
            else:
                result = evidence.finish(root, args.slug, review=args.review, complete=args.evidence_action == 'complete')
        elif args.action == 'evaluate-pilot':
            result = pilot.run(root)
        elif args.action == 'evaluate':
            result = evaluation.run(root, args.suite, args.label)
        elif args.action == 'experiment':
            result = (experiments.run(root, args.recipe, args.variant) if args.experiment_action == 'run'
                      else experiments.compare(root, args.baseline, args.candidate))
        elif args.action == "project":
            path = workflows.create(root, args.slug, args.goal)
            result = {"status": "created", "workflow": str(path.relative_to(root)), "state": "draft",
                      "note": "Fill in real project commands and context, then activate explicitly."}
        elif args.action == "context":
            result = context.select(root, args.kind, args.paths, args.topic, workflow=args.project, read=args.read)
        elif args.action == "session":
            result = workspaces.status(root) if args.session_action == "status" else workspaces.start(root, args.slug, args.base, args.goal, args.scope)
        elif args.action == "integration":
            if args.integration_action == "prepare":
                result = workspaces.prepare(root, args.slug, args.source, args.target, args.goal, args.acceptance)
            elif args.integration_action == "status":
                result = workspaces.inspect_integration(root, args.slug)
            else:
                result = workspaces.verify(root, args.slug, full=args.full, plan=args.plan, workflow=args.project)
        else:
            if args.snapshot and (args.staged or args.reuse or args.plan or args.report_dir):
                raise ValueError("--snapshot cannot combine with --staged, --reuse, --plan or a custom report directory")
            if args.staged and (args.paths or args.reuse):
                raise ValueError("--staged cannot use working-tree --paths or cached results")
            paths = changed_paths(root, staged=args.staged) if args.staged else args.paths
            if paths is None:
                paths = source_paths(root) if args.full else changed_paths(root)
            if args.plan:
                result = checks.plan(root, paths, args.full, args.project, checkpoint=args.checkpoint)
                result["status"] = "needs_configuration" if result["uncovered_paths"] or result["configuration_pending"] else "planned"
            elif args.staged:
                result = checks.staged(root, args.full, args.project, checkpoint=args.checkpoint)
            elif args.snapshot:
                result = check_snapshots.run(root, paths, full=args.full, workflow=args.project, checkpoint=args.checkpoint)
            else:
                result = checks.run(root, paths, full=args.full, reuse=args.reuse, report_dir=args.report_dir, workflow=args.project, checkpoint=args.checkpoint)
        display = {k: v for k, v in result.items() if k != 'captured_sources'}
        if 'source_snapshot' in result:
            display = {k: v for k, v in result.items() if k not in {'source_snapshot', 'source_executable', 'environment', 'protocol', 'captured_sources'}}
            display['source_file_count'] = len(result['source_snapshot'])
        if args.action == "check" and "report" in result:
            display = {k: v for k, v in display.items() if k != "paths"}
            display["changed_path_count"] = len(result.get("paths", []))
            display["results"] = [{k: v for k, v in record.items() if k not in {"command", "cwd"}}
                                  for record in result["results"]]
        print(json.dumps(display, ensure_ascii=False, indent=2))
        if args.action == "check" and result.get("status") == "checks_passed_security_pending":
            return 0 if not args.full and args.checkpoint in {"edit", "feature"} else 2
        return 0 if result.get("status") in {"passed", "planned", "created", "prepared", "checks_passed_review_pending", "checkpoint_passed", "deferred"} else 2
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
