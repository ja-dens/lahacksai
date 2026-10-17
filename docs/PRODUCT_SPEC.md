# Sticker interpreter: product decisions and methodology

> Publication scope: planning and synthetic fixtures only. References to the local backend describe separate workspace work; its application source is not included in this revision.

Updated: October 17, 2026 (America/Los_Angeles).

Status: agreed product decisions plus explicitly labeled recommendations and implementation defaults. A local backend prototype now implements the fixture workflow; see PLANS.md for actual verification. Live Photon access and model accuracy are not established by this document.

## How to use this document

Read this document before implementing product behavior. The confirmed decisions below record the user's choices in the project discussion. Later direct user instructions take precedence. Recommendations and open questions are not additional confirmed requirements.

Use [PLANS.md](../PLANS.md) for implementation progress, [CONTRACTS.md](CONTRACTS.md) for agreed internal interfaces, and [ERROR_LOG.md](../ERROR_LOG.md) for actual errors and clearly labeled prevention risks. Older research and the parent folder's STICKER_PROJECT_PLAN.md provide historical context; they do not supersede the decisions recorded here.

When a decision changes, update its current wording and append a change-log entry. Preserve the reason for the change. Do not silently turn an untested proposal into a confirmed decision or a completed feature.

## Product purpose

Help older adults understand unfamiliar stickers in conversations with people from other generations. Interpret the sticker in its conversational setting and explain its likely use in understandable language.

The central experience is automatic: the recipient does not open a separate AI interface, paste a conversation, or submit a request for each sticker. Initial enrollment, settings, and later feedback are separate from the automatic explanation flow.

## Confirmed decisions

| ID | Decision | Implementation implication |
| --- | --- | --- |
| D01 | Automatically produce an explanation for each incoming sticker in an enabled conversation. | Do not require an interpretation request, a confusion prediction, or a novelty check before explaining. Two distinct messages containing the same image still count as two sticker messages. |
| D02 | Present the two most plausible interpretations only when they do not directly oppose one another. | Check both plausibility and compatibility before showing a pair. |
| D03 | When the strongest interpretations oppose one another, show the best-supported interpretation with an explicit uncertainty caveat. | Prefer wording such as "probably" and acknowledge that the intended tone is unclear. Do not present the opposing pair as the default output. |
| D04 | Users may voluntarily validate an interpretation later. | Feedback must not block explanation delivery or become a required task for each sticker. |
| D05 | Limit overgeneralization from validation. | Save feedback as an example tied to the particular exchange. Do not promote one selection into a broad rule about a person or every use of a sticker. |
| D06 | Provide personalization settings in this priority order: preferred language, explanation length, then sender relationship. | These three controls are selected. Defaults, supported values, and whether any initial settings screen is required remain open. D09 establishes sender–recipient relationship scope. The stated priority is not a weighting rule for inferring intent. |
| D07 | Maintain a Markdown record of product specifics and an error log for later implementation. | Keep this specification and the repository error log discoverable and current as the discussion continues. |
| D08 | Text context contains a limited number of messages preceding the target message and sticker; the user's preferred working range is around 20–25 messages. | Use the target sticker and any accompanying text plus up to N immediately preceding messages from the same conversation. Select the exact cap within that range before implementation and evaluate it rather than claiming it is optimal. Do not automatically search older chat history or include later replies. An extra reply target outside the window is not yet approved. |
| D09 | Build user context from three separately stored record types: recipient preferences, sender–recipient relationships, and situation-specific validated exchanges. | Save explicitly supplied settings and relationships, and preserve feedback source and exchange scope. The backend loads applicable preferences and relationships for each request. Do not require model retraining or rely on the model remembering prior requests. Exact database fields and technology remain open. |
| D10 | In the first working version, store validations for evaluation rather than automatically reusing them in future interpretations. | Live requests use the sticker, bounded chat context, recipient preferences, and applicable relationship. Keep prior validation records out of live model inputs. Test whether selective feedback reuse improves accuracy before adopting it. |
| D11 | Prefer a longer database conversation history and separately stored context-window instances. | Preserve observed messages beyond the current N-message window. Freeze a separate request snapshot for each sticker and enrolled recipient so later history or settings updates do not rewrite the original inputs. Exact storage technology and production retention are implementation matters. |
| D12 | Maintain context across time gaps. | Do not impose a maximum-age or inactivity cutoff on the preceding-message window. Keep timestamps so temporal gaps remain visible; the N-message bound still applies. |
| D13 | Include an optional Fetch/ASI:One demo that retrieves a saved explanation and records voluntary feedback. | Keep it separate from automatic Photon interpretation. A user may ask about saved demo exchange demo-3 or select a shown interpretation; the agent performs an authorized stored-result lookup or scoped feedback write, without reinterpreting the sticker. |

