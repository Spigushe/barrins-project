<!-- cSpell: ignore HSTS -->
# Barrin's Ecosystem — Development Constitution

Version: 1.0

---

## 1. Purpose of this document

This document defines the permanent development rules for Claude Code when
working on the Barrin's ecosystem.

Claude Code must consider this file as the highest-level project guidance.

The objective is to maintain a coherent, scalable and maintainable architecture
across all current and future Barrin's applications.

This document applies to:

- Barrin's API
- Tamiyo Scroll
- Future Barrin's applications
- Shared authentication
- Shared domain services
- Infrastructure
- Documentation

---

## 2. Project Vision

Barrin's is a multi-application ecosystem.

Applications must share:

- identity management
- domain knowledge
- API conventions
- security principles
- deployment standards

Applications must remain independent while benefiting from common backend capabilities.

The architecture must allow new applications to be added without requiring major
redesign.

---

## 3. Current Applications

### 3.1 Barrin's API

Backend platform.

Responsibilities:

- domain logic
- persistence
- business rules
- authentication
- authorization
- shared services
- machine learning services

Technology:

- Python
- FastAPI
- PostgreSQL

## 3.2 Tamiyo Scroll

Frontend application.

Responsibilities:

- user interface
- user experience
- presentation
- interaction handling

Technology:

- React 19
- TypeScript
- Vite
- React Router
- TanStack Query
- Zod
- TailwindCSS
- shadcn/ui

The frontend must never become a second business layer.

---

## 4. Core Architecture Principles

These rules are mandatory.

### 4.1 Backend owns business logic

All business rules belong to the backend.

The frontend:

- displays information;
- collects user input;
- performs client-side validation for user experience only;
- never decides domain rules.

Example:

Incorrect:

```text
Frontend:
if(user.level >= 2)
enable_feature()
```

Correct:

```text
Backend:
returns available_actions

Frontend:
renders available_actions
```

### 4.2 No duplicated business logic

Never implement the same rule twice.

Forbidden:

- validation rules duplicated between frontend and backend;
- calculations duplicated between applications;
- duplicated authorization logic.

If a rule exists in multiple places, architecture must be reviewed.

### 4.3 API contracts are first-class objects

Every API contract must be:

- explicit;
- documented;
- versioned;
- stable.

Never expose internal database models directly.

Prefer:

```text
Database Model
|
v
Domain Service
|
v
DTO / Schema
|
v
API Response
```

### 4.4 Backward compatibility

Existing applications must continue working.

Before modifying:

- database schema;
- API contracts;
- authentication;
- shared entities;

evaluate compatibility impact.

Breaking changes require explicit approval.

### 4.5 Prefer composition

Prefer:

- independent modules;
- dependency injection;
- small services;
- explicit interfaces.

Avoid:

- deep inheritance trees;
- hidden behavior;
- magic abstractions.

### 4.6 Explicit code over magic

Code should be understandable without requiring framework knowledge.

Prefer:

```python
user_service.create_user(user_data)
```

over:

```python
User.create_from_magic_context()
```

### 4.7 Dependencies policy

Before adding a dependency:

1. Explain the problem.
2. Explain why existing dependencies cannot solve it.
3. Explain maintenance impact.
4. Ask for approval.

Minimize external dependencies.

---

## 5. Agent Governance

The development process is organized around specialized agents.

Agents represent responsibilities, not autonomous decision makers.

When agents disagree on subjective decisions:

STOP.

Present:

- alternatives;
- advantages;
- disadvantages;
- consequences.

Wait for user decision.

---

## 6. Agent 0 — Solution Architect and Technical Lead

### Mission

Agent 0 guarantees global coherence of the Barrin's ecosystem.

Agent 0 does not replace implementation agents.

Agent 0 reviews, validates and coordinates.

### Responsibilities

Agent 0 must:

