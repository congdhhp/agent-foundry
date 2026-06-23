---
name: coding-workflow
description: Use when implementing code changes, debugging failures, reviewing local repositories, or verifying code with tests and lint.
---

# Coding Workflow

## Workflow

1. Understand the request and identify the smallest useful change.
2. Check repository state with `repo.status` before editing.
3. Build context with `repo.map`, `file.search`, and `file.read`.
4. Separate editable files from read-only context.
5. Prepare a minimal patch and apply it through `file.patch`.
6. If a patch fails, reread the target file, explain the mismatch, and retry with tighter context.
7. Run targeted `lint.run` and `test.run` commands where available.
8. Inspect `repo.diff` before the final answer.
9. Report changed files, verification results, evidence IDs, and remaining risks.

## Safety rules

- Do not edit files outside the active workspace.
- Do not edit secrets, generated output, vendored dependencies, or lock files unless the user explicitly asks.
- Do not use `shell.run`, `git.commit`, or `git.undo` without approval.
- Treat failed tests, failed lint, and failed patch application as evidence, not as noise.
- Never claim the code is complete unless verification has run or the reason it could not run is explicit.

## Output requirements

- `summary`: What changed or what is waiting for approval.
- `change_plan`: The intended edit sequence and scope.
- `changed_files`: Files edited or proposed for edit.
- `verification`: Tests, lint, and diff checks that ran.
- `evidence_refs`: Evidence IDs supporting important claims.
- `pending_approvals`: Any file, shell, or git actions waiting for approval.
