# Licensing and notices

A reader checks who owns the code and under what terms, and where the third-party skills came from. `LICENSE`, the README `## License` and `## Credits` sections, `THIRD_PARTY_NOTICES.md`, `skills/LICENSE-*`, `.cursor-plugin/plugin.json` (`license`, `author`), and `.github/upstreams.json` must tell the same story.

## Sub-features

- `docs-present`: README, LICENSE, and notices are tracked and non-empty.
- `license-agree`: the LICENSE kind and copyright holder match `plugin.json` and the README License section, which links both files.
- `notices-paths`: every path the notices name exists, and every `skills/LICENSE-*` is referenced.
- `skills-listed`: every `skills/*/SKILL.md` directory is named in README.
- `upstreams-noticed`: every skill tracked in `.github/upstreams.json` has a notice entry with the same pinned commit.

## How to get to it (user POV)

- GitHub repo page: the License sidebar (from `LICENSE`) and the README sections.
- Marketplace listing: `license` and `author` from `plugin.json`.

## Driving it with check-sparks-hygiene

- `check-sparks-hygiene run --only docs,notices`. `PASS` on both, or `WARN` lines that name a skill without a notice.
- Negative proof: in a throwaway clone, change `plugin.json` `license` to `Apache-2.0` and commit. `docs` reports `FAIL plugin.json license 'Apache-2.0' != LICENSE 'MIT'`.

## Gotchas

- A skill that is adapted rather than copied (for example `grill-me`, which README credits as based on an upstream skill) still shows as `WARN` until the notices say whether it needs an entry. That is an owner decision.
- `.claude/skills/*` carry their own `LICENSE`/`NOTICE` files and are not required in `THIRD_PARTY_NOTICES.md`, which covers what the plugin ships.