- define architecture before implementation;
- validate cross-project decisions;
- protect domain boundaries;
- prevent duplicated logic;
- maintain API consistency;
- validate security architecture;
- validate deployment strategy;
- detect technical debt;
- suggest simplifications;
- ensure roadmap compatibility.

### Authority

Agent 0 controls:

#### Architecture

- application boundaries;
- service responsibilities;
- module organization.

#### API

- endpoint structure;
- DTO contracts;
- versioning strategy.

#### Data

- domain model evolution;
- migration strategy.

#### Security

- authentication;
- authorization;
- communication rules.

#### Infrastructure

- deployment architecture;
- environment strategy.

#### Development standards

- coding conventions;
- documentation structure;
- quality requirements.

### Architectural Decision Process

When several solutions are valid:

Agent 0 must:

1. Identify alternatives.
2. Explain trade-offs.
3. Recommend an option.
4. Ask the user before implementation.

Agent 0 must never silently choose subjective architecture.

### Conflict Resolution

If Agent 1, Agent 2, Agent 3 or Agent 4 disagree:

The workflow stops.

Agent 0 provides:

- summary of disagreement;
- technical impact;
- possible solutions.

The user decides.

---

## 7. Agent 1 — Backend Lead

Role:

Senior Python/FastAPI developer.

Repository:

Barrin's API

Responsibilities:

- maintain backend architecture;
- implement API endpoints;
- preserve domain ownership;
- improve backend quality;
- propose backend improvements;
- maintain tests;
- maintain typing.

Agent 1 must never move business logic into the frontend.

---

## 8. Agent 2 — Frontend Lead

Role:

Senior React/TypeScript developer.

Repository:

Tamiyo Scroll

Responsibilities:

- create maintainable components;
- maximize component reuse;
- maintain accessibility;
- improve UX when appropriate;
- maintain frontend architecture;
- maintain type safety.

Restrictions:

Frontend must not:

- implement business rules;
- duplicate backend validation;
- access database concepts directly.

---

## 9. Agent 3 — DevOps Lead

Role:

Senior infrastructure engineer.

Responsibilities:

- VPS management;
- deployment;
- reverse proxy;
- TLS;
- monitoring;
- environment management;
- security hardening;
- CORS security.

Agent 3 owns infrastructure security.

---

## 10. Agent 4 — UX Validator

Role:

UX and product usability specialist.

Responsibilities:

- review user journeys;
- identify usability issues;
- propose improvements;
- create tutorials;
- validate onboarding.

Agent 4 does not modify technical architecture.

---

## 11. Backend Development Standards

### 11.1 General principles

The backend is the source of truth for:

- business rules;
- domain validation;
- permissions;
- calculations;
- workflow state.

The backend must expose stable contracts for clients.

### 11.2 Backend technology stack

Current backend stack:

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic

Required tooling:

- uv for dependency management
- ty for type checking

Legacy tooling must not be reintroduced.

### 11.3 Python code quality

Python code must:

- be typed;
- be explicit;
- be documented when behavior is not obvious;
- follow project formatting rules.

Avoid:

- implicit side effects;
- hidden global state;
- unnecessary abstractions;
- framework-specific coupling.

### 11.4 Dependency injection

Use dependency injection where it improves:

- testability;
- separation of concerns;
- maintainability.

Examples:

Good:

```python
def create_report(
 service: ReportService = Depends(get_report_service)
):
 return service.generate()
````

Avoid:

```python
def create_report():
 database = Database()
 service = ReportService(database)
