# Optional saved-explanation agent (#11 / T8)

This module retrieves an existing result and records voluntary feedback. It does
not interpret images, call a model, or participate in automatic Photon processing.
The standalone `agent.py` sun tutorial remains available separately.

From the nested `lahacksai` Git repository, using Python 3.13:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_fetch_agent.py'
python -m src.adapters.fetch_agent --demo
```

The last command runs the two approved prompts against the supplied fictional
record, without credentials or network access:

1. `Explain the sticker in saved demo exchange demo-3.`
2. `Mark interpretation one as helpful for demo-3.`

Observed offline output on October 17, 2026: lookup returned
`This probably means the joke was so funny they are crying.`, the cue
`They just said the joke got them.`, and the saved uncertainty caveat. Feedback
returned `ok: true`, `feedback_id: 1`, `window_id: 1`, `selection: first`, and
`provenance: recipient_judgment`, with a creation timestamp. This demonstrates
local tool execution, not ASI:One discovery or a live sponsor demonstration.

## How the pieces fit

`src/adapters/fetch_agent.py` translates an ACP text message into a narrow tool
operation. It removes only its own leading `@agent-address` routing mention and
surrounding whitespace before matching the approved prompts. That mention is
never used to authenticate the sender. `src/fetch_tools.py` enforces authorization, validates feedback and
remembers replay receipts. `FakeBackend` loads only the synthetic saved exchange
in memory; it stands in for T4's database operations.

| Decision | Reason and tradeoff |
| --- | --- |
| Retrieve the stored explanation | Reinterpretation could contradict what the recipient originally saw and adds a model call. |
| Match the approved prompts explicitly | Predictable, credential-free and testable. Arbitrary paraphrases currently receive help; there is no local LLM router. |
| Use Python for policy and SDK integration | Ordinary validation and authorization need no graph runtime; one language keeps the service easier to run and debug. |
| Supply identity separately | A prompt or model argument cannot establish permission. Missing and unauthorized exchanges give the same safe response. |
| Remember `(recipient, transport sender + msg_id)` | A replay returns the original receipt without a second write. Reusing that ID for changed arguments is rejected. |
| Keep feedback evaluation-only | A recipient's opinion is not confirmed sender intent and does not enter future interpretation requests. |

The service's `call(tool, arguments, authenticated_recipient_id=..., command_id=...)`
accepts only `get_explanation` with `window_id`, or `save_feedback` with
`window_id`, `selection` and optional `note`. Identity and command ID are trusted
caller parameters, never tool/model arguments. Backend methods retain T8's
`get_explanation(window_id, authenticated_recipient_id)` and
`save_feedback(window_id, authenticated_recipient_id, selection, note=None)` shapes.
The demo resolver additionally maps `demo-3` to one window within that recipient's
scope; missing or ambiguous aliases are refused.

Feedback accepts `first`, `second`, `neither`, or `not_sure`. A first choice requires
a shown meaning; a second requires an actual shown alternative. Notes are limited
to 2,000 characters. The chat grammar currently exposes the approved first-choice
prompt and its `interpretation two` counterpart. The other selections are available
through the narrow service API for later interface integration.

## Opt-in live Agentverse / ASI:One check

The implementation follows the official [mailbox tutorial](https://uagents.fetch.ai/docs/examples/asi-1)
and [Agent Chat Protocol documentation](https://docs.asi1.ai/documentation/tutorials/agent-chat-protocol).
The installed/pinned runtime is uagents 0.26.1, verified with real ACP schemas in
the fake-transport tests. The integrated backend uses Python 3.13 without Jac.

1. Stop the earlier sun tutorial if it is using port 8001. These commands are two
   separate runtimes; run only one with the same seed and port.
2. Set `FETCH_AGENT_NAME` and `FETCH_AGENT_SEED` in ignored `.env`. Retaining the
   previous seed retains the previous agent address. The new tools do not require
   `ASI1_API_KEY`; ASI:One's own account access remains separate.
3. Explicitly start the public, synthetic-only mode:

   ```sh
   python -m src.adapters.fetch_agent --serve-synthetic
   ```

4. Sign in to Agentverse, open the printed Inspector URL, connect the mailbox if
   needed, and check the runtime's registration/manifest logs. Open the agent's
   profile and Chat with Agent in ASI:One; send both prompts above.
5. Record the agent address, registration output, the returned explanation and
   feedback receipt, and whether repeating the *same ACP message ID* caused only
   one write. Sending a new chat message creates a new command and may create
   another feedback record. Keep the process running during the chat.

Every sender in this explicit mode sees the same fictional demo recipient. That
is public sample data, **not authenticated access to a real person's account**.
The general protocol factory accepts an injected trusted sender-to-account
resolver; an unbound sender is denied. Before using private app data, T4/T5 must
implement and verify real account binding and scoped database operations.

The CLI's FakeBackend keeps feedback and replay receipts in memory, so they
disappear on restart. When `FetchTools` is instead injected with
`src.context_store.SQLiteStore`, it uses the store's durable `execute_command`
operation. Feedback and command receipts commit together; a repeated transport
command returns its original receipt even after restarting the store and agent.
See [CONTEXT_STORE.md](CONTEXT_STORE.md) for transaction, authorization and purge
behavior. Real account binding and live transport verification are still required.
Nothing in these saved-result tools sends through Photon or introduces a model
request; no exactly-once network delivery guarantee is claimed.

## Observed live check, October 17, 2026

The user authorized the synthetic-only demonstration conditional on its inclusion
in the GitHub issues. A live read of [issue #11](https://github.com/ja-dens/lahacksai/issues/11)
confirmed the explicit opt-in registration/ASI:One test requirement.

Agent address: `agent1q2njg7mwfkt7pm83e883dpsghgee668adzc72flk5nt27ss2enfd2n8785k`.
Runtime logs confirmed `Manifest published successfully: AgentChatProtocol`, active
registration, and successful Almanac API registration. The SDK also warned that
the wallet lacked funds for Almanac **contract** registration; no funds were sent.
The mailbox test nevertheless reached the agent and returned a reply.

The initial lookup at 18:52 PDT returned the grammar help response. The addressed
ASI message included a leading routing mention, which the original full-match
parser did not accept. After adding exact own-address normalization, the retry
at 18:53 PDT displayed in ASI:One:

```json
{"ok": true, "window_id": 1, "source_message_id": "demo-3", "status": "interpreted", "meaning": "This probably means the joke was so funny they are crying.", "alternative": null, "context_cue": "They just said the joke got them.", "uncertainty_caveat": "This is a likely interpretation, not confirmed sender intent.", "candidate_relation": "single"}
```

The Inspector independently showed the incoming request, acknowledgement, and
successful explanation payload in the same chat session. At 18:55 PDT, the
second approved prompt displayed this receipt in ASI:One:

```json
{"ok": true, "feedback": {"feedback_id": 1, "window_id": 1, "recipient_id": "demo-older-recipient", "selection": "first", "note": null, "provenance": "recipient_judgment", "created_at": "2026-10-18T01:55:24.492159+00:00"}}
```

Both required prompts therefore have observed live responses from this synthetic
saved-result agent. No new sticker-interpretation call was introduced.

All 17 Fetch adapter tests and all 189 application tests passed after the routing
fix. Those tests cover addressed lookup/feedback, replay, different-address
refusal and unbound identity. The same-message-ID replay guarantee is verified
locally with real ACP schemas and separately with SQLite restart tests; it has
not been forced through the public ASI UI. Public demo feedback remains in memory.
Sponsor eligibility, private account binding and Photon delivery remain unverified.
