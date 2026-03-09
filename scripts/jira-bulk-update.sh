#!/bin/bash
#
# jira-bulk-update.sh
# Bulk update Jira issues with acceptance criteria or other fields
#
# Usage:
#   ./scripts/jira-bulk-update.sh [command] [options]
#
# Commands:
#   add-ac <issue-key>     Add acceptance criteria template to a single issue
#   add-ac-bulk <jql>      Add acceptance criteria to issues matching JQL
#   transition <issue> <status>  Transition issue to status
#   list-epics             List all epics in project
#   list-stories <epic>    List stories under an epic
#
# Prerequisites:
#   - .netrc file with Jira credentials
#   - jq installed (brew install jq)
#

set -e

# Configuration
JIRA_URL="https://landrightiq.atlassian.net"
PROJECT="KAN"

# Get credentials from .netrc
get_auth() {
    local password=$(grep -A2 "machine landrightiq.atlassian.net" ~/.netrc | grep password | awk '{print $2}')
    local login=$(grep -A2 "machine landrightiq.atlassian.net" ~/.netrc | grep login | awk '{print $2}')
    echo -n "$login:$password" | base64
}

AUTH=$(get_auth)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Generate acceptance criteria ADF based on issue type
generate_ac_adf() {
    local issue_type="$1"
    
    case "$issue_type" in
        "Epic")
            cat <<'EOF'
{
  "type": "taskList",
  "attrs": {"localId": "epic-ac"},
  "content": [
    {"type": "taskItem", "attrs": {"localId": "ac-1", "state": "TODO"}, "content": [{"type": "text", "text": "All child stories completed and verified"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-2", "state": "TODO"}, "content": [{"type": "text", "text": "Technical documentation updated"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-3", "state": "TODO"}, "content": [{"type": "text", "text": "E2E tests passing for all workflows"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-4", "state": "TODO"}, "content": [{"type": "text", "text": "Code reviewed and merged to main"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-5", "state": "TODO"}, "content": [{"type": "text", "text": "Deployed to staging environment"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-6", "state": "TODO"}, "content": [{"type": "text", "text": "UAT sign-off received from stakeholders"}]}
  ]
}
EOF
            ;;
        "Story"|"Task"|"Feature")
            cat <<'EOF'
{
  "type": "taskList",
  "attrs": {"localId": "story-ac"},
  "content": [
    {"type": "taskItem", "attrs": {"localId": "ac-1", "state": "TODO"}, "content": [{"type": "text", "text": "Feature implemented per requirements"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-2", "state": "TODO"}, "content": [{"type": "text", "text": "Unit tests written (coverage >= 80%)"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-3", "state": "TODO"}, "content": [{"type": "text", "text": "Code reviewed and approved"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-4", "state": "TODO"}, "content": [{"type": "text", "text": "No critical linter errors"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-5", "state": "TODO"}, "content": [{"type": "text", "text": "Documentation updated if needed"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-6", "state": "TODO"}, "content": [{"type": "text", "text": "Manual testing completed"}]}
  ]
}
EOF
            ;;
        "Bug")
            cat <<'EOF'
{
  "type": "taskList",
  "attrs": {"localId": "bug-ac"},
  "content": [
    {"type": "taskItem", "attrs": {"localId": "ac-1", "state": "TODO"}, "content": [{"type": "text", "text": "Root cause identified and documented"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-2", "state": "TODO"}, "content": [{"type": "text", "text": "Fix implemented and verified"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-3", "state": "TODO"}, "content": [{"type": "text", "text": "Original bug scenario no longer reproduces"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-4", "state": "TODO"}, "content": [{"type": "text", "text": "Test added to prevent regression"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-5", "state": "TODO"}, "content": [{"type": "text", "text": "No new issues introduced"}]}
  ]
}
EOF
            ;;
        *)
            cat <<'EOF'
{
  "type": "taskList",
  "attrs": {"localId": "default-ac"},
  "content": [
    {"type": "taskItem", "attrs": {"localId": "ac-1", "state": "TODO"}, "content": [{"type": "text", "text": "Requirements implemented"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-2", "state": "TODO"}, "content": [{"type": "text", "text": "Tested and verified"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-3", "state": "TODO"}, "content": [{"type": "text", "text": "Documentation updated"}]},
    {"type": "taskItem", "attrs": {"localId": "ac-4", "state": "TODO"}, "content": [{"type": "text", "text": "Code reviewed"}]}
  ]
}
EOF
            ;;
    esac
}

# Get issue details
get_issue() {
    local issue_key="$1"
    curl -s \
        -H "Authorization: Basic $AUTH" \
        "$JIRA_URL/rest/api/3/issue/$issue_key"
}

# Add acceptance criteria to a single issue
add_ac() {
    local issue_key="$1"
    
    echo -e "${YELLOW}Processing $issue_key...${NC}"
    
    # Get issue type
    local issue_data=$(get_issue "$issue_key")
    local issue_type=$(echo "$issue_data" | python3 -c "import sys,json; print(json.load(sys.stdin)['fields']['issuetype']['name'])")
    local current_desc=$(echo "$issue_data" | python3 -c "import sys,json; d=json.load(sys.stdin)['fields'].get('description'); print(json.dumps(d) if d else 'null')")
    
    echo "  Issue type: $issue_type"
    
    # Generate AC ADF
    local ac_adf=$(generate_ac_adf "$issue_type")
    
    # Build new description with AC appended
    local ac_heading='{"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Acceptance Criteria"}]}'
    
    # Create updated description
    if [ "$current_desc" = "null" ] || [ -z "$current_desc" ]; then
        # No existing description
        local new_desc="{\"type\": \"doc\", \"version\": 1, \"content\": [$ac_heading, $ac_adf]}"
    else
        # Append to existing description
        local existing_content=$(echo "$current_desc" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('content', [])))")
        local new_desc=$(python3 -c "
import json
existing = json.loads('$existing_content')
heading = json.loads('$ac_heading')
ac = json.loads('$ac_adf')
existing.extend([heading, ac])
print(json.dumps({'type': 'doc', 'version': 1, 'content': existing}))
")
    fi
    
    # Update issue
    local response=$(curl -s -X PUT \
        -H "Authorization: Basic $AUTH" \
        -H "Content-Type: application/json" \
        "$JIRA_URL/rest/api/3/issue/$issue_key" \
        -d "{\"fields\": {\"description\": $new_desc}}")
    
    if [ -z "$response" ]; then
        echo -e "  ${GREEN}Updated successfully${NC}"
    else
        echo -e "  ${RED}Error: $response${NC}"
    fi
}

# Add AC to issues matching JQL
add_ac_bulk() {
    local jql="$1"
    
    echo -e "${YELLOW}Searching for issues: $jql${NC}"
    
    # Search for issues
    local issues=$(curl -s \
        -H "Authorization: Basic $AUTH" \
        "$JIRA_URL/rest/api/3/search?jql=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$jql'))")&fields=key")
    
    local keys=$(echo "$issues" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(i['key']) for i in d.get('issues', [])]")
    
    if [ -z "$keys" ]; then
        echo -e "${RED}No issues found${NC}"
        return
    fi
    
    echo "Found issues:"
    echo "$keys"
    echo ""
    
    read -p "Add acceptance criteria to these issues? (y/n) " confirm
    if [ "$confirm" != "y" ]; then
        echo "Cancelled"
        return
    fi
    
    for key in $keys; do
        add_ac "$key"
    done
    
    echo -e "${GREEN}Done!${NC}"
}

# Transition issue to status
transition_issue() {
    local issue_key="$1"
    local target_status="$2"
    
    # Get available transitions
    local transitions=$(curl -s \
        -H "Authorization: Basic $AUTH" \
        "$JIRA_URL/rest/api/3/issue/$issue_key/transitions")
    
    local transition_id=$(echo "$transitions" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('transitions', []):
    if t['name'].lower() == '$target_status'.lower():
        print(t['id'])
        break
")
    
    if [ -z "$transition_id" ]; then
        echo -e "${RED}Transition '$target_status' not found${NC}"
        echo "Available transitions:"
        echo "$transitions" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"  - {t['name']}\") for t in d.get('transitions', [])]"
        return 1
    fi
    
    curl -s -X POST \
        -H "Authorization: Basic $AUTH" \
        -H "Content-Type: application/json" \
        "$JIRA_URL/rest/api/3/issue/$issue_key/transitions" \
        -d "{\"transition\": {\"id\": \"$transition_id\"}}"
    
    echo -e "${GREEN}$issue_key -> $target_status${NC}"
}

# List epics
list_epics() {
    echo -e "${YELLOW}Epics in $PROJECT:${NC}"
    
    curl -s \
        -H "Authorization: Basic $AUTH" \
        "$JIRA_URL/rest/api/3/search?jql=project=$PROJECT%20AND%20issuetype=Epic&fields=key,summary,status" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
for issue in data.get('issues', []):
    key = issue['key']
    summary = issue['fields']['summary']
    status = issue['fields']['status']['name']
    print(f'  {key}: {summary} [{status}]')
"
}

# List stories under epic
list_stories() {
    local epic_key="$1"
    
    echo -e "${YELLOW}Stories under $epic_key:${NC}"
    
    curl -s \
        -H "Authorization: Basic $AUTH" \
        "$JIRA_URL/rest/api/3/search?jql=parent=$epic_key&fields=key,summary,status,issuetype" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
for issue in data.get('issues', []):
    key = issue['key']
    summary = issue['fields']['summary']
    status = issue['fields']['status']['name']
    itype = issue['fields']['issuetype']['name']
    print(f'  {key} [{itype}]: {summary} [{status}]')
"
}

# Show help
show_help() {
    cat <<EOF
Jira Bulk Update Script

Usage: ./scripts/jira-bulk-update.sh <command> [options]

Commands:
  add-ac <issue-key>        Add acceptance criteria to a single issue
  add-ac-bulk "<jql>"       Add acceptance criteria to issues matching JQL
  transition <issue> <status>  Transition issue to a status
  list-epics                List all epics in project
  list-stories <epic-key>   List stories under an epic
  help                      Show this help

Examples:
  # Add AC to a single issue
  ./scripts/jira-bulk-update.sh add-ac KAN-15

  # Add AC to all stories without AC
  ./scripts/jira-bulk-update.sh add-ac-bulk "project=KAN AND issuetype=Story"

  # Transition issue to Done
  ./scripts/jira-bulk-update.sh transition KAN-15 Done

  # List all epics
  ./scripts/jira-bulk-update.sh list-epics

  # List stories under an epic
  ./scripts/jira-bulk-update.sh list-stories KAN-6
EOF
}

# Main
case "${1:-help}" in
    add-ac)
        if [ -z "$2" ]; then
            echo "Usage: $0 add-ac <issue-key>"
            exit 1
        fi
        add_ac "$2"
        ;;
    add-ac-bulk)
        if [ -z "$2" ]; then
            echo "Usage: $0 add-ac-bulk \"<jql>\""
            exit 1
        fi
        add_ac_bulk "$2"
        ;;
    transition)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 transition <issue-key> <status>"
            exit 1
        fi
        transition_issue "$2" "$3"
        ;;
    list-epics)
        list_epics
        ;;
    list-stories)
        if [ -z "$2" ]; then
            echo "Usage: $0 list-stories <epic-key>"
            exit 1
        fi
        list_stories "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
