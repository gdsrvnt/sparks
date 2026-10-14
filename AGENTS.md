# Agent rules

Rules for agents working in this repository. This file is not a plugin rule. Do not copy it into `rules/`.

Priority labels are specified in [CONTRIBUTING.md](CONTRIBUTING.md). Every issue and every open (non-draft) pull request carries exactly one of `low`, `medium`, `high`, or `urgent`. Do not restate or relax that rule.

`rules/blocker-clearing.mdc` and `rules/post-call-self-healing.mdc` still apply.

## Pull requests

The pull request description, and every comment on that pull request that reports work, must include an implementation overview.

A comment reports work if it is a progress update, a final reply, a review summary of what changed, or any other note that says what was built or changed. A question, an acknowledgement, or a label note does not.

The overview walks through how the change is built, by component and file, in the order a reviewer should read it. For each file that matters, name it, say what it does in the change, and say how it connects to the other pieces. A small change gets a short overview, not an exemption.

A reviewer must be able to follow the change from that overview without reading the diff file by file. A summary of behavior is not an overview. A paste of the diff is not an overview.

If a later comment changes the implementation, its overview covers that change. Do not assume the reviewer will reconstruct it from the description.
