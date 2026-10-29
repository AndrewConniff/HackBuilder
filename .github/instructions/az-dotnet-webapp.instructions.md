---
description: ".NET 10 C# coding standards, project structure, and sample data patterns for demo web applications"
applyTo: "**/*.cs,**/*.csproj,**/Dockerfile"
---

# .NET 10 Web Application Instructions

## Framework Requirements

- **Target framework**: `net10.0` — always use the latest .NET 10
- **Project type**: ASP.NET Core Razor Pages (`dotnet new webapp`)
- **Data strategy**: Use the Azure data service (Storage Table, SQL, Cosmos DB, etc.) when the architecture includes one. Fall back to local JSON seed files only when no data endpoint is specified.

## Project Structure

```text
{ProjectName}.Web/
├── {ProjectName}.Web.csproj
├── Program.cs
├── appsettings.json
├── Models/           → Domain entity classes
├── Services/         → SampleDataService (in-memory JSON loader)
├── SeedData/         → JSON files with sample records
├── Pages/            → Razor Pages (Index + per-entity CRUD)
└── wwwroot/          → Static assets (CSS, JS)
```

## Coding Standards

### General

- Use file-scoped namespaces
- Use primary constructors where appropriate
- Prefer `string.Empty` over `""`
- Initialize collection properties with `new()` or `[]`
- Use `required` or `= string.Empty` for non-nullable string properties

### Models

- Every model has an `int Id` property
- Use C# records for immutable data if appropriate
- Keep models flat — no deep object graphs
- Include 2-4 entities per industry domain

### Services

- When an Azure data service is present: register the appropriate data service (e.g., `TableStorageDataService`) as singleton
- When no data endpoint: register `SampleDataService` as singleton
- Use `System.Text.Json` for deserialization (not Newtonsoft)
- Use `Azure.Identity` (`DefaultAzureCredential`) for authenticating to Azure services
- Load seed data lazily on first access
- Handle missing files gracefully (return empty list)

### Razor Pages

- One page model per `.cshtml.cs` file
- Use constructor injection for `SampleDataService`
- Keep page models thin — delegate to service
- Use tag helpers for forms and links

### Seed Data

- Derive entities, records, documents and actions from the requirements' industry,
  `businessUnits`, personas and handoffs. Use the workflow's stable IDs; Generic
  is exclusive and means a typical industry workflow without unit targeting.
- For catalog adaptations, regenerate target business app/data rather than
  relabeling source examples. Use source architecture as read-only guidance;
  never copy deployment state, secrets, scopes, approvals, packages or runtime success.
- Cover selected-unit workflows, cross-unit handoffs and negative cases in tests.
- Preserve company/person CSV provenance and exact recorded identities across
  seeds, app displays, grounding, evaluations and learner/coach fixtures.
- JSON files with 10-20 realistic but fictional records
- Use PascalCase property names in JSON (match C# models)
- Include varied data (different statuses, dates, amounts)
- No real personal information — use fictional names and addresses

## .csproj Template

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <Content Include="SeedData\**\*.json" CopyToOutputDirectory="PreserveNewest" />
  </ItemGroup>
</Project>
```

> [!IMPORTANT]
> The `<Content Include="SeedData\...">` entry ensures JSON seed files are
> included in the published output. Without this, `azd deploy` will fail
> to include the data files.

## Dockerfile Requirements (Container Targets)

- Use multi-stage build: SDK image for build, ASP.NET image for runtime
- Pin the SDK build stage to `--platform=$BUILDPLATFORM` to avoid emulated SDK crashes on ARM64 hosts.
  Retain the intended target platform for the runtime stage. Portable framework-dependent IL with
  `UseAppHost=false` does not require a target-architecture SDK. For RID-specific/native output,
  align restore/publish runtime arguments and lock files explicitly; preserve locked restore.
  Diagnose generated Dockerfile platform selection before requesting shared Docker/emulator repair.
- Base images: `mcr.microsoft.com/dotnet/sdk:10.0` and `mcr.microsoft.com/dotnet/aspnet:10.0`
- Expose port 8080 (ASP.NET Core default in containers)
- Set `ASPNETCORE_URLS=http://+:8080`
- Use `/p:UseAppHost=false` in publish for smaller images

## appsettings.json Template

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*"
}
```

## Anti-Patterns to Avoid

- ❌ Do not use Entity Framework or any ORM — use native SDKs (`Azure.Data.Tables`, `Microsoft.Azure.Cosmos`, `Microsoft.Data.SqlClient`)
- ❌ Do not use local JSON seed data when an Azure data service exists in the architecture
- ❌ Do not use consent-dependent Entra sign-in, anonymous bypasses or hard-coded shared demo passwords
- ❌ Do not use `HttpClient` to fetch external data
- ❌ Do not add Swagger/OpenAPI (this is a Razor Pages app, not an API)
- ❌ Do not use `IConfiguration` for seed data paths — use `IWebHostEnvironment.ContentRootPath`
- ❌ Do not add health check endpoints (keep the app minimal)
- ❌ Do not store secrets in appsettings.json — use environment variables or managed identity

## Sample authentication and Azure access

Apply the [local-account and Azure RBAC contract](
../skills/hack-builder-workflow/SKILL.md#sample-application-accounts-and-azure-resource-access).
Sample apps authenticate local app accounts with salted framework password hashes, secure cookies,
CSRF checks, bounded sessions and login lockout/throttling. Enforce server-assigned roles.
Never use Entra ID authentication if admin consent is required.
Record generated participant and coach credentials separately in private, gitignored deployment access files;
public guides contain placeholders and delivery instructions, not live passwords.
Azure runtime calls always use managed identity. Provision the reviewed least-privilege Azure control/data-plane
roles for the deploying admin user too; operator CLI validation does not replace app managed-identity tests.
