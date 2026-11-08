# Student contributions: HCI in the terminal

Improve SafeDelete by making one small interaction easier to understand, use, or
recover from. Choose a task below, or propose your own. Documentation and usability
studies are welcome contributions; you do not need to change Python code.

These are proposals, not promises that every feature will be accepted. Describe
your approach in an issue before starting a larger change. One focused improvement
per pull request (PR) makes review easier.

## Choose a task

Start with **HCI-01**, **HCI-02**, or **HCI-03** if this is your first PR.

### HCI-01 — A clearer first-use example · Starter

- [ ] Add a short “create → delete → list → restore” walkthrough to the Quick Reference Guide.

**Concept:** Nielsen’s help and documentation; Norman’s gulf of execution
(the gap between a goal and knowing what action to take).

**Done when:** A beginner can follow the example using a disposable file, knows
where to find the deletion ID, and sees what success looks like. Explain that
`ID` is a placeholder. Try the instructions with a classmate and fix one point
of confusion. Report the OS and shell used.

### HCI-02 — Explain the recovery deadline · Starter

- [ ] Improve help text so users understand the default recovery window and expiration.

**Concept:** Visibility of system status; Norman’s conceptual model.

**Done when:** Help clearly distinguishes quarantine, expiration, and permanent
purge. It says that undo ends at expiration, while automatic cleanup requires
explicit scheduling. Include the revised terminal output in the PR.

### HCI-03 — Make cancellation reassuring · Starter

- [ ] Improve the message shown when a user declines confirmation.

**Concept:** User control and freedom; feedback.

**Done when:** The message explains that the requested action was cancelled,
does not imply success, and gives one useful next step. Check cancellation for
delete, restore, and purge. Cancellation must leave the target and quarantine
unchanged. Keep the existing nonzero cancellation status.

### HCI-04 — Errors that suggest the next action · Small

- [ ] Improve one common error: missing path, restore conflict, busy quarantine, or expired ID.

**Concept:** Help users recognize, diagnose, and recover from errors; Norman’s
gulf of evaluation (understanding what happened).

**Done when:** The message states the problem in plain language and suggests a
specific, safe action. Show a before/after example and reproduce the error using
disposable files. Preserve the underlying error details and exit status.

### HCI-05 — A readable list of recoverable items · Medium

- [ ] Propose an opt-in `list --human` view with ID, escaped path, state, and time left.

**Concept:** Recognition rather than recall; visibility of system status.

**Done when:** Long paths, spaces, expired entries, and an empty quarantine have
readable output. Use words as well as any colors. Keep the default JSON-lines
output unchanged for scripts. Show a sample containing at least three states.

### HCI-06 — Confirmation that explains consequences · Small

- [ ] Improve deletion and purge prompts so users can predict the result before approving.

**Concept:** Error prevention; Norman’s feedforward (information about what an
action will do) and constraints.

**Done when:** Delete shows the intended path and recovery period; purge clearly
says the removal is permanent. Both explain how to cancel. Preserve exact `YES`
confirmation, escaped paths, and explicit `--yes` behavior. Do not add a default
“Yes” response.

### HCI-07 — Make output pacing discoverable · Small

- [ ] Explain the existing `SAFEDELETE_OUTPUT_DELAY` setting in CLI help.

**Concept:** Flexibility and efficiency of use; user control.

**Done when:** Users can discover the default delay, disable it, and adjust it
without reading source code. Show both paced and immediate usage. Piped output
must remain immediate and retain its existing format.

### HCI-08 — Easier installation troubleshooting · Small

- [ ] Improve one setup failure message or add a short troubleshooting example.

**Concept:** Help and documentation; consistency and standards.

**Done when:** A user can identify and resolve one concrete problem, such as
missing Python, a command absent from PATH, or an existing installation. Include
the relevant Linux/macOS and Bash/zsh distinction. Avoid changing shell startup
files or installing system packages without the user’s explicit choice.

### HCI-09 — A usability study with three participants · No code required

- [ ] Ask three consenting classmates to try the first-use workflow.

