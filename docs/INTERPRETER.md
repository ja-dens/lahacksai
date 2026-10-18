# Canonical sticker interpreter

The combined application retains T3's one-call interpreter and removes the duplicate implementation from the former Fetch module branch. See [T3_INTERPRETER.md](T3_INTERPRETER.md) for its policy, fixtures, failure behavior and standalone commands, and [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) for the application flow.

Use `from src.interpreter import interpret_sticker` with a callable raw-candidate provider such as `src.adapters.vision.OpenAIVision`. T5 receives the final result through `src.adapters.assembly.Interpreter`. Apply candidate policy once. The model never chooses a recipient, and saved feedback is not inserted into live interpretation.

`requirements.txt`/`requirements.lock` supply one combined Python 3.13 setup. The former `requirements-agent-modules.txt` now points to that setup. The hamster asset is retained as an additional fixture; the canonical shared exchange still uses the original laughing PNG and hashes.

The optional Fetch adapter supplies saved-result lookup and voluntary feedback, separately from automatic interpretation. See [FETCH_AGENT_DEMO.md](FETCH_AGENT_DEMO.md). Its offline demo remains available; live model/Photon and saved-result Agentverse checks are not inferred from compilation.
