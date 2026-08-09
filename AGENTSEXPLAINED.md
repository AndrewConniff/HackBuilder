# Agents, Skills, Instructions, and Prompts — How They Work Together

This document explains the architecture behind the GitHub Copilot custom agent
system used in this repository. It covers the four building blocks — agents,
skills, instructions, and prompts — how they relate to each other, and how to
extend or modify them.

## The Four Building Blocks

```text

┌──────────────────────────────────────────────────────────────────┐
│                         USER PROMPT                              │
│  "Build me an Azure demo with App Service and Key Vault..."     │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     AGENT (.agent.md)                            │
│  Defines: identity, model, tools, subagent delegation           │
│  Reads: skills + instructions at runtime                        │
└───────┬──────────────────────────────┬───────────────────────────┘
        │                              │
        ▼                              ▼
┌───────────────────┐    ┌─────────────────────────────────────────┐
│   SKILLS (SKILL.md)│    │   INSTRUCTIONS (.instructions.md)      │
│  Domain knowledge  │    │  File-scoped coding standards          │
│  Patterns, tables  │    │  Auto-injected by glob match           │
│  Read on demand    │    │  Always active for matching files      │
└───────────────────┘    └─────────────────────────────────────────┘
```

### Agents

**What**: An agent is a persona with a system prompt, a set of tools it can call,
and optionally a list of subagents it can delegate to. Each agent is a single
`.agent.md` file in `.github/agents/`.

**File format**: YAML front matter + Markdown body.

```yaml
---
name: 05-Bicep
description: Generates Bicep templates using Azure Verified Modules
model: "Claude Opus 4.6"
user-invokable: true # appears in the agent picker in VS Code
argument-hint: Describe the infrastructure to implement in Bicep
agents: [] # subagent names this agent can delegate to
tools: [execute/runInTerminal, edit/createFile, search, ...]
---
# Bicep Agent

Instructions written in Markdown. This is the agent's system prompt.
Everything below the front matter is injected as context when the agent runs.
```

**Key front matter fields:**

| Field            | Purpose                                                               |
| ---------------- | --------------------------------------------------------------------- |
| `name`           | Identifier used for subagent delegation and the VS Code agent picker  |
| `description`    | One-line summary shown in the UI                                      |
| `model`          | Which LLM backs this agent (`Claude Opus 4.6`, `GPT-5.3-Codex`, etc.) |
| `user-invokable` | If `true`, the user can select and talk to this agent directly        |
| `agents`         | Array of agent `name` values this agent can call via `runSubagent`    |
| `tools`          | Array of tool identifiers this agent has access to                    |

**Body (Markdown)**: This is the agent's full system prompt. It typically contains:

- Mandatory pre-work (e.g., "read SKILL.md before doing anything")
- DO / DON'T rules
- A phased workflow describing how the agent should approach its task
- Output file expectations (what artifacts to produce and where)
- A validation checklist

### Skills

**What**: A skill is a reusable knowledge document that agents read at runtime.
Skills contain domain-specific facts, patterns, code snippets, and lookup tables
that are too large or too volatile to embed directly in an agent's body.

**Location**: `.github/skills/` (configured via `chat.agentSkillsLocations` in
`.vscode/settings.json`).

**File format**: YAML front matter + Markdown body, named `SKILL.md`.

```yaml
---
name: azd-demo-builder
description: "Consolidated skill for Azure demo scenario generation"
compatibility: Works with Claude Code, GitHub Copilot, VS Code
---

# Azure Demo Builder — Consolidated Skill

## 1. Azure Defaults
... naming conventions, default regions, security baseline ...

## 2. Azure Verified Modules (AVM)
... module table, usage patterns, known pitfalls ...

## 3. Bicep Patterns
... private endpoints, diagnostics, role assignments ...
```

**How agents consume skills**: Agents explicitly read skill files as their first
action. This is a convention enforced in each agent's body:

```markdown
## MANDATORY: Read Skills First

1. **Read** `.github/skills/az-consolidated/SKILL.md`
2. **Read** `.github/skills/az-azure-artifacts/templates/04-implementation-plan.template.md`
```

The agent uses the `read_file` tool to load skill content into its context window.
This is a pull model — skills are not auto-injected; agents must request them.

**When to use a skill vs. an instruction:**

| Criterion   | Skill                              | Instruction                             |
| ----------- | ---------------------------------- | --------------------------------------- |
| Activation  | Agent reads it explicitly          | Auto-injected by file glob              |
| Scope       | Domain knowledge, patterns, tables | Coding standards for a file type        |
| Granularity | Broad (can span hundreds of lines) | Focused (rules for one language/format) |
| Audience    | One or more specific agents        | Any agent editing matching files        |

### Instructions

**What**: Instructions are coding standards that VS Code automatically injects
into the agent's context whenever the agent creates or edits a file matching the
instruction's `applyTo` glob pattern. You do not need to read them manually —
they are always active.