```

The implementation choice must remain simple.

### 11.5 Backend module organization

Modules must have clear responsibilities.

Recommended structure:

```text
app/
├── api/
│ ├── routes/
│ ├── schemas/
│ └── dependencies/
├── domain/
│ ├── models/
│ ├── services/
│ └── rules/
├── infrastructure/
│ ├── database/
│ ├── repositories/
│ └── external_services/
├── core/
│ ├── config/
│ ├── security/
│ └── logging/
└── tests/
```

Adaptation is allowed if the existing repository structure requires it.

Architecture changes require review by Agent 0.

### 11.6 Database principles

Database changes must consider:

- migration strategy;
- backward compatibility;
- existing applications;
- future features.

Never:

- remove columns without migration planning;
- rename public fields without compatibility strategy;
- expose database structure directly.

### 11.7 Pydantic schemas

Schemas represent API contracts.

Rules:

- API schemas are not database models.
- Response schemas must be explicit.
- Request schemas must validate user input.
- Optional fields must have clear meaning.

Example:

```python
class UserResponse(BaseModel):
 id: UUID
 username: str
 email_verified: bool
```

Avoid:

```python
class UserResponse(UserDatabaseModel):
 pass
```

---

## 12. Barrin's API BFF Architecture

### Objective

Create a dedicated Backend For Frontend layer for Tamiyo Scroll.

Namespace:

```text
/api/v1/tamiyo-scroll/
```

### BFF responsibilities

The BFF may:

- aggregate backend responses;
- adapt data format for frontend needs;
- reduce frontend complexity;
- provide frontend-oriented workflows.

The BFF must not:

- duplicate business rules;
- bypass domain services;
- directly implement business decisions.

### BFF example

Allowed:

```text
Tamiyo Scroll

GET /api/v1/tamiyo-scroll/dashboard
 |
 v
BFF
 |
 +--> User service
 |
 +--> Deck service
 |
 +--> Report service
```

Not allowed:

```text
Frontend logic duplicated inside BFF
```

### BFF endpoint rules

Every endpoint requires:

- purpose description;
- request schema;
- response schema;
- authentication requirements;
- error cases;
- documentation.

Example documentation:

```text
GET /api/v1/tamiyo-scroll/reports/current

Purpose:
Return report data for currently selected deck.

Authentication:
Required.

Response:
CurrentDeckReportDTO

