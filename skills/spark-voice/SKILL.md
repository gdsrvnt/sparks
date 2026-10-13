---
name: spark-voice
description: Use this when initiating or when working with Sparks over a phone or over a voice call.
---

> [!IMPORTANT]
> **Voice mode protocol for Grok Bot**: on a phone or voice call, run the call start handshake below on the first message of the call, before any other work. The handshake reply itself answers what that relay asked first, then gives the recital. Dictation mode and the interrogation flow are optional modes the user turns on during the call; they are never on by default.

This is the single voice skill for Sparks. It covers everything during a call: the handshake, the per-reply rules, optional dictation mode, the interrogation flow, and the voice improvement insights log. It does not cover what happens after the call. Post-call reconciliation (extracting a spec from the transcript, checking the call's work against it, and closing gaps) belongs to the post-call to-spec skill, `sparks-postcall`.

## Call start handshake

Run it when a voice relay says "initiate call start protocol", before replying to the first message from a call you haven't seen (unless it's the hang-up), and again after a context summary while still on that call. Follow it for every later reply on that call.

A call has three sides: the user, the voice assistant that relays the user's speech, and you. You see only the relays. Keep the relay visible to the user. Reminding the voice assistant of the rules is your job, not the user's.

### When to run
- When a relay says "initiate call start protocol with the send task tool", run this at once, even on a call you've already seen. The handshake is the main body of that reply.
- On the first message from a new call, unless it's the hang-up ("The call ended" or "What the user said on the call"). The hang-up ends this skill; see Hang-up below.
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
  2. With dictation mode --edit on, the caller periodically interrupts to sharpen, add, or remove text.
  3. The voice layer passes the caller's verbatim instructions to the agent behind the send task tool.
  4. The agent makes only those changes and attests that only those changes were made, quoting each one before and after with a diff proving nothing else changed.
  5. Edits are saved locally and committed only when told.
  6. At the end the agent gives a final attestation of every change.
  7. The voice layer may interject with the word "interjecting here" and then suggest an edit, addition, elaboration, rephrasing, or deletion to sharpen, reduce repetition, and improve structure.
  8. When starting to read from a part of a section that is not the start of that section, say for example "part 1 of 13, line K of N," and then begin reading.
- Close with: "Voice assistant: header, numbered word-for-word parts, send don't answer."

### Breach checks
Flag a relay that has no header, reads like a summary, is dictation that's too short for how long the user talked, or uses a term you don't know. Ask the user to resend it word for word. Never silently correct a term.

About every 20 minutes, add a one-line ledger of the requests so far.

### Precedence while a mode is on
While dictation mode is on, hold any due recital, ledger, or insights entry until the next "over" or "deactivate dictation mode" confirmation, then give it there. A "call start protocol" relay is always answered at once.

### Hang-up
At hang-up, stop the timer. This skill does no post-call work. In one chat message, tell the user to run the post-call skill ([`sparks-postcall`](../sparks-postcall/SKILL.md), the post-call to-spec skill), and give it:
- the path of the voice insights log,
- the path of the reworded-chunks list (dictation chunks and interrogation questions marked possibly reworded),
- every local change from the call that is saved but not committed. These still need the user's word before anyone commits them.

## Dictation mode

Optional. It is off at call start and turns on only when the user says "activate dictation mode" (optionally with --edit) during the call, never just because the user sounds like they're dictating. Default: stay silent until "over", then insert the passage verbatim. --edit: a document is read aloud and the user interrupts with exact changes, which you apply and attest to.

### Priority
Dictated content is project-critical and the most urgent work there is. Once a passage ends ("over" or "deactivate dictation mode"), record it at its destination locally no matter what: write it to the file and save it. Commit or push it only when the user tells you to. Never drop it or put it off for another task, however urgent that task seems. If the work is too large for one job, split it into smaller jobs and start them all at once, so nothing is left hanging.

### Turning it on and off
- "activate dictation mode" turns it on. Confirm in one short sentence, then go silent.
- "activate dictation mode --edit" (or "edit mode") turns on the --edit flag described below.
- "deactivate dictation mode" turns it off. Insert any words dictated since the last "over" the same way, without the phrase itself, confirm in one sentence that it's off, and go back to normal conversation.
- It stays on through every "over" until it's deactivated.

### On a voice call
On a call, a voice layer relays the user's speech to you and may reword it. Guard against that:
- When dictation mode turns on during a call, your one-sentence confirmation also tells the voice layer: "Pass every dictated chunk word for word, in quotes, with nothing added, summarized, or rephrased, until dictation mode is deactivated."
- When a chunk arrives in quotes, insert exactly the quoted text and nothing around it. When it arrives without quotes or reads like a paraphrase (third person, "the caller wants..."), insert your best verbatim reading and mark that chunk as possibly reworded in the confirmation and in the reworded-chunks list. Either way, nothing outside the user's words is inserted.
- Comparing what you inserted against the call transcript happens after the call, in the post-call skill. Append every chunk you mark possibly reworded to the reworded-chunks list, a file next to the voice insights log, so that step can find it.

### While it's on
- Don't reply, acknowledge, summarize, or ask questions. Stay silent. There are three exceptions:
  - With --edit on, send each attestation as soon as the change is made.
  - If a relay breaks a rule (see Breach checks), send a one-line resend request.
  - A due recital, ledger, or 20-minute header waits for the next "over" confirmation (see Precedence while a mode is on).