Sources: D01 follows the user's choice to explain every sticker without additional input. D02 revises the earlier plan to show two plausible meanings in ambiguous cases. D03 follows the user's selection of the single-best-guess-with-caveat option. D04 and D05 record voluntary later validation and the choice that limits overgeneralization. D06 records the settings choice and the subsequent selection of three controls in priority order. D07 records the documentation request. D08 records the user's confirmation of a limited preceding-message window and subsequent preference for around 20–25 messages.

D09 and D10 record the user's agreement with the proposed user-context model, including the recommendation to store validations for evaluation in the first version. This accepts the conceptual design and initial reuse policy, not a database implementation or a proven accuracy improvement.

D11 and D12 record the user's subsequent preference for a longer database history with separate context windows and their instruction to maintain context across time. The user asked to end extended product questioning and move into building; remaining unknowns below are implementation work unless further input is essential.

D13 records the user's explicit approval of the optional saved-explanation/feedback Fetch demo while Photon explanations remain automatic. Task T8 defines the concrete prompts and mockable backend operations. This approval does not establish a working ASI:One registration or sponsor eligibility.

## Interpretation and presentation policy

The following table operationalizes the confirmed decisions. The clear-meaning and insufficient-evidence cases are recommendations or open items where noted.

| Evidence situation | Output behavior | Decision status |
| --- | --- | --- |
| One interpretation is clearly supported. | Give one concise explanation; do not manufacture a second. | Recommended operational rule; not separately confirmed. |
| The two strongest interpretations are plausible, distinct, and compatible. | Present both as possible meanings. | D02; the distinctness check is a recommended safeguard against duplicate wording. |
| The two strongest interpretations directly oppose one another, but a best-supported candidate can be identified. | Show that candidate with an explicit uncertainty caveat. | D03. |
| The media is unreadable, neither candidate is defensible, or there is no basis to rank opposing meanings. | Do not invent a confident interpretation. The exact user-facing fallback needs a decision. | Open question Q04. |
| A model or transport request fails. | Handle the operational failure explicitly rather than inventing a sticker meaning. | Existing interface agreement; final wording and retry behavior remain open. |

Compatibility examples are illustrative, not a complete classification algorithm:

- Compatible: surprise at good news and excitement for the recipient. Both can hold at once.
- Opposing: sincere approval and sarcastic disapproval. These imply conflicting attitudes toward the same thing.

Recommended safeguards: evaluate the strongest candidates first; do not replace an opposing candidate with a weaker third choice merely to produce a compatible pair. Preserve uncertainty even when two candidates are compatible. Do not invent numerical confidence percentages.

How the model will classify opposition, rank candidates, and decide when evidence is sufficient remains to be validated. A prompt instruction alone is not evidence that the policy works.

## Context methodology

The teammate's proposal is to use the sticker and chat context as a baseline, then refine the explanation with user context. D08 confirms the bounded preceding-message window; D09 confirms the conceptual user-context structure; D10 keeps saved validations out of live requests in the first working version. Exact fields and measured effects still require implementation and evaluation.

| Context category | Examples | Intended role |
| --- | --- | --- |
| Sticker evidence | Actual image, visible text, supported animation when available. | Establish what the sticker depicts. |
| Current conversation | Target message and sticker, plus up to N immediately preceding messages, speakers, and timestamps in the same conversation. | Establish likely conversational use within D08's preferred 20–25-message range. The exact cap remains open; do not silently add a reply target from outside the window. |
| Specific shared-history examples | A prior exchange with a recorded recipient selection or explicit sender confirmation. | Stored for evaluation initially under D10. Reuse as a live contextual clue is a later possibility requiring evidence and a new decision. |
| Recipient presentation settings | Selected controls are preferred language and explanation length. | Make the explanation understandable while preserving meaning and uncertainty. |
| Sender relationship setting | A user-provided relationship to the particular sender; supported values remain undecided. | Supply a limited contextual cue without treating a relationship category as proof of the sender's attitude. |