Errors:
401 Unauthorized
404 No selected deck
```

---

## 13. Authentication Architecture

### 13.1 Shared Barrin's identity

Accounts belong to the Barrin's ecosystem.

The same account must be usable by:

- Tamiyo Scroll;
- future Barrin's applications.

Do not create application-specific user tables.

### 13.2 Account creation

Registration requires:

Fields:

```text
username
email
password
```

Rules:

- username must be unique;
- email must be unique.

These rules are backend responsibilities.

### 13.3 Email verification workflow

Account creation requires two steps.

#### Step 1

User submits:

```text
username
email
password
```

Backend:

- creates pending account;
- generates verification code;
- sends code by email.

#### Step 2

User submits:

```text
email
verification_code
```

Backend validates ownership.

### 13.4 Account levels

Current model:

#### Level 1

Account exists but email is not verified.

#### Level 2

Email verified.

Currently:

No feature restrictions are attached to levels.

The architecture must allow future permissions.

### 13.5 Authentication rules

Authentication decisions must remain centralized.

Frontend:

- stores authentication state;
- redirects users;
- displays information.

Frontend must not:

- decide permissions;
- calculate access rights.

---

## 14. Tamiyo Scroll Frontend Standards

### 14.1 General principles

Frontend responsibilities:

- rendering;
- interaction;
- navigation;
- local UI state;
- API communication.

Frontend is not responsible for:

- business rules;
- authorization;
- domain calculations.

### 14.2 Frontend stack

Mandatory:

- React 19
- TypeScript
- Vite
- React Router
- TanStack Query
- Zod
- TailwindCSS
- shadcn/ui

### 14.3 Component architecture

Prefer:

- reusable components;
- composition;
- clear props;
- isolated responsibilities.

Avoid:

- giant components;
- duplicated UI;
- hidden state coupling.

### 14.4 Data fetching

Use TanStack Query.

API calls must be centralized.

Recommended:

```text
src/
├── api/
│ ├── client.ts
│ ├── users.ts
│ └── reports.ts
├── hooks/
├── components/
├── pages/
```

### 14.5 Runtime validation

External data must be validated.

Use Zod schemas for:

- API responses;
- user inputs;
- external payloads.

---

## 15. Reporting Feature Rules

### Current deck dependency

Until a user selects a deck in:

```text
My Personal Deck
```

the report page must display no report data.

---

Once a deck is selected:

Only the current selected deck data may appear.

Forbidden:

- displaying previous deck data;
- mixing multiple decks;
- using cached unrelated reports.

---

## 16. Development Workflow

### 16.1 General workflow

Every implementation must follow this sequence:

1. Understand the requirement.
2. Analyze architectural impact.
3. Identify affected repositories.
4. Identify API impact.
5. Identify database impact.
6. Identify security impact.
7. Identify deployment impact.
8. Present important decisions.
9. Implement.
10. Validate.
11. Document.
12. Commit.

### 16.2 Never guess requirements

When a requirement is ambiguous:

STOP.

Ask the user.

Examples requiring validation:

- choosing between two authentication strategies;
- choosing a database structure;
- introducing a dependency;
- changing API behavior;
- changing user workflow;
- changing deployment architecture.

Do not silently select one option.

---

## 16.3 Technical decisions

Every significant technical decision must include:

### Context

Why is this decision needed?

### Alternatives

What other solutions exist?

### Trade-offs

Advantages and disadvantages.

### Decision

The selected approach.

### Consequences

Impact on:

- code;
- maintenance;
- deployment;
- future roadmap.

---

## 16.4 Tests-first sequencing

Implementation is test-driven at the planning level, not only at the code
level.

For every feature-level plan produced under this constitution:

1. Tests are planned first — as part of the architecture/documentation
   phase, before any application code is written.
2. The test plan is confirmed by the user before implementation starts.
3. Tests are implemented before the missing production logic is built to
   satisfy them.

Only once tests are planned, confirmed and implemented does an agent write
the logic that makes them pass.

A feature-level plan should therefore ship with its own dedicated test-plan
document, separate from the architecture document, so it can be reviewed
and confirmed on its own (see `docs/content/back/barrins_identity/tests.md`
for an example of this split).

---

## 17. Agent Collaboration Workflow

### 17.1 Before implementation

The responsible agent must explain:

- understanding of the task;
- files affected;
- architectural considerations;
- possible risks.

### 17.2 During implementation

Agents must:

- keep changes focused;
- avoid unrelated refactoring;
- maintain compatibility;
- update documentation.

### 17.3 After implementation

The responsible agent must verify:

- tests;
- formatting;
- lint;
- typing;
- documentation.

### 17.4 Agent communication

Agents must communicate decisions explicitly.

Example:

```text
Agent 2 proposes:
Move report aggregation logic into frontend.

Agent 0 review:
Rejected.

Reason:
Business logic duplication.

Alternative:
Create BFF endpoint.
```

---

## 18. Git Standards

### 18.1 Commit philosophy

Each commit must represent one coherent task.

Forbidden:

- mixing unrelated features;
- large cleanup mixed with feature work;
- undocumented architecture changes.

### 18.2 Commit structure

Recommended:

```text
type(scope): description
```

Examples:

```text
feat(tamiyo-scroll): add account registration flow

feat(api): add tamiyo-scroll report endpoint

fix(auth): prevent duplicate username creation

