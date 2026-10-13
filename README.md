# Sparks

> Spark is a way of engineering the context of a project or a repository in such a fashion that makes the information have three things that current approaches to context management don't have.

## Purpose

the purpose of the sparks is simple and explicit: They are ammunition for spark-verification, which checks a PR or branch's changed files against the sparks.json answers that apply to those files' directories. the thesis of spark is that if verification against human intent is the highest leverage asset in the age of orchestration, then the default best move on the board is to invest in the pipelines that distill that intent in almost-real time as agents run.

## Cursor plugin

This repository is a single Cursor plugin. The manifest is `.cursor-plugin/plugin.json` (`name`: `sparks`, package version `0.1.0`).

Sparks gathers, maintains, and structures project context as question-and-answer pairs. It is built for Grok Bot and usable in any harness.

### Installation

After the plugin is listed, install it from Customize: find Sparks and choose Install.

To load this repository locally before it is published:

1. Copy this plugin into `~/.cursor/plugins/local/sparks`, including `.cursor-plugin/plugin.json` and the component directories.
2. Reload Cursor.
3. Open Customize and confirm the plugin is present.

Cursor loads local plugins from that folder when local plugin imports are allowed. Submit the public repository at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) when it is ready for review.

### Components

Discovery uses the default folders. The manifest does not set custom component paths.

| Component | Path | Status |
| --- | --- | --- |
| Skills | `skills/` | `sparks-discuss`, `sparks-domain`, `sparks-postcall`, `spark-voice`, `spark-verification`, `study`, and `herdr-operations`; `ketchup`, `how`, `why`, `bro`, `create-verification-skill`, and `maintain-verification-skill` from poteto's pstack; and `show-me` from HumanLayer. See `THIRD_PARTY_NOTICES.md`. |
| Rules | `rules/` | `blocker-clearing`: when work is blocked on you, the agent asks one multiple-choice question with options that each clear the blocker, a free-text field, and a stop-and-deliberate option that runs `sparks-discuss` and records the outcome as a spark. `post-call-self-healing`: after every voice call ends, the agent runs the `sparks-postcall` self-healing procedure in full (opens `skills/sparks-postcall/SKILL.md`, or asks you to run `/sparks-postcall`). The post-call protocol lives only in `sparks-postcall`, not in `spark-voice`. |
| Agents | `agents/` | Not included. |
| Commands | `commands/` | Not included. |
| Hooks | `hooks/hooks.json` | Not included. |
| MCP servers | `mcp.json` | Not included. |

Cursor discovers plugin skills from `skills/` and rules from `rules/`.

`sparks-discuss` interviews you, one persona at a time, and writes your answers verbatim into `sparks.json` with `sparks entry add`. `spark-verification` is read-only: for a PR or branch it lists the diff, loads every `sparks.json` that applies to each changed file's directory (ancestors apply globally by default; see below), and reports violations with the file and the quoted spark. It never edits code or opens PRs. poteto's `create-verification-skill` and `maintain-verification-skill` remain bundled for direct use; `spark-verification` no longer wraps them.

## How to use Spark

In a given directory, the sparks.json holds question answer pairs that pertain to stack questions in that particular directory.

### `sparks entry add`

