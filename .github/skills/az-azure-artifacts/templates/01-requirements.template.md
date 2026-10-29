# Step 1: Requirements - {project-name}

Requirements Overview

- [Project Overview](#project-overview)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements (NFRs)](#non-functional-requirements-nfrs)
- [Summary for Architecture Assessment](#summary-for-architecture-assessment)

## Project Overview

| Field                   | Value          |
| ----------------------- | -------------- |
| **Project Name**        | {project-name} |
| **Primary Stakeholder** | {name / role}  |
| **Industry**            | {exact intake industry} |
| **Business Units**      | {businessUnits array using workflow IDs} |
| **Business Outcome**    | {measurable industry/unit outcome} |
| **Reuse Source**        | {null or scenarioId and manifestDigest; architecture guidance only} |

### Personas and scope

Generic is exclusive of specific units and means a typical industry workflow
without unit targeting. For specific units, describe each persona and cross-unit
handoff. Do not infer Azure permissions from a business-unit selection.

| Persona | Business unit or Generic workflow | Responsibility | Data and access boundary |
| --- | --- | --- | --- |
| {role} | {selected unit ID or generic} | {action and handoff} | {allowed and denied access} |

**In scope:** {business workflows, application actions and sample-data coverage}

**Out of scope:** {excluded workflows and units}

For an adaptation, regenerate app/data for this target scope and refresh technical
evidence. Never inherit source deployment state, secrets, scopes, approvals,
packages or runtime success; require new design, validation and approval.

## Functional Requirements

### Core Capabilities

| #   | Capability   | Priority                       | Acceptance Criteria    |
| --- | ------------ | ------------------------------ | ---------------------- |
| 1   | {capability} | Must / Should / Could | {measurable industry/unit criterion} |
| 2   | {capability} | Must / Should / Could | {measurable criterion and negative case} |

### Agentic business workflow

Use the [pattern selection guide](../../az-scenario-requirements/references/agentic-patterns.md);
tailor its ideas to the exact industry and selected units rather than copying a source use case.

| Decision | Scenario-specific requirement |
| --- | --- |
| Business trigger and result | {input, accountable persona, useful artifact/action and measurable improvement} |
| Primary pattern and overlays | {catalog IDs/names; include only justified supporting patterns} |
| Simpler alternative | {single-agent baseline and reason for accepting/rejecting extra coordination} |
| Roles and handoffs | {runtime ownership, typed contracts and intentionally withheld context} |
| Grounding, tools and fixtures | {authoritative sources, read/draft/commit actions, synthetic schemas and provenance} |
| Controls and limits | {deterministic rules, identity, approval rights, stop/budget and recovery conditions} |
| Runtime acceptance | {success target, ambiguous input and coordination-specific failure with expected evidence} |

### Network Security

| Control                     | Required | Notes     |
| --------------------------- | -------- | --------- |
| Private endpoints           | Yes / No | {details} |
| VNet integration            | Yes / No | {details} |
| Public endpoints acceptable | Yes / No | {details} |
| WAF required                | Yes / No | {details} |

### Recommended Security Controls

Table of recommended controls based on workload pattern and compliance requirements:

| Control               | Recommended | User Confirmed | Notes                   |
| --------------------- | ----------- | -------------- | ----------------------- |
| Managed Identity      | {yes/no}    | {yes/no}       | {Prefer over keys}      |
| Private Endpoints     | {yes/no}    | {yes/no}       | {For data services}     |
| WAF                   | {yes/no}    | {yes/no}       | {For public endpoints}  |
| Key Vault for Secrets | {yes/no}    | {yes/no}       | {Centralized secrets}   |
| Diagnostic Settings   | {yes/no}    | {yes/no}       | {Audit logging}         |
| TLS 1.2 Minimum       | {yes/no}    | {yes/no}       | {Always recommended}    |
| Encryption at Rest    | {yes/no}    | {yes/no}       | {Platform default}      |
| Network Isolation     | {yes/no}    | {yes/no}       | {VNet/NSG/Private Link} |

## Non-Functional Requirements (NFRs)

| Requirement | Target | Acceptance evidence |
| --- | --- | --- |
| {security, reliability, performance or cost constraint} | {measurable target} | {check} |

## Summary for Architecture Assessment

### Handoff Summary

| Aspect               | Key Points                                                    |
| -------------------- | ------------------------------------------------------------- |
| Critical Constraints | {top 3 constraints driving architecture}                      |
| Key Decisions        | {decisions made during requirements that affect architecture} |
| Open Risks           | {unresolved items that architect must address}                |
| Recommended Pattern  | {workload pattern from Functional Requirements}               |

### Requirements Completeness

| Section                  | Status       | Notes   |
| ------------------------ | ------------ | ------- |
| Project Overview         | Complete / Pending / Blocked | {notes} |
| Functional Requirements  | Complete / Pending / Blocked | {notes} |
| Non-Functional Requirements | Complete / Pending / Blocked | {notes} |
| Industry and Business Units | Complete / Pending / Blocked | {persona, app/data and test coverage} |

---