docs(deployment): add production deployment guide
```

### 18.3 One commit per task

The current project policy:

Each task receives exactly one logical commit.

If a task requires several implementation steps:

Squash before final commit.

### 18.4 Commit checklist

Before committing:

- [ ] tests pass
- [ ] formatting passes
- [ ] lint passes
- [ ] typing passes
- [ ] documentation updated
- [ ] no secrets committed
- [ ] no temporary files committed

---

## 19. Testing Requirements

### 19.1 General principle

Tests are part of the implementation.

A feature without tests is incomplete.

### 19.2 Backend testing

Backend tests must cover:

- business rules;
- API contracts;
- validation;
- authentication workflows;
- database behavior when relevant.

Priority:

1. Domain logic tests.
2. Service tests.
3. API integration tests.

### 19.3 Frontend testing

Frontend tests should cover:

- user workflows;
- component behavior;
- API integration behavior.

Priority:

1. Critical user paths.
2. Forms.
3. Authentication.
4. Data loading states.
5. Error handling.

### 19.4 Regression testing

Before modifying existing behavior:

identify:

- affected features;
- existing tests;
- compatibility risks.

---

## 20. Code Quality Requirements

Every implementation must pass:

### Backend

- formatter
- linter
- type checker
- tests

Required tooling:

- uv
- ty

---

### Frontend

Required validation:

- TypeScript compilation
- formatter
- linter
- tests

---

## 21. Documentation Requirements

Documentation is mandatory.

Documentation must exist for:

- APIs;
- architecture decisions;
- deployment;
- user workflows;
- configuration;
- migrations.

### 21.1 API documentation

Every endpoint requires:

- HTTP method;
- path;
- purpose;
- authentication;
- request format;
- response format;
- error responses.

---

Example:

```markdown
## Create account

POST

/api/v1/tamiyo-scroll/auth/register


Purpose:
Create a Barrin's ecosystem account.


Authentication:
None.


Request:

username
email
password


Responses:

201:
Account created.

400:
Invalid data.

409:
Username or email already exists.
```

### 21.2 Architecture documentation

Architecture changes require documentation.

Examples:

- new service;
- new module boundary;
- database evolution;
- security flow;
- deployment changes.

### 21.3 Relative links in app READMEs

`apps/<app>/README.md` files are rendered in two different locations:

- directly on GitHub, relative to `apps/<app>/`;
- copied verbatim by `docs/hooks/sync_readmes.py` into
  `docs/content/<section>/<app>/index.md` during the mkdocs build,
  relative to that different directory — whenever a matching docs page
  already exists there.

A single relative link cannot be correct in both places at once.
Therefore:

- App READMEs must not contain raw relative links into `docs/content/`.
- Links to other documentation pages belong in the sibling `_links.md`
  file next to the target `index.md` (see `docs/hooks/sync_readmes.py`);
  these are appended under a generated "## See also" section and are
  relative to `docs_dir`, so they resolve correctly in the built site.
- If no docs page exists yet for the app, refer to the other document by
  name in prose only — do not promise a link the sync step cannot
  produce.

---

## 22. Dependency Management

### 22.1 General rule

Dependencies are liabilities.

Before adding one:

Provide:

- problem solved;
- alternatives considered;
- maintenance impact;
- security impact.

Wait for approval.

### 22.2 Backend dependencies

The backend uses:

- uv

Do not introduce:

- pip workflows;
- unmanaged dependencies.

### 22.3 Frontend dependencies

Prefer:

- existing stack;
- browser APIs;
- existing utilities.

Avoid adding libraries for simple problems.

---

## 23. Security Principles

Security must be considered for every feature.

Review:

- authentication;
- authorization;
- input validation;
- data exposure;
- secrets;
- CORS;
- network boundaries.

### 23.1 Sensitive data

Never expose:

- passwords;
- tokens;
- private keys;
- internal database information.

### 23.2 Authentication security

Authentication must:

- use secure password handling;
- validate user identity;
- avoid leaking account existence unnecessarily.

### 23.3 API security

Every endpoint must define:

- authentication requirement;
- authorization requirement;
- input validation.

---

## 24. Environment Management

Configuration must use environment variables.

Never commit:

- secrets;
- production credentials;
- private keys.

Recommended:

```text
.env.example
.env.production.example
```

Documentation must explain required variables.

---

## 25. Release Policy

Packages are not deployed directly from development branches.

Deployment artifacts must be retrieved from the latest repository release tag.

---

Deployment process:

1. Build from release tag.
2. Deploy artifact.
3. Validate health.
4. Monitor.
5. Roll back if necessary.

---

## 26. Infrastructure and Deployment Architecture

### 26.1 Infrastructure objective

The Barrin's ecosystem must be deployable independently:

- Backend API
- Frontend applications

A deployment of one component must not require rebuilding unrelated components.

### 26.2 Current production target

Production host:

```text
Domain:
barrins-codex.org

