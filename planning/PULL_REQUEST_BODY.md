## Summary

Establish the private sticker interpreter's implementation plan and independent three-person ownership. Add a repository workflow that publishes the task backlog, labels, and milestones from versioned planning files.

## Features

- A narrow MVP, roadmap, interfaces, ownership, and reusable work requests.
- Eight task definitions with dependencies and acceptance evidence.
- Issue and pull-request templates, synthetic text input, and credential placeholders.
- A tested planning publisher that preserves human issue content and records actual published links.

## Jac Usage

No application source is implemented in this change. Repository automation uses Node.js because it runs on GitHub Actions and calls the GitHub REST API without application dependencies. The implementation plan places important core behavior in Jac and retains the at least 40% Jac application-source requirement.

## Testing

- Publisher test suite: 11 tests passed, including reruns, lost responses, human edits, assignments, and PR restrictions.
- Dry run: validated eight issues, eight labels, two milestones, and dependencies with zero external writes.
- Workflow/form YAML, local Markdown links, and whitespace checks passed locally.
- The publication report records actual remote results. These checks do not establish Photon or model functionality.

## Known Issues

Actual Photon project/line access, native sticker-format support, private delivery, model access/budget, and deployment remain unverified. Usernames have not been supplied. GitHub repository settings may prevent automatic draft PR creation; the publisher records that limitation without changing settings.