Do not assume that a preferred writing style establishes the sender's intent. For example, a preference for reassuring language must not turn supported frustration into affection. Relevant confirmed shared usage may help interpretation; recipient presentation preferences principally affect wording.

Recommended initial flow:

1. Receive a new sticker event from an enabled conversation and preserve its source identity.
2. Include the target sticker and accompanying text, then select at most N immediately preceding messages from the same conversation, as confirmed in D08. The user's preferred range is around 20–25; the exact cap remains open. Include a reply target only if it is already inside that window unless an explicit exception is agreed later. Do not use subsequent replies as if they had been available on arrival.
3. Retrieve the recipient's chosen language and length preferences and their declared relationship to this sender. Do not retrieve prior validations for live interpretation in the first working version (D10).
4. Send the actual sticker and clearly separated context sections to one multimodal model call.
5. Request likely meaning, a brief supporting cue, uncertainty, candidate compatibility where applicable, and the recipient-facing explanation.
6. Apply the output policy above and route the result privately using application-controlled enrollment settings.
7. Accept voluntary later feedback without interrupting subsequent automatic explanations.

The one-backend, one-model-call starting point is an existing repository implementation agreement. Separate interpretation and presentation roles logically; a second model call is not an agreed requirement or an established accuracy improvement. Do not claim that prompt sections guarantee semantic isolation.

## Personalization settings

Confirmed settings, in the user's stated priority order:

1. Preferred language.
2. Explanation length.
3. Sender relationship.

The selection priority does not mean language preferences should override evidence about a sticker's meaning. Language and length govern presentation. Relationship information is a contextual cue whose actual effect must be evaluated.

Defaults, supported languages, length options, relationship categories, where settings appear, the initial setup experience, and database technology are not yet decided. D09 establishes separate application-owned preference, relationship, and validated-exchange records, with relationships scoped to the relevant sender and recipient. Exact fields still require T0 coordination.

Earlier suggestions such as a separate slang-familiarity control or shared-reference settings are not part of the selected settings list. Do not require a new settings answer each time a sticker arrives.

### Agreed conceptual structure for user context

The three-record structure is agreed under D09; exact field names, physical tables, and database technology are still proposals requiring T0 coordination. No implemented feature is claimed. User context is stored in application-owned records; it does not require model training or depend on the model remembering earlier API calls. In the first version, retrieve preferences and relationships for live requests and store validated exchanges separately for evaluation (D10).

| Agreed record type | Lookup scope | Contents and role |
| --- | --- | --- |
| Recipient preferences | Recipient ID within the enrolled account. | Explicitly selected preferred language and explanation length, with source and update time. Controls presentation. Missing-value defaults are still open. |
| Relationship | Recipient ID plus sender ID within the authorized scope. | The recipient's declared relationship to that sender, with source and update time. A limited clue to interpretation, not a personality profile. |
| Validated exchange | Recipient, sender, conversation, and source message IDs. | The situation-specific feedback described below, including its source and whether the sender confirmed it. Evaluation data initially; exclude it from live interpretation inputs under D10. |

Agreed initial construction: save explicit settings and relationship information when supplied. Record voluntary feedback as an additional exchange-specific record for evaluation. Do not infer age, personality, or a general communication style merely to populate a profile. Do not automatically convert model-generated explanations into confirmed user facts.

At sticker arrival, the backend resolves the authorized recipient and sender and loads their applicable settings and relationship. Keep those inputs separate from the current N-message window. Do not add historical validation examples in the first working version. Exact retention rules remain open. A later evaluation of selective example reuse should start with narrow recipient/sender/conversation scope; eligibility and maximum count would need a separate decision.

Send labeled sticker, current-chat, relationship, and presentation-settings inputs in the existing single model request. Preferences affect the explanation's language and length; relationship information may affect the inferred meaning, but must not override clear current evidence or erase uncertainty. A settings change updates subsequent requests without retraining the model.