Server:
146.59.146.57
```

Current state:

- no service is running;
- infrastructure can be designed from scratch.

### 26.3 Infrastructure Agent responsibility

Agent 3 owns:

- server architecture;
- security hardening;
- deployment process;
- reverse proxy;
- TLS;
- networking;
- service management.

Agent 3 must report security concerns immediately.

---

## 27. Deployment Principles

### 27.1 Release-based deployment

Production deployments must use released versions.

Do not deploy:

- untagged commits;
- development branches;
- local modifications.

Deployment source:

```text
latest repository release tag
```

### 27.2 Independent deployments

Backend and frontend must have separate deployment processes.

Example:

```text
Frontend release
|
v
Build static assets
|
v
Deploy web server

Backend release
|
v
Install application
|
v
Restart API service
```

### 27.3 Environment separation

Minimum environments:

```text
Development
Testing
Production
```

Each environment must have:

- separate configuration;
- separate secrets;
- documented variables.

---

## 28. Recommended Server Architecture

The exact implementation is decided by Agent 3 and validated by Agent 0.

A possible architecture:

```text
Internet
|
|
HTTPS :443
|
|
Reverse Proxy
|
+----------------+
|
|
Frontend
(static files)
|
|
/api/
|
|
FastAPI application
|
|
PostgreSQL
```

---

## 29. Reverse Proxy Requirements

The reverse proxy must provide:

- TLS termination;
- HTTP to HTTPS redirect;
- request forwarding;
- security headers;
- access logging.

### 29.1 Security headers

Recommended:

- HSTS;
- X-Content-Type-Options;
- X-Frame-Options;
- Content-Security-Policy where applicable.

---

## 30. TLS Requirements

Production must use HTTPS.

Requirements:

- valid certificate;
- automatic renewal;
- certificate expiration monitoring.

Never expose production authentication over plain HTTP.

---

## 31. API Deployment

### 31.1 Backend deployment responsibilities

Backend deployment must handle:

- application installation;
- dependency installation;
- environment variables;
- database connection;
- migrations;
- service restart;
- health checks.

### 31.2 Backend service requirements

The API service must:

- restart automatically after failure;
- expose health information;
- log errors;
- support graceful shutdown.

---

Example health endpoint:

```text
GET /health
````

Expected:

```json
{
 "status": "ok"
}
```

### 31.3 Database migration policy

Before migration:

- backup database;
- verify compatibility;
- test migration.

Never run destructive migrations blindly.

---

## 32. Frontend Deployment

### 32.1 Frontend build process

The frontend must be built from a release version.

Example:

```text
checkout release tag

install dependencies

build application

deploy generated assets
```

### 32.2 Static hosting

The frontend should be served through the reverse proxy.

Requirements:

- cache static assets;
- support SPA routing;
- return index.html for frontend routes.

---

Example:

```text
/dashboard
 |
 v
index.html
 |
 v
React Router
```

---

## 33. CORS Security

### 33.1 General rule

CORS must be restrictive.

Never use:

```text
Access-Control-Allow-Origin: *
```

for authenticated production APIs.

### 33.2 Allowed origins

Allowed origins must be explicitly configured.

Example:

Development:

```bash
http://localhost:5173
```

Production:

```bash
https://barrins-codex.org
```

### 33.3 CORS validation

Agent 3 must verify:

- allowed origins;
- allowed methods;
- allowed headers;
- credentials handling.

---

## 34. Secrets Management

Secrets must never be stored:

- inside repositories;
- inside frontend code;
- inside documentation.

Examples:

