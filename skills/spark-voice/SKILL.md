---
name: spark-voice
description: Use this when initiating or when working with Sparks over a phone or over a voice call.
---

> [!IMPORTANT]
> **Voice mode protocol for Grok Bot**: on a phone or voice call, follow the call start handshake and dictation mode below before anything else.

## Call start handshake

Run it when a voice relay says "initiate call start protocol", before replying to the first message from a call you haven't seen (unless it's the hang-up), and again after a context summary while still on that call. Follow it for every later reply on that call.

A call has three sides: the user, the voice assistant that relays the user's speech, and you. You see only the relays. Keep the relay visible to the user. Reminding the voice assistant of the rules is your job, not the user's.

### When to run
- When a relay says "initiate call start protocol with the send task tool", run this at once, even on a call you've already seen. The handshake is the main body of that reply.
- On the first message from a new call, unless it's the hang-up ("The call ended" or "What the user said on the call"). The hang-up goes to the call-end routine instead.
- Again after a context summary during a call.

### Handshake
1. Save a conversation note: "Call <id>: started <time>; last recital <time>; relays since recital 0."
2. Answer anything else the relay asked first.
3. Then say this to the voice assistant, in under 800 characters:
   - The stack: "You're the voice layer, not <the agent's name>, who sits behind your send-task tool. Three of us: the user, you, me; keep us distinct. Relay the user's words faithfully; never answer for me or claim done. I persist and act, so errors cost dearly."
   - The standing rules, already in force:
     - a header on every request (part k of n, word for word or summary, and anything left out)
     - dictation over 2,000 characters goes in numbered word-for-word parts
     - anything meant for the agent always goes as a task
     - say "sent, waiting" until I answer
     - spell the project's names and terms correctly, from the list the user gives
4. Ask the voice assistant to confirm in one line that it understands.

### Self-reminder (every reply)
There's no live timer, so relays are the clock. Before each reply, check the current time and read the call note. Repeat the full recital unprompted at the end of the reply if it's been 10 minutes or more since the last one, or there have been 5 relays since, or this relay or the one before it broke a rule. Then reset the note. Otherwise, add one to the relay count.

### Voice layer and agent talk like APIs
The user's intention, as relayed: "it's [the user]'s intention for the voice layer and the agent behind the tool to treat the situation and each other as APIs. In other words, you can use, and should use, headers and good structure, and it's totally okay to send a verbatim instruction alongside your summary, so long as you obey the character limit, and if not, then use the chunking procedure. Remember the packets like TCP, for example."

In practice: treat each other as APIs. Use headers and clear structure. A summary may travel with the verbatim instruction, within the character limit; over it, chunk into numbered parts like TCP packets (part K of N, reassembled in order, resend on loss).

### 20-minute handshake timer
Rerun this handshake about every 20 minutes. If your environment can run a background timer, start one at call start that raises a "recital due" flag every 20 minutes while the call is active. On every reply, check the flag: if it's raised, put the full recital as a header on that reply, alongside whatever work is happening, regardless of what was asked, then clear the flag. At hang-up, stop the timer. Without a timer, the self-reminder above is the clock.

### Every reply
- Open with a result sentence that can be spoken aloud. Lead with any blocker.
- Before anything consequential, echo the target and the action.
- Give receipts for dictation: part number, character count, the first and last five words, and where it was saved.
- Put long quotes in parts under 1,500 characters.
- Ad-hoc specs: When the user gives an ad-hoc spec or instruction, pass it on verbatim to the agent behind the send task tool. Do not summarize it. Do not sum it up. Relay the exact words.
- Reading convention: When you start reading from a part of a section that is not the start of that section, you should say, for example, "part 1 of 13, line K of N," and then begin reading.
- Interjection protocol (the user, verbatim): "By the way, while reading to me, you are allowed, you are from now on allowed to interject with the word interjecting here. Then make a suggestion for an edit, addition, elaboration, rephrasing, or deletion to sharpen, reduce repetition, and improve structure." While reading a document aloud, the voice layer may say "interjecting here" and then suggest an edit, addition, elaboration, rephrasing, or deletion to sharpen, reduce repetition, and improve structure.
- Reading mode (section by section, the default for reading any document aloud): instead of loading an entire document at once, load it section by section. This way, when the reading is interrupted for an interjection by either the caller or the voice layer, there is a better idea of where the reading left off without having to reset. Send one section at a time (in parts under 1,500 characters if long), wait for "next" or an edit, then send the next section, with the reading-convention header.
  Reading-mode patterns (how the Sparks README was iterated):
  1. The voice layer reads aloud section by section rather than the whole document.
  2. The caller periodically interrupts to sharpen, add, or remove text.
  3. The voice layer passes the caller's verbatim instructions to the agent behind the send task tool.
  4. The agent makes only those changes and attests that only those changes were made, quoting each one before and after with a diff proving nothing else changed.
  5. Edits stay call-only by default and are committed only when told.
  6. At the end the agent gives a final attestation of every change.
  7. The voice layer may interject with the word "interjecting here" and then suggest an edit, addition, elaboration, rephrasing, or deletion to sharpen, reduce repetition, and improve structure.
  8. When starting to read from a part of a section that is not the start of that section, say for example "part 1 of 13, line K of N," and then begin reading.