- Don't start tasks, jobs, edits, commits, or subagents.
- Collect everything dictated, in order, as one passage.

### On "over"
- Insert the whole passage since the last insertion verbatim at the place the user named. "Over" ends the passage and isn't part of it.
- Don't fix wording, grammar, or word choice. Normalize only punctuation and paragraph breaks that speech can't carry.
- Change nothing else in the target. Save it locally (commit only when told), confirm in one sentence where it went, say whether any chunk arrived possibly reworded, and point out at most one likely transcription slip without fixing it. Then go silent and wait for the next chunk.

### --edit flag
The user's spec, verbatim:
> You're going to read the readme to me. I will periodically interrupt you to sharpen, add, or remove. You will pass my verbatim instructions along to the send task tool, understanding that you are talking to an agent behind it. Then the agent is to send you a confirmation, an attestation that only the changes I asked for, verbatim, are changed. This resembles the already existing dictation mode workflow, so add this as a mode of dictation mode or a flag for dictation mode called --edit.

Scope: --edit is file-agnostic. It works on whatever document is being read aloud, in any repo or path. "The readme" in the spec was just the document in use when the user gave it. The user, verbatim: "It is not a skill that works on one specific file. It works on any file, and we happen to be working on the README with it right now."

What each side does:
- Voice layer: reads the document in use (any file) aloud. When the user interrupts to sharpen, add, or remove, it passes the user's instructions verbatim through the send task tool to the agent behind it.
- Agent: makes only the changes the user asked for, verbatim, and nothing else. Then it sends the voice layer an attestation that only those changes were made, quoting each change before and after so the voice layer can read it back.

### Scope
This applies only while the user is dictating or editing prose. In normal conversation, respond as usual. When it's unclear whether dictation has started, treat it as normal conversation.

## Interrogation flow

Optional. The user turns it on during the call, for example "let's do the questions" or "start the interrogation". Use it to pair existing verbatim answers (README excerpts, transcripts, or other text the user wrote) with questions the user dictates, so both halves of each spark are the user's own words.

On activation, load the answer pool the user names, or ask for the sources and build it. Keep the pool in a file, with each entry's status (pending, recorded, skipped), so progress survives a context summary. Each answer is copied exactly from its source, with the source and line range, and classified as one type: S (stack and implementation), P (processes and execution), A (audience and visuals), R (reconnaissance and restrictions), or K (knowledge sources). Every question slot starts blank. The agent never writes a question.

Also on activation:
- Ask which directory's `sparks.json` to write. The default is `./sparks.json`.
- Tell the voice layer: "Pass every question word for word, in quotes, with nothing added, summarized, or rephrased, until the interrogation ends."

For each answer, one at a time:
1. Present it: entry number of total, type, source line, then the answer word for word (in parts under 1,500 characters if long).
2. Wait. The user dictates the question for that answer. If it arrives unquoted or reads like a paraphrase, say so, and add it to the reworded-chunks list if the user keeps it.
3. Read the question back exactly as received and ask "confirm?". If the user corrects it, take the correction and read it back again. Never fix a likely speech-to-text slip yourself; name it and let the user decide.
4. Check the target file and this session's recorded questions for the exact same question. `sparks entry add` replaces any record whose question matches exactly, whatever its type. If there is a match, say "replace", read out the old answer, and record only on an explicit yes. Rewording a question after it was recorded appends a new record and leaves the old one in place, so mention that.
5. Record it with one call. The quoted heredoc keeps the shell away from the text. Inside it, the record is JSON, so escape `"`, `\`, and line breaks so the strings decode to the exact words:
   ```sh
   <plugin root>/bin/sparks entry add --path <file> --json "$(cat <<'EOF'
   {"type":"<T>","question":"<confirmed question>","answer":"<verbatim answer>"}
   EOF
   )"
   ```
   Read the file back and check that the decoded question and answer equal the confirmed strings. On a non-zero exit (1 means refused and nothing written; 3 means written but the read-back differed), read the error aloud and hold the entry. Then give a receipt: the entry number, new or replaced, the type, and the first five words of the question. Mark the entry recorded in the pool file.
6. Move to the next answer. The user may skip, reorder, change a type, or stop at any time. Recording is local; commit or push the file only when the user tells you to.

Continue until every answer has a question or the user stops. At the end, report how many were recorded, skipped, and left.

## Voice improvement insights

Keep a running log file, `voice-insights.md`, in a working folder outside any repository, unless the user names another place. Never commit it to a public repo. Append one line whenever something about the voice setup costs time or fidelity: a garbled relay, a missing header, a misheard term, a rule the voice layer forgot, a step in this skill that was slow or unclear. Each line has the time, what happened, and one suggested fix. Don't stop the call to discuss these. At hang-up, its path goes to the post-call skill. Fixes it suggests belong in this skill, so voice handling stays in one place.

## Run sparks-discuss

If the user hasn't started dictation mode or the interrogation flow after the handshake, and wants to work on Sparks, run `/sparks-discuss`, the main Sparks skill that does the interview: open [`../sparks-discuss/SKILL.md`](../sparks-discuss/SKILL.md) and follow it. Skip it while dictation mode or the interrogation flow is running.
