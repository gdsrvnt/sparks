# Sparks

> Spark is a way of engineering the context of a project or a repository in such a fashion that makes the information have three things that current approaches to context management don't have.

## How to use Spark

Ideally, in a given directory, the sparks .json should hold question answer pairs that pertain to stack questions in that particular directory.

## Background

The point of Spark is to improve context engineering in three ways that no existing paradigm achieves.

### Human prose is primary

#### User and human prose

There's a lot of craft encoded in the prose of highly technical or skilled humans, and the more of this voice exists in the context window of an agent working on any task, the better the agent adheres to desired behaviors.

One of the shortcomings of current approaches to context management is that the sources of context that are created, whether they are AGENTS.md files, some other kind of knowledge store, or even documentation, is not written by the engineers who commissioned the creation of such documents by agents. This is degenerate; because a human being passes understanding to agents in the form of prose which is then compiled into context files by an agent. This process is doubly lossy:

1. Summarization and paraphrasing are always lossy.

2. The assumptions and understandings underpinning the assertions themselves are typically not preserved by agents when creating or maintaining docs because *agents care more about what is than how it became*.

   and thus, even if the human practitioner encodes the rationale for certain facts into their communication of those facts to an agent, the agent typically strips them from the final product, and because it is rare that humans review that final project, since they instead prefer to rely on their skills, framework, model, harness, and workflow, those facts are not only lost, but worse yet, it is rarely detected that the facts are lost until it is too late. Then invariably, the human comes back, and the model makes an error, or some other agent makes an error further down the line, and wonders why it is that the agent did not behave in the desirable fashion.

This is problematic because the same state in two projects, if a change needs to be made, are not treated the same by each team if the paths to that same state were radically different.

> Understanding how things came to be the way that they are is important for projecting current truth onto future action.

Spark addresses this in 2 ways.

### 1. Spark is verbatim-driven

The verbatim prose of a human being is an asset. Spark persists context as user prose, whether out of written session transcripts or voice session transcripts over calls. The prose itself is elicited out of the user by specific means or mined  from transcripts and discussed cooperatively. 

Spark leans on the human practitioner to give clear, unambiguous and confident statements about the project. In so doing, *it demands more of the user than any other framework*.

> Agents tend to copy the conventions, rigor, and semantics of surrounding code when working in code. Since they think in *prose*, surround them with yours.

### 2. Spark encodes context as Question-Answer pairs

Spark makes pieces of context and truths about the project easier to correlate by representing them as QA pairs. Existing context-management paradigms give an agent information, but because the agent does not know what gave it rise, it does not act on it desirably when judgment in correlating facts is required at implementation time. By representing context as QA pairs, Spark natively binds rules to rationale, decisions to their assumptions, and facts to their relevance.


## Why use Spark

Reason number one. Most excitingly, Spark presents a new way to scale the performance of agents regardless of their harness, organization-wide or for the totality of an individual user's workflows. The reason for this is that Spark allows any person or organization to build a moat of skill that is not easily acquired by other entities and only compounds into improved model performance in any application, in any project. The new access that Spark unlocks is indeed the aspect of eloquence itself.

Spark unlocks the capacity to build the moats and out-competes rivals along an axis that has hitherto been unharnessed.

In most industries, current state, the root of many organizations is already maximized or at the very least close to the maximum value that it should responsibly have because at the end of the day, organizations are limited now, not by what's creatable and generatable and predictable, but as a matter of fact, by what is reviewable.

And so, one of the axes that organizations and teams that have levered is number one, how good material is before it gets to the review stage in the first place, since it reduces the length of the review phase and thereby increases productive throughput, but they are also limited by the way that the rate at which such output can be generated.

Furthermore, many teams rely on rigid, albeit effective, frameworks like to ensure that even at volume, agents produce desirable results with minimal human review. However, not unlike the problem with LLMs themselves, this results in a flattening or sanding down of the extremities where personality, brand, character, creativity, and originality arise.

Furthermore, in an age where the vast majority of content, copy, and code is agent-generated, the premium on human-generated content will only get higher and higher, and indeed, it may be at a century high right now, and perhaps at the highest high since more than 90% of the population could read.

And so, teams and organizations, they have a vested interest in improving not only the quality of their human output, as this is a strong moat, but indeed the throughput and retention of that human output as well, but if human output is to be retained, and verbatim human-generated text is to be retained, then it is in the vested interest of the very same teams that this human content be produced at the highest rate and the highest quality possible.

However, even more of the team's interests lie, and the interests, and the teams have more to gain in creating pipelines, not by which the models can distill intent into action anymore, but indeed in the pipelines by which intent is distilled into the agent's context to begin with. And so whether across a long-running solo project or any length of time in a project with a large team, the very reasons for which those individuals are on that team make it in the best interest of the team, and indeed apply, imply already that it is the intent of the team, the expertise, craft, takes decision-making, and rationale of those people is distilled in the behavior of the agents. Indeed, when any organization requires, requests for so much as permits the use of agents by their team, it is on the unspoken assumption that those agents will act in accordance with the proficiencies and aptitudes of the team members. However, in most ways, this promise is yet to be delivered faithfully by agents today.

Spark already fixes this by distilling context only in the verbatim prose of human beings, and this has two marked benefits. Number one, it requires human practitioners to guard the context more closely and indeed compels them to create the context themselves. Number two, it gives all practitioners a channel through which to develop professionally that will in all likelihood become only more salient as all industries lean more and more heavily on the use of agents.

Spark is very difficult to use at first. This is because it requires the human either to type long and detailed responses, or the human must dictate those responses in a fashion that is expressive, unambiguous, detailed, formal, and correct. Whereas currently, most workflows and working styles that incorporate dictation lean on the dictation software itself to clean disfluencies, and some of them even go so far as to write the dictation completely, which again is doubly degenerate on top of the degeneracy that has already been discussed, which arises from the current paradigms of context engineering in the first place.

