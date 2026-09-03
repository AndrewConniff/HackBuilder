"""Validate Skillable authoring resources and generated scenario packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

SKILL_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INDUSTRIES = {
    "financial-services",
    "healthcare",
    "manufacturing",
    "retail",
    "energy-oil-gas",
    "government-public-sector",
}
CHALLENGE_PREFIXES = ("01-", "02-", "03-", "04-", "05-")
EXPECTED_CHALLENGE_FILES = (
    "01-secure-foundation.md",
    "02-build-the-agent.md",
    "03-ground-it.md",
    "04-give-it-tools.md",
    "05-harden-and-demo.md",
)
REQUIRED_LAB_KEYS = {
    "title",
    "module",
    "description",
    "duration",
    "level",
    "islab",
    "primarytopics",
}
REQUIRED_CHALLENGE_SECTIONS = (
    "## 💡 Scenario",
    "## 🎯 What you will learn",
    "## 🛠️ High-level lab steps",
    "## 🎒 Prerequisites",
    "## 🎯 Goal",
    "## 💡 Why this matters",
    "## 🧱 Build on what works",
    "## 🧭 Choose your path",
    "## ✅ Done when",
    "## 💬 Stuck?",
    "## 🌟 Stretch goal",
    "## 🔁 Fallback",
    "## Summary",
)
COACH_NOTE_LABELS = (
    "Objective and expected outcome",
    "Completion evidence",
    "Coach talking points",
    "Common blockers and recovery",
    "Hint escalation",
    "Fallback checkpoint",
    "Demo and debrief prompts",
    "Security and governance reminders",
)
REQUIRED_NEXTSTEPS_SECTIONS = (
    "## Scenario context",
    "## Delivery rules",
    "## Artifact inventory",
    "## Detailed artifact specifications",
    "## Creation and review sequence",
    "## Package and GitHub publication",
    "## Azure load and installation plan",
    "## Deployment and test gate",
    "## Completion tracking",
)
REQUIRED_ARTIFACT_FIELDS = (
    "Purpose and challenge use",
    "Deployment classification",
    "Status",
    "Proposed filename",
    "Repository destinations",
    "Package visibility",
    "Artifact type and format",
    "Target Azure service and destination",
    "Schema or document structure",
    "Required fields or sections",
    "Expected quantity or size",
    "Synthetic content requirements",
    "Generation method and dependencies",
    "Upload or installation method",
    "Identity and access",
    "Local validation",
    "Azure validation",
    "Acceptance criteria",
    "Owner and creation priority",
)
ARTIFACT_CLASSIFICATIONS = {"deployment-critical", "release-enrichment"}
ARTIFACT_STATUSES = {"planned", "created", "validated", "packaged", "azure-verified"}
PACKAGED_STATUSES = {"packaged", "azure-verified"}
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "references/repository-structure.md",
    "references/industry-catalog.md",
    "references/finale-coach-notes.md",
    "references/scenario-artifact-inventory.md",
    "references/validation-checklist.md",
    "assets/industry-catalog.json",
    "assets/challenge-page.template.md",
    "assets/finale-page.template.md",
    "assets/nextsteps.template.MD",
    "assets/index.template.md",
    "assets/readme.template.md",
    "assets/resources.template.md",
    "assets/allfiles-readme.template.md",
    "assets/config.template.yml",
    "assets/build.template.yml",
)
TEMPLATE_TOKEN_PATTERN = re.compile(r"<[A-Z][A-Z0-9_]*>")
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bAccountKey\s*=", re.IGNORECASE),
    re.compile(r"\bSharedAccessSignature\s*=", re.IGNORECASE),
    re.compile(
        r"\b(?:api[-_ ]?key|client[-_ ]?secret)\s*[:=]\s*[^<\s]",
        re.IGNORECASE,
    ),
    re.compile(
        r"https://[^\s)]+\.(?:azurewebsites\.net|cognitiveservices\.azure\.com)",
        re.IGNORECASE,
    ),
    re.compile(r"\b[A-Za-z]:\\"),
)
PUBLIC_FORBIDDEN_PATTERNS = (
    re.compile(r"\bcoach notes?\b", re.IGNORECASE),
    re.compile(r"\banswer key\b", re.IGNORECASE),
    re.compile(r"\bprivate coach\b", re.IGNORECASE),
    re.compile(r"\bexpected solution\b", re.IGNORECASE),
    *SENSITIVE_VALUE_PATTERNS,
)
DEPLOYMENT_BYPASS_PATTERNS = (
    re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*[^*]+:\*\*\s*)?skip\s+.*\bazd up\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"\bazd up\b.{0,40}\boptional\b", re.IGNORECASE),
    re.compile(r"\bdo not run\s+`?azd up`?", re.IGNORECASE),
    re.compile(r"\bwithout running\s+`?azd up`?", re.IGNORECASE),
)


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_error(errors, f"Cannot read {path}: {exc}")
        return ""


def parse_lab_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = read_text(path, errors)
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        add_error(errors, f"{path} must start with YAML frontmatter.")
        return {}

    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        add_error(errors, f"{path} has no closing YAML frontmatter delimiter.")
        return {}

    frontmatter_lines = lines[1:closing_index]
    if "lab:" not in frontmatter_lines:
        add_error(errors, f"{path} has no lab frontmatter object.")
        return {}

    values: dict[str, str] = {}
    in_lab = False
    for line in frontmatter_lines:
        if line == "lab:":
            in_lab = True
            continue
        if in_lab and line and not line.startswith(" "):
            break
        match = re.match(r"^  ([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$", line)
        if match:
            values[match.group(1)] = (match.group(2) or "").strip().strip('"\'')

    missing = sorted(REQUIRED_LAB_KEYS - values.keys())
    if missing:
        add_error(errors, f"{path} is missing lab keys: {', '.join(missing)}")
    return values


def section_text(text: str, heading: str) -> str:
    pattern = rf"^{re.escape(heading)}[ \t]*\r?\n(.*?)(?=^##[ \t]|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def artifact_field(block: str, label: str) -> str:
    pattern = rf"^- \*\*{re.escape(label)}:\*\*\s*(.*?)(?=^- \*\*|\Z)"
    match = re.search(pattern, block, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def code_value(value: str) -> str:
    match = re.fullmatch(r"`([^`]+)`", value.strip())
    return match.group(1) if match else ""


def validate_markdown_lines(path: Path, text: str, errors: list[str]) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if len(line) > 120:
            add_error(errors, f"{path}:{line_number} exceeds 120 characters.")


def validate_local_images(path: Path, text: str, errors: list[str]) -> None:
    for target in re.findall(r"!\[[^\]]+\]\(([^)]+)\)", text):
        clean_target = target.split("#", maxsplit=1)[0]
        if clean_target.startswith(("http://", "https://")) or TEMPLATE_TOKEN_PATTERN.search(clean_target):
            continue
        if not (path.parent / clean_target).resolve().is_file():
            add_error(errors, f"{path} references missing image {target}.")


def find_exact_case_file(root: Path, expected_name: str, errors: list[str]) -> Path | None:
    if not root.is_dir():
        add_error(errors, f"Missing scenario root {root}.")
        return None

    matches = [
        path
        for path in root.iterdir()
        if path.is_file() and path.name.casefold() == expected_name.casefold()
    ]
    if not matches:
        add_error(errors, f"Missing required file {root / expected_name}.")
        return None
    if len(matches) != 1:
        add_error(errors, f"{root} must contain exactly one case-insensitive match for {expected_name}.")
        return None
    if matches[0].name != expected_name:
        add_error(errors, f"{matches[0]} must use the exact filename {expected_name}.")
    return matches[0]


def validate_artifact_destination(
    raw_path: str,
    scenario_root: Path,
    source_path: Path,
    errors: list[str],
    require_exists: bool,
) -> None:
    normalized_path = raw_path.replace("\\", "/")
    destination = PurePosixPath(normalized_path)
    if (
        destination.is_absolute()
        or ".." in destination.parts
        or not normalized_path.startswith("packages/")
    ):
        add_error(errors, f"{source_path} has invalid package destination {raw_path!r}.")
        return
    resolved = scenario_root.joinpath(*destination.parts)
    if require_exists and not resolved.is_file():
        add_error(errors, f"{source_path} lists missing packaged artifact {resolved}.")


def validate_nextsteps(scenario_root: Path, errors: list[str]) -> None:
    path = find_exact_case_file(scenario_root, "nextsteps.MD", errors)
    if path is None:
        return

    text = read_text(path, errors)
    validate_markdown_lines(path, text, errors)
    validate_local_images(path, text, errors)
    if TEMPLATE_TOKEN_PATTERN.search(text):
        add_error(errors, f"{path} contains unresolved template tokens.")
    if UUID_PATTERN.search(text):
        add_error(errors, f"{path} contains a UUID-like identifier.")
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.search(text):
            add_error(errors, f"{path} contains sensitive-content pattern {pattern.pattern!r}.")
    for pattern in DEPLOYMENT_BYPASS_PATTERNS:
        if pattern.search(text):
            add_error(errors, f"{path} contains deployment-bypass language {pattern.pattern!r}.")

    for section in REQUIRED_NEXTSTEPS_SECTIONS:
        if section not in text:
            add_error(errors, f"{path} is missing section {section}.")
    section_positions = [text.find(section) for section in REQUIRED_NEXTSTEPS_SECTIONS if section in text]
    if section_positions != sorted(section_positions):
        add_error(errors, f"{path} sections are not in the required order.")

    deployment_gate = section_text(text, "## Deployment and test gate")
    for required_phrase in (
        "`azd up` is mandatory",
        "`packages/coach/`",
        "`packages/participant/`",
    ):
        if required_phrase not in deployment_gate:
            add_error(errors, f"{path} deployment gate must contain {required_phrase}.")

    inventory = section_text(text, "## Artifact inventory")
    inventory_ids = re.findall(r"^\|\s*(ART-\d{3})\s*\|", inventory, re.MULTILINE)
    if not inventory_ids:
        add_error(errors, f"{path} artifact inventory must contain at least one ART-NNN row.")
    if len(inventory_ids) != len(set(inventory_ids)):
        add_error(errors, f"{path} artifact inventory contains duplicate artifact IDs.")

    inventory_values: dict[str, tuple[str, str]] = {}
    for line in inventory.splitlines():
        if not re.match(r"^\|\s*ART-\d{3}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            add_error(errors, f"{path} inventory row must contain exactly six columns: {line}")
            continue
        artifact_id = cells[0]
        classification = code_value(cells[4])
        status = code_value(cells[5])
        if classification not in ARTIFACT_CLASSIFICATIONS:
            add_error(errors, f"{path} {artifact_id} inventory classification is invalid.")
        if status not in ARTIFACT_STATUSES:
            add_error(errors, f"{path} {artifact_id} inventory status is invalid.")
        inventory_values[artifact_id] = (classification, status)

    details = section_text(text, "## Detailed artifact specifications")
    heading_matches = list(re.finditer(r"^### (ART-\d{3}) — .+$", details, re.MULTILINE))
    detail_ids = [match.group(1) for match in heading_matches]
    if not detail_ids:
        add_error(errors, f"{path} must contain at least one ART-NNN detailed specification.")
    if len(detail_ids) != len(set(detail_ids)):
        add_error(errors, f"{path} contains duplicate detailed artifact IDs.")
    if set(inventory_ids) != set(detail_ids):
        add_error(errors, f"{path} inventory rows and detailed artifact IDs must match exactly.")

    for index, match in enumerate(heading_matches):
        artifact_id = match.group(1)
        block_end = (
            heading_matches[index + 1].start()
            if index + 1 < len(heading_matches)
            else len(details)
        )
        block = details[match.end() : block_end]
        for label in REQUIRED_ARTIFACT_FIELDS:
            if not artifact_field(block, label):
                add_error(errors, f"{path} {artifact_id} is missing field {label}.")

        classification = code_value(artifact_field(block, "Deployment classification"))
        status = code_value(artifact_field(block, "Status"))
        if classification not in ARTIFACT_CLASSIFICATIONS:
            add_error(errors, f"{path} {artifact_id} has invalid deployment classification {classification!r}.")
        if status not in ARTIFACT_STATUSES:
            add_error(errors, f"{path} {artifact_id} has invalid status {status!r}.")
        if inventory_values.get(artifact_id) != (classification, status):
            add_error(errors, f"{path} {artifact_id} inventory and detail classification or status differ.")
        if classification == "deployment-critical" and status not in PACKAGED_STATUSES:
            add_error(errors, f"{path} {artifact_id} is deployment-critical but is not packaged.")

        destinations = artifact_field(block, "Repository destinations")
        destination_paths = re.findall(r"`(packages/[^`]+)`", destinations)
        if not destination_paths:
            add_error(errors, f"{path} {artifact_id} must list at least one package destination.")
        for destination_path in destination_paths:
            validate_artifact_destination(
                destination_path,
                scenario_root,
                path,
                errors,
                require_exists=status in PACKAGED_STATUSES,
            )


def validate_challenge_page(path: Path, errors: list[str]) -> tuple[str, str, int]:
    text = read_text(path, errors)
    values = parse_lab_frontmatter(path, errors)
    validate_markdown_lines(path, text, errors)
    validate_local_images(path, text, errors)

    for section in REQUIRED_CHALLENGE_SECTIONS:
        if section not in text:
            add_error(errors, f"{path} is missing section {section}.")
    section_positions = [text.find(section) for section in REQUIRED_CHALLENGE_SECTIONS]
    if section_positions != sorted(section_positions):
        add_error(errors, f"{path} challenge sections are not in the required order.")

    duration_match = re.fullmatch(r"(\d+) minutes", values.get("duration", ""))
    duration = int(duration_match.group(1)) if duration_match else 0
    if not duration_match:
        add_error(errors, f"{path} duration must use '<integer> minutes'.")
    if values.get("islab", "").lower() != "true":
        add_error(errors, f"{path} lab.islab must be true.")
    if values.get("level") not in {"100", "200", "300"}:
        add_error(errors, f"{path} lab.level must be 100, 200, or 300.")
    for key in ("title", "module", "description"):
        if not values.get(key):
            add_error(errors, f"{path} lab.{key} must not be empty.")

    title = challenge_title(path, errors)
    if values.get("title") != title:
        add_error(errors, f"{path} lab.title must match the title after the H1 em dash.")

    scenario = section_text(text, "## 💡 Scenario")
    if not scenario:
        add_error(errors, f"{path} has an empty Scenario section.")

    return values.get("module", ""), scenario, duration


def challenge_title(path: Path, errors: list[str]) -> str:
    text = read_text(path, errors)
    match = re.search(r"^#\s+.*?—\s*(.+?)\s*$", text, re.MULTILINE)
    if not match:
        add_error(errors, f"{path} H1 must end with an em dash and the challenge title.")
        return ""
    return match.group(1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_tree(source: Path, target: Path, errors: list[str]) -> None:
    source_files = sorted(path.relative_to(source) for path in source.rglob("*") if path.is_file())
    target_files = sorted(path.relative_to(target) for path in target.rglob("*") if path.is_file())
    if source_files != target_files:
        add_error(errors, f"Copied file sets differ between {source} and {target}.")
        return
    for relative_path in source_files:
        if sha256(source / relative_path) != sha256(target / relative_path):
            add_error(errors, f"Copied file differs: {relative_path}")


def validate_finale(
    path: Path,
    challenge_pages: list[Path],
    expected_module: str,
    errors: list[str],
) -> None:
    text = read_text(path, errors)
    values = parse_lab_frontmatter(path, errors)
    validate_markdown_lines(path, text, errors)
    validate_local_images(path, text, errors)

    if values.get("audience", "").lower() != "coach":
        add_error(errors, f"{path} lab.audience must be coach.")
    if values.get("isfinale", "").lower() != "true":
        add_error(errors, f"{path} lab.isfinale must be true.")
    if values.get("module") != expected_module:
        add_error(errors, f"{path} lab.module must match the challenge pages.")
    if values.get("duration") != "20 minutes":
        add_error(errors, f"{path} lab.duration must be 20 minutes.")
    if TEMPLATE_TOKEN_PATTERN.search(text):
        add_error(errors, f"{path} contains unresolved template tokens.")
    if UUID_PATTERN.search(text):
        add_error(errors, f"{path} contains a UUID-like identifier.")

    for challenge_number, page in enumerate(challenge_pages):
        title = challenge_title(page, errors)
        heading = f"## Challenge {challenge_number} — {title}"
        body = section_text(text, heading)
        if not body:
            add_error(errors, f"{path} is missing exact mapping {heading}.")
            continue
        for label in COACH_NOTE_LABELS:
            if f"**{label}**" not in body:
                add_error(errors, f"{path} section {heading} is missing label {label}.")

    if "## Event wrap-up" not in text:
        add_error(errors, f"{path} is missing the Event wrap-up section.")


def validate_root_files(root: Path, private: bool, errors: list[str]) -> None:
    required = {"README.md", "index.md", "_config.yml", "_build.yml", "resources.md"}
    if private:
        required.update({"solution-overview.md", "deployment-guide.md"})
    for filename in sorted(required):
        if not (root / filename).is_file():
            add_error(errors, f"Missing required file {root / filename}.")
    if not (root / "Allfiles" / "README.md").is_file():
        add_error(errors, f"Missing required file {root / 'Allfiles' / 'README.md'}.")


def validate_public_tree(root: Path, errors: list[str]) -> None:
    text_extensions = {".md", ".yml", ".yaml", ".json", ".txt"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_extensions:
            continue
        text = read_text(path, errors)
        if TEMPLATE_TOKEN_PATTERN.search(text):
            add_error(errors, f"{path} contains unresolved template tokens.")
        if UUID_PATTERN.search(text):
            add_error(errors, f"{path} contains a UUID-like identifier.")
        for pattern in PUBLIC_FORBIDDEN_PATTERNS:
            if pattern.search(text):
                add_error(errors, f"{path} contains public-content pattern {pattern.pattern!r}.")


def validate_single_industry(instructions_root: Path, industry: str, errors: list[str]) -> None:
    actual = (
        sorted(path.name for path in instructions_root.iterdir() if path.is_dir())
        if instructions_root.is_dir()
        else []
    )
    if actual != [industry]:
        add_error(errors, f"{instructions_root} must contain only the {industry!r} industry folder.")


def validate_package(packages_root: Path, industry: str) -> list[str]:
    errors: list[str] = []
    if industry not in EXPECTED_INDUSTRIES:
        add_error(errors, f"Unsupported industry slug {industry!r}.")
        return errors

    learner_root = packages_root / "hack"
    coach_root = packages_root / "coach-guide"
    validate_nextsteps(packages_root.parent, errors)
    learner_instructions = learner_root / "Instructions" / industry
    coach_instructions = coach_root / "Instructions" / industry
    validate_root_files(learner_root, private=False, errors=errors)
    validate_root_files(coach_root, private=True, errors=errors)
    validate_single_industry(learner_root / "Instructions", industry, errors)
    validate_single_industry(coach_root / "Instructions", industry, errors)
    validate_public_tree(learner_root, errors)

    learner_pages = sorted(learner_instructions.glob("[0-9][0-9]-*.md"))
    if len(learner_pages) != 5:
        add_error(errors, f"{learner_instructions} must contain exactly five challenge pages.")
    for prefix in CHALLENGE_PREFIXES:
        matches = [path for path in learner_pages if path.name.startswith(prefix)]
        if len(matches) != 1:
            add_error(errors, f"{learner_instructions} must contain exactly one {prefix} challenge page.")
    actual_names = tuple(path.name for path in learner_pages)
    if actual_names != EXPECTED_CHALLENGE_FILES:
        add_error(errors, f"{learner_instructions} challenge filenames do not match the required stable names.")

    modules: set[str] = set()
    scenarios: set[str] = set()
    total_minutes = 0
    for page in learner_pages:
        module, scenario, duration = validate_challenge_page(page, errors)
        modules.add(module)
        scenarios.add(scenario)
        total_minutes += duration
        coach_copy = coach_instructions / page.name
        if not coach_copy.is_file():
            add_error(errors, f"Missing coach copy {coach_copy}.")
        elif sha256(page) != sha256(coach_copy):
            add_error(errors, f"Coach challenge copy differs: {page.name}")

    if len(modules) != 1 or "" in modules:
        add_error(errors, "All challenge pages must use one nonempty lab.module value.")
    if len(scenarios) != 1 or "" in scenarios:
        add_error(errors, "All challenge pages must use one identical, nonempty Scenario section.")
    if total_minutes != 150:
        add_error(errors, f"Challenge durations total {total_minutes} minutes instead of 150.")
    expected_module = next(iter(modules)) if len(modules) == 1 else ""

    learner_finale = learner_instructions / "99-finale.md"
    if learner_finale.exists():
        add_error(errors, f"Public learner source must not contain {learner_finale}.")
    coach_finale = coach_instructions / "99-finale.md"
    if not coach_finale.is_file():
        add_error(errors, f"Missing required Finale page {coach_finale}.")
    else:
        validate_finale(coach_finale, learner_pages, expected_module, errors)

    coach_pages = sorted(path.name for path in coach_instructions.glob("[0-9][0-9]-*.md"))
    expected_coach_pages = sorted((*EXPECTED_CHALLENGE_FILES, "99-finale.md"))
    if coach_pages != expected_coach_pages:
        add_error(errors, f"{coach_instructions} must contain five challenge copies and only one Finale page.")

    learner_resources = learner_root / "resources.md"
    coach_resources = coach_root / "resources.md"
    if learner_resources.is_file() and coach_resources.is_file():
        if sha256(learner_resources) != sha256(coach_resources):
            add_error(errors, "Learner and coach resources.md files must match exactly.")

    learner_allfiles = learner_root / "Allfiles"
    coach_allfiles = coach_root / "Allfiles"
    if learner_allfiles.is_dir() and coach_allfiles.is_dir():
        compare_tree(learner_allfiles, coach_allfiles, errors)

    learner_media = learner_instructions / "media"
    coach_media = coach_instructions / "media"
    if learner_media.exists() or coach_media.exists():
        if not learner_media.is_dir() or not coach_media.is_dir():
            add_error(errors, "Learner and coach media directories must both exist when either is present.")
        else:
            compare_tree(learner_media, coach_media, errors)

    return errors


def validate_skill() -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_SKILL_FILES:
        if not (SKILL_ROOT / relative_path).is_file():
            add_error(errors, f"Missing bundled skill file {relative_path}.")

    catalog_path = SKILL_ROOT / "assets" / "industry-catalog.json"
    if catalog_path.is_file():
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            actual_slugs = {item["slug"] for item in catalog}
            if actual_slugs != EXPECTED_INDUSTRIES:
                add_error(errors, "Industry catalog slugs do not match the required six industries.")
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            add_error(errors, f"Cannot validate industry catalog: {exc}")

    skill_text = read_text(SKILL_ROOT / "SKILL.md", errors)
    if not re.search(r"^name:\s*skillable-lod-authoring\s*$", skill_text, re.MULTILINE):
        add_error(errors, "SKILL.md frontmatter name must match the skill folder.")

    challenge_template = read_text(SKILL_ROOT / "assets" / "challenge-page.template.md", errors)
    for section in REQUIRED_CHALLENGE_SECTIONS:
        if section not in challenge_template:
            add_error(errors, f"Challenge template is missing section {section}.")

    finale_template = read_text(SKILL_ROOT / "assets" / "finale-page.template.md", errors)
    for challenge_number in range(5):
        heading_prefix = f"## Challenge {challenge_number} —"
        if heading_prefix not in finale_template:
            add_error(errors, f"Finale template is missing Challenge {challenge_number} mapping.")
            continue
        body_match = re.search(
            rf"^{re.escape(heading_prefix)}.*?$\n(.*?)(?=^##\s|\Z)",
            finale_template,
            re.MULTILINE | re.DOTALL,
        )
        body = body_match.group(1) if body_match else ""
        for label in COACH_NOTE_LABELS:
            if f"**{label}**" not in body:
                add_error(errors, f"Finale Challenge {challenge_number} is missing label {label}.")

    nextsteps_template = read_text(SKILL_ROOT / "assets" / "nextsteps.template.MD", errors)
    for section in REQUIRED_NEXTSTEPS_SECTIONS:
        if section not in nextsteps_template:
            add_error(errors, f"Next-steps template is missing section {section}.")
    for label in REQUIRED_ARTIFACT_FIELDS:
        if f"**{label}:**" not in nextsteps_template:
            add_error(errors, f"Next-steps template is missing artifact field {label}.")
    for phrase in ("`deployment-critical`", "`release-enrichment`", "`azd up` is mandatory"):
        if phrase not in nextsteps_template:
            add_error(errors, f"Next-steps template is missing required phrase {phrase}.")

    markdown_paths = (
        path
        for path in SKILL_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() == ".md"
    )
    for markdown_path in markdown_paths:
        validate_markdown_lines(markdown_path, read_text(markdown_path, errors), errors)

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages_root", nargs="?", type=Path)
    parser.add_argument("--industry", choices=sorted(EXPECTED_INDUSTRIES))
    parser.add_argument("--check-skill", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check_skill:
        errors = validate_skill()
        target = "Skillable authoring resources"
    else:
        if args.packages_root is None or args.industry is None:
            print("ERROR: packages_root and --industry are required unless --check-skill is used.")
            return 2
        errors = validate_package(args.packages_root.resolve(), args.industry)
        target = str(args.packages_root)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAIL: {target} has {len(errors)} validation error(s).")
        return 1

    print(f"PASS: {target} is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
