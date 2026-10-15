# Changelog

## 2026-10-14
- Added check_answer.py: judge runs it on every proposal. Answers are quotes plus [bracketed] notes only (no attributions); quotes must match the local reference dir; type K answers may be a single link or path.
- Unified spark-handshake into sparks-ingest. Full handshake protocol (schema, protocol, streak rule, player responsibilities, examples, done condition) now lives in the main body. Removed separate spark-handshake skill. Invocation form unchanged: play the role of <player|judge> with <agent> to ingest <source> into <repo>.
