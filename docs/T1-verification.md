# T1 verification, October 17, 2026

Issue: https://github.com/ja-dens/lahacksai/issues/2

This records what was observed. It is not a completed ping, sticker, or private-delivery test. No API key or project secret is included.

## Photon 2.0 beta

Signed in at https://app.beta.photon.codes as the same Google account used for Spectrum.

| Item | Observed status |
| --- | --- |
| Organization | Kalena's Org, `pho_org_01m55yft3jfvq9b64abja4yf5w` |
| Project | `lahacksai`, slug `lahacksai`, Free, `pho_prj_01m55yjqt0esk81ms9g1w3kyxs` |
| API key | `lahacksai-t1`, 90 days, `platforms:read`, `platforms:write`, `project:read`, `project:write`. The secret is only in the gitignored `.env`. |
| Phone | Account phone verification was skipped. The owner later supplied an iMessage sender, stored only in gitignored `.env` as `PHOTON_TEST_SENDER`. |
| iMessage line | Assigned on October 17, 2026. `POST /v1/projects/{id}/platforms/imessage/assignments` returned 201. Assignment `pho_asg_01m562efr8e8g8pc3qtjvbcmre`. Shared-pool number `+16285024649`. |
| Ping/reply | Inbound plain text `Ping` received at 2026-10-17T23:19:28Z as `pho_msg_698qe8a1b9hbzsqdkkf0w9bf5b` in direct space `pho_spc_0nhxpaja9ngpfvaj6eevmkcmd2`. A threaded reply returned 409 `SPACE_NOT_SENDABLE`. A normal message in that space, `pho_msg_40ncpnpd8cg1vrr2x6x5g26vy5`, was accepted and later read back with status `delivered` at 2026-10-17T23:20:51Z. |
| Sticker media | Not sent. No bytes, media ID, timestamp, or direction were observed. |
| Private explanation | Not sent. |

The live iMessage setup page states that shared iMessage is one to one: each person is paired with a line from the project pool. A dedicated iMessage number is the option that includes group chats, cold outreach, SMS/RCS fallback, and calls. That option is on the Messaging Business plan, at least $250 a month, and was not purchased.

The beta iMessage walkthrough also says a shared assignment supports direct conversations, not group chats: https://photon.codes/docs/beta/get-started/imessage

The beta documentation index has no sticker page. Native sticker support remains unverified.

## Spectrum fallback

The earlier dashboard at https://app.photon.codes is Spectrum, not Photon 2.0 beta.

| Item | Observed status |
| --- | --- |
| Project | `lahacksai`, Free, `9c35348c-9428-4dad-8a2c-b1eade874bce` |
| Platforms | 0 of 3 connected |
| iMessage | Shared, no assigned number, needs attention |
| Users | 0 of 10 on Free |
| Account phone | Empty. Getting started reported `account_phone_missing`. |
| WhatsApp | Listed, not connected. Meta signup was not started. |
| Telegram | Listed as a built-in provider that needs a bot token. No token is configured. |

No Spectrum message, sticker, or private reply was sent. Spectrum is not evidence of beta sticker or group behavior.

## Check

The shared line received one inbound text and delivered one outbound text in the same direct space. Sticker media and a private explanation remain untested.

## Integration follow-up: later issue evidence

This report above is the original branch checkpoint. Later [issue #2 text/explanation evidence](https://github.com/ja-dens/lahacksai/issues/2#issuecomment-6243175043) records a fixed explanation read back with provider status delivered; that is not visual phone receipt. The [native-sticker follow-up](https://github.com/ja-dens/lahacksai/issues/2#issuecomment-6243333423) says the phone showed a sticker delivered but repeated API reads through 2026-10-17T23:48:27Z still returned three text messages and zero attachments. Native sticker input is therefore blocked, not a completed integration.

The integration target is now an explicit image-attachment fallback: send a
static PNG/JPEG/WebP from the enrolled sender using the iMessage photo button.
This is not a claim that native sticker bubbles work. Authenticated local polling
was observed to read two existing received text messages on October 17, 2026;
no image attachment or model call was present in that smoke test.

The integration repair performed no new live Photon checks. The synthetic adapter/demo checks verify local behavior only. Real sticker event/media evidence and observed phone receipt are still needed.
