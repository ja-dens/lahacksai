# Product architecture and feasibility checks

Approved conversation → Photon adapter → context/enrollment checks → multimodal interpreter → validated explanation → private Photon delivery.

One backend owns this flow. GitHub stores source and tasks; a laptop or hosting service runs the backend. Start with a bounded in-memory conversation buffer and describe its restart limitations.

## Platform checks

Verify a real text exchange, actual static-sticker media, stable conversation/message identifiers, incoming direction, and private delivery to an enrolled recipient. For iMessage groups, confirm dedicated-line access with Photon. If the initial channel is blocked, investigate another Photon-supported channel and document which operation works. A replayed JSON fixture is not proof of native sticker support.

Private delivery in an assistant thread is the candidate MVP. An invisible inline annotation inside someone else's native chat interface is a separate unverified capability.

## Interpretation

Pass the actual sticker image plus selected recent messages to one multimodal model. Explain likely use in one or two sentences. Handle ambiguity, unfamiliar imagery, invalid results, and provider timeouts. No special training pipeline is part of the initial plan.

## User experience

Process explicitly enabled conversations and send explanations only to the enrolled recipient. Provide pause or request controls in the chosen interface. State that selected context and sticker media are processed by the chosen providers; private delivery does not make all processing on-device.

## Evaluation

Compare image-only and image-plus-context calls using the same model and examples. Reserve some examples until final evaluation. Measure delivery time, comprehension, and confidently wrong interpretations; record sample count and limitations.
