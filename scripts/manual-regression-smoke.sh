#!/usr/bin/env bash
# Quick HTTP smoke checks for API regression (requires curl).
# Usage: API_BASE=http://localhost:8050 ./scripts/manual-regression-smoke.sh
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8050}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

code() {
  curl -s -o /dev/null -w "%{http_code}" -H "X-Persona: ${1:?persona}" "${2:?url}"
}

echo "=== LandGrant manual smoke (API_BASE=$API_BASE) ==="

echo -n "GET /health/live ... "
c=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health/live")
[[ "$c" == "200" ]] || fail "/health/live got $c"
echo "OK ($c)"

echo -n "GET /health/invite ... "
c=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health/invite")
[[ "$c" == "200" ]] || fail "/health/invite got $c"
echo "OK ($c)"

echo -n "GET /health/esign ... "
c=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health/esign")
[[ "$c" == "200" ]] || fail "/health/esign got $c"
echo "OK ($c)"

echo -n "GET / (root) ... "
c=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/")
[[ "$c" == "200" ]] || fail "/ got $c"
echo "OK ($c)"

echo -n "RBAC templates in_house_counsel ... "
c=$(code in_house_counsel "$API_BASE/templates")
[[ "$c" == "200" ]] || fail "/templates counsel got $c"
echo "OK ($c)"

echo -n "RBAC templates outside_counsel ... "
c=$(code outside_counsel "$API_BASE/templates")
[[ "$c" == "403" ]] || fail "/templates outside_counsel got $c (expected 403)"
echo "OK ($c)"

echo -n "RBAC workflows/approvals land_agent ... "
c=$(code land_agent "$API_BASE/workflows/approvals")
[[ "$c" == "403" ]] || fail "/workflows/approvals land_agent got $c (expected 403)"
echo "OK ($c)"

echo -n "RBAC communications landowner ... "
c=$(code landowner "$API_BASE/communications?parcel_id=PARCEL-001")
[[ "$c" == "403" ]] || fail "/communications landowner got $c (expected 403)"
echo "OK ($c)"

echo -n "RBAC communications land_agent ... "
c=$(code land_agent "$API_BASE/communications?parcel_id=PARCEL-001")
[[ "$c" == "200" ]] || fail "/communications land_agent got $c"
echo "OK ($c)"

echo -n "RBAC rules/results land_agent ... "
c=$(code land_agent "$API_BASE/rules/results?parcel_id=PARCEL-001")
[[ "$c" == "200" ]] || fail "/rules/results got $c"
echo "OK ($c)"

echo -n "Invalid persona ... "
c=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Persona: not_a_real_persona" "$API_BASE/templates")
[[ "$c" == "401" ]] || fail "invalid persona got $c (expected 401)"
echo "OK ($c)"

echo -n "Portal invite empty body ... "
c=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "X-Persona: landowner" -H "Content-Type: application/json" "$API_BASE/portal/invites" -d '{}')
[[ "$c" == "422" ]] || fail "portal invites empty got $c (expected 422)"
echo "OK ($c)"

echo "=== All smoke checks passed ==="
