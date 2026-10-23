---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance (Vercel). Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with the Web Interface Guidelines.

## How It Works

1. Read the rules in [guidelines.md](guidelines.md), in this folder
2. Read the specified files (or ask the user for files or a pattern)
3. Check the files against all rules in the guidelines
4. Output findings in the terse `file:line` format the guidelines describe

## Adapting to this project

The guidelines are written with React and Tailwind in mind. In this project (Django templates + Bootstrap 5.3):
- `onClick`/`onKeyDown`, hydration, `useState`, `<Link>`, `virtua`/`nuqs` → the equivalent rule for HTML forms and links, or skip it.
- `focus-visible:ring-*` → Bootstrap's own focus styles; flag only CSS in `static/css/app.css` that removes them.
- `Intl.*` for dates and numbers → Django's localization (`|date`, `|floatformat`, `LANGUAGE_CODE = "ro"`).
- "Title Case" and the English copy rules do not apply. Interface text is Romanian, in sentence case, following `ui-conventions`.

Where the guidelines and `ui-conventions` disagree, `ui-conventions` wins.

## Source

`guidelines.md` is a local snapshot of `command.md` from https://github.com/vercel-labs/web-interface-guidelines (MIT, see LICENSE), commit `434b7f9` (2026-10-05). The original skill fetched it from the internet on every run. We keep a copy so the instructions cannot change without review. To update it, download the new version, read it, and replace the file.
