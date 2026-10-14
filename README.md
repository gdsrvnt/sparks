# sparks

**Your project's intent, in your own words, checked on every PR.**

sparks stores what a project needs to know as question-and-answer pairs, written in the verbatim prose of the people who own it. Agents read them before they work and verify against them before they ship.

## Why sparks

- **Your voice, not a summary.** Context stays in human prose. Nothing is paraphrased away.
- **Rules that carry their reasons.** Every answer is bound to the question that gave rise to it.
- **Verification built in.** `spark-verification` checks a PR or branch against every `sparks.json` that applies.
- **Any harness.** A Cursor plugin, a CLI, and pi agents launched by persona.

## Get started

Install **sparks** from Cursor's Customize panel. To run it locally before it is published, copy this repository into `~/.cursor/plugins/local/sparks` (keep `.cursor-plugin/`, `skills/`, `rules/`, `docs/`, `defaults/`, and `pi/`), then reload Cursor.

Add your first spark with the CLI ([uv](https://docs.astral.sh/uv/) installs its one dependency):

```sh
cd path/to/project
path/to/sparks/bin/sparks add --json '{"type":"s","question":"What is spark?","answer":"spark is a way of gathering, maintaining, and structuring context about a project in Q&A pairs."}'
# added <id> to sparks.json
```

Then let sparks interview you: `/sparks-discuss`.

## How it works

1. **Capture.** `sparks-discuss`, `study`, and `spark-voice` draw intent out of you, typed or spoken, and save it verbatim.
2. **Store.** Each `sparks.json` holds sparks of five types: **S**tack, **P**rocesses, **A**udience, **R**econnaissance, and **K**nowledge sources. They apply project-wide by default.
3. **Launch.** `sparks agent spawn <persona>` starts a pi agent in herdr with its model, tools, and skills set, falling back across models on API errors.
4. **Verify.** Every agent checks its diff against the sparks that apply and quotes any it breaks.

## Learn more

- [Philosophy](philosophy/): why verbatim prose, and where sparks is going. The full CLI reference and spark types live in [philosophy/README.md](philosophy/README.md).
- [Docs](docs/): the [file format](docs/format.md) and design notes.
- [Contributing](CONTRIBUTING.md): every issue and open PR needs exactly one priority label: `low`, `medium`, `high`, or `urgent`. Pull request text: [AGENTS.md](AGENTS.md).

## Credits

- [Lauren Tan (@poteto)](https://github.com/poteto), who wrote the pstack skills in this plugin: `ketchup`, `how`, `why`, `bro`, `create-verification-skill`, and `maintain-verification-skill`. Those last two are bundled for direct use; `spark-verification` is a separate read-only skill that checks a PR or branch against `sparks.json`.
- [Matt Pocock (@mattpocock)](https://github.com/mattpocock), whose `grilling` skill is the basis for the grilling core of `sparks-discuss`, whose `domain-modeling` skill is the basis for `sparks-domain`, and whose `to-spec` skill is the basis for `sparks-postcall`.
- [Yann Collet (@Cyan4973)](https://github.com/Cyan4973), who created [xxHash](https://github.com/Cyan4973/xxHash). `spark_hash.py` is a Python port of its XXH64 algorithm.
## License

MIT. Copyright (c) 2026 gdsrvnt. See `LICENSE`. That license covers this project's own work.

Third-party skills keep their authors' copyright and MIT licenses. Lauren Tan's skills are MIT, Copyright (c) 2026 Lauren Tan. `create-verification-skill` and `maintain-verification-skill` each carry her license in a `LICENSE` file next to their `SKILL.md`, and her other skills share `skills/LICENSE-poteto`. Matt Pocock's license is in `skills/LICENSE-mattpocock`, and `sparks-domain` and `sparks-postcall` each also carry it in a `LICENSE` file next to their `SKILL.md`. HumanLayer's license is in `skills/LICENSE-humanlayer`. `spark_hash.py` ports XXH64 from Yann Collet's xxHash, BSD 2-Clause, Copyright (c) 2012-2021 Yann Collet; its license is in `LICENSE-xxhash`. See `THIRD_PARTY_NOTICES.md`.