**Concept:** Usability evaluation; learnability; effectiveness and efficiency.

**Done when:** Submit a short report with the tasks, anonymous observations,
completion counts, and the three most useful improvements. Ask participants to
find help, delete a practice file, locate its ID, and restore it. Record where
they hesitate and whether they finish without hints; offer help if they get
stuck and note it. Do not include names, recordings, or personal file paths.
Treat the findings as exploratory, not proof about all users.

### HCI-10 — Consistent language across the interface · Starter

- [ ] Review help, prompts, and guides for confusing or inconsistent terms.

**Concept:** Consistency and standards; match between system and the real world.

**Done when:** Propose a small vocabulary for “quarantine,” “restore,” “expire,”
and “purge,” then fix a focused set of messages. Keep command names compatible.
Explain why “backup” can mislead users: quarantine moves the original item and
does not create a separate copy. Include examples of the revised wording.

### HCI-11 — Color that helps users understand prompts · Small

- [ ] Add consistent colors to confirmation prompts, status messages, and errors.

**Concept:** Visibility of system status; consistency; accessible feedback.

**Done when:**

- Use a small, consistent palette: for example, green for success, yellow for
  confirmation or caution, and red for errors or permanent-removal warnings.
- Keep explicit words such as “Restored,” “Warning,” and “Error.” Users must
  understand every message without distinguishing colors.
- Apply color only when the destination stream is a terminal. Respect `NO_COLOR`
  when set, and disable color for `TERM=dumb`.
- Preserve plain output when piped or captured, including deletion IDs and JSON
  records. Check stdout and stderr independently.
- Reset terminal styling after each message, including when a prompt is cancelled.
- Show examples with color enabled and disabled. Check readability on light and
  dark backgrounds and explain the chosen palette in the PR.

Keep exact `YES` confirmation and existing safety checks. Color should clarify
the action and its consequences without changing what approval means.

## Keep the safety contract

Every interaction change must preserve these behaviors:

- Never overwrite a restore destination or bypass protected-path and symlink checks.
- Never shorten a recovery period or trigger permanent deletion implicitly.
- Keep explicit confirmation and the deliberate `--yes` option.
- Keep stdout usable by scripts: delete returns its ID, and default list emits JSON lines.
- Send explanatory messages and errors to stderr; escape user-controlled paths.
- Do not invent progress percentages for an atomic move. Report actual status.
- Preserve Linux/macOS support and compatibility with Bash 3.2+ and Python 3.11+.

Discuss a proposed change to any of these behaviors before implementing it.

## Make your first pull request

1. Read [the Quick Reference Guide](QUICK_REFERENCE.md) and choose one task.
2. Fork the repository on GitHub, clone your fork, and enter the project folder.
3. Create a branch, for example `git switch -c hci-03-cancel-feedback`.
4. Make a small change. Try it with disposable practice files in a private test
   directory, using a separate `--root` on the same filesystem. Avoid important
   files and shared classroom data. On macOS, avoid symlink parents such as `/tmp`;
   use its physical path `/private/tmp` instead.
5. For code changes, run `./tests/run-native.sh` as a regular user. Add or update
   a focused test when behavior changes. For documentation-only changes, check
   links and follow your instructions literally; no new automated test is needed.
6. Review `git diff`, commit only your intended files, and push your branch.
7. Open a PR from your fork to the original repository and use the template below.

When testing the downloaded source, use `./bin/safedelete`, so you do not
accidentally test an older installed copy. Never commit quarantined payloads,
private paths, generated caches, or personal test data. Report the platform you
actually tested; do not claim Linux and macOS coverage from one machine.

## Copy this into your PR description

```markdown
Task: HCI-__

Problem:
Who gets confused or stuck, and at which step?

Change:
What does the user see or do differently?

HCI connection:
Name one principle and explain how this change supports it.

Before / after:
Include a short terminal example or the revised instructions.

Validation:
OS and shell:
Commands or usability tasks tried:
Observed result:
Any limitations or checks still needed:
```

A strong contribution connects a real usability problem to an observable
improvement. Small, clear changes with evidence are welcome.
