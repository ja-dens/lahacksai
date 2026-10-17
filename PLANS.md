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
- Fetch.ai and Photon are both targets. Start with the sponsor's standalone
  mailbox quickstart in agent.py, then connect ACP to the shared Jac backend.
  The quickstart's sun-topic chatbot is setup work, not sticker functionality.

## Discoveries and unknowns

The target repository initially contained a single README and an initial commit. Git can read the repository and its push dry run permits a feature branch. The in-app browser is signed out; authenticated GitHub API access is not assumed.

The Photon sponsor guidelines state that iMessage group chat requires a dedicated line. Static-sticker media access, private-delivery behavior, the actual model budget, and deployment access still require real tests.

GitHub Actions uses a short-lived repository token for issue publishing. Repository settings can prevent draft PR creation. If so, preserve the branch and issues and record the limitation; do not change settings automatically.

Observed publication result: the workflow created issues #1–#8 and milestones #1–#2. The draft PR request returned HTTP 403 because GitHub Actions is not permitted to create or approve pull requests in this repository. The review branch and issues are published; no PR was created and main remains unchanged. Review the changes at https://github.com/ja-dens/lahacksai/compare/main...codex%2Fsticker-planning. A signed-in user or another authorized GitHub integration can create the PR without changing this repository setting.

## Verification and outcomes

Planning automation must pass its automated checks and dry run before publication. planning/published.json records remote issue/milestone/PR results after a successful workflow run. It is evidence of planning publication, not product functionality.

Application verification must include ambiguous media, identical images in different contexts, duplicate events, paused conversations, and isolation between conversations.

Fetch setup work uses the local codex/fetch-ai-setup branch. See
docs/FETCH_SETUP.md for the sponsor's mailbox route and local commands. A Python
3.13 virtual environment and ignored .env with a unique name and seed were
created. The user supplied the ASI:One key locally. Live startup published the
AgentChatProtocol manifest and registered successfully on the Almanac API.
After the user connected through the Inspector, the running SDK reported
"Successfully registered as mailbox agent in Agentverse". The user then showed
an ASI:One response from the named agent to the sun-facts question. The running
process logged HTTP 200 OK from POST https://api.asi1.ai/v1/chat/completions,
confirming a successful model API call. The quickstart's live round trip works;
Photon integration remains unverified. The standalone Python
sponsor example is outside product application-source counting; there is still
no implemented Jac sticker workflow or application Jac percentage to report.

Local Fetch verification passed on October 17, 2026: Python 3.13.14,
uagents 0.26.1, openai 3.34.0; agent.py --check; pip check; Python compilation;
mocked handler checks for acknowledgement/reply, provider failure, and empty
input; and git diff --check. Environment/runtime paths are ignored by Git. These
checks made no model requests and do not establish live registration or delivery.

Live startup evidence: agent address
agent1q2njg7mwfkt7pm83e883dpsghgee668adzc72flk5nt27ss2enfd2n8785k,
local server port 8001. The SDK also warned of insufficient funds for the separate
Almanac contract registration; no funds were sent. The mailbox connection is
verified from the runtime log; the subsequent ASI:One exchange is verified by
the user's screenshot and the successful model request in the runtime log.