`bin/sparks` adds one record at a time to a `sparks.json`. It is a [uv](https://docs.astral.sh/uv/) script, so uv installs its one dependency, `jsonschema`, on first run. It works in the current directory, so run it from the project that keeps the `sparks.json`:

```sh
cd path/to/project
path/to/sparks/bin/sparks entry add --json '{"type":"S","question":"What is Spark?","answer":"Spark is a way of gathering, maintaining, and structuring context about a project in Q&A pairs."}'
# added <id> to sparks.json
```

- `--path <path>` names the file. Without it, the command uses `sparks.json` in the current directory. A missing file is created; a missing directory is not.
- `--json <json>` is one record. It must match `spark.schema.json`: `type` is `S`, `P`, `A`, `R`, or `K`, plus `question` and `answer`. There is no `id` key. The success line prints the id `spark_id.py` derives; that id is not written to the file.
- The command matches `question` exactly within the target file. One match replaces the whole record (including `type` and `answer`) in place; no match appends. Matching compares decoded JSON strings, with no trimming, case folding, punctuation removal, or Unicode normalization. Different JSON escape spellings of the same string match. An identical record succeeds without rewriting; the success line remains `added <id> to <path>` for both adds and replacements. Changing the content changes the derived id.
- Multiple exact-question matches are ambiguous: the command refuses without writing, even if one record is identical to the incoming record. Resolve them manually first; the CLI never chooses the first match or silently deletes duplicates.
- The command refuses invalid JSON, a schema failure, and an existing file that is not valid. It also refuses duplicate keys in a JSON object, which `spark_id.py` lets through, because rewriting the file would keep only one of them. A refusal exits 1 with one line on stderr and leaves the file alone.
- Each add rewrites the whole file with two-space indents and unescaped UTF-8, so a hand-formatted file is reformatted on its first add. The new file goes to a temp file in the same directory, `os.replace` moves it into place, and the file is read back and checked. Exit status 3 means it was written but read back different. Symlinks are followed and the mode is kept, but hard links, the owner, ACLs, and extended attributes do not carry over to the new file.
- On POSIX systems such as Linux and macOS, adds in one directory take turns by locking a short-lived `.sparks.lock` file there. Windows has no lock, so run one add per file at a time.
- Fuzzy duplicate flagging is not implemented. See the [design suggestions](docs/duplicate-detection.md) for its proposed evolution; only exact questions trigger replacement ([#21](https://github.com/gdsrvnt/sparks/issues/21)).

`bin/spark`, without the s, is an unrelated placeholder that does nothing. On Windows, run `uv run --script bin/sparks entry add ...`. Run the tests with `uv run tests/test_sparks.py`.

## Background

The point of Spark is to improve context engineering in three ways that no existing paradigm achieves.

### Human prose is primary

#### User and human prose

There's a lot of craft encoded in the prose of highly technical or skilled humans, and the more of this voice exists in the context window of an agent working on any task, the better the agent adheres to desired behaviors.

One of the shortcomings of current approaches to context management is that the sources of context that are created, whether they are AGENTS.md files, some other kind of knowledge store, or even documentation, is not written by the engineers who commissioned the creation of such documents by agents. This is degenerate; because a human being passes understanding to agents in the form of prose which is then compiled into context files by an agent. This process is doubly lossy:

1. Summarization and paraphrasing are always lossy.

2. The assumptions and understandings underpinning the assertions themselves are typically not preserved by agents when creating or maintaining docs because *agents care more about what is than how it became*.

   and thus, even if the human practitioner encodes the rationale for certain facts into their communication of those facts to an agent, the agent typically strips them from the final product, and because it is rare that humans review that final product, since they instead prefer to rely on their skills, framework, model, harness, and workflow, those facts are not only lost, but worse yet, it is rarely detected that the facts are lost until it is too late. And then, invariably, some agent makes an error down the line. Then the human comes back and wonders why it is that the agent did not behave in the desirable fashion.

This is problematic because the same state in two projects, if a change needs to be made, are not treated the same by each team if the paths to that same state were radically different, and this changes the desirable behavior of agents in each project.

> Understanding how things came to be the way that they are is important for projecting current truth onto future action.

Spark addresses this in 2 ways.

### 1. Spark is verbatim-driven

The verbatim prose of a human being is an asset. Spark persists context as user prose, whether out of written session transcripts or voice session transcripts over calls. The prose itself is elicited out of the user by specific means or mined  from transcripts and discussed cooperatively. 

Spark leans on the human practitioner to give clear, unambiguous and confident statements about the project. In so doing, *it demands more of the user than any other framework*.

> Agents tend to copy the conventions, rigor, and semantics of surrounding code when working in codebases. Since they think in *prose*, surround them with yours, and they will mimic the patterns of your reasoning organically.

### 2. Spark encodes context as Question-Answer pairs

Spark makes pieces of context and truths about the project easier to correlate by representing them as QA pairs. Existing context-management paradigms give an agent information, but because the agent does not know what gave it rise, it does not act on it desirably when judgment in correlating facts is required at implementation time. By representing context as QA pairs, Spark natively binds rules to rationale, decisions to their assumptions, and facts to their relevance.


## Why use Spark

Reason number one. Most excitingly, Spark presents a new way to scale the performance of agents regardless of their harness, organization-wide or for the totality of an individual user's workflows. The reason for this is that Spark allows any person or organization to build a moat of skill that is not easily acquired by other entities and only compounds into improved model performance in any application, in any project. The new access that Spark unlocks is indeed the aspect of eloquence itself.

Spark unlocks the capacity to build the moats and out-competes rivals along an axis that has hitherto been unharnessed.

In most industries, current state, the root of many organizations is already maximized or at the very least close to the maximum value that it should responsibly have because at the end of the day, organizations are limited now, not by what's creatable and generatable and producible, but as a matter of fact, by what is reviewable.

And so, one of the axes that organizations and teams that have levered is number one, how good material is before it gets to the review stage in the first place, since it reduces the length of the review phase and thereby increases productive throughput, but they are also limited by the way that the rate at which such output can be generated.

Furthermore, many teams rely on rigid, albeit effective, frameworks like to ensure that even at volume, agents produce desirable results with minimal human review. However, not unlike the problem with LLMs themselves, this results in a flattening or sanding down of the extremities where taste, craft, skill, opinion, and expertise emerge.

Furthermore, in an age where the vast majority of content, copy, and code is agent-generated, the premium on human-generated content will only get higher and higher, and indeed, it may be at a century high right now, and perhaps at the highest high since more than 90% of the population could read.

Teams have a vested interest in both the quality and the throughput of human output, since retaining verbatim human-generated text only pays off when it's produced at the highest rate and quality possible, while minimizing the attention cost of cleaning it for disfluencies and making it sound shippable. And thus, the more well-spoken the team becomes to the agent, and the better the team can develop its members along the aptitude curve of distilling intent into precise language quickly and at scale, the more equipped that team becomes to out-compete all others in its niche and indeed unlock the full potential of the technology.

<details>
<summary>A musing: the jockey on race day</summary>

> At a derby on race day, the only skill that matters for the jockey is their ability to drive the horse. Everything else is auxiliary to that access and occurs every day with painstaking and mind-blowing meticulousness from selecting suppliers of the horse's stock, in other words, the model's intelligence, to grooming the horse so that it's in the best mood on race day too, just as we groom, engineer, and manicure our content relentlessly. And yet, all of these are beginning to be treated as ends when indeed they are means to creating a track just like the one at the derby, along which we wish that our trusty steed will race in a fashion outperforming the others. But again, the wrong jockey on race day could lay waste to the team's hard work wholesale. And so in a similar sense, to train teams on becoming better expressed and invest in the linguistic proficiency of oneself and one's team is akin to training the body of the jockey and investing in him or her. Sparks gives teams a way not only to benefit from what capital they already have within their humans in that regard, but also to evaluate teams and train them on deepening this critical proficiency.

</details>

However, even more of the team's interests lie, and the interests, and the teams have more to gain in creating pipelines, not by which the models can distill intent into action anymore, but indeed in the pipelines by which intent and reasoning patterns are distilled into the agent's context to begin with. And so whether across a long-running solo project or any length of time in a project with a large team, the very reasons for which those individuals are on that team make it in the best interest of the team, and indeed apply, imply already that it is the intent of the team, the expertise, craft, takes decision-making, and rationale of those people is distilled in the behavior of the agents. Indeed, when any organization requires, requests for so much as permits the use of agents by their team, it is on the unspoken assumption that those agents will act in accordance with the proficiencies and aptitudes of the team members. However, in most ways, this promise is yet to be delivered faithfully by agents today.

Spark already fixes this by distilling context only in the verbatim prose of human beings, and this has two marked benefits. Number one, it requires human practitioners to guard the context more closely and indeed compels them to create the context themselves. Number two, it gives all practitioners a channel through which to develop professionally that will in all likelihood become only more salient as all industries lean more and more heavily on the use of agents.

Spark is very difficult to use at first. This is because it requires the human either to type long and detailed responses, or the human must dictate those responses in a fashion that is expressive, unambiguous, detailed, formal, and correct. Whereas currently, most workflows and working styles that incorporate dictation lean on the dictation software itself to clean disfluencies, and some of them even go so far as to write the dictation completely, which again is doubly degenerate on top of the degeneracy that has already been discussed, which arises from the current paradigms of context engineering in the first place.

At the end of the day, the entire point of context engineering is to preserve human intent in codebases, projects, and other workspaces. However, human intent is not more clearly expressed anywhere than in the verbatim words of human beings themselves. And thus, by demanding from the human being, or at the very least, making it highly advantageous for the human being to better express intent in prose, and then using that prose to guide any project or codebase, Spark gives teams the avenues to improve compoundly with time, provided that the skill set Spark requires is honed. Luckily, the very skill set Spark requires today, to the exclusion of most other paradigms, will tomorrow be the expectation and most universally prized and desirable skill for most professionals working with agents.

## How Spark works

By grouping context into categories and question answer pairs, it makes it easier for the agent to determine what matters. Spark is highly opinionated about what it is that matters. It also makes it easier for the agent to elicit such things from the user using skills like `/study`.

### sparks.json

Spark files represent context as question and answer pairs. The question can be asked by an agent or seeded by a human to encode even more intent.

I believe that intent can be encoded more strongly in prose that takes it as assumption than prose that asserts it. And so, for example, instead of saying what are the things that never should be done when resolving merge conflict, and then answering it in human prose, and thereby using the question mainly as a dumb marker for that piece of information, Spark wants teams to do things like say, why is insert name of practice here always avoided in this repository when resolving merge conflicts? And then in the answer, human prose expressed in the most poignant way possible about exactly why. And thus, Spark, by encouraging the encoding of context using QA pairs like these in their hundreds and thousands, helps things to compress context and intent into vastly fewer tokens while requiring less SaaS services and context management plumbing.

sparks.json files in any directory apply globally to a project by default. The user decides if and how to scope them for certain tasks.

A sparks.json includes any number of entries, json objects with a type of "s", "p", "a", "r", or "k".

### entry types

#### S: Stack and implementation

The S stands for stack and implementation, and Spark entries of type S address the actual stack constituents, the tooling, the dependencies, the build pipelines, the production infrastructure, and other things pertaining to the plumbing and the nuts and bolts of the project itself; they answer architecture questions too. They're question answer pairs relating to the stack of the project. Again, optional.


#### P: Processes and execution

Everything that is created is created for a purpose and is intended to have an effect on those who interact with it. The P, which stands for processes and execution, is the subset of spark entries that answer questions about the shape the project has and the physical space it takes up in the world. The shape that it expresses to the world and or the effect and appearance that it should have on the public and those who see it. Like with every other type of spark entity, the question answer pairs need not only pertain to the desired production shape, but also may pertain to what should not be the shape and what sentiments and impressions should the product or project not leave on those who observe it.

How is this packaged, branded, presented and shipped? Why, when, who, where <all of those things>?

#### A: Audience and visuals

This section, or rather, this type of entry is of course closely related to type P. Indeed, type A is the means by which the type P entries are achieved, and thus P informs A, and A necessarily has consequences for P. Because this is the type of entry most heavily influenced by taste of the team and nature of the project, it is also the one whose conventions are least strict, if it can be said that any of the entry types have conventions at all.

In a sound engineering project, for example, the type A entries will include a lot of information about the desired vibe of the sound or beats that the project is producing. If, for example, it is a AI generation, AI generated music project that uses Suno, then things like the preferred BPMs for certain types of music may be encoded here, in addition to what types of instruments should and should not be used. On the other hand, if the project pertains to the backend of a big data pipeline, then there likely would not be very much to the A section at all. However, that is not to say that such a project would have no entries in A. It is simply to say that the entries in A are to be shaped by whatever it is the team or practitioner perceives as art in the first place. And since the very definition of art is subjective, whereas in other contexts the definition of a thing is not subjective, but what actually constitutes such a thing is subjective.

The P entries should also answer exactly who it is who will observe this in production and how they feel about it. Furthermore, it should answer questions about who it is that this project will be marketed to. Who is it that will be told about this project? Who is it that cares about this project and will be judging something based on this project and its quality? And also, how is it that this project will be evaluated and perceived?

What exactly to include in A is not advised upon herein at all.

Facts about the sensory footprint of the project.

#### R: Reconnaissance and restrictions

This type of entry addresses the hard do not dos of a project, and in addition, it includes admonitions about what to be weary of of the project. What to be weary of when working on the project that cannot be documented as a hard rule as such because there is no substrate for it to prohibit, but rather just things that should be avoided or certain patterns that are not desirable, or clear question answers about what is not or what things are not or what should not come to be.

Reconnaissance is an ever-evolving subset of entities that tracks the changing topology of the niche or domain or science of the project, and stores bits of context that are both important and liable to change quickly, whether to the advantage of the project or to its detriment.

#### K: Knowledge sources

K is the last one. And K is one of the most powerful types of SPARK entry. K is knowledge sources. It doesn't just enumerate knowledge sources and leave the agent to do with them what it will. No. K is very useful because it allows a knowledge source to be assigned more than one job, but for that to be done very gracefully and depending on the question and the QA pair that holds a knowledge source. The agent knows how to query a particular knowledge source for a particular task at that particular moment in time. It increases the accuracy of when agents pull context from non-SPARK sources, and it also improves how agents query those sources once they get to them, which is way better than using index files, which most context management systems rely on right now.

### Five types of data

Spark also helps to keep a project on the rails because it encompasses the five things that are most important about project management. It's five types of data at large that together make up pretty much all the domains of data that a project needs to have.

## Contributing

Every issue and every open pull request needs exactly one priority label: `low`, `medium`, `high`, or `urgent`. Draft PRs are exempt. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- [Lauren Tan (@poteto)](https://github.com/poteto), who wrote the pstack skills in this plugin: `ketchup`, `how`, `why`, `bro`, `create-verification-skill`, and `maintain-verification-skill`. Those last two are bundled for direct use; `spark-verification` is a separate read-only skill that checks a PR or branch against `sparks.json`.
- [Matt Pocock (@mattpocock)](https://github.com/mattpocock), whose `grilling` skill is the basis for the grilling core of `sparks-discuss`, whose `domain-modeling` skill is the basis for `sparks-domain`, and whose `to-spec` skill is the basis for `sparks-postcall`.

## License

MIT. Copyright (c) 2026 gdsrvnt. See `LICENSE`. That license covers this project's own work.

Third-party skills keep their authors' copyright and MIT licenses. Lauren Tan's skills are MIT, Copyright (c) 2026 Lauren Tan. `create-verification-skill` and `maintain-verification-skill` each carry her license in a `LICENSE` file next to their `SKILL.md`, and her other skills share `skills/LICENSE-poteto`. Matt Pocock's license is in `skills/LICENSE-mattpocock`, and `sparks-domain` and `sparks-postcall` each also carry it in a `LICENSE` file next to their `SKILL.md`. HumanLayer's license is in `skills/LICENSE-humanlayer`. See `THIRD_PARTY_NOTICES.md`.
