# Secrets and privacy

Nothing in a tracked file should leak a credential, a personal email, or a path from someone's machine.

## Sub-features

- `secret-patterns`: GitHub, Anthropic, OpenAI-style, AWS, Google, and Slack tokens, private key blocks, bearer headers, and quoted assignments to `token`/`secret`/`password`/`api_key`.
- `emails`: any address other than `noreply@…`, `…@users.noreply.github.com`, or `example.com/org/net`. Output masks it (`b***@domain`).
- `home-paths`: `/home/<user>`, `/Users/<user>`, the root home directory, `C:\Users\<user>`, except the placeholders `user`, `username`, `me`, and `you`.
- `denylist`: terms from `--deny-file` or `$SPARKS_HYGIENE_DENYLIST`, matched case-insensitively and reported by index only.

## How to get to it (user POV)

- Anyone reading the public repository or its history on GitHub.

## Driving it with check-sparks-hygiene

- `check-sparks-hygiene run --only secrets --deny-file ~/private-terms.txt`.
- Negative proof: in a throwaway clone, commit a markdown line with a personal-looking address at a public mail domain, a path under `/home/` plus a made-up user name, and a fake `ghp_` token with 36 characters after the prefix. The check reports all three as `FAIL`, with the email masked. Do not write those values into this repository, because this check would flag them here too.

## Gotchas

- Only the current tree is scanned, not git history or commit metadata.
- Patterns are heuristics. A `FAIL` needs a human look before anyone rotates a key.
