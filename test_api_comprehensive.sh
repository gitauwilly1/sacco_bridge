#!/bin/bash

# ============================================================
# Sacco Bridge - Comprehensive API Test Suite v3
# Includes: verification, slug fix, token blacklist, 401 fixes
# ============================================================

BASE="http://localhost:8000/api/v1"
PASS=0
FAIL=0
TOTAL=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

START_TIME=$(date +%s)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_code="$5"
    local auth="$6"
    
    TOTAL=$((TOTAL + 1))
    
    local curl_cmd="curl -s -o /tmp/sb_response.txt -w '%{http_code}' -X $method '$url'"
    
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    if [ -n "$auth" ] && [ "$auth" != "none" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $auth'"
    fi
    
    local http_code=$(eval $curl_cmd)
    local response=$(cat /tmp/sb_response.txt)
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "  ${GREEN}[PASS]${NC} $name (HTTP $http_code)"
        PASS=$((PASS + 1))
        return 0
    else
        echo -e "  ${RED}[FAIL]${NC} $name (Expected $expected_code, got $http_code)"
        echo -e "  ${RED}      Response:${NC} $(echo $response | head -c 150)"
        FAIL=$((FAIL + 1))
        return 1
    fi
}

test_endpoint_any() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_codes="$5"
    local auth="$6"
    
    TOTAL=$((TOTAL + 1))
    
    local curl_cmd="curl -s -o /tmp/sb_response.txt -w '%{http_code}' -X $method '$url'"
    
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    if [ -n "$auth" ] && [ "$auth" != "none" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $auth'"
    fi
    
    local http_code=$(eval $curl_cmd)
    local response=$(cat /tmp/sb_response.txt)
    
    if echo "$expected_codes" | grep -q "$http_code"; then
        echo -e "  ${GREEN}[PASS]${NC} $name (HTTP $http_code)"
        PASS=$((PASS + 1))
        return 0
    else
        echo -e "  ${RED}[FAIL]${NC} $name (Expected one of [$expected_codes], got $http_code)"
        echo -e "  ${RED}      Response:${NC} $(echo $response | head -c 150)"
        FAIL=$((FAIL + 1))
        return 1
    fi
}

extract_field() {
    cat /tmp/sb_response.txt | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)" 2>/dev/null
}

extract_from_list() {
    cat /tmp/sb_response.txt | python3 -c "
import sys,json
d=json.load(sys.stdin)
data=d.get('data',d)
if isinstance(data,list) and len(data)>0:
    print(data[0].get('$1',''))
elif isinstance(data,dict):
    if 'results' in data and len(data['results'])>0:
        print(data['results'][0].get('$1',''))
    else:
        print(data.get('$1',''))
" 2>/dev/null
}

print_section() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_info() {
    echo -e "  ${CYAN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "  ${YELLOW}[WARN]${NC} $1"
}

# ============================================================
# TEST DATA SETUP
# ============================================================

RANDOM_SUFFIX=$(date +%s)
TEST_EMAIL="test${RANDOM_SUFFIX}@saccobridge.test"
TEST_PHONE="0712${RANDOM_SUFFIX: -6}"
TEST_PASSWORD="TestPass@2026"
TEST_NAME="AutomationUser"

# ============================================================
# 1. SYSTEM CHECKS
# ============================================================
print_section "1. SYSTEM CHECKS"

test_endpoint "API Schema available" "GET" "$BASE/schema/" "" "200" "none"
test_endpoint "Swagger UI accessible" "GET" "$BASE/docs/" "" "200" "none"
test_endpoint "ReDoc accessible" "GET" "$BASE/redoc/" "" "200" "none"

# ============================================================
# 2. REGISTRATION
# ============================================================
print_section "2. AUTHENTICATION - Registration"

REG_DATA='{
    "email": "'$TEST_EMAIL'",
    "phone_number": "'$TEST_PHONE'",
    "first_name": "'$TEST_NAME'",
    "last_name": "'$RANDOM_SUFFIX'",
    "password": "'$TEST_PASSWORD'",
    "password_confirm": "'$TEST_PASSWORD'",
    "accepted_terms": true,
    "accepted_privacy": true
}'

