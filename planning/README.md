# Planning source and publication

backlog.json is the machine-readable issue/milestone/label source. issues/ contains task bodies. Owner roles are A, B, C, and optional D; usernames are unset.

The workflow creates missing items and updates only its marked sections in matching issues. Human text outside the generated section, checked task lines, comments, closed state, assignees, and unrelated labels remain intact. Do not delete the hidden task marker from a managed issue. Record additional work outside the generated section or in comments.

Dependencies become actual issue links after publication. All tasks stay open until their implementation evidence is verified. Existing checked acceptance items are retained when their wording matches.

The generated published.json report records actual URLs and any partial failures. It does not contain tokens or private conversation data. Re-running after a partial failure finds items using stable markers rather than creating a second backlog.

To revise assignments, set A/B/C username mappings and commit backlog.json. Leave D unset unless a fourth teammate is available. The workflow adds desired assignees; it does not remove human assignments.

A draft PR is attempted for codex/sticker-planning when allowed by GitHub settings. If that operation is blocked, the report includes a compare link and a warning. No setting is changed automatically.

The October 17 methodology revision updates T0–T7 in place and is described in [METHODOLOGY_UPDATE.md](METHODOLOGY_UPDATE.md). Its review branch publishes planning/methodology sources only; the local application prototype remains separate. Existing human assignments and T1's completed documentation/evidence must be retained. Local prototype checks are labeled separately from passing live integration.
