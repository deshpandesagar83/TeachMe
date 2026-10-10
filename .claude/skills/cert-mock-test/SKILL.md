---
name: cert-mock-test
description: Generate a mock certification exam when the user types a certification name or code (e.g. "AWS SAA-C03", "PMP", "CKA", "CompTIA Security+") expecting a practice test. Produces a questions-only .md file and a matching answer-key .md file, 100+ items each, using latest exam info with per-question timestamps, and a balanced/non-predictable option-letter distribution.
---

# Certification mock test generator

Triggered when the user types a certification name or code in chat and wants a practice test.

## Workflow

1. **Research first.** Before writing any questions, search the web for the current version of this certification's exam (objectives, domains, recent changes, retirement/replacement of exam codes). Prefer the most recent information available relative to today's date — if the exam was recently updated, write questions against the current version, not an outdated one.

2. **Draft the raw questions.** Write at least 100 unique questions to a scratch JSON file (use the project's scratchpad, not the two deliverable files) with this shape:

   ```json
   [
     {
       "question": "Full question text, including any code/config snippets.",
       "timestamp": "2026-10 (per AWS exam guide v7, effective 2026-09)",
       "options": ["<correct answer text>", "<wrong 1>", "<wrong 2>", "<wrong 3>"]
     }
   ]
   ```

   Rules while drafting:
   - The **correct option is always index 0** in this draft — the script below handles shuffling into a non-predictable letter.
   - Pull real variety from the chat context and the research in step 1; don't reuse question phrasing or scenarios across runs for the same cert. If prior mock tests for this cert exist in the working directory, skim their question file first and avoid repeating the same question.
   - `timestamp` should reflect how current the underlying fact is (exam version, doc date, service feature date) — not just today's date.
   - Keep each question self-contained. No explanations, no difficulty labels, no "Note:" asides — those are exactly the kind of extra text that leaks hints.

3. **Build the two deliverables with the script — do not hand-arrange options yourself.** Run:

   ```
   python .claude/skills/cert-mock-test/scripts/build_exam.py <draft.json> <Cert>-Questions.md <Cert>-AnswerKey.md
   ```

   This script:
   - Shuffles each question's options into A/B/C/D (or however many options it has).
   - Balances which letter holds the correct answer across the whole exam so no letter dominates.
   - Caps consecutive repeats of the same correct-letter at 2 in a row, and breaks up patterns where a repeated pair recurs too close together (e.g. avoids `A,A,B,A,A`), while still allowing things like `A,A,B,D,A`.
   - Writes the question file with **only** numbered questions + their options (plus the timestamp line) — nothing else.
   - Writes the matching answer key with **only** the numbered correct letter, in the same order.

   Do not manually reorder options after this step — the script's balancing is the point; hand-editing will reintroduce the bias the user explicitly asked to eliminate.

4. **Verify before handing off.** Open the answer key and confirm: no run of 3+ identical letters, and the letter counts are roughly even (within a couple of questions of n/4 each). If the script's retry budget couldn't satisfy the constraints (rare, only on very small option counts), it will say so — rerun it rather than fixing the file by hand.

5. Report the two filenames and a one-line summary (cert, question count, exam version/date the questions target). Don't paste the questions into chat.

## Notes

- Both deliverables are `.md` files, numbered identically, in the same order.
- The question file must never contain the answer key, explanations, or anything beyond question text + options — that's the hint-leak risk the user explicitly flagged.
- Re-running this for the same cert later in the conversation should produce a materially different set of 100+ questions, not a reshuffled copy of the same ones.