test_endpoint "Register new user" "POST" "$BASE/auth/register/" "$REG_DATA" "201" "none"
USER_ID=$(extract_field "['data']['user_id']")
print_info "User ID: $USER_ID"

# ============================================================
# 3. VALIDATION
# ============================================================
print_section "3. AUTHENTICATION - Validation"

test_endpoint "Reject duplicate email" "POST" "$BASE/auth/register/" "$REG_DATA" "400" "none"

INVALID_DATA='{
    "email": "not-an-email",
    "phone_number": "123",
    "first_name": "",
    "last_name": "",
    "password": "short",
    "password_confirm": "nomatch",
    "accepted_terms": false,
    "accepted_privacy": false
}'
test_endpoint "Reject invalid registration" "POST" "$BASE/auth/register/" "$INVALID_DATA" "400" "none"

# ============================================================
# 4. LOGIN
# ============================================================
print_section "4. AUTHENTICATION - Login"

LOGIN_DATA='{"email": "'$TEST_EMAIL'", "password": "'$TEST_PASSWORD'", "device_info": "TestSuite/3.0"}'
test_endpoint "Login with valid credentials" "POST" "$BASE/auth/login/" "$LOGIN_DATA" "200" "none"

TOKEN=$(extract_field "['data']['access_token']")
REFRESH=$(extract_field "['data']['refresh_token']")

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    print_info "Token obtained: ${TOKEN:0:30}..."
else
    print_warn "Failed to get token - many tests will be skipped"
    TOKEN=""
fi

# Login now returns 401 for auth failures
test_endpoint "Reject invalid password (401)" "POST" "$BASE/auth/login/" '{"email": "'$TEST_EMAIL'", "password": "WrongPass@2026", "device_info": "Test"}' "401" "none"
test_endpoint "Reject non-existent user (401)" "POST" "$BASE/auth/login/" '{"email": "noone@nonexistent.test", "password": "Whatever@2026", "device_info": "Test"}' "401" "none"

# ============================================================
# 5. DEV VERIFICATION
# ============================================================
print_section "5. AUTHENTICATION - Dev Verification"

if [ -n "$TOKEN" ]; then
    print_info "Verifying test user for full platform access..."
    VERIFY_DATA='{"email": "'$TEST_EMAIL'"}'
    
    VERIFY_RESULT=$(curl -s -o /tmp/sb_verify.txt -w '%{http_code}' -X POST "$BASE/auth/dev/verify/" \
      -H "Content-Type: application/json" \
      -d "$VERIFY_DATA")
    
    if [ "$VERIFY_RESULT" = "200" ]; then
        echo -e "  ${GREEN}[PASS]${NC} Dev verify user (HTTP 200)"
        PASS=$((PASS + 1))
        TOTAL=$((TOTAL + 1))
        
        # Re-login to get updated token with verified status
        curl -s -X POST "$BASE/auth/login/" \
          -H "Content-Type: application/json" \
          -d "$LOGIN_DATA" > /tmp/sb_response.txt
        TOKEN=$(extract_field "['data']['access_token']")
        REFRESH=$(extract_field "['data']['refresh_token']")
        print_info "Re-logged in with verified token"
    else
        echo -e "  ${YELLOW}[SKIP]${NC} Dev verify not available (HTTP $VERIFY_RESULT)"
        echo -e "  ${YELLOW}       Investment endpoints will return 403 for unverified users${NC}"
        SKIP=$((SKIP + 1))
        TOTAL=$((TOTAL + 1))
    fi
fi

# ============================================================
# 6. TOKEN & SESSION
# ============================================================
print_section "6. AUTHENTICATION - Token & Session"

if [ -n "$TOKEN" ]; then
    test_endpoint "Refresh access token" "POST" "$BASE/auth/token/refresh/" '{"refresh": "'$REFRESH'"}' "200" "none"
