"""Regression checks for scenario approval and canonical customization routing."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("hack_workflow", ROOT / "scripts" / "hack_workflow.py")
assert SPEC is not None and SPEC.loader is not None
workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workflow)


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="abc-workflow-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in workflow.REQUIRED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("reference artifact\n", encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "src" / "Reference.csproj").write_text("<Project />", encoding="utf-8")
        self.evidence = {
            "status": "passed",
            "checkedAtUtc": "2026-10-22T12:00:00Z",
            "applicationUrl": "https://example.invalid",
            "checks": dict.fromkeys(workflow.REQUIRED_CHECKS, True),
        }
        self.write_evidence()

    def write_evidence(self) -> None:
        (self.root / "scenario-validation.json").write_text(json.dumps(self.evidence), encoding="utf-8")

    def approve(self) -> None:
        workflow.snapshot(self.root)
        workflow.record_decision(self.root, "Yes, this working scenario is usable for the hack.", "approved")

    def test_legacy_packages_do_not_authorize_authoring(self) -> None:
        (self.root / "packages").mkdir()
        with self.assertRaises(OSError):
            workflow.check_approval(self.root)

    def test_snapshot_is_not_approval(self) -> None:
        workflow.snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            workflow.check_approval(self.root)

    def test_explicit_approval_is_persisted(self) -> None:
        self.approve()
        state = workflow.check_approval(self.root)
        self.assertEqual("hack-authoring", state["phase"])
        self.assertEqual("approved", state["approval"]["decision"])
        self.assertTrue(state["approval"]["recordedAtUtc"])

    def historical_attestation(self) -> None:
        (self.root / "scenario-validation.json").unlink()
        workflow.attest_history(
            self.root,
            "The full scenario worked as expected; deployment was successful and resources were deleted.",
            "One-off hosted lab subscription is no longer accessible; URL and test logs unavailable.",
        )

    def test_historical_attestation_requires_separate_approval_and_preserves_unknowns(self) -> None:
        self.historical_attestation()
        evidence = workflow.read_object(self.root / "scenario-validation.json")
        self.assertEqual("user-attested", evidence["status"])
        self.assertEqual({}, evidence["checks"])
        self.assertIsNone(evidence["applicationUrl"])
        self.assertIsNone(evidence["checkedAtUtc"])
        state = workflow.snapshot(self.root)
        self.assertEqual(workflow.HISTORICAL_ATTESTATION, state["evidenceType"])
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            workflow.check_approval(self.root)
        workflow.record_decision(self.root, "I approve the tested reference for this hack.", "approved")
        workflow.check_approval(self.root)
        (self.root / "infra" / "main.bicep").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Reference changed"):
            workflow.check_approval(self.root)

    def test_historical_attestation_cannot_overwrite_runtime_evidence_or_invent_checks(self) -> None:
        with self.assertRaisesRegex(ValueError, "already exists"):
            workflow.attest_history(self.root, "Worked", "Unavailable")
        self.historical_attestation()
        self.evidence = workflow.read_object(self.root / "scenario-validation.json")
        for field, value in (
            ("checks", {"deployment": True}),
            ("applicationUrl", "https://invented.invalid"),
            ("checkedAtUtc", "2026-10-22T20:00:00Z"),
            ("status", "passed"),
        ):
            with self.subTest(field=field):
                original = self.evidence[field]
                self.evidence[field] = value
                self.write_evidence()
                with self.assertRaisesRegex(ValueError, "explicit, complete"):
                    workflow.snapshot(self.root)
                self.evidence[field] = original

    def test_invalid_historical_attestation_is_not_a_success_fallback(self) -> None:
        self.historical_attestation()
        self.evidence = workflow.read_object(self.root / "scenario-validation.json")
        for field, value in (
            ("statement", ""), ("unavailableReason", ""), ("recordedAtUtc", "not-a-date"),
            ("successfulDeployment", False), ("fullScenarioWorked", None),
            ("source", "agent-assumption"), ("resourceState", "unknown"),
        ):
            with self.subTest(field=field):
                original = self.evidence["attestation"][field]
                self.evidence["attestation"][field] = value
                self.write_evidence()
                with self.assertRaises(ValueError):
                    workflow.snapshot(self.root)
                self.evidence["attestation"][field] = original

    def test_unknown_evidence_type_rejected(self) -> None:
        self.evidence["evidenceType"] = "assumed-success"
        self.write_evidence()
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            workflow.snapshot(self.root)

    def package_evidence(self) -> None:
        for name in ("coach", "participant", "hack", "coach-guide", "validation"):
            (self.root / "packages" / name).mkdir(parents=True)
            (self.root / "packages" / name / "README.md").write_text("package content", encoding="utf-8")
        for name in ("08-hack-package-contract.md", "nextsteps.MD", "09-hack-event-manifest.json"):
            (self.root / name).write_text("package metadata", encoding="utf-8")
        evidence = {"allCommandsPassed": True, "checks": [
            {"name": name, "exitCode": 0, "command": ["test"]}
            for name in workflow.PACKAGE_CHECKS
        ]}
        (self.root / "packages" / "validation" / "local-checks.json").write_text(
            json.dumps(evidence), encoding="utf-8",
        )

    def test_package_receipt_requires_approval_and_detects_changed_packages(self) -> None:
        self.package_evidence()
        workflow.snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            workflow.record_packages(self.root)
        workflow.record_decision(self.root, "Approved for hack authoring", "approved")
        workflow.record_packages(self.root)
        self.assertEqual("packages_validated", workflow.current_packages(self.root)["status"])
        workflow.check_approval(self.root)
        (self.root / "packages" / "hack" / "README.md").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            workflow.current_packages(self.root)

    def test_package_receipt_rejects_failed_or_missing_checks(self) -> None:
        self.package_evidence()
        self.approve()
        path = self.root / "packages" / "validation" / "local-checks.json"
        evidence = workflow.read_object(path)
        evidence["checks"][0]["exitCode"] = 1
        path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "required commands"):
            workflow.record_packages(self.root)

    def test_empty_approval_is_rejected(self) -> None:
        workflow.snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "explicit user response"):
            workflow.record_decision(self.root, " ", "approved")

    def test_story_code_and_fixture_changes_invalidate_approval(self) -> None:
        self.approve()
        for name in ("01-requirements.md", "infra/main.bicep", "src/Program.cs", "data/products.json"):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes() if path.exists() else None
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("changed\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Reference changed"):
                    workflow.check_approval(self.root)
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)

    def test_reference_change_between_review_and_answer_blocks_approval(self) -> None:
        workflow.snapshot(self.root)
        (self.root / "azure.yaml").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Reference changed"):
            workflow.record_decision(self.root, "Approved", "approved")

    def test_new_review_clears_old_approval(self) -> None:
        self.approve()
        workflow.snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            workflow.check_approval(self.root)

    def test_package_generation_and_progress_do_not_invalidate_reference(self) -> None:
        self.approve()
        for name in ("packages/coach/azure.yaml", "README.md", "nextsteps.MD", "09-hack-event-manifest.json"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("post-approval output", encoding="utf-8")
        workflow.check_approval(self.root)

    def test_missing_live_chat_or_failing_check_blocks_review(self) -> None:
        for value in (False, None, "true", 1):
            with self.subTest(value=value):
                self.evidence["checks"]["applicationChat"] = value
                self.write_evidence()
                with self.assertRaises(ValueError):
                    workflow.snapshot(self.root)

    def test_additional_capability_must_pass(self) -> None:
        self.evidence["checks"]["grounding"] = False
        self.write_evidence()
        with self.assertRaises(ValueError):
            workflow.snapshot(self.root)

    def test_agentic_coordination_failure_blocks_review(self) -> None:
        self.evidence["checks"]["agenticWorkflow"] = False
        self.write_evidence()
        with self.assertRaises(ValueError):
            workflow.snapshot(self.root)
        self.evidence["checks"]["agenticWorkflow"] = True
        self.write_evidence()
        workflow.snapshot(self.root)

    def test_missing_artifacts_block_review(self) -> None:
        (self.root / "demoguide" / "demoguide.md").unlink()
        with self.assertRaisesRegex(ValueError, "Missing or empty"):
            workflow.snapshot(self.root)

    def test_failed_validation_blocks_review(self) -> None:
        self.evidence["status"] = "failed"
        self.write_evidence()
        with self.assertRaisesRegex(ValueError, "has not passed"):
            workflow.snapshot(self.root)

    def test_missing_acceptance_check_blocks_review(self) -> None:
        del self.evidence["checks"]["agentInvocation"]
        self.write_evidence()
        with self.assertRaisesRegex(ValueError, "missing required checks"):
            workflow.snapshot(self.root)

    def test_invalid_application_url_blocks_review(self) -> None:
        self.evidence["applicationUrl"] = "not-deployed"
        self.write_evidence()
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            workflow.snapshot(self.root)

    def test_rejected_approval_does_not_authorize_authoring(self) -> None:
        self.approve()
        workflow.record_decision(self.root, "No, revise the scenario before authoring.", "rejected")
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            workflow.check_approval(self.root)

    def test_cli_failure_is_explicit_and_nonzero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "hack_workflow.py"), "check-approval", str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("Workflow blocked:", result.stderr)
        self.assertNotIn("passed", result.stdout)


class CustomizationTests(unittest.TestCase):
    def test_authorization_continuity_prepares_repairs_before_requesting_new_scope(self) -> None:
        skills = ROOT / ".github" / "skills"
        contract = (skills / "hack-builder-workflow" / "SKILL.md").read_text(encoding="utf-8")
        for requirement in (
            "### Authorization continuity and consolidated review",
            "Do not ask permission merely to prepare a repair or price an unapproved addition",
            "A later read-only grant does not revoke an earlier deployment grant",
            "Agent-written summaries, status reports and derived authorization files "
            "cannot create or revoke user consent",
            "Trace a claimed restriction to its actual user response",
            "defer only",
            "affected cloud operations",
            "Azure readiness reads and Entra ownership reads are distinct",
            "Do not require a preliminary choice",
            "Present one consolidated new-scope review",
            "incremental and total estimated cost",
            "Request only missing authority or the material change",
            "Event rollout, publication and suitability remain separate",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contract)
        for path in (
            ROOT / ".github" / "agents" / "az-01-conductor.agent.md",
            skills / "az-scenario-architecture" / "SKILL.md",
            skills / "az-azure-deploy" / "SKILL.md",
            skills / "az-azure-validate" / "SKILL.md",
        ):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIn("#authorization-continuity-and-consolidated-review", path.read_text(encoding="utf-8"))

    def test_validation_failures_do_not_force_routine_approval_or_offer_gate_bypass(self) -> None:
        text = (ROOT / ".github" / "skills" / "az-azure-validate" / "SKILL.md").read_text(encoding="utf-8")
        for requirement in (
            "A failed required check still blocks its dependent operation",
            "Diagnose and repair generated code/configuration within existing authority",
            "Continue independent local preparation",
            "Never offer to skip a required security or acceptance check",
            "Do not install shared tools, change shared defaults or register providers "
            "without applicable authorization",
            "defer unauthorized discovery",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)
        self.assertNotIn("Skip the gate (accepting risk)", text)
        self.assertNotIn("**Ask the user**", text)

    def test_private_management_access_is_designed_and_consumed_across_phases(self) -> None:
        skills = ROOT / ".github" / "skills"
        contract = (skills / "hack-builder-workflow" / "SKILL.md").read_text(encoding="utf-8")
        for requirement in (
            "### Private-workload management access",
            "public-IP allowlist does not route to a private endpoint",
            "not automatic network connectivity for the local Copilot worker",
            "Route metadata alone is not acceptance evidence",
            "ongoing VM/disk/Bastion/VPN",
            "absent management path is a design gap",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contract)
        for path in (
            skills / "az-scenario-architecture" / "SKILL.md",
            skills / "az-scenario-bicep" / "SKILL.md",
            skills / "az-azure-deploy" / "SKILL.md",
            ROOT / ".github" / "agents" / "az-01-conductor.agent.md",
            skills / "az-azure-artifacts" / "templates" / "02-architecture-assessment.template.md",
        ):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIn("#private-workload-management-access", path.read_text(encoding="utf-8"))

    def test_container_guidance_avoids_emulated_sdk_without_changing_runtime_target(self) -> None:
        skill = (ROOT / ".github" / "skills" / "az-webapp-development" / "SKILL.md").read_text(encoding="utf-8")
        instructions = (ROOT / ".github" / "instructions" / "az-dotnet-webapp.instructions.md").read_text(encoding="utf-8")
        self.assertIn("FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0 AS build", skill)
        self.assertIn("FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime", skill)
        self.assertIn("never drop `--locked-mode`", skill)
        self.assertIn("not a missing Docker/SDK prerequisite", skill)
        self.assertIn("--platform=$BUILDPLATFORM", instructions)

    def test_identity_setup_guidance_is_wired_across_scenario_procedures(self) -> None:
        skill = ROOT / ".github" / "skills"
        contract = (skill / "hack-builder-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("### Scenario-owned application identity setup", contract)
        self.assertIn("default to new dedicated scenario-owned registrations", contract)
        self.assertIn("Read-only preparation", contract)
        self.assertIn("ask the same route question again", contract)
        self.assertIn("**Deployment outputs are not user inputs.**", contract)
        self.assertIn("Do not request them in a business decision", contract)
        self.assertIn("Avoid a circular preparation gate", contract)
        for path in (
            skill / "az-scenario-architecture" / "SKILL.md",
            skill / "az-scenario-bicep" / "SKILL.md",
            skill / "az-azure-deploy" / "SKILL.md",
            ROOT / ".github" / "agents" / "az-01-conductor.agent.md",
        ):
            with self.subTest(path=path.name, parent=path.parent.name):
                self.assertIn("#scenario-owned-application-identity-setup", path.read_text(encoding="utf-8"))

    def test_sample_accounts_and_deployer_rbac_contract_is_wired(self) -> None:
        contract = (ROOT / ".github/skills/hack-builder-workflow/SKILL.md").read_text(encoding="utf-8")
        for requirement in (
            "### Sample application accounts and Azure resource access",
            "Never use Entra ID authentication for a sample app if admin consent is required",
            ".private/participant-access.json",
            ".private/coach-access.json",
            "Public/GitHub-ready guides contain placeholders",
            "Azure resource-to-resource authentication always uses managed identities",
            "Subscription ownership alone does not",
            "runtime managed-identity acceptance",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contract)
        for relative in (
            ".github/agents/az-01-conductor.agent.md",
            ".github/agents/az-09-hackcreator.agent.md",
            ".github/skills/az-scenario-architecture/SKILL.md",
            ".github/skills/az-scenario-bicep/SKILL.md",
            ".github/skills/az-azure-deploy/SKILL.md",
            ".github/skills/az-webapp-development/SKILL.md",
            ".github/instructions/az-dotnet-webapp.instructions.md",
            ".github/instructions/hack-authoring.instructions.md",
        ):
            path = ROOT / relative
            with self.subTest(path=relative):
                text = path.read_text(encoding="utf-8")
                self.assertIn("#sample-application-accounts-and-azure-resource-access", text)
                self.assertTrue(any(word in text for word in ("private", "deploying-admin", "deploying admin")))
        webapp = (ROOT / ".github/skills/az-webapp-development/SKILL.md").read_text(encoding="utf-8")
        dotnet = (ROOT / ".github/instructions/az-dotnet-webapp.instructions.md").read_text(encoding="utf-8")
        self.assertNotIn("Add authentication to the sample app (keep it simple for demos)", webapp)
        self.assertNotIn("Do not add authentication/authorization middleware", dotnet)

    def test_agentic_catalog_has_all_18_patterns_and_source_pages(self) -> None:
        guide = (
            ROOT / ".github" / "skills" / "az-scenario-requirements" / "references" / "agentic-patterns.md"
        ).read_text(encoding="utf-8")
        names = re.findall(r"(?m)^### (\d{2})\. (.+)$", guide)
        self.assertEqual([
            "Single-Agent Tool Loop", "Sequential / Pipeline", "Concurrent / Fan-Out-Fan-In",
            "Routing / Triage", "Handoff / Transfer of Control", "Moderated Group Chat",
            "Magentic Dynamic Collaboration", "Supervisor / Hierarchical Delegation", "Orchestrator-Workers",
            "Planner-Executor", "Deterministic Loop", "Evaluator-Optimizer / Reflection", "Mixture of Agents",
            "Event-Driven / Reactive Agents", "Blackboard / Shared Workspace", "Swarm / Peer-to-Peer",
            "Human-in-the-Loop (HITL)", "Adaptive Hybrid / Composite Orchestration",
        ], [name for _, name in names])
        self.assertEqual([f"{number:02}" for number in range(1, 19)], [number for number, _ in names])
        for number in range(18):
            self.assertIn(f"PDF pp. {5 + number * 3}-{7 + number * 3}.", guide)
        for unit in (
            "generic", "executives", "it", "operations", "communications", "executive-assistant",
            "legal", "hr", "business-manager", "finance", "sales", "marketing",
        ):
            self.assertIn(f"| `{unit}` |", guide)
        for boundary in (
            "not 18 native Foundry features", "not permission to add Copilot agents",
            "not a separate package plan before approval", "checks.agenticWorkflow",
            "not hidden chain-of-thought", "not automatically rewritten",
        ):
            self.assertIn(boundary, guide)

    def test_agentic_contract_is_wired_through_both_phases(self) -> None:
        paths = (
            ".github/agents/az-01-conductor.agent.md",
            ".github/instructions/az-foundry.instructions.md",
            ".github/skills/hack-builder-workflow/SKILL.md",
            ".github/skills/az-scenario-requirements/SKILL.md",
            ".github/skills/az-scenario-architecture/SKILL.md",
            ".github/skills/az-webapp-development/SKILL.md",
            ".github/skills/az-webapp-development/app-creation-SKILL.md",
            ".github/skills/az-azure-validate/SKILL.md",
            ".github/skills/az-scenario-demonstration/SKILL.md",
            ".github/skills/azure-foundry-hack-builder/SKILL.md",
            ".github/skills/azure-foundry-hack-builder/references/composition-procedure.md",
            ".github/skills/az-azure-artifacts/templates/01-requirements.template.md",
            ".github/skills/az-azure-artifacts/templates/02-architecture-assessment.template.md",
        )
        for relative in paths:
            path = ROOT / relative
            with self.subTest(path=relative):
                text = path.read_text(encoding="utf-8")
                links = re.findall(r"\]\(([^)]+agentic-patterns\.md)\)", text)
                self.assertTrue(links)
                for link in links:
                    self.assertTrue((path.parent / link).resolve().is_file(), link)
        companion = (ROOT / paths[6]).read_text(encoding="utf-8")
        self.assertNotIn("specialist-agent-3.agent.md", companion)
        self.assertIn("A bounded single-agent tool loop remains valid", companion)

    def test_agentic_templates_preserve_required_h2_order(self) -> None:
        templates = ROOT / ".github" / "skills" / "az-azure-artifacts" / "templates"
        for filename, headings, new_section in (
            ("01-requirements.template.md", [
                "Project Overview", "Functional Requirements", "Non-Functional Requirements (NFRs)",
                "Summary for Architecture Assessment",
            ], "Agentic business workflow"),
            ("02-architecture-assessment.template.md", [
                "Requirements Validation", "Resource SKU Recommendations", "Architecture Decision Summary",
                "Implementation Handoff",
            ], "Agentic runtime contract"),
        ):
            with self.subTest(template=filename):
                text = (templates / filename).read_text(encoding="utf-8")
                self.assertEqual(headings, re.findall(r"(?m)^## (.+)$", text))
                self.assertIn(f"### {new_section}", text)

    def test_exactly_two_canonical_agent_contexts_exist(self) -> None:
        agents = ROOT / ".github" / "agents"
        self.assertEqual(
            {"az-01-conductor.agent.md", "az-09-hackcreator.agent.md"},
            {path.name for path in agents.glob("*.agent.md")},
        )
        for filename, name in (
            ("az-01-conductor.agent.md", "az-01-conductor"),
            ("az-09-hackcreator.agent.md", "HackCreator Agent"),
        ):
            with self.subTest(agent=name):
                text = (agents / filename).read_text(encoding="utf-8")
                self.assertIn(f"name: {name}\n", text)

    def test_agent_models_are_inherited_and_visibility_is_valid(self) -> None:
        for path in (ROOT / ".github" / "agents").glob("*.agent.md"):
            with self.subTest(agent=path.name):
                frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
                self.assertNotRegex(frontmatter, r"(?m)^model:")
                self.assertNotIn("user-invokable:", frontmatter)
                self.assertIn("user-invocable: true", frontmatter)
                self.assertNotRegex(frontmatter, r"(?m)^(?:model|reasoning-effort|handoffs):")

    def test_skill_names_match_directories(self) -> None:
        for folder in (ROOT / ".github" / "skills", ROOT / ".agents" / "skills"):
            for path in folder.glob("*/SKILL.md"):
                with self.subTest(skill=path.parent.name):
                    frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
                    match = re.search(r"(?m)^name: (.+)$", frontmatter)
                    self.assertIsNotNone(match)
                    self.assertEqual(path.parent.name, match[1])

    def test_compatibility_launchers_are_small_and_manual_only(self) -> None:
        for path in (ROOT / ".agents" / "skills").glob("*/SKILL.md"):
            with self.subTest(launcher=path.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("disable-model-invocation: true", text)
                self.assertIn("hack-builder-workflow/SKILL.md", text)
                self.assertLess(len(text.splitlines()), 30)

    def test_hackcreator_enforces_approval_and_does_not_deploy(self) -> None:
        text = (ROOT / ".github" / "agents" / "az-09-hackcreator.agent.md").read_text(encoding="utf-8")
        self.assertIn("check-approval", text)
        self.assertIn("both modes", text)
        self.assertIn("Do not deploy resources", text)
        self.assertIn("scenario-specific minimum", text)
        self.assertIn("composition-procedure.md", text)
        self.assertIn("decision required", text)

    def test_reference_and_event_deployment_are_separate(self) -> None:
        text = (ROOT / ".github" / "skills" / "az-azure-deploy" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Default to **reference** scope", text)
        self.assertIn("separate explicit event-deployment request", text)
        self.assertIn("Never require a hack contract", text)
        self.assertRegex(text, r"application\s+URL only if the starter")
        self.assertIn("Approve architecture & deploy", text)
        self.assertIn("Agent owns in-scope repairs", text)

    def test_both_agents_execute_without_delegation(self) -> None:
        for path in (ROOT / ".github" / "agents").glob("*.agent.md"):
            with self.subTest(agent=path.name):
                frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
                self.assertIn("agents: []", frontmatter)
                tools = re.search(r"(?m)^tools: \[(.+)\]$", frontmatter)
                self.assertIsNotNone(tools)
                self.assertNotIn("agent", {value.strip() for value in tools[1].split(",")})
                self.assertNotIn("runSubagent", frontmatter)

    def test_procedural_sources_are_skill_references_not_agents(self) -> None:
        skills = ROOT / ".github" / "skills"
        for folder, source in (
            ("az-scenario-requirements", "historical-validation.md"),
            ("az-scenario-architecture", "historical-architecture.md"),
            ("az-scenario-bicep", "historical-bicep.md"),
            ("az-webapp-development", "historical-development.md"),
            ("az-azure-deploy", "historical-deployment.md"),
            ("az-scenario-demonstration", "historical-demoguide.md"),
            ("az-azure-diagrams", "historical-diagrammer.md"),
            ("az-scenario-contribution", "historical-contribution.md"),
        ):
            with self.subTest(skill=folder):
                entry = (skills / folder / "SKILL.md").read_text(encoding="utf-8")
                reference = skills / folder / "references" / source
                self.assertIn(f"./references/{source}", entry)
                self.assertTrue(reference.is_file())
                self.assertIn("Historical source preserved on 2026-10-22", reference.read_text(encoding="utf-8"))

    def test_active_customizations_do_not_reference_removed_agent_names(self) -> None:
        roots = (
            ROOT / ".github" / "agents",
            ROOT / ".github" / "skills",
            ROOT / ".github" / "instructions",
            ROOT / ".agents" / "skills",
        )
        for folder in roots:
            for path in folder.rglob("*.md"):
                if path.name.startswith("historical-") or path.name == "oilgas-legacy-input.md":
                    continue
                with self.subTest(file=str(path.relative_to(ROOT))):
                    self.assertNotRegex(path.read_text(encoding="utf-8"), r"az[-:]0[2-8](?:[-:]|b-)")
                    self.assertNotRegex(
                        path.read_text(encoding="utf-8"),
                        r"(?:Deploy|Development|Validation|Bicep) agent",
                    )

    def test_vscode_agents_own_execution_and_never_auto_start_composition(self) -> None:
        text = (ROOT / ".github" / "agents" / "az-01-conductor.agent.md").read_text(encoding="utf-8")
        for phrase in (
            "directly in this VS Code context",
            "portal_status.py",
            "Handle decisions and tool permission prompts in this VS Code session",
            "Do not approve",
            "composition automatically",
            "projectSlug",
            "no setup-retry loop",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        contract = (ROOT / ".github" / "skills" / "hack-builder-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scenario process must not start composition automatically", contract)
        self.assertIn("reviewed fingerprint", contract)
        self.assertIn("separate explicit event-deployment request", contract)

    def test_industry_intake_and_skillable_support_remain_distinct(self) -> None:
        catalog = ROOT / ".github" / "skills" / "skillable-lod-authoring" / "assets" / "industry-catalog.json"
        entries = json.loads(catalog.read_text(encoding="utf-8"))
        self.assertEqual(8, len(entries))
        self.assertIn(
            {"displayName": "Media & Communications", "slug": "media-communications",
             "positioning": "Campaign engagement, subscriber recovery and human-reviewed cross-unit handoffs"},
            entries,
        )
        self.assertIn(
            {"displayName": "Hospitality & Travel", "slug": "hospitality-travel",
             "positioning": "Sales-led service readiness, guest workflows and reviewed business handoffs"},
            entries,
        )
        self.assertTrue((ROOT / "microsoft_industry_verticals.csv").is_file())
        for path in (
            ROOT / ".github" / "agents" / "az-09-hackcreator.agent.md",
            ROOT / ".github" / "skills" / "skillable-lod-authoring" / "SKILL.md",
        ):
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("microsoft_industry_verticals.csv", text)
                self.assertRegex(text.lower(), r"unsupported\s+industr(?:y|ies)")
                self.assertRegex(text.lower(), r"never silently\s+map")


if __name__ == "__main__":
    unittest.main()
