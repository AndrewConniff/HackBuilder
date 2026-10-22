# Step 2: Architecture Assessment - {project-name}

Assessment Contents

- [Requirements Validation](#requirements-validation)
- [Resource SKU Recommendations](#resource-sku-recommendations)
- [Architecture Decision Summary](#architecture-decision-summary)
- [Implementation Handoff](#implementation-handoff)

---

## Requirements Validation

| Scope | Design response | Acceptance evidence |
| --- | --- | --- |
| {industry and exact businessUnits} | {personas, app/data and handoffs} | {tests} |

### Recommended Architecture

```mermaid
flowchart TB
    User["Users"] --> FD["Front Door / CDN"]
    FD --> App["App Service"]
    App --> DB[("Database")]
    App --> KV["Key Vault"]
    App --> Storage["Storage"]
    App --> Monitor["Monitor"]

    subgraph Security
        KV
        NSG["NSG"]
    end

    subgraph Data
        DB
        Storage
    end
```

> Replace the above with actual architecture for the project.

---

## Resource SKU Recommendations

| Service   | Recommended SKU | Configuration |
| --------- | --------------- | ------------- |
| {service} | {sku}           | {config}      |

---

## Architecture Decision Summary

| Decision   | Choice | Rationale |
| ---------- | ------ | --------- |
| Decision 1 |        |           |
| Decision 2 |        |           |

---

## Implementation Handoff

### Ready for bicep-plan

The architecture is ready for implementation with the following key parameters:

| Parameter      | Value    |
| -------------- | -------- |
| Region         | {region} |
| Environment    | {env}    |
| Resource Count | {count}  |

### Resources to Provision

| #   | Resource   | SKU   | Key Config |
| --- | ---------- | ----- | ---------- |
| 1   | {resource} | {sku} | {config}   |
| 2   | {resource} | {sku} | {config}   |

---