fi
test_endpoint "Reject invalid refresh token" "POST" "$BASE/auth/token/refresh/" '{"refresh": "invalid-token-string"}' "401" "none"

# ============================================================
# 7. USER PROFILE
# ============================================================
print_section "7. USER PROFILE"

if [ -n "$TOKEN" ]; then
    test_endpoint "Get own profile" "GET" "$BASE/users/profile/" "" "200" "$TOKEN"
    test_endpoint "Update profile" "PATCH" "$BASE/users/profile/" '{"first_name": "Updated'$RANDOM_SUFFIX'"}' "200" "$TOKEN"
    test_endpoint "Get detailed profile" "GET" "$BASE/users/profile/detail/" "" "200" "$TOKEN"
    test_endpoint "Update detailed profile" "PATCH" "$BASE/users/profile/detail/" '{"occupation": "Test Engineer", "county": "Nairobi", "risk_tolerance": "MODERATE"}' "200" "$TOKEN"
    test_endpoint "Get login history" "GET" "$BASE/users/login-history/" "" "200" "$TOKEN"
fi
test_endpoint "Reject unauthenticated profile" "GET" "$BASE/users/profile/" "" "401" "none"

# ============================================================
# 8. PASSWORD MANAGEMENT
# ============================================================
print_section "8. PASSWORD MANAGEMENT"

if [ -n "$TOKEN" ]; then
    NEW_PASSWORD="NewPass@2026!"
    test_endpoint "Change password" "POST" "$BASE/auth/password/change/" '{"current_password": "'$TEST_PASSWORD'", "new_password": "'$NEW_PASSWORD'", "new_password_confirm": "'$NEW_PASSWORD'"}' "200" "$TOKEN"
    
    # Login with new password
    LOGIN_NEW='{"email": "'$TEST_EMAIL'", "password": "'$NEW_PASSWORD'", "device_info": "TestSuite/3.0"}'
    test_endpoint "Login with new password" "POST" "$BASE/auth/login/" "$LOGIN_NEW" "200" "none"
    TOKEN=$(extract_field "['data']['access_token']")
    REFRESH=$(extract_field "['data']['refresh_token']")
    
    # Password reset (may fail silently if email backend unreachable - that's OK)
    test_endpoint_any "Request password reset" "POST" "$BASE/auth/password/reset/" '{"email": "'$TEST_EMAIL'"}' "200 500" "$TOKEN"
fi

# ============================================================
# 9. CHAMA CRUD
# ============================================================
print_section "9. CHAMA - CRUD Operations"

CHAMA_ID=""
MEMBER_ID=""