Do not bypass D08 by inserting an unrestricted summary of older conversation text into a user profile. Selective reuse of separately recorded feedback is deferred under D10. Compare outputs with and without that reuse during evaluation before proposing its adoption or claiming it improves accuracy.

### Conversation storage versus model context: tradeoffs under discussion

The 20–25-message preference limits model input; it does not by itself select a storage policy. A rolling buffer can be the only retained conversation history, an in-memory cache backed by a longer database history, or a bounded persistent record set. Count bounds and restart persistence are separate choices. A longer archive can still provide exactly the same preceding-message window without semantic relevance ranking or another model call.

| Storage approach | Benefits | Limitations |
| --- | --- | --- |
| Retain only a rolling recent-message window. | Bounds message count per conversation and reduces retained chat data; simple append/evict behavior. | Evicted exchanges cannot be reconstructed locally for debugging or later feedback unless a permitted snapshot was saved. A RAM-only implementation loses state on restart; persistence can avoid that. Count alone does not bound bytes or the number of active conversations. |
| Retain a longer database history; select only the preceding N for each request. | Supports replay, investigation of errors, delayed feedback, and different context-size evaluations, subject to permissions and retention. | More stored data and cleanup/access-management work. Loading the whole archive or adding semantic search is unnecessary for selecting the latest N. |
| Retain recent history for a limited period in a database; select only preceding N. | Provides restart recovery and a limited replay window while bounding retention. Does not require a separate cache for a small prototype. | Needs explicit retention/size limits and cleanup; data outside the retention period is unavailable. |