**Location**: `.github/instructions/`.

**File format**: YAML front matter with `applyTo` glob + Markdown body.

```yaml
---
description: "Infrastructure as Code best practices for Bicep templates"
applyTo: "**/*.bicep"
---

# Bicep Development Best Practices

## Naming Conventions
... rules that apply every time a .bicep file is touched ...
```

**The `applyTo` field is the key mechanism.** It uses glob syntax to match file
paths. When an agent writes to a `.bicep` file, VS Code automatically includes
the Bicep instruction in the context. Examples:

| `applyTo`    | Effect                                               |
| ------------ | ---------------------------------------------------- |
| `**/*.bicep` | Active whenever a `.bicep` file is created or edited |
| `**/*.md`    | Active for all Markdown files                        |
| `**/*.py`    | Active for all Python files                          |
| `**`         | Active for every file (repo-wide rule)               |

**Instructions in this repo:**

| File                                           | `applyTo`             | Purpose                                             |
| ---------------------------------------------- | --------------------- | --------------------------------------------------- |
| `az-bicep-code-best-practices.instructions.md` | `**/*.bicep`          | AVM-first, naming, security defaults, deployer RBAC |
| `az-markdown.instructions.md`                  | `**/*.md`             | Line length, heading hierarchy, callout styles      |
| `az-python.instructions.md`                    | `**/*.py`             | Ruff formatting, type hints, import ordering        |
| `az-powershell.instructions.md`                | `**/*.ps1, **/*.psm1` | Comment-based help, approved verbs                  |
| `az-code-commenting.instructions.md`           | `**`                  | Minimal-comment philosophy across all languages     |
| `az-agent-research-first.instructions.md`      | `**/*.agent.md, ...`  | Enforces research-before-implementation             |
| `az-azure-artifacts.instructions.md`           | `**/generated-scenarios/**/*.md` | Template compliance for generated artifacts         |

### Prompts (User Messages)

The user's natural language message is the entry point. It flows to whichever
agent is selected in the VS Code chat panel. The prompt does not need special
syntax — just describe what you want.

The **Conductor** agent is designed as the default entry point. It parses
the user's prompt, derives a project name, and delegates to specialized agents
in sequence. You can also invoke any agent directly if you only need one step
(e.g., select **05-Bicep** and ask it to regenerate templates for an existing
project).

## How They Wire Together

### The Resolution Chain

When you type a message in VS Code Copilot Chat, here is what happens:

```
1. User selects an agent (e.g., "az-01-conductor") and types a prompt
2. VS Code loads the agent's .agent.md file (front matter + body = system prompt)
3. VS Code checks which files the agent will touch and auto-injects matching instructions
4. The agent's body tells it to read specific skills (via read_file tool calls)
5. The agent now has: system prompt + instructions + skill knowledge + user prompt
6. The agent reasons, calls tools, and produces output
7. If the agent has subagents listed, it can delegate via runSubagent
```

### Binding Relationships

```
                    ┌─────────────────┐
                    │    User Prompt   │
                    └────────┬────────┘
                             │ selects
                             ▼
                    ┌─────────────────┐
              ┌─────│     Agent       │─────┐
              │     └────────┬────────┘     │
              │              │              │
         delegates      reads (pull)   touches files
              │              │              │
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌───────────────┐
     │  Subagent  │  │   Skill    │  │  Instruction  │
     │ (another   │  │ (SKILL.md) │  │ (auto-inject) │
     │  .agent.md)│  └────────────┘  └───────────────┘
     └────────────┘
```

**Agent → Skill**: Pull relationship. The agent's Markdown body contains
explicit instructions like "Read `.github/skills/az-consolidated/SKILL.md` before doing
any work." The agent calls the `read_file` tool to load it.

**Agent → Instruction**: Push relationship. VS Code automatically injects
instructions when the agent's tool calls target files matching the
instruction's `applyTo` glob. The agent does not need to know about
instructions — they are silently added to context.

**Agent → Subagent**: Delegation relationship. The parent agent's `agents`
array in front matter lists which agents it can invoke via the `runSubagent`
tool. Subagents run independently with their own system prompt, skills,
and instructions.

**Skill → Instruction**: No direct relationship. Skills are domain knowledge
(what to build); instructions are coding standards (how to write the code).
They complement each other but are loaded through different mechanisms.

### Context Flow Between Agents

Agents communicate through **artifact files**, not direct message passing.
Each agent writes its output to `generated-scenarios/{project}/` with a numbered prefix:

```
generated-scenarios/{project}/
├── 01-requirements.md            ← Written by Validations agent
├── 02-architecture-assessment.md ← Written by Architect agent
├── 03-architect-diagram.py             ← Written by Diagrammer agent
├── 04-implementation-plan.md     ← Written by Bicep agent
├── infra/main.bicep              ← Written by Bicep agent
├── 06-deployment-summary.md      ← Written by Deploy agent
└── demoguide/demoguide.md       ← Written by DemoGuide agent
└── demoguide/images/*.png*      ← Written by DemoGuide agent
```

