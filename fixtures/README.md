# Synthetic fixtures

chats/joke.json is fictional text for independent context/pipeline development. It references stickers/laughing.png, an original synthetic PNG produced by scripts/make_demo_sticker.py and visually inspected during the initial build. The asset can be regenerated with the standard library; it is not a downloaded or real person's private sticker.

fixture_model_output is a fixed integration substitute, not a vision result or verified sender-intent label. The default demo never analyzes the image. Optional live mode supplies the actual image and frozen context to the configured model; it still performs no Photon send. Include ambiguous examples and the same sticker in different contexts when building the evaluation set. Keep final evaluation examples separate from prompt-tuning examples.

Do not add private chat histories, real contact identifiers, or credentials.

stickers/hamster_pack_reference.jpg is the user-supplied 19-tile reference
sheet. `evaluation/hamster_pack.json` records crop bounds and visible features
for recognition/evaluation. Both files are kept local-only (excluded through
`.git/info/exclude`) and are not pushed; the code skips the reference when they
are absent. The sheet is sent as an app-supplied recognition
reference in the existing single model request; it is not a set of
sender-confirmed meaning labels. Permission to use this supplied image does not
establish ownership or permit unrelated redistribution.

Serialized v2 interfaces for all independent tasks are in [contracts/README.md](contracts/README.md). Run `python3 scripts/check_contract_fixtures.py` with the standard library only. Passing that check verifies example consistency, not a live model or Photon send. The application CLI and image-generator implementation described above are local prototype work until separately published; the included PNG and serialized boundaries can be used immediately.