At the end of the day, the entire point of context engineering is to preserve human intent in codebases, projects, and other workspaces. However, human intent is not more clearly expressed anywhere than in the verbatim words of human beings themselves. And thus, by demanding from the human being, or at the very least, making it highly profitable for the human being to better express intent in prose, and then using that prose to guide any project or codebase, Spark gives all teams, projects, and codebases the avenues to improve linearly and predictably, infinitely, with time, provided that the skill set Spark requires is honed. Luckily, the very skill set Spark requires today, to the exclusion of most other paradigms, will tomorrow be the expectation and most universally prized and desirable skill for most professionals working with agents.

## How Spark works

By grouping context into categories and question answer pairs, it makes it easier for the agent to determine what matters. Spark is highly opinionated about what it is that matters. It also makes it easier for the agent to elicit such things from the user.

### sparks.json

Spark files represent context as question and answer pairs. The question can be asked by an agent or seeded by a human to encode even more intent.

sparks.json files in any directory apply globally to a project by default. The user decides if and how to scope them.

A sparks.json includes any number of entries, json objects with a type of "s", "p", "a", "r", or "k".

### entry types

#### S: Stack

The S stands for stack, and Spark entries of type S address the actual stack constituents, the tooling, the dependencies, the build pipelines, the production infrastructure, and other things pertaining to the plumbing and the nuts and bolts of the project itself; they answer architecture questions too. They're question answer pairs relating to the stack of the project. Again, optional.


#### P: Productization

Everything that is created is created for a purpose and is intended to have some effect on those perceive or use it. The P, which stands for productization, is the subset of spark entries that answer questions about the image that the project is meant to have. The shape that it expresses to the world and or the effect and appearance that it should have on the public and those who see it. The P entries should also answer exactly who it is who will observe this in production and how they are meant to feel about it. Like with every other type of spark entity, the question answer pairs need not only pertain to the desired production shape, but also may pertain to what should not be the shape and what sentiments and impressions should the product or project not leave on those who observe it. Furthermore, it should answer questions about who it is that this project will be marketed to. Who is it that will be told about this project? Who is it that cares about this project and will be judging something based on this project and its quality? And also, how is it that this project will be judged and perceived?

How is this packaged, branded, presented and shipped? Why, when, who, where <all of those things>?

#### A: Art and design

This section, or rather, this type of entry is of course closely related to type Indeed, type A is the means by which the type P entries are achieved, and thus P informs A, and A necessarily has consequences for P. Because this is the type of entry most heavily influenced by taste of the team and nature of the project, it is also the one whose conventions are least strict, if it can be said that any of the entry types have conventions at all.

In a sound engineering project, for example, the type A entries will include a lot of information about the desired vibe of the sound or beats that the project is producing. If, for example, it is a AI generation, AI generated music project that uses Suno, then things like the preferred BPMs for certain types of music may be encoded here, in addition to what types of instruments should and should not be used. On the other hand, if the project pertains to the backend of a big data pipeline, then there likely would not be very much to the A section at all. However, that is not to say that such a project would have no entries in A. It is simply to say that the entries in A are to be shaped by whatever it is the team or practitioner perceives as art in the first place. And since the very definition of art is subjective, whereas in other contexts the definition of a thing is not subjective, but what actually constitutes such a thing is subjective.

What exactly to include in A is not advised upon herein at all.

Facts about the sensory footprint of the project.

#### R: Risks and restrictions

This type of entry addresses the hard do not dos of a project, and in addition, it includes admonitions about what to be weary of of the project. What to be weary of when working on the project that cannot be documented as a hard rule as such because there is no substrate for it to prohibit, but rather just things that should be avoided or certain patterns that are not desirable, or clear question answers about what is not or what things are not or what should not come to be.

#### K: Knowledge sources

K is the last one. And K is one of the most powerful types of SPARK entry. K is knowledge sources. It doesn't just enumerate knowledge sources and leave the agent to do with them what it will. No. K is very useful because it allows a knowledge source to be assigned more than one job, but for that to be done very gracefully and depending on the question and the QA pair that holds a knowledge source. The agent will know how to query a particular knowledge source for a particular task at that particular moment in time. It will increase the accuracy of when agents pull context from non-SPARK sources, and it will also improve how agents query those sources once they get to them, which is way better than using index files, which most context management systems rely on right now.

### Five types of data

Spark also helps to keep a project on the rails because it unironically does encompass the five things that are most important about project management. It's five types of data at large that together make up pretty much all the domains of data that a project needs to have.

## Install

Clone the repository.

```bash
git clone https://github.com/gdsrvnt/spark.git
cd spark
```

### Dependencies

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). uv installs a Python interpreter that satisfies the `requires-python` line in `spark_id.py`.

## Usage

### CLI

From the repository root, check that every stored id matches its question and answer.

```bash
uv run spark_id.py spark.json
```

Exit code 0 and no output means the file matches. The sample record id is `107ee97d1abd8e36`.

Check `spark.json` against `spark.schema.json`.

```bash
uvx check-jsonschema --schemafile spark.schema.json spark.json
```

Run the placeholder binary. It exits 0 and writes nothing.

```bash
bin/spark
```

The id rules and the `bin/spark` placeholder are in [Format](docs/format.md).

## Contributing

Questions go to [GitHub issues](https://github.com/gdsrvnt/spark/issues). Pull requests are accepted.

Before you open a pull request, run both checks in Usage. When a record fails, fix the record. When the id rule changes, change `spark_id.py` in the same pull request.

## License

License: not yet chosen.

The SPDX license identifier is UNLICENSED. No license owner is named.