Forbidden:

```text
DATABASE_PASSWORD=my-secret
JWT_SECRET=abcdef
```

inside git.

---

Recommended:

- environment variables;
- server secret storage;
- restricted permissions.

---

## 35. Logging and Monitoring

Production services must provide:

## Application logs

Including:

- startup;
- errors;
- warnings;
- important security events.

---

## Infrastructure logs

Including:

- reverse proxy;
- failed requests;
- TLS issues;
- service failures.

---

## 36. Backup Strategy

Production data requires backups.

Minimum:

- database backups;
- backup verification;
- documented restoration procedure.

A backup that has never been tested is not considered reliable.

## 37. Deployment Playbooks

Two independent playbooks are required.

### 37.1 Backend deployment playbook

Must document:

#### Preparation

- server requirements;
- dependencies;
- environment variables.

#### Deployment

- retrieve release;
- install dependencies;
- apply migrations;
- restart service.

#### Validation

- health check;
- logs;
- API test.

#### Rollback

- restore previous release;
- restore database if required.

### 37.2 Frontend deployment playbook

Must document:

#### Preparation

- Node environment;
- configuration.

#### Deployment

- retrieve release;
- install dependencies;
- build application;
- publish assets.

#### Validation

- homepage loading;
- authentication flow;
- API communication.

#### Rollback

- restore previous frontend release.

---

## 38. Infrastructure Documentation

Required documents:

```text
docs/
├── architecture/
├── deployment/
│ ├── backend.md
│ ├── frontend.md
│ └── rollback.md
├── security/
└── operations/
```

---

## 39. Future Compatibility Requirements

The current implementation must anticipate future features.

Do not design solutions that prevent future evolution.

However:

- do not implement unused features prematurely;
- do not create unnecessary abstractions;
- keep today's solution simple.

The objective is:

Simple today.

Extensible tomorrow.

---

## 40. Authentication Future Evolution

### Current implementation

Shared Barrin's identity, currently owned by Barrin's API.

Current requirements:

- username;
- email;
- password;
- email verification;
- account level.

### Decision: extraction in progress

This section previously recommended *not* extracting a dedicated identity
service until a second account-based application existed, and proposed a
full OAuth2/OIDC provider as the eventual shape.

That guidance is superseded. The extraction is now planned and in progress:
a dedicated app, `apps/barrins_identity/`, will own authentication for
Barrin's API, Tolaria News and Tamiyo Scroll, using JWT RS256 + JWKS (not a
full OIDC provider). See
`docs/content/back/barrins_identity/platform.md` for the architecture and
decision rationale, and
`docs/content/back/barrins_identity/tests.md` for the test plan that must
be confirmed before implementation starts (§16.4).

#### Future requirements

The architecture must allow:

- multiple applications;
- shared sessions;
- additional authentication methods;
- account management;
- user preferences;
- permissions.

---

## 41. Commander Validation

Future feature:

Validate commander names dynamically.

Expected architecture:

Frontend:

```text
User enters commander name
↓
BFF:
/api/v1/tamiyo-scroll/commanders/search
↓
Backend:
Commander domain service
↓
Response:
Validated commander entity
```

---

Rules:

- frontend must not contain commander database;
- validation logic belongs to backend;
- external data sources must be abstracted.

---

## 42. Partner Commander Support

Future feature:

Support specific selection for double commanders / partners.

The data model must not assume:

```text
Deck -> Commander = One entity
```

Prefer an extensible relationship:

```text
Deck
|
+---- Commander A
|
+---- Commander B
```

---

Do not implement this feature now unless required.

Ensure current architecture does not block it.

---

## 43. Tournament Top 8 Data

Future feature:

Populate Top 8 information from database.

Requirements:

- tournament data belongs to backend;
- frontend displays only;
- aggregation logic remains server-side.

---

## 44. Internationalization

Future feature:

Full website i18n.

Frontend architecture must avoid:

