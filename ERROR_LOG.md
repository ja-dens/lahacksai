# Planning and setup errors

## 2026-10-17: GitHub access routes differed

What happened: the GitHub command-line tool was absent, and the in-app browser was signed out, even though Git could clone the private target repository and its push dry run succeeded.

Why: Git, the browser, and installed integrations use separate access paths.

Correction: use authenticated Git for the review branch and a repository-scoped GitHub Actions token for planning item publication. Verify actual results through a committed publication report. Do not treat clone access alone as proof of issue or PR access.

Prevention: check each required operation independently and record partial publication failures rather than claiming all items were created.

## 2026-10-17: integration discovery parameter mismatch

What happened: the first GitHub plugin discovery request used an unsupported plural parameter and failed validation.

Why: the callable tool's required argument was singular.

Correction: retry with the required argument; discovery then succeeded. No repository data was changed by the failed request.

Prevention: use the returned schema-validation information to correct a read-only request before continuing.

## 2026-10-17: optional YAML parser was not bundled

What happened: local YAML verification could not load the Node yaml module.

Why: the bundled Node runtime did not include that optional package.

Correction: use the system Ruby YAML parser for the owned workflow/form files and account for its YAML 1.1 handling of the on key. Keep the publisher itself dependency-free.

Prevention: check tool availability before relying on optional packages and make verification commands stop on a failed check.

## 2026-10-17: repository blocked Actions-created pull requests

What happened: issue and milestone publication succeeded, but the workflow's draft PR request returned HTTP 403: GitHub Actions is not permitted to create or approve pull requests.

Why: this repository's Actions policy does not allow that operation. Contents and issue access do not establish permission to create PRs as the Actions app.

Status and handling: eight issues, two milestones, and the review branch were published. The report includes the warning and compare link. No PR was created, main was left unchanged, and no repository setting was altered. PR creation remains available through a separately authenticated user or authorized integration.

Prevention: verify each external operation separately and keep optional PR creation failure from discarding successfully published planning items.
