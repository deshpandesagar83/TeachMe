#!/usr/bin/env python3
"""Build a questions.md + answer_key.md pair from a draft JSON exam.

Draft JSON shape:
[
  {"question": str, "timestamp": str (optional), "options": [correct, wrong1, wrong2, ...]},
  ...
]
The first element of "options" is always the correct answer in the draft;
this script shuffles options per-question and balances which letter ends
up correct across the whole exam, so the answer distribution isn't
predictable or dominated by A/B.
"""
import json
import random
import string
import sys


def assign_letters(n, k, max_run=2, max_tries=2000):
    """Return a list of n letter-indices (0..k-1) that is roughly balanced
    across k letters, has no run longer than max_run, and avoids a repeated
    pair recurring within a short window (e.g. A,A,B,A,A)."""
    base = n // k
    rem = n % k
    counts = [base + (1 if i < rem else 0) for i in range(k)]

    for _ in range(max_tries):
        pool = []
        for letter_idx, c in enumerate(counts):
            pool.extend([letter_idx] * c)
        random.shuffle(pool)

        if _is_acceptable(pool, max_run):
            return pool

    # Fall back to the last generated pool even if imperfect, but tell caller.
    sys.stderr.write(
        "warning: could not satisfy run/pattern constraints within max_tries; "
        "using best-effort shuffle\n"
    )
    return pool


def _is_acceptable(seq, max_run):
    n = len(seq)
    # No run longer than max_run.
    run_len = 1
    for i in range(1, n):
        if seq[i] == seq[i - 1]:
            run_len += 1
            if run_len > max_run:
                return False
        else:
            run_len = 1

    # Avoid a repeated-pair pattern recurring too close together, e.g.
    # A,A,B,A,A (same letter forms a run-of-2 twice within a 5-window).
    for i in range(n - 4):
        window = seq[i:i + 5]
        if window[0] == window[1] and window[3] == window[4] and window[0] == window[3]:
            return False

    return True


def main():
    if len(sys.argv) != 4:
        sys.stderr.write(
            "usage: build_exam.py <draft.json> <questions_out.md> <answer_key_out.md>\n"
        )
        sys.exit(1)

    draft_path, questions_out, answers_out = sys.argv[1:4]

    with open(draft_path, "r", encoding="utf-8") as f:
        draft = json.load(f)

    if len(draft) < 100:
        sys.stderr.write(
            f"warning: draft has only {len(draft)} questions (minimum requested is 100)\n"
        )

    # Group by option-count so balancing is correct even if a question has
    # a different number of options (e.g. true/false) than the rest.
    by_k = {}
    for idx, q in enumerate(draft):
        k = len(q["options"])
        by_k.setdefault(k, []).append(idx)

    correct_letter_idx = [None] * len(draft)
    for k, indices in by_k.items():
        letters_for_group = assign_letters(len(indices), k)
        for pos, draft_idx in enumerate(indices):
            correct_letter_idx[draft_idx] = letters_for_group[pos]

    letters = string.ascii_uppercase

    q_lines = []
    a_lines = []

    for i, q in enumerate(draft, start=1):
        options = q["options"]
        k = len(options)
        correct_text = options[0]
        wrong_texts = options[1:]

        target_letter = correct_letter_idx[i - 1]

        wrong_slots = [j for j in range(k) if j != target_letter]
        shuffled_wrong = wrong_texts[:]
        random.shuffle(shuffled_wrong)

        final_options = [None] * k
        final_options[target_letter] = correct_text
        for slot, text in zip(wrong_slots, shuffled_wrong):
            final_options[slot] = text

        q_lines.append(f"**{i}. {q['question']}**")
        ts = q.get("timestamp")
        if ts:
            q_lines.append(f"*({ts})*")
        for j, text in enumerate(final_options):
            q_lines.append(f"{letters[j]}. {text}")
        q_lines.append("")

        a_lines.append(f"{i}. {letters[target_letter]}")

    with open(questions_out, "w", encoding="utf-8") as f:
        f.write("\n".join(q_lines).rstrip() + "\n")

    with open(answers_out, "w", encoding="utf-8") as f:
        f.write("\n".join(a_lines).rstrip() + "\n")

    # Report distribution so the caller can sanity-check without re-parsing.
    dist = {}
    for idx in correct_letter_idx:
        dist[letters[idx]] = dist.get(letters[idx], 0) + 1
    sys.stderr.write(f"wrote {len(draft)} questions. letter distribution: {dist}\n")


if __name__ == "__main__":
    main()