- hardcoded user-facing strings everywhere;
- UI components depending on one language.

Recommended:

```text
Component
|
Translation key
|
Language resource
```

---

## 45. Machine Learning Integration

Future objective:

Use machine learning to estimate card impact on win rate.

Possible future features:

- card impact weighting;
- commander archetype extraction;
- macro archetype classification;
- matchup analysis.

### 45.1 ML architecture rules

Machine learning must remain isolated.

Do not couple:

- frontend;
- authentication;
- reports;
- core domain.

Recommended:

```text
Application Layer
 |
ML Service
 |
Feature Extraction
 |
Models
```

### 45.2 Data quality

ML features depend on:

- validated data;
- reproducible pipelines;
- documented datasets.

Every ML result must have:

- source data;
- version;
- model information.

---

## 46. Administration Features

Future requirement:

Administrator aggregated report view.

Possible features:

- global statistics;
- user aggregation;
- deck trends;
- usage analysis.

---

Rules:

Admin functionality must use:

- explicit permissions;
- backend authorization;
- dedicated endpoints.

Never hide admin logic only in frontend.

---

## 47. Advanced Reporting

## 47.1 Current reporting

Current rule:

Only selected deck data is displayed.

---

## 47.2 Future reverse reports

Future feature:

Analyze results from opponent perspective.

Example:

Given:

Opponent deck X

Return:

- matchup information;
- reverse statistics;
- selection analysis.

---

Architecture must allow:

```text
Report
|
+---- Own deck perspective
|
+---- Opponent perspective
```

---

## 48. Product Evolution Principles

Future features must follow:

### Avoid premature implementation

Do not add:

- unused tables;
- unused APIs;
- unused abstractions.

### Preserve simplicity

A simple understandable system is preferred over a complex theoretical system.

### Prefer migration paths

When evolution is needed:

Prefer:

```text

Version 1
*
migration strategy
*
Version 2
```

over:

```text
Rewrite everything
```

---

## 49. Final Definition of Done

A task is complete only when all conditions are satisfied.

### Architecture

Checklist:

- [ ] architecture reviewed
- [ ] responsibilities are correctly separated
- [ ] no duplicated business logic
- [ ] future compatibility considered
- [ ] security impact reviewed

### Backend

Checklist:

- [ ] API contracts documented
- [ ] schemas defined
- [ ] business rules remain backend-owned
- [ ] migrations reviewed
- [ ] tests pass
- [ ] typing passes
- [ ] lint passes
- [ ] formatting passes

### Frontend

Checklist:

- [ ] components are reusable
- [ ] no business logic duplication
- [ ] API contracts respected
- [ ] accessibility considered
- [ ] TypeScript passes
- [ ] lint passes
- [ ] formatting passes
- [ ] tests pass

### Infrastructure

Checklist:

- [ ] deployment impact reviewed
- [ ] security reviewed
- [ ] configuration documented
- [ ] rollback considered
- [ ] monitoring considered

### Documentation

Checklist:

- [ ] API documentation updated
- [ ] architecture documentation updated
- [ ] deployment documentation updated
- [ ] user documentation updated when required

---

## 50. Claude Code Behavior Rules

Claude Code must:

- act as a senior engineering team;
- prioritize correctness over speed;
- protect architecture;
- ask when uncertain;
- avoid assumptions;
- explain important decisions;
- maintain documentation;
- think about future compatibility.

---

Claude Code must never:

- invent requirements;
- silently introduce dependencies;
- duplicate business rules;
- break compatibility without approval;
- skip tests;
- skip documentation;
- choose subjective architecture without discussion.

---

## 51. Final Instruction

When starting any task:

First:

1. Analyze the request.
2. Identify impacted areas.
3. Identify architectural decisions.
4. Ask questions if needed.

Then:

1. Implement.
2. Validate.
3. Document.
4. Commit.

The goal is not only to make the code work.

The goal is to maintain a coherent Barrin's ecosystem over time.
