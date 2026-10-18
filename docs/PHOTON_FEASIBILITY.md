# Photon 2.0 beta feasibility, October 17, 2026

Issue: https://github.com/ja-dens/lahacksai/issues/2

This is an evidence report for the lahacksai beta project. It is not a working sticker integration. The API key and the enrolled phone number stay in the gitignored `.env`. Sanitized event shapes are in `fixtures/photon_vendor/`.

The check below does not call Photon:

```sh
python3 scripts/check_photon_feasibility.py
```

A live read uses the configuration names `PHOTON_API_KEY`, `PHOTON_PROJECT_ID`, `PHOTON_TEST_SENDER`, and `PHOTON_AGENT_HANDLE`. Do not print those values. The calls that produced this report were `GET /v1/projects/{id}/platforms/imessage`, `GET /v1/projects/{id}/messages`, `GET /v1/projects/{id}/attachments`, and `POST /v1/projects/{id}/messages` with an `Idempotency-Key`.

## Operations

| Operation | Result | Evidence |
| --- | --- | --- |
| Shared line assignment | Supported | `POST /v1/projects/{id}/platforms/imessage/assignments` returned 201. Assignment `pho_asg_01m562efr8e8g8pc3qtjvbcmre`. Pool number `+16285024649`. The sender handle is only in `.env`. |
| Inbound text | Supported | Plain text `Ping` was stored as `pho_msg_698qe8a1b9hbzsqdkkf0w9bf5b` at `2026-10-17T23:19:28.938Z`. Space `pho_spc_0nhxpaja9ngpfvaj6eevmkcmd2` is `direct`. Sender kind was human and receiver kind was agent. |
| Outbound text in that direct space | Supported by the provider | `pho_msg_40ncpnpd8cg1vrr2x6x5g26vy5` reached status `delivered` at `2026-10-17T23:20:51.485Z`. Fixed explanation `pho_msg_1v7312gj71g3js27mej9b0nbpq` reached status `delivered` at `2026-10-17T23:32:41.606Z`. Neither status is a visual confirmation on the phone. |
| Threaded reply | Unsupported | Sending with `parentMessageId` set to the inbound message returned 409 `SPACE_NOT_SENDABLE`: replies are not supported for this space. |
| Group iMessage | Blocked | Platform `mode` is `shared`. A shared assignment is direct only. No group send was attempted. |
| Dedicated line | Blocked | The same platform read returned `dedicatedLineAvailableNow: true` while `mode` stayed `shared`. No dedicated resource was created, and no Business line was purchased. The flag does not mean a line is owned. |
| Static sticker | Not ingested | At 4:47 PM Pacific the enrolled phone showed a native sticker as Delivered in the same iMessage thread. Through 2026-10-17T23:48:27Z the project still had 3 messages, 0 attachments, and the space `updatedAt` was unchanged at 2026-10-17T23:19:28.923Z. No bytes, media id, or sticker event were available. |
| Inline annotation | Untested | Not attempted. The private path that worked is a normal message in the enrolled direct space, not an annotation inside another chat. |

Account phone verification in the dashboard was skipped. The shared-line assignment still succeeded for the enrolled iMessage handle.

## Smallest next step

A native sticker can leave the phone and still never appear in list messages or attachments. The stored image path is a photo sent with the photo button. At 2026-10-17T23:54:57Z a later plain text `hi` was stored, which confirms text ingest while the sticker stayed absent. T5 cannot claim sticker media until an image attachment exists.

## Channel requirements

Photon 2.0 beta, project `pho_prj_01m55yjqt0esk81ms9g1w3kyxs`, API `https://api.photon.codes/v1`, a project key with `project:read`, `project:write`, `platforms:read`, and `platforms:write`. The observed text path needs one shared iMessage assignment and an inbound message before the line can send. Group chat and a separate assistant thread were not available on this shared line.
