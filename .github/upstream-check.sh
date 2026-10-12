#!/usr/bin/env bash
# Usage: upstream-check.sh <upstreams.json>   (needs gh + jq; DRY_RUN=1 prints payloads, no POST, no dedupe)
set -euo pipefail
pins="$1"
if [ "${DRY_RUN:-0}" != 1 ]; then
  if [ -z "${WEBHOOK_URL:-}" ] || [ -z "${WEBHOOK_KEY:-}" ] || [ -z "${WEBHOOK_HEADER:-}" ]; then
    echo "::error::UPSTREAM_WEBHOOK_URL, UPSTREAM_WEBHOOK_KEY and UPSTREAM_WEBHOOK_HEADER must all be set"
    exit 1
  fi
fi
n=$(jq length "$pins")
for i in $(seq 0 $((n - 1))); do
  e=$(jq -c ".[$i]" "$pins")
  name=$(jq -r .upstream <<<"$e"); repo=$(jq -r .repo <<<"$e"); kind=$(jq -r .kind <<<"$e")
  path=$(jq -r .path <<<"$e"); pinned=$(jq -r .pinned_version <<<"$e")
  if [ "$kind" = release ]; then
    rel=$(gh api "repos/$repo/releases/latest")
    current=$(jq -r .tag_name <<<"$rel"); ref="$current"
  else
    ref=$(gh api "repos/$repo/commits/HEAD" --jq .sha)
    current=$(gh api "repos/$repo/contents/$path?ref=$ref" --jq .content | base64 -d | jq -r .version)
  fi
  if [ "$current" = "$pinned" ]; then echo "$name: up to date ($current)"; continue; fi
  title="upstream: $name $current"
  payload=$(jq -c -n --argjson e "$e" --arg v "$current" --arg r "$ref" \
    '{upstream: $e.upstream, repo: $e.repo, path: $e.path, kind: $e.kind, new_version: $v, our_pinned_ref: $e.pinned_ref, upstream_ref: $r, sparks_skills: $e.sparks_skills}')
  if [ "${DRY_RUN:-0}" = 1 ]; then echo "$name: $pinned -> $current (dry run)"; echo "$payload"; continue; fi
  hits=$(gh api graphql -f q="repo:$REPO in:title \"$title\"" -f query='query($q:String!){search(query:$q,type:DISCUSSION,first:20){nodes{... on Discussion{title}}}}' \
    --jq "[.data.search.nodes[] | select(.title == \"$title\")] | length")
  if [ "$hits" != 0 ]; then echo "$name: $current already has a discussion, skipping"; continue; fi
  echo "$name: $pinned -> $current, notifying"
  curl --fail-with-body -sS -X POST "$WEBHOOK_URL" -H "Content-Type: application/json" \
    -H "${WEBHOOK_HEADER}: ${WEBHOOK_KEY}" --data-binary "$payload"
done
