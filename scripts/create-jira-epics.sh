#!/bin/bash
#
# create-jira-epics.sh
# Creates LandRight MVP milestone epics in Jira using jira-cli
#
# Usage: ./scripts/create-jira-epics.sh
#
# Prerequisites:
#   - jira-cli installed: brew install ankitpokhrel/jira-cli/jira-cli
#   - Configured with: jira init
#

set -e

PROJECT="KAN"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if jira-cli is installed
if ! command -v jira &> /dev/null; then
    echo -e "${RED}Error: jira-cli is not installed.${NC}"
    echo ""
    echo "Install it with:"
    echo "  brew install ankitpokhrel/jira-cli/jira-cli"
    echo ""
    echo "Then configure with:"
    echo "  jira init"
    exit 1
fi

# Check if jira is configured
if ! jira me &> /dev/null; then
    echo -e "${RED}Error: jira-cli is not configured.${NC}"
    echo ""
    echo "Run 'jira init' to configure your Jira instance."
    exit 1
fi

echo -e "${GREEN}Creating LandRight MVP Epics in project ${PROJECT}...${NC}"
echo ""

# Array to store created epic keys
declare -a EPIC_KEYS

# -----------------------------------------------------------------------------
# Epic 1: Technical Design & Product Refinement
# Sprints 1-2 | Feb 4, 2026 - Mar 3, 2026
# -----------------------------------------------------------------------------
echo -e "${YELLOW}Creating Epic 1: Technical Design & Product Refinement${NC}"

EPIC1=$(jira issue create \
  --project "$PROJECT" \
  -tEpic \
  -s "M1: Technical Design & Product Refinement" \
  -b "$(cat <<'EOF'
## Milestone 1 - Technical Design & Product Refinement

**Duration:** Feb 4, 2026 - Mar 3, 2026 (Sprints 1-2)
**Release Date:** March 3, 2026

### Deliverables
- Technical architecture documentation
- Product requirements refinement
- Database schema design
- API contract definitions
- Development environment setup
- CI/CD pipeline configuration

### Acceptance Criteria
- Architecture reviewed and approved
- All team members onboarded
- Development environment operational
EOF
)" \
  --custom "start-date=2026-02-04,due-date=2026-03-03" \
  -l mvp -l milestone-1 -l "release-2026-03-03" \
  --no-input 2>&1 | grep -oE "${PROJECT}-[0-9]+")

EPIC_KEYS+=("$EPIC1")
echo -e "  Created: ${GREEN}${EPIC1}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Epic 2: Backend MVP API
# Sprints 3-4 | Mar 4, 2026 - Mar 31, 2026
# -----------------------------------------------------------------------------
echo -e "${YELLOW}Creating Epic 2: Backend MVP API${NC}"

EPIC2=$(jira issue create \
  --project "$PROJECT" \
  -tEpic \
  -s "M2: Backend MVP API" \
  -b "$(cat <<'EOF'
## Milestone 2 - Backend MVP API

**Duration:** Mar 4, 2026 - Mar 31, 2026 (Sprints 3-4)
**Release Date:** March 31, 2026

### Deliverables
- Core project and parcel management APIs
- Legal-first notices & service engine
- ROE (Right-of-Entry) management
- Litigation calendar APIs
- Title & curative tracking
- Payment ledger (status-only)
- Communications and audit events
- GIS alignment and parcel segmentation

### Acceptance Criteria
- All MVP scope APIs implemented
- Unit test coverage >= 80%
- API documentation complete
- Integration tests passing
EOF
)" \
  --custom "start-date=2026-03-04,due-date=2026-03-31" \
  -l mvp -l milestone-2 -l "release-2026-03-31" \
  --no-input 2>&1 | grep -oE "${PROJECT}-[0-9]+")

EPIC_KEYS+=("$EPIC2")
echo -e "  Created: ${GREEN}${EPIC2}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Epic 3: Frontend Internal Web App
# Sprints 5-6 | Apr 1, 2026 - Apr 28, 2026
# -----------------------------------------------------------------------------
echo -e "${YELLOW}Creating Epic 3: Frontend Internal Web App${NC}"

