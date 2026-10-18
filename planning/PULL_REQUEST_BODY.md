## Summary

Update the sticker interpreter's canonical planning Markdown and backlog so teammates can complete module tasks independently. Carry forward the confirmed context, personalization and interpretation decisions, and add the approved optional Fetch/ASI:One saved-explanation and feedback demo.

## Features

- Preserve T0–T7 and add optional T8 with concrete inputs/outputs, file ownership, mocks, commands and standalone done criteria.
- Separate hard prerequisites from later integration handoffs; only the final phone-integration task requires finished components.
- Publish synthetic v2 JSON boundaries and an original PNG with a standard-library consistency check.
- Preserve human issue content, assignments, state and checked work, including checked lines removed by a task rewrite.
- Test PRs without issue writes and sync only reviewed main, preventing outdated feature-branch publication.

## Implementation language

All application modules use Python, including core context, policy and workflow. No additional language runtime or source-percentage requirement applies. Node handles GitHub planning automation; Python standard library checks the demo fixtures. State the actual implementation scope in each module PR.

## Testing

- 15 publisher tests passed, including independent starts, handoff validation/cycles, preservation of checked work, assignments, reruns and main publication.
- Dry run validates nine task definitions, nine labels and two milestones with zero external writes.
- Synthetic contract checker passed without application/vendor dependencies or network calls.
- Workflow YAML and whitespace checks passed locally. Remote checks and observed publication results are recorded separately.

## Known Issues

Application source remains local until separately reviewed/published. Live Photon sticker/private delivery, model access/accuracy and ASI:One registration/query remain unverified. The existing Photon access blocker is preserved. This change neither buys a line nor modifies the separate Fetch branch. Mock tests and fixed outputs do not establish product accuracy or sponsor eligibility.
