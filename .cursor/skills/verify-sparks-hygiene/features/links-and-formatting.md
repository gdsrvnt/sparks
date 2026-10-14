# Links and formatting

Docs should navigate and diff cleanly on GitHub.

## Sub-features

- `relative-links`: inline links, images, `<a href>`/`<img src>`, and reference definitions outside code spans and fences resolve to a tracked file. A missing `#anchor` (GitHub slug rules) is `WARN`.
- `whitespace`: no trailing spaces or tabs, exactly one final newline, no CRLF.
- `json-valid`: every tracked `*.json` parses.
- `exec-bit`: files with a `#!` shebang are mode `100755` in git.
- `vendored`: findings in paths that `THIRD_PARTY_NOTICES.md` lists as copied unchanged are `WARN` and marked `(vendored, copied unchanged)`.

## How to get to it (user POV)

- Clicking links in README and skill docs on GitHub. Reading diffs in pull requests.

## Driving it with check-sparks-hygiene

- `check-sparks-hygiene run --only links,format`.
- Negative proof: in a throwaway clone, commit `docs/x.md` with `[bad](nope.md)` and a trailing space, plus `x.json` containing `{bad` and a non-executable `s.sh` with a shebang. You get four `FAIL` lines.

## Gotchas

- Markdown hard line breaks (two trailing spaces) count as trailing whitespace. Use a backslash break or a new paragraph.
- Template placeholders such as `[PR #123](url)` in vendored prompts show up as broken links (`WARN`).
