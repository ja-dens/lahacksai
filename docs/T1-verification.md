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
| Phone | Verification was offered and skipped. No phone number is on the account. |
| iMessage line | Not assigned. The page asks for a sender phone number or iMessage email before a shared-pool number can be assigned. |
| Ping/reply | Not run. No message was sent or received. |
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

There is no passing command. The blocked check is the beta ping walkthrough above. It requires `PHOTON_TEST_SENDER` and an assigned shared line, neither of which exists.