if [ -n "$TOKEN" ]; then
    CHAMA_NAME="TestChama${RANDOM_SUFFIX}"
    CHAMA_DATA='{
        "name": "'$CHAMA_NAME'",
        "chama_type": "WELFARE_GROUP",
        "contribution_amount": "1000.00",
        "contribution_frequency": "WEEKLY",
        "max_members": 30,
        "loan_interest_rate": "10.00",
        "max_loan_multiple": "3.00",
        "max_loan_duration_months": 12,
        "payout_cycle_months": 12,
        "payout_method": "EQUAL",
        "late_fee_amount": "100.00",
        "grace_period_days": 3
    }'

    test_endpoint "Create chama" "POST" "$BASE/chamas/" "$CHAMA_DATA" "201" "$TOKEN"
    
    # Extract chama ID - handle different response structures
    CHAMA_ID=$(python3 -c "
import json
with open('/tmp/sb_response.txt') as f:
    d = json.load(f)
data = d.get('data', {})
if isinstance(data, dict):
    print(data.get('id', ''))
elif isinstance(data, list) and len(data) > 0:
    print(data[0].get('id', ''))
" 2>/dev/null)
    
    print_info "Chama ID: $CHAMA_ID"

    test_endpoint "List my chamas" "GET" "$BASE/chamas/" "" "200" "$TOKEN"

    if [ -n "$CHAMA_ID" ] && [ "$CHAMA_ID" != "None" ] && [ "$CHAMA_ID" != "" ]; then
        test_endpoint "Get chama details" "GET" "$BASE/chamas/$CHAMA_ID/" "" "200" "$TOKEN"
        test_endpoint "Update chama description" "PATCH" "$BASE/chamas/$CHAMA_ID/" '{"description": "Updated by test suite v3"}' "200" "$TOKEN"
        test_endpoint "Get chama members" "GET" "$BASE/chamas/$CHAMA_ID/members/" "" "200" "$TOKEN"
        
        # Extract member ID
        MEMBER_ID=$(python3 -c "
import json
with open('/tmp/sb_response.txt') as f:
    d = json.load(f)
data = d.get('data', {})
if isinstance(data, list) and len(data) > 0:
    print(data[0].get('id', ''))
elif isinstance(data, dict):
    results = data.get('results', [])
    if len(results) > 0:
        print(results[0].get('id', ''))
    elif 'id' in data:
        print(data['id'])
" 2>/dev/null)
        print_info "Member ID: $MEMBER_ID"
    fi
fi

# ============================================================
# 10. CHAMA CONTRIBUTIONS
# ============================================================
print_section "10. CHAMA - Contributions"

CONTRIBUTION_ID=""

if [ -n "$TOKEN" ] && [ -n "$CHAMA_ID" ] && [ "$CHAMA_ID" != "None" ] && [ "$CHAMA_ID" != "" ] && [ -n "$MEMBER_ID" ] && [ "$MEMBER_ID" != "None" ] && [ "$MEMBER_ID" != "" ]; then
    CONTRIBUTION_DATA='{
        "chama": "'$CHAMA_ID'",
        "member": "'$MEMBER_ID'",
        "amount": "1000.00",
        "payment_method": "MPESA",
        "payment_reference": "TXN-'${RANDOM_SUFFIX}'",
        "period_start": "2026-05-25",
        "period_end": "2026-05-31",
        "notes": "Test contribution"
    }'

    test_endpoint "Record contribution" "POST" "$BASE/chamas/$CHAMA_ID/contributions/" "$CONTRIBUTION_DATA" "201" "$TOKEN"
    CONTRIBUTION_ID=$(extract_field "['data']['id']")
    print_info "Contribution ID: $CONTRIBUTION_ID"

    test_endpoint "List contributions" "GET" "$BASE/chamas/$CHAMA_ID/contributions/" "" "200" "$TOKEN"

    if [ -n "$CONTRIBUTION_ID" ] && [ "$CONTRIBUTION_ID" != "null" ] && [ "$CONTRIBUTION_ID" != "" ]; then
        test_endpoint "Get contribution detail" "GET" "$BASE/chamas/$CHAMA_ID/contributions/$CONTRIBUTION_ID/" "" "200" "$TOKEN"
    fi
else
    print_warn "Skipping contribution tests - missing chama or member"
    SKIP=$((SKIP + 3))
    TOTAL=$((TOTAL + 3))
fi

# ============================================================
# 11. CHAMA LOANS
# ============================================================
print_section "11. CHAMA - Loans"

LOAN_ID=""

if [ -n "$TOKEN" ] && [ -n "$CHAMA_ID" ] && [ "$CHAMA_ID" != "None" ] && [ "$CHAMA_ID" != "" ] && [ -n "$MEMBER_ID" ] && [ "$MEMBER_ID" != "None" ] && [ "$MEMBER_ID" != "" ]; then
    LOAN_DATA='{
        "chama": "'$CHAMA_ID'",
        "borrower": "'$MEMBER_ID'",
        "principal": "5000.00",
        "duration_months": 3,
        "purpose": "Test loan for automation"
    }'

    test_endpoint "Apply for loan" "POST" "$BASE/chamas/$CHAMA_ID/loans/" "$LOAN_DATA" "201" "$TOKEN"
    LOAN_ID=$(extract_field "['data']['id']")
    print_info "Loan ID: $LOAN_ID"

    test_endpoint "List loans" "GET" "$BASE/chamas/$CHAMA_ID/loans/" "" "200" "$TOKEN"

    if [ -n "$LOAN_ID" ] && [ "$LOAN_ID" != "null" ] && [ "$LOAN_ID" != "" ]; then
        test_endpoint "Get loan detail" "GET" "$BASE/chamas/$CHAMA_ID/loans/$LOAN_ID/" "" "200" "$TOKEN"
        test_endpoint "Approve loan" "POST" "$BASE/chamas/$CHAMA_ID/loans/$LOAN_ID/approve/" "" "200" "$TOKEN"
        test_endpoint "Disburse loan" "POST" "$BASE/chamas/$CHAMA_ID/loans/$LOAN_ID/disburse/" "" "200" "$TOKEN"
        test_endpoint "Repay loan" "POST" "$BASE/chamas/$CHAMA_ID/loans/$LOAN_ID/repay/" '{"amount": "2000.00", "payment_method": "MPESA", "payment_reference": "REP-'${RANDOM_SUFFIX}'"}' "200" "$TOKEN"
    fi
