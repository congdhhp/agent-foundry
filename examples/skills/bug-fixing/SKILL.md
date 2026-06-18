# Bug Fixing Skill

## Purpose

Modify code safely and verify the result with tests or equivalent checks.

## When to use

Use this skill when a user asks to fix a bug, repair failing tests, change code behavior or prepare a focused patch.

## Workflow

1. Understand the task.
2. Read relevant files.
3. Plan a minimal patch.
4. Apply the patch only through workspace capabilities.
5. Run verification if policy allows or approval is granted.
6. Summarize changed files, tests and remaining risks.

## Required capabilities

- file.read@1.0
- file.patch@1.0
- shell.run@1.0
- git.diff@1.0

## Evidence requirements

- File reads and diffs must create evidence.
- Verification commands must create evidence.

## Safety constraints

- Do not run destructive commands.
- Do not install dependencies or access the network without approval.
- Do not write outside the authorized workspace.

