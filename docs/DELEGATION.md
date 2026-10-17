# Independent assignments

| Role | Work | Owned implementation files | Independent development |
| --- | --- | --- | --- |
| A | Photon input, sticker media, private output | src/adapters/photon.py | Send fixed explanation text on a test channel |
| B | One multimodal call, interpretation policy, evaluation | src/interpreter.jac, src/adapters/vision.py, prompts/sticker.txt | Use local images and synthetic conversations |
| C | Context, enrollment, routing, integration | src/main.jac, src/context.jac, src/delivery.jac | Use fake input and interpreter components |
| Optional D | User checks, accessible wording, demo evidence | Evaluation notes and demo material | Review saved examples and results |

The source files above are assigned implementation targets, not files that already exist. C coordinates shared contracts, dependencies, and run instructions. Owners coordinate interface changes rather than editing the same files independently.

Suggested branches: codex/photon-connection, codex/sticker-interpreter, and codex/context-pipeline. Teammates use separate clones. A branch alone does not isolate concurrent edits in one shared directory.

A and B should verify external runtime access early; C can build the fixture flow while those checks run. All three integrate the first real exchange as soon as the interfaces are usable. An optional fourth person improves evidence and polish without becoming necessary for the basic product.

Record username mappings in planning/backlog.json only when supplied. The publisher adds mapped assignees and preserves existing human assignments. It does not message teammates, invite collaborators, or create separate Codex chats.
