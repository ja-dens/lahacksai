# Sanitized Photon 2.0 beta examples

These files copy the field shape observed on October 17, 2026. Handles and resource ids in the JSON events are synthetic. The operation table cites the real resource ids from the live check and does not include an API key, project secret, or the enrolled phone number.

`inbound_text.json` is a human plain-text message in a direct shared-iMessage space. `outbound_text.json` is an agent text the provider later marked delivered. Neither file is a sticker.

Check them without credentials:

```sh
python3 scripts/check_photon_feasibility.py
```