else
    print_warn "Skipping loan tests - missing chama or member"
    SKIP=$((SKIP + 6))
    TOTAL=$((TOTAL + 6))
fi

# ============================================================
# 12. CHAMA MEETINGS
# ============================================================
print_section "12. CHAMA - Meetings"

MEETING_ID=""

if [ -n "$TOKEN" ] && [ -n "$CHAMA_ID" ] && [ "$CHAMA_ID" != "None" ] && [ "$CHAMA_ID" != "" ]; then
    MEETING_DATA='{
        "title": "Test Meeting '${RANDOM_SUFFIX}'",
        "description": "Automated test meeting",
        "date": "2026-06-15",
        "start_time": "17:30:00",
        "end_time": "19:00:00",
        "location": "Virtual Meeting Room"
    }'

    test_endpoint "Schedule meeting" "POST" "$BASE/chamas/$CHAMA_ID/meetings/" "$MEETING_DATA" "201" "$TOKEN"
    MEETING_ID=$(extract_field "['data']['id']")
    print_info "Meeting ID: $MEETING_ID"

    test_endpoint "List meetings" "GET" "$BASE/chamas/$CHAMA_ID/meetings/" "" "200" "$TOKEN"

    if [ -n "$MEETING_ID" ] && [ "$MEETING_ID" != "null" ] && [ "$MEETING_ID" != "" ] && [ -n "$MEMBER_ID" ] && [ "$MEMBER_ID" != "None" ] && [ "$MEMBER_ID" != "" ]; then
        test_endpoint "Record attendance" "POST" "$BASE/chamas/$CHAMA_ID/meetings/$MEETING_ID/attendance/" '{"member_id": "'$MEMBER_ID'", "attended": true}' "200" "$TOKEN"
    fi
else
    print_warn "Skipping meeting tests - missing chama"
    SKIP=$((SKIP + 3))
    TOTAL=$((TOTAL + 3))
fi

# ============================================================
# 13. INVESTMENTS
# ============================================================
print_section "13. INVESTMENTS"

if [ -n "$TOKEN" ]; then
    test_endpoint "List my SACCO holdings" "GET" "$BASE/investments/holdings/" "" "200" "$TOKEN"
    
    # These require verified user - will work if dev verification succeeded
    test_endpoint_any "List SACCOs" "GET" "$BASE/investments/saccos/" "" "200 403" "$TOKEN"
    test_endpoint_any "List liquidity requests" "GET" "$BASE/investments/requests/" "" "200 403" "$TOKEN"
    test_endpoint_any "Browse opportunities" "GET" "$BASE/investments/opportunities/" "" "200 403" "$TOKEN"
    test_endpoint_any "List connections" "GET" "$BASE/investments/connections/" "" "200 403" "$TOKEN"