EPIC3=$(jira issue create \
  --project "$PROJECT" \
  -tEpic \
  -s "M3: Frontend Internal Web App" \
  -b "$(cat <<'EOF'
## Milestone 3 - Frontend Internal Web App

**Duration:** Apr 1, 2026 - Apr 28, 2026 (Sprints 5-6)
**Release Date:** April 28, 2026

### Deliverables
- Agent workbench UI
- Counsel controls and approvals
- Operations dashboard
- ROE management interface
- Negotiation panel
- Title & curative tracking UI
- Litigation panel
- GIS/Map component (Mapbox integration)
- Communications log

### Acceptance Criteria
- All internal user workflows implemented
- Responsive design
- Accessibility standards met
- E2E tests for critical paths
EOF
)" \
  --custom "start-date=2026-04-01,due-date=2026-04-28" \
  -l mvp -l milestone-3 -l "release-2026-04-28" \
  --no-input 2>&1 | grep -oE "${PROJECT}-[0-9]+")

EPIC_KEYS+=("$EPIC3")
echo -e "  Created: ${GREEN}${EPIC3}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Epic 4: Landowner Portal & Hardening
# Sprints 7-8 | Apr 29, 2026 - May 26, 2026
# -----------------------------------------------------------------------------
echo -e "${YELLOW}Creating Epic 4: Landowner Portal & Hardening${NC}"

EPIC4=$(jira issue create \
  --project "$PROJECT" \
  -tEpic \
  -s "M4: Landowner Portal & Hardening" \
  -b "$(cat <<'EOF'
## Milestone 4 - Landowner Portal & Hardening

**Duration:** Apr 29, 2026 - May 26, 2026 (Sprints 7-8)
**Release Date:** May 26, 2026

### Deliverables
- Magic link portal authentication
- E-sign integration (DocuSign)
- Portal session management
- Landowner intake flow
- Decision actions (Accept/Counter/Request Call)
- Document upload capability
- Security hardening
- Performance optimization

### Acceptance Criteria
- Landowner portal fully functional
- E-sign workflow operational
- Security audit passed
- Performance benchmarks met
EOF
)" \
  --custom "start-date=2026-04-29,due-date=2026-05-26" \
  -l mvp -l milestone-4 -l "release-2026-05-26" \
  --no-input 2>&1 | grep -oE "${PROJECT}-[0-9]+")

EPIC_KEYS+=("$EPIC4")
echo -e "  Created: ${GREEN}${EPIC4}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Epic 5: UAT Completion & Production-Ready
# Sprints 9-10 | May 27, 2026 - Jun 23, 2026
# -----------------------------------------------------------------------------
echo -e "${YELLOW}Creating Epic 5: UAT Completion & Production-Ready${NC}"

EPIC5=$(jira issue create \
  --project "$PROJECT" \
  -tEpic \
  -s "M5: UAT Completion & Production-Ready" \
  -b "$(cat <<'EOF'
## Milestone 5 - UAT Completion & Production-Ready Package

**Duration:** May 27, 2026 - Jun 23, 2026 (Sprints 9-10)
**Release Date:** June 23, 2026

### Deliverables
- Complete E2E test coverage
- Performance testing with Locust
- Security baseline verification
- Production deployment documentation
- Monitoring and alerting setup
- Backup and recovery procedures
- Runbooks and operational docs
- Final UAT sign-off

### Acceptance Criteria
- All E2E tests passing
- Performance targets met
- Security checklist complete
- Production environment ready
- Documentation approved
- UAT accepted by stakeholders
EOF
)" \
  --custom "start-date=2026-05-27,due-date=2026-06-23" \
  -l mvp -l milestone-5 -l "release-2026-06-23" \
  --no-input 2>&1 | grep -oE "${PROJECT}-[0-9]+")

EPIC_KEYS+=("$EPIC5")
echo -e "  Created: ${GREEN}${EPIC5}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo "=============================================="
echo -e "${GREEN}All epics created successfully!${NC}"
echo "=============================================="
echo ""
echo "Epic Keys:"
echo "  M1 Technical Design:     ${EPIC_KEYS[0]}"
echo "  M2 Backend MVP API:      ${EPIC_KEYS[1]}"
echo "  M3 Frontend Web App:     ${EPIC_KEYS[2]}"
echo "  M4 Landowner Portal:     ${EPIC_KEYS[3]}"
echo "  M5 UAT & Production:     ${EPIC_KEYS[4]}"
echo ""
echo "Release Schedule:"
echo "  M1: March 3, 2026"
echo "  M2: March 31, 2026"
echo "  M3: April 28, 2026"
echo "  M4: May 26, 2026"
echo "  M5: June 23, 2026"
echo ""
echo "View epics at:"
echo "  jira epic list --project ${PROJECT}"
