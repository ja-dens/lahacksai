# Planning source and publication

Use docs/PRODUCT_SPEC.md for current decisions, PLANS.md for observed progress, and docs/CONTRACTS.md for shared boundaries. backlog.json stores issue metadata/dependencies and issues/ stores canonical task Markdown. docs/DELEGATION.md describes independent file ownership. The older parent-folder STICKER_PROJECT_PLAN.md provides the original idea/module split; its rolling-only storage and dependency sequence are historical.

Edit these versioned sources before syncing GitHub. Editing only a generated issue section can be overwritten by the next sync. Publish changes through a feature-branch PR, then use reviewed main as the canonical sync source. Pull-request checks are read-only; only main publishes issues.

`depends_on` is a prerequisite for a task's own deliverable. `integration_depends_on` records a later live handoff, without blocking standalone completion. Only T5 requires finished components to close; all module tasks have shared synthetic fixtures and fake-client strategies. T8 is the approved optional Fetch saved-explanation/feedback adapter, separate from automatic Photon interpretation.

The publisher finds tasks by stable hidden IDs. It creates missing issues, updates its marked sections, retains matching checked items and carries removed checked lines into a historical-work section. It preserves human text outside those sections, comments, closed state, human titles/assignments/milestones and unrelated labels. Do not delete task markers. No issue closes automatically. Additional human notes belong outside generated sections or in comments.

Run before publication:

```sh
node --test .github/scripts/sync-planning.test.cjs
node .github/scripts/sync-planning.cjs --dry-run
python3 scripts/check_contract_fixtures.py
```

These checks require no model or Photon credentials and perform no external writes. The publisher itself uses no Node package dependencies. published.json records actual issue URLs and publication results; METHODOLOGY_UPDATE.md records the current source revision. Local application verification remains distinct from fixture/tooling checks and live results.

Owner roles A/B/C/D are skill groupings, not a required team size. Set GitHub username mappings only when supplied. Preserve existing human assignments. No teammate is messaged, no paid line purchased and no unrelated branch changed by a planning sync.