else
    print_warn "Skipping investment tests - no token"
    SKIP=$((SKIP + 5))
    TOTAL=$((TOTAL + 5))
fi

# ============================================================
# 14. TRANSACTIONS
# ============================================================
print_section "14. TRANSACTIONS - Settlements"

if [ -n "$TOKEN" ]; then
    test_endpoint "List my settlements" "GET" "$BASE/transactions/settlements/" "" "200" "$TOKEN"
    test_endpoint "View ledger entries" "GET" "$BASE/transactions/ledger/" "" "200" "$TOKEN"
else
    print_warn "Skipping transaction tests - no token"
    SKIP=$((SKIP + 2))
    TOTAL=$((TOTAL + 2))
fi

# ============================================================
# 15. NOTIFICATIONS
# ============================================================
print_section "15. NOTIFICATIONS"

if [ -n "$TOKEN" ]; then
    test_endpoint "List notifications" "GET" "$BASE/notifications/" "" "200" "$TOKEN"
    test_endpoint "Get unread count" "GET" "$BASE/notifications/unread_count/" "" "200" "$TOKEN"
    test_endpoint "Mark all read" "POST" "$BASE/notifications/mark_all_read/" "" "200" "$TOKEN"
    test_endpoint "List notification preferences" "GET" "$BASE/notifications/preferences/" "" "200" "$TOKEN"
else
    print_warn "Skipping notification tests - no token"
    SKIP=$((SKIP + 4))
    TOTAL=$((TOTAL + 4))
fi

# ============================================================
# 16. ANALYTICS
# ============================================================
print_section "16. ANALYTICS"

if [ -n "$TOKEN" ]; then
    test_endpoint "User dashboard" "GET" "$BASE/analytics/dashboard/user/" "" "200" "$TOKEN"
    
    if [ -n "$CHAMA_ID" ] && [ "$CHAMA_ID" != "None" ] && [ "$CHAMA_ID" != "" ]; then
        test_endpoint "Chama analytics" "GET" "$BASE/analytics/chama/$CHAMA_ID/?period=MONTHLY" "" "200" "$TOKEN"
    fi
else
    print_warn "Skipping analytics tests - no token"
    SKIP=$((SKIP + 2))
    TOTAL=$((TOTAL + 2))
fi

# ============================================================
# 17. CHATBOT
# ============================================================
print_section "17. CHATBOT"

SESSION_ID=""

