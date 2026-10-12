# Plugin submission review

Reviewed `.cursor-plugin/plugin.json` and the repository layout for a single-plugin Cursor package named `sparks`. Manifest checked with `python3 -m json.tool` and against the Cursor plugin schema (`https://cursor.com/schemas/cursor-plugin/plugin.json`).

## Pass/fail by section

| Section | Result |
| --- | --- |
| Manifest validity | Pass |
| Component discoverability | Pass |
| Component metadata | Pass |
| Repository integration | Pass |
| Documentation | Pass |

Marketplace submission is still blocked by deferred items below. The scaffold itself is consistent.

## Findings

### 1. Manifest omitted recommended metadata

**Finding.** The first `plugin.json` had `name`, `version`, `description`, `author`, and `keywords` only. `license` was absent while `README.md` already stated the SPDX identifier `UNLICENSED`. There was no `LICENSE` file, no homepage, and no repository URL.

**Fix.** Manifest now includes `displayName`, `license` (`UNLICENSED`), `publisher`, `homepage`, `repository`, `category`, and `tags`. `LICENSE` repeats the same unlicensed statement. `version` stays `0.0.0`, which matches the semver pattern. `name` is `sparks` (lowercase, starts and ends with an alphanumeric). Author remains `gdsrvnt`, matching the GitHub org. No absolute paths or `..` segments. Schema validation passed. No custom component paths were added, because default folder discovery is enough.

### 2. README did not explain plugin install or components

**Finding.** `README.md` described the spark format and did not state how to install the Cursor plugin or which components the package contains.

**Fix.** Added a Cursor plugin section with purpose, marketplace and local install steps, and a component table. The existing format essay is unchanged.

### 3. Plugin package version and changelog `1.0.0` looked like one version

**Finding.** `CHANGELOG.md` recorded format release `1.0.0`. The plugin manifest is `0.0.0` because this package is a scaffold.

**Fix.** Added an Unreleased changelog entry that separates the plugin package version from the spark format release.

### 4. Open-source license required for the marketplace

**Finding.** Cursor marketplace review expects plugins to be open source. This repository states that a license has not been chosen and that the SPDX identifier is `UNLICENSED`. No license owner is named.

**Deferred.** Choosing MIT or another OSI license would grant rights the repository has not granted. `license` is set to `UNLICENSED` so the manifest, `LICENSE`, and README agree. Replace that identifier only when an owner chooses a license.

### 5. No plugin skills are shipped

**Finding.** `skills/` contains only `.gitkeep`. There is no `skills/*/SKILL.md`, so the plugin publishes no skills. Rules, agents, commands, hooks, and `mcp.json` are absent. The repo root `SKILL.md` has `name` and `description` frontmatter, and `.cursor/skills/` holds learning playbooks, but those paths are existing project source. With a `skills/` directory present, Cursor discovers plugin skills from that directory and does not treat the root `SKILL.md` as the plugin skill.

**Deferred.** Skill packages come later. This review does not invent skill text and does not move existing skill files into `skills/`. Empty `skills/` is the reserved discovery path. Frontmatter checks are vacuous until those files exist.

### 6. No logo

**Finding.** The manifest has no `logo` field, and the repo has no logo asset.

**Deferred.** A logo is optional. Omitting the field avoids a path that does not exist.

### 7. Single-plugin repository has no marketplace manifest

**Finding.** There is no `.cursor-plugin/marketplace.json`.

**Deferred.** This repo is one plugin at the repository root. A marketplace manifest is for multi-plugin repositories. Adding one would point `source` at the same tree the root manifest already describes.

### 8. Not exercised inside Cursor

**Finding.** Schema and JSON parsing were checked in this environment. Cursor was not reloaded, and the plugin was not installed from Customize.

**Deferred.** Local load is: copy the plugin to `~/.cursor/plugins/local/sparks`, reload Cursor, and confirm it in Customize. A symlink that points outside that folder is not loaded.

## Prioritized fix list

1. Done: complete manifest metadata and align `license` with `LICENSE` and README.
2. Done: document purpose, installation, and component coverage in README.
3. Done: record the `0.0.0` plugin package version in the changelog.
4. Later: choose an open-source license and set `license` to that SPDX id.
5. Later: add real `skills/<name>/SKILL.md` files (and any rules, agents, commands, hooks, or MCP config) with required frontmatter.
6. Later: optional logo committed in-repo and referenced by a relative path.
7. Later: install the local copy in Cursor before submitting.

## Submission recommendation

Do not submit to the Cursor Marketplace yet. The manifest parses, matches the schema, and the single-plugin layout is coherent. Submission should wait until an owner chooses an open-source license and the intended skills are in `skills/`.
