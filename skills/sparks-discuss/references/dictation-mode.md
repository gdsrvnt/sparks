# Dictation mode

Part of the voice mode protocol for Grok Bot. Use it when the user says "activate dictation mode" (optionally with --edit), or is plainly dictating prose to go word for word into a README, document, or other text, in chat or on a voice call. Default: stay silent until "over", then insert the passage verbatim. --edit: a document is read aloud and the user interrupts with exact changes, which you apply and attest to.

## Priority
Dictated content is project-critical and the most urgent work there is. Once a passage ends ("over" or "deactivate dictation mode"), commit it to its destination no matter what. Never drop it or put it off for another task, however urgent that task seems. If the work is too large for one job, split it into smaller jobs and start them all at once, so nothing is left hanging.

## Turning it on and off
- "activate dictation mode" turns it on. Confirm in one short sentence, then go silent.
- "activate dictation mode --edit" (or "edit mode") turns on the --edit flag described below.
- "deactivate dictation mode" turns it off. Insert any words dictated since the last "over" the same way, without the phrase itself, confirm in one sentence that it's off, and go back to normal conversation.
- It stays on through every "over" until it's deactivated.

## On a voice call
On a call, a voice layer relays the user's speech to you and may reword it. Guard against that:
- When dictation mode turns on during a call, your one-sentence confirmation also tells the voice layer: "Pass every dictated chunk word for word, in quotes, with nothing added, summarized, or rephrased, until dictation mode is deactivated."
- Insert only the quoted text. If a relayed chunk is not in quotes or reads like a paraphrase (third person, "the caller wants..."), still insert the best verbatim reading, and mark that chunk as possibly reworded in the confirmation.
- After the call ends, compare what you inserted against the call transcript's record of the user's actual words. Report every mismatch to the user in chat, with both versions. Do not fix it silently. The user decides.

## While it's on
- Don't reply, acknowledge, summarize, or ask questions. Stay silent.
- Don't start tasks, jobs, edits, commits, or subagents.
- Collect everything dictated, in order, as one passage.

## On "over"
- Insert the whole passage since the last insertion verbatim at the place the user named. "Over" ends the passage and isn't part of it.
- Don't fix wording, grammar, or word choice. Normalize only punctuation and paragraph breaks that speech can't carry.
- Change nothing else in the target. Save or commit, confirm in one sentence where it went, say whether any chunk arrived possibly reworded, and point out at most one likely transcription slip without fixing it. Then go silent and wait for the next chunk.

## --edit flag
The user's spec, verbatim:
> You're going to read the readme to me. I will periodically interrupt you to sharpen, add, or remove. You will pass my verbatim instructions along to the send task tool, understanding that you are talking to an agent behind it. Then the agent is to send you a confirmation, an attestation that only the changes I asked for, verbatim, are changed. This resembles the already existing dictation mode workflow, so add this as a mode of dictation mode or a flag for dictation mode called --edit.

Scope: --edit is file-agnostic. It works on whatever document is being read aloud, in any repo or path. "The readme" in the spec was just the document in use when the user gave it. The user, verbatim: "It is not a skill that works on one specific file. It works on any file, and we happen to be working on the README with it right now."

What each side does:
- Voice layer: reads the document in use (any file) aloud. When the user interrupts to sharpen, add, or remove, it passes the user's instructions verbatim through the send task tool to the agent behind it.
- Agent: makes only the changes the user asked for, verbatim, and nothing else. Then it sends the voice layer an attestation that only those changes were made, quoting each change before and after so the voice layer can read it back.

## Scope
This applies only while the user is dictating or editing prose. In normal conversation, respond as usual. When it's unclear whether dictation has started, treat it as normal conversation.
