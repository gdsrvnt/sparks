# One level up: sparks in code, not prose

*Dictated intent, lightly edited. Filler and restarts are removed; the words are the speaker's own.*

This project is my own, so I'm going to be debugging it all today, and that's going to be the impetus for a lot of the questions I've asked and the discussion we've had. We'll keep learning about everything we've been discussing so far, because we're just scratching the surface.

What we're building towards is a more focused version of Sparks that wastes less time explaining its logic and skills, and puts more craft into expressing it in code: well-designed bash scripts that launch particular types of agents to do particular types of things, and even ensure at the harness level that coding agents are, for lack of a better term, type safe.

## Massive changes are coming

I want to take this full message, which declares my intent, along with a summary of everything we've talked about so far, and send it to Saleem, to put on their radar that massive changes are coming. We should start thinking about how to use pi in a headless and programmatic way, and potentially even work something like PiDurable into a Cloudflare-based system on the edge, to persist the state there and off of the GrokBot's machines. That would allow extreme parallelization by the GrokBot teams without overloading the computer, which has been an issue for us these days, as per the testament of the IT guy itself.

We've checked resources and not found severe RAM or CPU usage. I think what we might be suffering from is in fact extremely high network usage, and we might be getting rate limited on our egress. We're not quite so sure, but if we can outsource that to durable objects or even Cloudflare containers, we might be winners.

## Airtight programmatic workflows

All of that relies on airtight programmatic workflows that use agents at certain junctures and steps of the way to ensure very compliant results to the Sparks methodology.

We delegate the distillation of user intent into Sparks, the refinement of Sparks, and the creation of verification skills based on them. Exactly those three things. Those things go in the scope of the user along with the GrokBot.

Then come the steps that scripts and agents carry:

1. Distilling Sparks into specs.
2. The specs into PR graphs.
3. The PR graphs getting reviewed, the review landing exactly where we specify, like in a comment.
4. The comment being taken by some implementer and fixed.
5. The solution then fixed by the reviewer itself, fresh from the first reviewer. (A concept still to be discussed: this reviewer edits the fix rather than only re-checking it.)
6. Finally, the PR opened if determined by the GrokBot to be ready for review.

We have a path to making simple and robust scripts that execute all of this in either pi or PiDurable as a harness, most likely pi first. We can even delegate the orchestration of the workflow as it proceeds to an orchestrator agent running in pi on a free, big, relatively small, smart model like NVIDIA Nemotron 3 Ultra 550B, so that we're not overloading our GrokBots from the large machine at hand.

## One level of abstraction up

We're really trying to move one level of abstraction up from our current position: the GrokBot goes to where we are sitting now, and we go an even higher level, such that more agents can be managed practically with roughly the same amount of human cost.

Obviously this will require the refinement of certain assets of human capital: first of all, being able to verbally dictate specs, in addition to spatial reasoning, and the ability to draw diagrams and write quickly with a pen and paper. The Sparks style of working demands these things from the human, but there are enormous improvements in agent compliance and adherence the first time around, and mergeability of PRs with conventions that make sense per project.

So it's really a game of making the agents better at context switching.
