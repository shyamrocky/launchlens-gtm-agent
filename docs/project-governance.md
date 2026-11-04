# Canonical files and workspace boundary

Authority: explicit owner instruction, 2026-11-04 (America/Los_Angeles).
This is the canonical policy for file placement and the development-workspace
boundary. AGENTS.md links here rather than maintaining another policy copy.

## Choose the destination before creating a file

- docs/: authoritative project documentation, architecture, approved decisions
  and operating instructions.
- src/, tools/, tests/, or existing equivalents: maintained implementation,
  reusable scripts and tests. Do not add directories or abstractions until needed.
- workspace/: explicitly temporary drafts, private investigations, scratch outputs
  and development checkpoints. It is Git-ignored and nonauthoritative.

Never use workspace/ as the sole authoritative location for a project deliverable
or maintained implementation.

## Authority and promotion

Workspace notes cannot approve architecture changes. Approval must be reflected
in version-controlled documentation or explicitly provided by the owner. If notes
conflict with approved documentation or the latest explicit owner instruction,
stop the affected work and flag the discrepancy.

When a draft is accepted, promote it to its canonical repository location, update
references and mark the workspace copy as superseded. Maintain one authoritative
version. Do not treat approval of a draft as permission for an unrelated milestone.

## Reproducibility and private runtime artifacts

The application, build, tests, deployment and required safety checks must not
depend on files inside workspace/. Temporary experiments there must not become
required components. Missing development notes must not prevent setup or testing.

Keep private source material and execution records protected. Required private
runtime artifacts need an explicit storage and provisioning contract outside
workspace/, documented in docs/ without publishing restricted content. Describe
required locations, access, provisioning and verification, with safe fixtures or
substitutes where appropriate. M0 has no such runtime artifacts; no storage
provider or provisioning implementation is selected by this policy.

## Development memory and sharing

Keep BUILD_CONTEXT.md concise and current. IMPLEMENTATION_PROGRESS.md records
milestones and actual verification evidence; detailed history belongs in justified
task-specific files. Distinguish verified results, assumptions, proposals and owner
approvals. Never store credentials or employer-confidential material in context.

Git ignore rules do not protect manual uploads, archives, deployment packages or
prompt content. Inspect what is shared and exclude workspace/, credentials,
confidential material and restricted artifacts unless an explicitly permitted,
reviewed disclosure applies.

## Milestone check

At each milestone, verify that new required code and documentation occupy their
canonical locations and that no runtime, build, test, deployment or required
safety-check dependency on workspace/ has been introduced. Report actual checks
and any limits. Report existing violations before relocating files or changing
historical bindings; this policy is not blanket migration authorization.
