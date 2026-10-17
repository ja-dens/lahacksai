# Fetch.ai sponsor quickstart

Follow the sponsor's [official agent.py mailbox example](https://uagents.fetch.ai/docs/examples/asi-1)
first. The root `agent.py` keeps its sun-topic assistant, `asi1` model, ACP
acknowledgements/replies, port 8001, and mailbox registration. Small changes load
secrets from `.env`, use timezone-aware timestamps, keep runtime files in ignored
`local-data/fetch/`, and provide an offline check. This example is setup code;
sticker interpretation and Photon delivery are not implemented.

Verified October 17, 2026: mailbox registration succeeded, the user received the
sun-facts reply from the named agent in ASI:One, and the local runtime logged a
successful HTTP 200 model API request. The quickstart connection works.

## Install and check

Use the nested `lahacksai/` directory containing `.git`:

```sh
uv venv --python 3.13 .venv
.venv/bin/python -m ensurepip
.venv/bin/python -m pip install -r requirements-fetch.txt
.venv/bin/python agent.py --check
```

The sponsor's two libraries are `uagents` and `openai`. `python-dotenv` just loads
the ignored local configuration. Python 3.13 avoids the default local Python
3.14, which is outside the package's documented 3.10–3.13 support.

## Connect to Agentverse and ASI:One

1. Sign in to [Agentverse](https://agentverse.ai) and get an ASI:One API key from
   [the developer dashboard](https://asi1.ai/developer).
2. In `.env`, fill in `ASI1_API_KEY`, `FETCH_AGENT_NAME`, and `FETCH_AGENT_SEED`.
   If `.env` does not exist, copy `.env.example` first. Keep the seed private and
   stable; changing it changes the agent's identity. Do not paste the API key in
   chat or commit it.
3. Run `.venv/bin/python agent.py`. This starts the networked agent and attempts
   registration and manifest publication, just as the sponsor example does.
4. Open the **Agent inspector** link printed by the process. Choose **Connect →
   Mailbox** and follow its prompts while signed in to Agentverse.
5. Open **Agent Profile → Chat with Agent** to reach ASI:One. Ask **Give me three
   facts about the sun**. Keep the local agent running while testing.

This mailbox route does not require a public HTTPS tunnel. Successful startup is
not proof of the full flow: verify the mailbox connection, the ASI:One reply, and
the Agentverse profile. Record the real profile and chat URLs after success.

## Add Photon after the quickstart works

Use one backend. Replace the quickstart's sun-answering model call with a thin
adapter into the shared Jac workflow described in [CONTRACTS.md](CONTRACTS.md).
Photon remains responsible for messaging input and private delivery. Keep
recipient selection in enrollment settings, outside the model. An ACP sender
address is not a Photon recipient ID; account linking remains an integration
decision before handling private chat context or triggering delivery.

A candidate sponsor demo starts with an ASI:One request about a selected
permitted sticker and invokes the shared context, interpretation, and Photon
delivery flow. ACP media handling, authenticated enrollment, sticker selection,
and real Photon media support still need implementation and live verification.

The [Fetch challenge](https://www.fetch.ai/events/hackathons/la-hacks-ai-hackathon-2026/hackpack)
requires a discoverable ACP agent and a useful primary workflow completed from
ASI:One with meaningful tool execution/orchestration. This basic chatbot is only
the starting point. No product Jac percentage is claimed for the standalone
sponsor example; the at least 40% Jac application-source requirement remains.
