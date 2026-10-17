# Product architecture and feasibility checks

Approved conversation → Photon 2.0 beta adapter → context/enrollment checks → multimodal interpreter → validated explanation → private delivery on the enrolled recipient's own thread.

One backend owns this flow. GitHub stores source and tasks; a laptop or hosting service runs the backend. Start with a bounded in-memory conversation buffer and describe its restart limitations.

## Hackathon channel plan

The prize requires a project built on Photon 2.0 beta and live on at least one Photon channel. This project uses the beta API at `https://api.photon.codes/v1` and the beta clients (`@photon-ai/api`, `photonhq-api`). The Spectrum SDK (`spectrum-ts`) and the stable dashboard at `app.photon.codes` are a different product and do not qualify.

Use features the Free plan actually includes, and use each one for the job it supports.

| Feature | Use it for | Do not use it for |
| --- | --- | --- |
| Shared iMessage assignment (Free includes 25) | The qualifying text agent. One enrolled person texts a shared line, sends a sticker, and receives the private explanation in that same 1:1 thread. | Group chats, cold outreach, or phone calls. A shared assignment is direct only. |
| Dedicated iMessage line | Group chats and calls on the same iMessage number. Business plan, $250 per line per month. | The hackathon demo. Do not buy it to imitate a group. |
| SMS number plus a Voice profile | The separate Best Voice Agent prize. Calls go over SIP to one of Retell, ElevenLabs, LiveKit, or Twilio. | The sticker text flow. Voice does not run on iMessage. Free includes no SMS parts or voice minutes; US/Canada use is billed at about $0.01 per SMS part and $0.013 per voice minute. |
| Shared WhatsApp assignment (Free includes 25) | A later reach channel, only after a real WhatsApp Business account is connected. | A stand-in for iMessage. |
| Email domain (Free includes 1) | A later inbox channel, only with a domain the team controls. | The demo. |
| Telegram bot | A later reach channel, only with a bot token the team controls. | The qualifying channel. |

iMessage sends on the shared line have no per-message Photon fee. The enrolled recipient is chosen by enrollment settings, never by the model. If SMS voice is added later, reuse that same enrollment record and context window so the call and the text thread stay one conversation. Do not answer the agent's own outbound messages.

The beta project `pho_prj_01m55yjqt0esk81ms9g1w3kyxs` has one shared-pool number, `+16285024649`, paired with the enrolled sender. That sender completed one real 1:1 text exchange on October 17, 2026. Sticker media and a private explanation are still untested. A saved API key is not qualification by itself.

## Platform checks

Verify a real text exchange, actual static-sticker media, stable conversation/message identifiers, incoming direction, and private delivery to an enrolled recipient. For iMessage groups, confirm dedicated-line access with Photon. If the initial channel is blocked, investigate another Photon-supported channel and document which operation works. A replayed JSON fixture is not proof of native sticker support.

Private delivery in an assistant thread is the candidate MVP. An invisible inline annotation inside someone else's native chat interface is a separate unverified capability.

## Interpretation

Pass the actual sticker image plus selected recent messages to one multimodal model. Explain likely use in one or two sentences. Handle ambiguity, unfamiliar imagery, invalid results, and provider timeouts. No special training pipeline is part of the initial plan.

## User experience

Process explicitly enabled conversations and send explanations only to the enrolled recipient. Provide pause or request controls in the chosen interface. State that selected context and sticker media are processed by the chosen providers; private delivery does not make all processing on-device.

## Evaluation

Compare image-only and image-plus-context calls using the same model and examples. Reserve some examples until final evaluation. Measure delivery time, comprehension, and confidently wrong interpretations; record sample count and limitations.