When an agent starts, it reads the artifacts from previous steps to get context.
For example, the Bicep agent reads `02-architecture-assessment.md` to know
which resources to generate templates for.

## VS Code Settings That Enable This

The agent system requires specific VS Code settings in `.vscode/settings.json`:

```jsonc
{
  // Enable custom agent files
  "chat.useAgentsMdFile": true,
  "chat.useNestedAgentsMdFiles": true,

  // Allow agents to delegate to subagents
  "chat.customAgentInSubagent.enabled": true,

  // Where to find agent files
  "chat.agentFilesLocations": {
    ".github/agents": true,
  },

  // Where to find skill files
  "chat.agentSkillsLocations": {
    ".github/skills": true,
  },

  // Enable skill loading
  "chat.useAgentSkills": true,
}
```

## Building Your Own: Step-by-Step

### Adding a New Agent

1. Create `.github/agents/your-agent.agent.md`
2. Define the YAML front matter with `name`, `description`, `model`, and `tools`
3. Write the Markdown body with the agent's system prompt
4. If it needs skills, add "Read `.github/skills/...`" instructions in the body
5. If a parent agent should delegate to it, add its `name` to the parent's `agents` array

### Adding a New Skill

1. Create `.github/skills/your-skill/SKILL.md` (or add to existing `SKILL.md`)
2. Add YAML front matter with `name` and `description`
3. Write domain knowledge, patterns, lookup tables in the Markdown body
4. In each agent that needs it, add a "Read this skill" instruction to the agent's body

### Adding a New Instruction

1. Create `.github/instructions/your-rule.instructions.md`
2. Set the `applyTo` glob to target the right file types
3. Write the coding standards in the Markdown body
4. Done — VS Code injects it automatically when agents touch matching files

### Adding a New Artifact Template

1. Create `.github/skills/az-azure-artifacts/templates/NN-name.template.md`
2. Define the required H2 headings and structure
3. Reference it in the relevant agent's body ("Read this template before generating output")

## Examples from This Repo

### How the Bicep Agent Uses All Four

1. **Prompt**: User asks the Conductor to build an Azure scenario
2. **Agent**: Conductor delegates to `az-05-Bicep` via `runSubagent`
3. **Skills**: Bicep agent reads `SKILL.md` for AVM module table, naming
   conventions, security baseline, and deployer RBAC patterns
4. **Instructions**: When the agent creates `infra/main.bicep`, VS Code
   auto-injects `az-bicep-code-best-practices.instructions.md`
5. **Templates**: Agent reads `04-implementation-plan.template.md` to
   know the exact H2 structure required for the plan artifact

### How the Conductor Orchestrates

```
Conductor receives user prompt
    │
    ├─ runSubagent("az-02-Validations", "Parse scenario and generate requirements")
    │   └─ Validations agent writes 01-requirements.md
    │
    ├─ runSubagent("az-03-Architect", "Assess architecture from 01-requirements.md")
    │   └─ Architect agent reads 01-requirements.md, writes 02-architecture-assessment.md
    │
    ├─ runSubagent("az-04-Diagrammer", "Generate architecture diagrams")
    │   └─ Diagrammer agent reads 02-*.md, writes 03-architect-diagram.py + .png
    │
    ├─ runSubagent("az-05-Bicep", "Generate Bicep templates per 02-*.md")
    │   └─ Bicep agent reads 02-*.md, writes infra/ + 04-*.md + 05-*.md
    │
    ├─ runSubagent("az-06-Deploy", "Deploy via azd up")
    │   └─ Deploy agent reads infra/, runs azd, writes 06-deployment-summary.md
    │
    └─ runSubagent("az-07-DemoGuide", "Generate demo guide from all artifacts")
        └─ DemoGuide agent reads all prior artifacts, writes `generated-scenarios/{project}/`demoguide/demoguide.md
```

Each subagent runs in isolation with its own context window. The only shared
state is the file system — specifically the `generated-scenarios/{project}/` folder.

## Quick Reference: What Goes Where

| I want to...                             | Put it in...                                | File type          | Activation                       |
| ---------------------------------------- | ------------------------------------------- | ------------------ | -------------------------------- |
| Define a new workflow step               | `.github/agents/`                           | `.agent.md`        | User selects or parent delegates |
| Store reusable domain knowledge          | `.github/skills/`                           | `SKILL.md`         | Agent reads explicitly           |
| Enforce coding standards for a file type | `.github/instructions/`                     | `.instructions.md` | Auto-injected by `applyTo` glob  |
| Define artifact structure                | `.github/skills/az-azure-artifacts/templates/` | `.template.md`     | Agent reads explicitly           |
| Configure agent discovery                | `.vscode/settings.json`                     | JSON               | Always active                    |
| Provide tool access (MCP servers, etc.)  | `.vscode/mcp.json`                          | JSON               | Always active                    |