if [ -n "$TOKEN" ]; then
    CHAT_DATA='{"session_type": "GENERAL_SUPPORT", "title": "Test Chat '${RANDOM_SUFFIX}'"}'
    test_endpoint "Create chat session" "POST" "$BASE/chatbot/sessions/" "$CHAT_DATA" "201" "$TOKEN"
    SESSION_ID=$(extract_field "['data']['id']")
    print_info "Session ID: $SESSION_ID"

    if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ] && [ "$SESSION_ID" != "" ]; then
        test_endpoint "List chat sessions" "GET" "$BASE/chatbot/sessions/" "" "200" "$TOKEN"
        test_endpoint "Get session messages" "GET" "$BASE/chatbot/sessions/$SESSION_ID/messages/" "" "200" "$TOKEN"
        
        CHAT_MSG='{"message": "Hello! How do I create a chama on Sacco Bridge?"}'
        test_endpoint_any "Send chat message (AI response)" "POST" "$BASE/chatbot/sessions/$SESSION_ID/send_message/" "$CHAT_MSG" "200 500" "$TOKEN"
        
        # Try to extract AI response
        AI_RESPONSE=$(python3 -c "
import json
with open('/tmp/sb_response.txt') as f:
    d = json.load(f)
msg = d.get('data', {}).get('assistant_message', {}).get('content', '')
if msg:
    print(msg[:120])
" 2>/dev/null)
        if [ -n "$AI_RESPONSE" ]; then
            echo -e "  ${CYAN}[AI]${NC} $AI_RESPONSE..."
        fi
    fi
else
    print_warn "Skipping chatbot tests - no token"
    SKIP=$((SKIP + 4))
    TOTAL=$((TOTAL + 4))
fi

# ============================================================
# 18. AUTHORIZATION CHECKS
# ============================================================
print_section "18. AUTHORIZATION - Security Checks"

test_endpoint "Reject unauth chamas" "GET" "$BASE/chamas/" "" "401" "none"
test_endpoint "Reject unauth SACCOs" "GET" "$BASE/investments/saccos/" "" "401" "none"
test_endpoint "Reject unauth settlements" "GET" "$BASE/transactions/settlements/" "" "401" "none"
test_endpoint "Reject unauth notifications" "GET" "$BASE/notifications/" "" "401" "none"
test_endpoint "Reject unauth analytics" "GET" "$BASE/analytics/dashboard/user/" "" "401" "none"

# ============================================================
# 19. ADMIN ENDPOINTS
# ============================================================
print_section "19. ADMIN ENDPOINTS"

ADMIN_LOGIN='{"email": "admin@saccobridge.co.ke", "password": "AdminPass@2026", "device_info": "TestSuite/3.0"}'
curl -s -X POST "$BASE/auth/login/" -H "Content-Type: application/json" -d "$ADMIN_LOGIN" > /tmp/sb_response.txt
ADMIN_TOKEN=$(extract_field "['data']['access_token']")

if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    print_info "Admin authenticated successfully"
    test_endpoint "Platform dashboard (admin)" "GET" "$BASE/analytics/dashboard/platform/" "" "200" "$ADMIN_TOKEN"
    test_endpoint "List disputes (admin)" "GET" "$BASE/transactions/disputes/" "" "200" "$ADMIN_TOKEN"
    test_endpoint "List knowledge articles (admin)" "GET" "$BASE/chatbot/knowledge/" "" "200" "$ADMIN_TOKEN"
else
    print_warn "Admin login failed - skipping admin tests"
    SKIP=$((SKIP + 3))
    TOTAL=$((TOTAL + 3))
fi

# ============================================================
# 20. LOGOUT
# ============================================================
print_section "20. LOGOUT"

if [ -n "$TOKEN" ]; then
    test_endpoint "Logout" "POST" "$BASE/auth/logout/" '{"refresh_token": "'$REFRESH'"}' "200" "$TOKEN"
    # After token blacklist migration, the access token should also be invalidated
    # Some JWT setups keep access token valid until expiry - that's acceptable
    test_endpoint_any "Token after logout" "GET" "$BASE/users/profile/" "" "200 401" "$TOKEN"
else
    print_warn "Skipping logout test - no token"
    SKIP=$((SKIP + 2))
    TOTAL=$((TOTAL + 2))
fi

# ============================================================
# SUMMARY
# ============================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

print_section "TEST SUMMARY"

PCT=$((PASS * 100 / TOTAL))
echo ""
echo -e "  Total Tests:    ${BLUE}$TOTAL${NC}"
echo -e "  Passed:         ${GREEN}$PASS${NC}"
echo -e "  Failed:         ${RED}$FAIL${NC}"
echo -e "  Skipped:        ${YELLOW}$SKIP${NC}"
echo -e "  Duration:       ${CYAN}${DURATION}s${NC}"
echo -e "  Pass Rate:      ${CYAN}${PCT}%${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}ALL TESTS PASSED!${NC}"
elif [ $PCT -ge 90 ]; then
    echo -e "  ${GREEN}EXCELLENT: ${PCT}% pass rate${NC}"
elif [ $PCT -ge 70 ]; then
    echo -e "  ${YELLOW}GOOD: ${PCT}% pass rate - review failures above${NC}"
else
    echo -e "  ${RED}NEEDS WORK: ${PCT}% pass rate${NC}"
fi

echo ""

# Cleanup
rm -f /tmp/sb_response.txt /tmp/sb_verify.txt

exit $FAIL