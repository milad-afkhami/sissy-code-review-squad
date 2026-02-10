---
model: haiku
description: Remove all discussions and notes from a GitLab merge request
---

# Clear MR Comments

Remove all discussions and notes from merge request `$ARGUMENTS` to prepare for a fresh review.

## Instructions

### Step 1: Parse MR Metadata

**Spawn the MR Metadata Parser Agent** to extract project info and MR IID from the URL.

Read and execute the parser agent instructions from `@agents/parse-mr-metadata.md` with the MR URL as input: `{$ARGUMENTS}`

**Wait for the Parser Agent to complete** and parse its JSON output to get:

- `project_id`
- `mr_iid`

### Step 2: Delete All Comments

Run the following bash script to delete all discussions and notes from the MR.

**Replace `{project_id}` and `{mr_iid}` with the values from Step 1.**

```bash
#!/bin/bash
PROJECT_ID="{project_id}"
MR_IID="{mr_iid}"

# Read token and API URL from ~/.claude/.mcp.json
MCP_CONFIG="$HOME/.claude/.mcp.json"
TOKEN=$(jq -r '.mcpServers["gitlab-mcp"].env.GITLAB_PERSONAL_ACCESS_TOKEN' "$MCP_CONFIG")
BASE_URL=$(jq -r '.mcpServers["gitlab-mcp"].env.GITLAB_API_URL' "$MCP_CONFIG")/api/v4

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Error: Could not read GITLAB_PERSONAL_ACCESS_TOKEN from $MCP_CONFIG"
  exit 1
fi

echo "Clearing comments from MR #$MR_IID in project $PROJECT_ID..."
echo "Using GitLab API: $BASE_URL"

# Get all discussions and delete notes
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$BASE_URL/projects/$PROJECT_ID/merge_requests/$MR_IID/discussions" > /tmp/discussions.json

deleted_count=0
skipped_count=0

jq -r '.[] | .id as $did | .notes[] | select(.system == false) | "\($did) \(.id)"' /tmp/discussions.json 2>/dev/null \
  | while read discussion_id note_id; do
      response=$(curl -s --request DELETE --header "PRIVATE-TOKEN: $TOKEN" \
        "$BASE_URL/projects/$PROJECT_ID/merge_requests/$MR_IID/discussions/$discussion_id/notes/$note_id")
      if echo "$response" | grep -q "403"; then
        echo "SKIPPED (no permission): note $note_id"
      else
        echo "Deleted note $note_id from discussion $discussion_id"
      fi
    done

# Delete standalone notes
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$BASE_URL/projects/$PROJECT_ID/merge_requests/$MR_IID/notes" > /tmp/notes.json

jq -r '.[] | select(.system == false) | .id' /tmp/notes.json 2>/dev/null \
  | while read note_id; do
      response=$(curl -s --request DELETE --header "PRIVATE-TOKEN: $TOKEN" \
        "$BASE_URL/projects/$PROJECT_ID/merge_requests/$MR_IID/notes/$note_id")
      if echo "$response" | grep -q "403"; then
        echo "SKIPPED (no permission): standalone note $note_id"
      else
        echo "Deleted standalone note $note_id"
      fi
    done

# Cleanup
rm -f /tmp/discussions.json /tmp/notes.json

echo ""
echo "Done! MR #$MR_IID is now ready for a fresh review."
```

### Step 3: Report Results

After the script completes, report:

- How many comments were deleted
- How many were skipped (if any)
- Confirmation that the MR is ready for a fresh review

## Important Notes

1. This command requires `jq` to be installed on the system
2. The GitLab token must have permission to delete notes on the target project
3. System notes (automated messages) are preserved and cannot be deleted
4. This action is **irreversible** - deleted comments cannot be recovered
