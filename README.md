# lahacksai: private sticker interpreter

A planned messaging assistant that explains a sticker's likely meaning using recent conversation context, starting with older adults in opted-in family chats.

**Status:** planning package. The application and live Photon/model integrations have not been implemented.

The standalone Fetch sponsor quickstart is available in [agent.py](agent.py).
See [local setup and mailbox connection](docs/FETCH_SETUP.md). This is separate
from the planned sticker interpreter. A live ASI:One exchange was verified on
October 17, 2026 using the tutorial's sun-topic assistant.

## First product milestone

Supported sticker arrives in an approved conversation → select recent messages → one multimodal model call → short explanation delivered privately to the enrolled recipient.

Start with one channel, static stickers, one language, and one enrolled test recipient. A private assistant thread is the candidate MVP; private annotations underneath existing messages remain unverified.

## Start here

- [Roadmap and progress](PLANS.md)
- [Shared interfaces](docs/CONTRACTS.md)
- [Independent assignments](docs/DELEGATION.md)
- [Architecture and platform checks](docs/ARCHITECTURE.md)
- [Fetch.ai / Agentverse setup and Photon integration boundary](docs/FETCH_SETUP.md)
- [Eight publishable task definitions](planning/backlog.json)
- [Reusable planning prompts](PROMPTS.md)

## Published planning work

The initial planning publication on October 17, 2026 used the codex/sticker-planning review branch and left main unchanged. GitHub Actions published [eight task issues](https://github.com/ja-dens/lahacksai/issues) and two milestones. [Review the branch changes](https://github.com/ja-dens/lahacksai/compare/main...codex%2Fsticker-planning).

Automatic draft PR creation was blocked by this repository's GitHub Actions setting. No PR is claimed. The generated publication report records that warning and the actual issue/milestone URLs.

The three-person, 24-hour baseline is a planning assumption carried from the project discussion. Owner A handles Photon, B handles interpretation, and C handles context and coordination. An optional fourth teammate handles user testing and demo evidence.

## GitHub planning automation

The Sync sticker planning workflow reads planning/backlog.json and planning/issues/. It creates missing labels, two milestones, and eight issues; updates its generated issue sections; preserves human notes, checked tasks, closed state, and existing assignees; and attempts to open a draft planning PR when repository settings permit it.

It runs when the planning inputs change on main or codex/sticker-planning, and supports manual dispatch. It records verified URLs in planning/published.json. Updating the plan does not implement the product or continuously run Codex.

No personal access token is required: the workflow uses its short-lived repository GITHUB_TOKEN with contents, issues, and pull-request permissions. No repository permissions or visibility settings are changed by the publisher. Assignees stay unset until GitHub usernames are mapped in backlog.json.

## Local planning checks

With Node.js 20 or newer:

    node --test .github/scripts/sync-planning.test.cjs
    node .github/scripts/sync-planning.cjs --dry-run
    git diff --check

These check the planning publisher. Application checks belong to the implementation issues and are not passing yet.

## Implementation baseline

Use Jac for the core workflow, context selection, interpretation policy, validation, and delivery decisions. Thin Python clients may connect Photon 2.0 beta and one multimodal API. The project instructions require at least 40% Jac once application code exists; measure actual source usage rather than counting filenames. Planning automation is repository tooling, not an implemented application.

GitHub stores the code and tasks. The application backend must run on a laptop or hosting service. Runtime model access and Photon project/line access are separate setup dependencies.

Keep actual keys in local environment configuration. Commit placeholders and synthetic examples only.

## Sources

- [Photon 2.0 beta docs](https://photon.codes/docs/beta)
- [Photon hackathon guidelines](https://somethingreat.notion.site/Hackathon-Guidelines-for-Photon-2-0-3f8e443f36bb81f9893fed0d08a4c01d)
- [Codex planning conventions](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex)
- [GitHub workflow authentication](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
