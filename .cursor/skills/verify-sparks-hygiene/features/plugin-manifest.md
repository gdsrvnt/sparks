# Plugin manifest

Cursor loads the plugin from `.cursor-plugin/plugin.json`, and discovers skills from `skills/*/SKILL.md` when the manifest has no `skills` key.

## Sub-features

- `manifest-parse`: valid JSON object.
- `manifest-fields`: kebab-case `name`, semver `version`, https `homepage`/`repository`; `description`, `version`, and `license` present (`WARN` if missing).
- `manifest-paths`: `logo`, `skills`, `rules`, `agents`, `commands`, `hooks`, and `mcpServers` paths exist inside the repo.
- `skill-frontmatter`: every discovered `SKILL.md` has frontmatter whose `name` matches its directory, plus a `description`.

## How to get to it (user POV)

- Cursor: loading the plugin locally or from the marketplace reads this manifest and lists the skills.

## Driving it with check-sparks-hygiene

- `check-sparks-hygiene run --only manifest`. `PASS`, with a note line `default skill discovery: N skills/*/SKILL.md` that matches `ls skills/*/SKILL.md | wc -l`.
- Negative proof: in a throwaway clone, set `"logo": "assets/logo.png"` and commit. The check reports `FAIL logo -> assets/logo.png does not exist`.

## Gotchas

- The script does not validate against an official Cursor schema. It checks the fields and paths that break loading or the listing.
