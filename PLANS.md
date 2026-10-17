# Sticker interpreter roadmap

## Outcome and scope

An enrolled recipient receives a short private explanation of a supported sticker, based on recent messages from an approved conversation. An existing multimodal model performs interpretation. One channel, static images, one language, and a small in-memory context window form the first scope.

Working phone delivery, useful interpretation, correct recipient routing, and honest uncertainty are the success criteria. Model training, a sticker dictionary, a new chat client, multiple channels, voice, and inline private annotations are later possibilities.

## Progress

- [x] Prepare product scope, interfaces, ownership, templates, and eight issue bodies locally.
- [x] Add an automated planning publisher and local verification commands.
- [x] Publish codex/sticker-planning and verify planning/published.json: eight issues and two milestones exist.
- [ ] Confirm the shared contract with the implementation team (T0).
- [ ] Verify Photon group/sticker/private-delivery access (T1).
- [ ] Implement independent modules (T2, T3, T4).
- [ ] Demonstrate one complete live exchange (T5).
- [ ] Evaluate context benefit and uncertainty (T6).
- [ ] Package a reproducible demo (T7).

Checked items describe completed planning work only. Update publication status only after observing the remote result.

## Milestones and dependencies

1. **Sticker MVP: independent modules** — T0 and T1 can start together. T2 needs both; T3 and T4 need T0 and can use local samples.
2. **Sticker MVP: working phone demo** — T5 joins T2/T3/T4. T6 evaluates T3. T7 needs T5 and T6.

The canonical task details live in planning/issues/. Metadata, dependencies, owner roles, and optional username assignments live in planning/backlog.json.

Aim for the first complete path within roughly hours 4–6 of the 24-hour reference build. Reserve the last several hours for fixes, reproducibility, and rehearsal. Adjust estimates to the team's actual access and skills.

## Decisions

- Interpretation starts with one multimodal call containing the actual sticker image and selected text.
- The backend chooses recipients from enrollment settings.
- Each owner develops against the shared format and substitutes unfinished dependencies.
- No live data, API key, model endpoint, or phone line is assumed provisioned.
- Owner roles are planning labels until teammates' GitHub usernames are supplied.
- Existing general hackathon research stays outside this repository.

## Discoveries and unknowns

The target repository initially contained a single README and an initial commit. Git can read the repository and its push dry run permits a feature branch. The in-app browser is signed out; authenticated GitHub API access is not assumed.

The Photon sponsor guidelines state that iMessage group chat requires a dedicated line. Static-sticker media access, private-delivery behavior, the actual model budget, and deployment access still require real tests.

On October 17, 2026 the signed-in dashboard at https://app.photon.codes/dashboard was Spectrum, the stable product, for account Kalena D. A Free project named lahacksai was created with iMessage selected. Its project id is 9c35348c-9428-4dad-8a2c-b1eade874bce. The project secret is only in the gitignored local .env. Getting started reported account_phone_missing, so Spectrum cannot enroll a line until a phone is added from the account menu. This is not a Photon 2.0 beta project id (those start with pho_prj_). No application source was added.

The same account then signed in to Photon 2.0 beta. Organization Kalena's Org is `pho_org_01m55yft3jfvq9b64abja4yf5w`. Free project lahacksai is `pho_prj_01m55yjqt0esk81ms9g1w3kyxs`. A 90-day project key named lahacksai-t1 has platforms and project read/write; its secret is only in `.env`. Shared iMessage is one to one and has no assigned line because no phone or iMessage email was added. A dedicated line, which is the documented group-chat option, requires Messaging Business at at least $250 a month and was not purchased. No ping, sticker, or private reply was sent. Details are in docs/T1-verification.md. T1 stays open.

GitHub Actions uses a short-lived repository token for issue publishing. Repository settings can prevent draft PR creation. If so, preserve the branch and issues and record the limitation; do not change settings automatically.

Observed publication result: the workflow created issues #1–#8 and milestones #1–#2. The draft PR request returned HTTP 403 because GitHub Actions is not permitted to create or approve pull requests in this repository. The review branch and issues are published; no PR was created and main remains unchanged. Review the changes at https://github.com/ja-dens/lahacksai/compare/main...codex%2Fsticker-planning. A signed-in user or another authorized GitHub integration can create the PR without changing this repository setting.

## Verification and outcomes

Planning automation must pass its automated checks and dry run before publication. planning/published.json records remote issue/milestone/PR results after a successful workflow run. It is evidence of planning publication, not product functionality.

Application verification must include ambiguous media, identical images in different contexts, duplicate events, paused conversations, and isolation between conversations.
