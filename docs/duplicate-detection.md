# Duplicate flagging: proposed evolution

Status: design suggestions from Sol for [#21](https://github.com/gdsrvnt/sparks/issues/21), not implemented. The CLI currently replaces only by exact decoded question in the target file. Question is the replacement key; the stored content id changes with the answer or type.

## Keep matching and flagging separate

Fuzzy similarity should produce review candidates, never choose a record to overwrite. Preserve verbatim questions and answers. Keep exact replacement deterministic and independent of warning thresholds. Cross-file matches should only be reported, not silently moved or replaced: local directory context can make the same question mean different things.

## A programmatic pipeline, no model required

1. **Candidate retrieval:** derive comparison-only forms with Unicode NFC, case folding, and collapsed whitespace. Combine character trigrams (good for typos) with token overlap (good for reordered wording). For small files, a linear scan is enough; add an inverted index only when measured size warrants it. Do not write normalized forms back to the records.
2. **Additional logic:** inspect differences in negation (`not`, `never`, `without`), numbers/versions, quoted identifiers, paths, URLs, and named tools. These can distinguish almost identical questions: “Why use Redis?” and “Why not use Redis?” must not become a high-confidence duplicate merely because their edit distance is small. Require sufficient shared meaningful tokens; short generic questions need stronger evidence.
3. **Supporting evidence:** same type boosts confidence, but different types must remain eligible (an entry may be reclassified). Similar answers support a likely duplicate; a different answer should be reported as a possible revision/conflict, not eliminate the candidate. Answer-only overlap is weak evidence: unrelated questions can legitimately share an answer.
4. **Explain and rank:** deterministic ordering by score then file and array position; emit a small top-k set with the original question, type, location, content id, and reasons such as “same normalized question; different version token.” Avoid presenting an uncalibrated score as a probability.

## Safe CLI rollout

Start with a read-only duplicate audit and fixtures containing labeled duplicates, revisions, and hard negatives. Tune thresholds against precision/recall, prioritizing precision so warnings do not become noise. Include Unicode, typos, negation, version changes, reordered clauses, cross-type entries, and similar questions from different directories. Snapshot candidate ordering and explanations for deterministic regressions.

Next, optionally show advisory candidates on stderr before a non-exact add; keep stdout and successful exit status stable for scripts. Offer structured audit output and an explicit strict mode if automation needs to refuse suspicious additions. Never require an interactive prompt in the default add path. Any future explicit replacement of a non-exact question should identify a file/record and check the old content hash to reject stale selections; the hash is a revision guard, not a stable identity.

This lexical approach will miss some paraphrases. Measure those misses before adding heavier mechanisms; flagging uncertain cases is safer than automatic deduplication.