For the same actual model payload, a larger stored archive does not itself increase input tokens or improve interpretation. With a suitable ordered index, a database can retrieve a limited recent window without scanning the entire archive: see [PostgreSQL's index and ORDER BY documentation](https://www.postgresql.org/docs/current/indexes-ordering.html). Limited selections also need deterministic ordering; see [LIMIT and OFFSET](https://www.postgresql.org/docs/current/queries-limit.html). These are feasibility references, not a database technology selection or a performance benchmark of this product.

D11 now selects longer database history with separately saved context-window instances, superseding the earlier rolling-only recommendation. A pure in-memory ring buffer is not the selected source of truth. Longer stored history does not expand the N-message model input. Production retention/deletion and any optional cache remain implementation work; indefinite retention is not a separate agreed product requirement.

Recommended safeguards, not yet fully selected policies:

- Treat message count, per-message content size, total model-input budget, and media handling as separate limits. Twenty-five short replies and twenty-five long pasted documents are different payloads. Record omissions or truncation explicitly; do not silently equate unsupported media with empty conversation.
- Preserve source message identity, sender, timestamp, reply reference when available, and content type. Include actual text where available; do not automatically download or interpret all historical media. Exact handling of preceding sticker/image/audio messages needs an agreement.
- Anchor selection to the target message and snapshot the permitted input before later activity or eviction can change it. Only use messages actually available through the authorized integration; a local database does not imply provider backfill access.
- D12 resolves the age policy: preserve the N-message context even across long gaps. Retain timestamps and let the interpreter assess their relevance rather than deleting messages from the input solely because they are old.
- Keep preferences and relationships separate from chat retention. Any permitted evaluation example needs its deliberately selected context and its own retention policy; first-version validations remain excluded from live inputs under D10.

Storage direction and context age are resolved under D11/D12. Content budgets and retention remain implementation work under Q11/Q12. A prompt-window limit does not itself establish deletion from backups, logs, or provider-held copies.

### Initial implementation defaults and build scope

These are concrete, reversible engineering choices for the local prototype, not claims that the user selected exact database fields or that accuracy is proven:

- Use SQLite for local persistent message history, profiles, enrollment, immutable context windows, results, evaluation feedback, and a private-delivery outbox. Keep the database in ignored local-data/.
- Default N to 25 within the user's preferred 20–25 range. No age cutoff, older semantic search, automatic conversation summarization, or live feedback retrieval is enabled.
- Store a separate snapshot for each source sticker and recipient. Preserve the selected source IDs, bounded text, actual target image, user-context values, policy version, and available interpreter metadata. Keep a snapshot hash; later messages and profile changes must not alter it.
- Preserve full observed message text in the local history. The model-input default limits recent text to 24,000 characters total and 4,000 per message, plus up to 4,000 characters of target text; mark truncation explicitly. These are character limits, not an exact model-token budget. Prior media is identified but not interpreted. The initial target format is a synthetic tested PNG, at most 5 MB.
- Start with English and short/detailed length values for the local demo. The model adapter accepts a declared language; multilingual accuracy and localized operational-failure wording still need evaluation.
- For insufficient or unsupported evidence, use an honest temporary English abstention message. This is a conservative implementation default while final wording remains open. Operational model failures retain a failed run and its input snapshot rather than a fabricated interpretation.
- Include an offline fixture interpreter and a replaceable OpenAI Responses API-key adapter. The offline demo is not a vision accuracy test. API access, a particular image-capable model, and billing are not assumed provisioned. ChatGPT plan usage through Sign in with ChatGPT would require a separate authorized integration and is not implemented by the API-key adapter.
- Queue a private explanation using enrollment-controlled routing; queuing is not a Photon send. Photon 2.0 beta sticker ingress and private transport still require real access and verification.
- The local development database keeps history until explicitly purged. Production access controls, retention, encryption, identity verification, webhook authentication, retry behavior, and deployment must be addressed before processing real personal chats.

## Feedback and limited generalization

Confirmed: validation is voluntary and should stay tied to the particular exchange rather than immediately becoming a broad behavioral pattern.

Recommended feedback record:

- Source conversation and message identifiers.
- Sender and recipient identifiers within the authorized scope.
- Sticker reference and the relevant context snapshot or an appropriately minimized reference to it.
- Interpretations that were shown and which one the recipient selected.
- Who supplied the feedback, when it was supplied, and any optional correction.
- Whether there is explicit sender confirmation; keep that separate from recipient judgment.

Interpret a recipient selection as "the recipient selected this meaning in this exchange." Do not relabel it as "this is definitely what the sender meant." Under D10, first-version feedback is for evaluation rather than live context. If later testing selective reuse, image identity alone does not establish equivalent meaning.

The exact feedback controls, whether to include "neither" or "not sure," similarity criteria, retention/deletion rules, and any threshold for deriving a broader pattern remain open. No broader-pattern learning is currently approved from a single validation.

## Working build baseline and platform constraints

Existing repository guidance starts with one channel, static stickers, one backend, one existing multimodal model, and private delivery to an enrolled recipient. Exact supported media and actual access require testing.

The core working direction is Photon plus one multimodal LLM request. D13 adds a separate optional Fetch/ASI:One entry point for saved-explanation lookup and voluntary feedback. It neither triggers nor blocks automatic explanations and does not reinterpret the image. ASI:One may use conversational/tool orchestration for that optional interaction. Its account, discovery and challenge-eligibility requirements still need verification; a local fake backend is sufficient to start the independent adapter task.

Photon 2.0 beta is the target. Prior research found that iMessage groups require a dedicated line and that private inline annotations beneath existing messages are unverified. The candidate MVP uses a private assistant thread. Treat platform access and actual sticker support as verification dependencies, not finished features.

Keep conversation permission checks and recipient routing in application code. The model does not choose who receives an explanation. A duplicate platform event should not create duplicate explanations, but a new message reusing an old sticker must still be processed under D01.

## Evidence to collect during implementation

These are proposed acceptance checks, not tests that have passed:

- Every supported incoming sticker in an enabled chat is processed without a separate request.
- Two distinct messages using the same image each receive an explanation; retrying one source event does not duplicate its result.
- Compatible plausible candidates can be shown together.
- Opposing top candidates produce one best-supported interpretation with a visible caveat.
- A weaker third interpretation is not substituted simply to avoid a conflict.
- A recipient's preference for positive wording does not change an inferred negative meaning into a positive one.
- One feedback selection remains an exchange-specific example and is not promoted to a universal sticker definition or a personality trait.
- Withholding feedback does not interrupt automatic processing.
- Each configured setting has an observable, appropriate effect without changing the intended interpretation or dropping uncertainty.
- Conversation context and feedback examples do not leak into an unauthorized conversation or destination.
- The current-chat payload respects the configured N-message bound, excludes later replies, and does not reintroduce unrestricted older chat through profile summaries.
- Stored validations do not enter first-version live model requests; evaluation records remain distinct from active user-context inputs.
- A longer retained conversation, if adopted, does not expand the live N-message window. Context selection remains anchored to the target message, even when later messages arrive before a job finishes.

For evaluating the agreed context structure, compare the same held-out examples with sticker plus chat, then add relationship context and presentation settings in separate comparisons. Assess interpretation accuracy separately from recipient comprehension. Where feasible, obtain sender confirmation of intent. Record wrong confident answers, meaning changes caused by presentation preferences, latency, sample count, and limitations. Test selective historical-example reuse only as a separate evaluation: do not retrieve the target exchange's own feedback as evidence or enable reuse in live requests without a later decision.

The local implementation establishes a v2 boundary in CONTRACTS.md. Teammates still need to review it before parallel integration; no remote issue publication or team sign-off is implied.

## Open decisions for future discussion

- Q01: The selected settings are preferred language, explanation length, then sender relationship. What defaults and supported values should these use?
- Q02: Are settings optional at first use, or is there a short initial setup?
- Q03: How will compatibility/opposition and sufficient evidence be assessed and tested?
- Q04: What should the automatic response say when no defensible interpretation can be ranked?
- Q05: Where and how can recipients provide voluntary validation later?
- Q06: What makes a prior exchange similar enough to reuse, and how are sources, retention, correction, and deletion handled?
- Q07: How is the explanation visually associated with its source sticker in a private assistant thread?
- Q08: Which live channel, line, and sticker format are actually available to the team?
- Q09: D08 records around 20–25 preceding messages; the initial implementation defaults to 25. No extra reply target outside the window is added. Revisit the cap using evaluation evidence if needed.
- Q10: Resolved by D09 and D10: use three user-context record types and initially store situation-specific validations for evaluation only. Exact shared fields and database technology remain open.
- Q11: Resolved in direction by D11: longer database history and separate context-window snapshots. SQLite is the local implementation default. Exact production retention, cleanup, and feedback-example lifetime remain implementation work.
- Q12: Age resolved by D12: no age/time-gap cutoff. Initial character/media limits and explicit truncation are recorded above; calibrate actual token usage and content policies against the chosen model.

## Decision history

All entries below were recorded October 17, 2026 from this conversation. These are refinements of the design, not software errors.

1. Selected automatic explanations for every sticker, rather than novelty-based or predicted-confusion gating.
2. Selected two plausible interpretations for ambiguous cases and voluntary later validation.
3. Revised the two-interpretation behavior: only show a pair when its meanings do not directly oppose one another.
4. Selected one best-supported interpretation with an uncertainty caveat when the strongest meanings conflict.
5. Selected feedback limited to a particular situation to reduce overgeneralization.
6. Selected personalization in settings; exact controls remain open.
7. Requested a maintained Markdown specification and error log for future product creation.
8. Selected the settings in priority order: preferred language, explanation length, then sender relationship. Asked to continue with technical aspects rather than further user-experience questions. Context-selection recommendations remain unconfirmed.
9. Confirmed that text context contains only a limited number of preceding messages plus the target message and sticker; the count is not yet selected. Returned to discussing how user context is constructed. The preferences/relationship/validated-exchange record structure and automatic reuse of validation remain proposals.
10. Agreed with the proposed user-context model: separate recipient preferences, sender–recipient relationships, and scoped validation records. Adopted the recommendation to store validations for evaluation in the first working version, with live reuse deferred pending testing. Exact schemas and storage/retention choices remain open; Q11 introduces the next storage discussion.
11. Preferred around 20–25 preceding messages and asked about rolling-buffer versus longer-history tradeoffs. Recorded that storage and model-context selection are independent. Revised the storage recommendation toward limited persistent recent history with deterministic N-message selection; no retention policy or database technology has been approved. Content size, media handling, and context age remain open under Q12.
12. Selected longer database history with separately saved context-window instances and instructed maintaining context across time. Asked to stop extended planning and move into creating the project. Recorded D11/D12 and began the local backend, using the explicit implementation defaults above while keeping live integration and accuracy work separate.
13. Approved an optional Fetch/ASI:One saved-explanation lookup and voluntary-feedback demo, while preserving automatic Photon explanations. Split development prerequisites from later live integration and requested durable updates to the planning source and GitHub issues with independently delegable tasks.