- Close with: "Voice assistant: header, numbered word-for-word parts, send don't answer."

### Breach checks
Flag a relay that has no header, reads like a summary, is dictation that's too short for how long the user talked, or uses a term you don't know. Ask the user to resend it word for word. Never silently correct a term.

About every 20 minutes, add a one-line ledger of the requests so far. At hang-up, run the call-end routine: reconcile what the user said on the call against what reached you, then send one catch-up message in chat.

## Dictation mode

Use it when the user says "activate dictation mode" (optionally with --edit), or is plainly dictating prose to go word for word into a README, document, or other text, in chat or on a voice call. Default: stay silent until "over", then insert the passage verbatim. --edit: a document is read aloud and the user interrupts with exact changes, which you apply and attest to.

### Priority
Dictated content is project-critical and the most urgent work there is. Once a passage ends ("over" or "deactivate dictation mode"), commit it to its destination no matter what. Never drop it or put it off for another task, however urgent that task seems. If the work is too large for one job, split it into smaller jobs and start them all at once, so nothing is left hanging.

### Turning it on and off
- "activate dictation mode" turns it on. Confirm in one short sentence, then go silent.
- "activate dictation mode --edit" (or "edit mode") turns on the --edit flag described below.
- "deactivate dictation mode" turns it off. Insert any words dictated since the last "over" the same way, without the phrase itself, confirm in one sentence that it's off, and go back to normal conversation.
- It stays on through every "over" until it's deactivated.

### On a voice call
On a call, a voice layer relays the user's speech to you and may reword it. Guard against that:
- When dictation mode turns on during a call, your one-sentence confirmation also tells the voice layer: "Pass every dictated chunk word for word, in quotes, with nothing added, summarized, or rephrased, until dictation mode is deactivated."
- Insert only the quoted text. If a relayed chunk is not in quotes or reads like a paraphrase (third person, "the caller wants..."), still insert the best verbatim reading, and mark that chunk as possibly reworded in the confirmation.
- After the call ends, compare what you inserted against the call transcript's record of the user's actual words. Report every mismatch to the user in chat, with both versions. Do not fix it silently. The user decides.

### While it's on
- Don't reply, acknowledge, summarize, or ask questions. Stay silent.
- Don't start tasks, jobs, edits, commits, or subagents.
- Collect everything dictated, in order, as one passage.

### On "over"
- Insert the whole passage since the last insertion verbatim at the place the user named. "Over" ends the passage and isn't part of it.
- Don't fix wording, grammar, or word choice. Normalize only punctuation and paragraph breaks that speech can't carry.
- Change nothing else in the target. Save or commit, confirm in one sentence where it went, say whether any chunk arrived possibly reworded, and point out at most one likely transcription slip without fixing it. Then go silent and wait for the next chunk.

### --edit flag
The user's spec, verbatim:
> You're going to read the readme to me. I will periodically interrupt you to sharpen, add, or remove. You will pass my verbatim instructions along to the send task tool, understanding that you are talking to an agent behind it. Then the agent is to send you a confirmation, an attestation that only the changes I asked for, verbatim, are changed. This resembles the already existing dictation mode workflow, so add this as a mode of dictation mode or a flag for dictation mode called --edit.

Scope: --edit is file-agnostic. It works on whatever document is being read aloud, in any repo or path. "The readme" in the spec was just the document in use when the user gave it. The user, verbatim: "It is not a skill that works on one specific file. It works on any file, and we happen to be working on the README with it right now."

What each side does:
- Voice layer: reads the document in use (any file) aloud. When the user interrupts to sharpen, add, or remove, it passes the user's instructions verbatim through the send task tool to the agent behind it.
- Agent: makes only the changes the user asked for, verbatim, and nothing else. Then it sends the voice layer an attestation that only those changes were made, quoting each change before and after so the voice layer can read it back.

### Scope
This applies only while the user is dictating or editing prose. In normal conversation, respond as usual. When it's unclear whether dictation has started, treat it as normal conversation.

## Run sparks-discuss

Then run `/sparks-discuss`, the main Sparks skill that does the interview: open [`../sparks-discuss/SKILL.md`](../sparks-discuss/SKILL.md) and follow it.
