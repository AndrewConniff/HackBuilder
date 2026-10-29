# Step 4b: Web Application Summary - {project-name}

Web Application Summary Contents

- [Application Overview](#application-overview)
- [Business Industry Context](#business-industry-context)
- [Data Model](#data-model)
- [Pages and Endpoints](#pages-and-endpoints)
- [Deployment Target](#deployment-target)
- [Build Validation](#build-validation)

## Application Overview

| Property         | Value                              |
| ---------------- | ---------------------------------- |
| **App Name**     | `{ProjectName}.Web`                |
| **Framework**    | .NET 10 (ASP.NET Core Razor Pages) |
| **Language**     | C#                                 |
| **Source Path**  | `src/{ProjectName}.Web/`           |
| **Data Storage** | In-memory (JSON seed files)        |
| **Auth**         | None (demo app)                    |

## Business Industry Context

| Property        | Value              |
| --------------- | ------------------ |
| **Industry**    | `{industry}`       |
| **Description** | `{brief-scenario}` |
| **Business Units** | `{approved businessUnits array}` |
| **Personas and Handoffs** | `{selected roles and interactions, or Generic workflow}` |

Derive app actions, entities and seed relationships from this scope. Generic
means a typical industry workflow without unit targeting. For catalog adaptations,
regenerate business app/data for the target rather than relabeling source examples.

## Data Model

### Entity: `{Entity1}`

| Field      | Type     | Description        |
| ---------- | -------- | ------------------ |
| `Id`       | `int`    | Primary identifier |
| `{Field1}` | `{Type}` | `{description}`    |

**Seed Records**: {count} records in `SeedData/{entity1}s.json`

### Entity: `{Entity2}`

| Field      | Type     | Description        |
| ---------- | -------- | ------------------ |
| `Id`       | `int`    | Primary identifier |
| `{Field1}` | `{Type}` | `{description}`    |

**Seed Records**: {count} records in `SeedData/{entity2}s.json`

## Pages and Endpoints

| Page              | Route                  | Description                 |
| ----------------- | ---------------------- | --------------------------- |
| Home Dashboard    | `/`                    | Overview with entity counts |
| {Entity1} List    | `/{Entity1}`           | List all {entity1} records  |
| {Entity1} Details | `/{Entity1}/Details/1` | Detail view for {entity1}   |
| {Entity2} List    | `/{Entity2}`           | List all {entity2} records  |
| {Entity2} Details | `/{Entity2}/Details/1` | Detail view for {entity2}   |

## Deployment Target

| Property             | Value                                        |
| -------------------- | -------------------------------------------- |
| **Compute Target**   | `{App Service / Container Apps / ACI / AKS}` |
| **Dockerfile**       | `{Yes / No}`                                 |
| **azd Service Name** | `web`                                        |
| **azd Host**         | `{appservice / containerapp / aci / aks}`    |

### azure.yaml Service Configuration

```yaml
services:
  web:
    project: ./src/{ProjectName}.Web
    host: { host }
    language: csharp
```

## Build Validation

| Check                   | Status        |
| ----------------------- | ------------- |
| `dotnet build`          | Passed / Failed |
| Seed data files present | Passed / Failed |
| Dockerfile present      | Passed / Failed / N/A |
| azure.yaml wired        | Passed / Failed |
| Unit/persona workflow and data coverage | Passed / Failed |
