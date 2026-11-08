# SafeDelete — Brief Usability Questionnaire

Complete this after trying SafeDelete. Takes approximately 2 minutes. Responses
are voluntary; do not include your name or personal file paths.

## Before answering

Using only disposable practice files, try to:

1. Find help and identify the delete and restore commands.
2. Delete a practice file with a recovery window of 10 minutes.
3. List quarantined items and find the file's ID and remaining recovery time.
4. Restore the file and check that it returned to its original location.
5. Start another deletion and cancel at the confirmation prompt.

The evaluator should prepare the practice files and a separate quarantine on the
same filesystem. Use the Quick Reference Guide as needed. Skip any task you cannot
complete and record it below. Do not test permanent purge on personal data.

**Optional context:**

- Operating system / shell: ____________________
- Terminal experience: ☐ Beginner ☐ Occasional user ☐ Frequent user
- Tasks completed without another person's help: ____ / 5

## Rate your experience

**1 = Strongly disagree · 2 = Disagree · 3 = Neither agree nor disagree ·
4 = Agree · 5 = Strongly agree · N/A = Not experienced**

Choose one response per row.

| Statement | 1 | 2 | 3 | 4 | 5 | N/A |
| --- | --- | --- | --- | --- | --- | --- |
| 1. It was easy to find the command I needed. | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2. The confirmation prompt made the consequences of deletion clear. | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3. I could tell whether an operation had succeeded or been cancelled. | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4. It was clear how much time remained to restore my file. | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5. Restoring my deleted file was easy. | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6. Overall, SafeDelete was easy to use. | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

## Two short questions

1. What was the most confusing or difficult step?

   ________________________________________________________________

2. What one change would most improve your experience?

   ________________________________________________________________

## For the student evaluator

Report the number of participants, task completion counts, and each item's mean
rating with its number of valid responses. Exclude N/A and unanswered items from
means. Keep ratings and observed task completion separate: perceived ease and
successful use can differ. Group anonymous comments into recurring issues and
propose one concrete improvement for a PR.

Items 1–5 address discoverability, error prevention, feedback, visibility of
status, and user control; item 6 captures overall perceived ease. Compare the
same items and tasks before and after a change, noting terminal experience and
platform differences. A small classroom sample provides exploratory feedback.

This is a custom classroom questionnaire, not a validated scale such as SUS.
Do not label its results a SUS score, apply SUS benchmarks, or treat high ratings
as evidence of filesystem safety.
