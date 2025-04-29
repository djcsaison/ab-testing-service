#!/bin/bash

# A/B Testing Service Test Script
# This script tests the full A/B testing workflow:
# 1. Authentication
# 2. Create an experiment
# 3. Assign users to variants
# 4. Track impressions for all users
# 5. Track conversions for every third user
# 6. Analyze results

# Configuration
HOST="localhost:8000"
API_URL="http://$HOST/api"
AUTH_USERNAME="admin"
AUTH_PASSWORD="password"
EXPERIMENT_NAME="test_experiment_$(date +%s)"
NUM_USERS=300
CONVERSION_RATE=3  # Every 3rd user will convert

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create temporary files to store results
RESULTS_DIR="./ab_test_results_$(date +%s)"
mkdir -p $RESULTS_DIR
ASSIGNMENTS_FILE="$RESULTS_DIR/assignments.json"
IMPRESSION_FILE="$RESULTS_DIR/impressions.json"
CONVERSION_FILE="$RESULTS_DIR/conversions.json"
STATS_FILE="$RESULTS_DIR/experiment_stats.json"

echo -e "${BLUE}A/B Testing Service Test Script${NC}"
echo -e "${BLUE}================================${NC}"

# Function to make authenticated API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local output_file=$4

    if [ -n "$data" ]; then
        if [ -n "$output_file" ]; then
            curl -s -X "$method" \
                "$API_URL$endpoint" \
                -u "$AUTH_USERNAME:$AUTH_PASSWORD" \
                -H 'Content-Type: application/json' \
                -d "$data" > "$output_file"
            return $?
        else
            curl -s -X "$method" \
                "$API_URL$endpoint" \
                -u "$AUTH_USERNAME:$AUTH_PASSWORD" \
                -H 'Content-Type: application/json' \
                -d "$data"
            return $?
        fi
    else
        if [ -n "$output_file" ]; then
            curl -s -X "$method" \
                "$API_URL$endpoint" \
                -u "$AUTH_USERNAME:$AUTH_PASSWORD" \
                -H 'Content-Type: application/json' > "$output_file"
            return $?
        else
            curl -s -X "$method" \
                "$API_URL$endpoint" \
                -u "$AUTH_USERNAME:$AUTH_PASSWORD" \
                -H 'Content-Type: application/json'
            return $?
        fi
    fi
}

# Step 1: Check if the service is running
echo -e "\n${YELLOW}Step 1: Checking if the service is running...${NC}"
health_check=$(curl -s "$API_URL/health")
if [[ "$health_check" == *"healthy"* ]]; then
    echo -e "${GREEN}Service is running!${NC}"
else
    echo -e "${RED}Service doesn't appear to be running. Please start the service first.${NC}"
    echo "$health_check"
    exit 1
fi

# Step 2: Create a test experiment
echo -e "\n${YELLOW}Step 2: Creating a test experiment...${NC}"
experiment_data='{
    "name": "'$EXPERIMENT_NAME'",
    "description": "Automated test experiment",
    "variants": [
        {"name": "control", "description": "Control variant", "weight": 50, "is_control": true},
        {"name": "treatment", "description": "Treatment variant", "weight": 50, "is_control": false}
    ],
    "status": "active",
    "total_population": 1000,
    "base_rate": 0.1,
    "min_detectable_effect": 0.05,
    "min_sample_size_per_group": 200,
    "confidence_level": 0.95
}'

experiment_response=$(api_call "POST" "/experiments" "$experiment_data")
echo "$experiment_response" > "$RESULTS_DIR/experiment_creation.json"

if [[ "$experiment_response" == *"$EXPERIMENT_NAME"* ]]; then
    echo -e "${GREEN}Experiment created successfully: $EXPERIMENT_NAME${NC}"
else
    echo -e "${RED}Failed to create experiment:${NC}"
    echo "$experiment_response"
    exit 1
fi

# Step 3: Assign users to variants
echo -e "\n${YELLOW}Step 3: Assigning $NUM_USERS users to variants...${NC}"
control_count=0
treatment_count=0
successful_assignments=0

echo "[" > $ASSIGNMENTS_FILE
for i in $(seq 1 $NUM_USERS); do
    user_id="test_user_$(date +%s)_$i"
    
    assignment_data="{\"subid\":\"$user_id\",\"experiment_id\":\"$EXPERIMENT_NAME\"}"
    assignment_response=$(api_call "POST" "/assignments/get" "$assignment_data")
    
    # Save to assignments file (comma for all except the last one)
    if [ $i -lt $NUM_USERS ]; then
        echo "$assignment_response," >> $ASSIGNMENTS_FILE
    else
        echo "$assignment_response" >> $ASSIGNMENTS_FILE
    fi
    
    # Extract the variant
    variant=$(echo "$assignment_response" | grep -o '"variant":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$variant" ]; then
        successful_assignments=$((successful_assignments + 1))
        
        # Count by variant
        if [ "$variant" == "control" ]; then
            control_count=$((control_count + 1))
        elif [ "$variant" == "treatment" ]; then
            treatment_count=$((treatment_count + 1))
        fi
        
        # Show progress
        if [ $((i % 50)) -eq 0 ]; then
            echo -e "  Processed $i users (Control: $control_count, Treatment: $treatment_count)"
        fi
    else
        echo -e "${RED}  Failed to assign user $user_id: $assignment_response${NC}"
    fi
done
echo "]" >> $ASSIGNMENTS_FILE

echo -e "${GREEN}Assignment complete: $successful_assignments successful assignments${NC}"
echo -e "  Control: $control_count users"
echo -e "  Treatment: $treatment_count users"

# Step 4: Track impressions for all users
echo -e "\n${YELLOW}Step 4: Tracking impressions for all users...${NC}"
successful_impressions=0

echo "[" > $IMPRESSION_FILE
for i in $(seq 1 $NUM_USERS); do
    user_id="test_user_$(date +%s)_$i"
    
    impression_response=$(api_call "POST" "/events/impression?subid=$user_id&experiment_id=$EXPERIMENT_NAME" "")
    
    # Save to impressions file
    if [ $i -lt $NUM_USERS ]; then
        echo "$impression_response," >> $IMPRESSION_FILE
    else
        echo "$impression_response" >> $IMPRESSION_FILE
    fi
    
    # Check for success
    if [[ "$impression_response" == *"experiment_id"* ]]; then
        successful_impressions=$((successful_impressions + 1))
    else
        echo -e "${RED}  Failed to track impression for user $user_id: $impression_response${NC}"
    fi
    
    # Show progress
    if [ $((i % 50)) -eq 0 ]; then
        echo -e "  Processed $i impressions"
    fi
done
echo "]" >> $IMPRESSION_FILE

echo -e "${GREEN}Impression tracking complete: $successful_impressions successful impressions${NC}"

# Step 5: Track conversions for every Nth user (based on CONVERSION_RATE)
echo -e "\n${YELLOW}Step 5: Tracking conversions for every $CONVERSION_RATE user...${NC}"
successful_conversions=0
expected_conversions=$((NUM_USERS / CONVERSION_RATE))

echo "[" > $CONVERSION_FILE
for i in $(seq 1 $NUM_USERS); do
    # Only convert every Nth user
    if [ $((i % CONVERSION_RATE)) -eq 0 ]; then
        user_id="test_user_$(date +%s)_$i"
        
        conversion_response=$(api_call "POST" "/events/conversion?subid=$user_id&experiment_id=$EXPERIMENT_NAME" "")
        
        # Save to conversions file (comma for all except potentially the last one)
        if [ $successful_conversions -lt $((expected_conversions - 1)) ]; then
            echo "$conversion_response," >> $CONVERSION_FILE
        else
            echo "$conversion_response" >> $CONVERSION_FILE
        fi
        
        # Check for success
        if [[ "$conversion_response" == *"experiment_id"* ]]; then
            successful_conversions=$((successful_conversions + 1))
        else
            echo -e "${RED}  Failed to track conversion for user $user_id: $conversion_response${NC}"
        fi
        
        # Show progress every 10 conversions
        if [ $((successful_conversions % 10)) -eq 0 ]; then
            echo -e "  Processed $successful_conversions conversions"
        fi
    fi
done
echo "]" >> $CONVERSION_FILE

echo -e "${GREEN}Conversion tracking complete: $successful_conversions conversions${NC}"

# Step 6: Get experiment statistics
echo -e "\n${YELLOW}Step 6: Getting experiment statistics...${NC}"
api_call "GET" "/experiments/$EXPERIMENT_NAME/stats?include_analysis=true" "" "$STATS_FILE"

# Extract conversion rates and display them
control_rate=$(grep -o '"control":{"conversions":[0-9]*,"impressions":[0-9]*,"rate":[0-9.]*' "$STATS_FILE" | grep -o 'rate":[0-9.]*' | cut -d':' -f2)
treatment_rate=$(grep -o '"treatment":{"conversions":[0-9]*,"impressions":[0-9]*,"rate":[0-9.]*' "$STATS_FILE" | grep -o 'rate":[0-9.]*' | cut -d':' -f2)

echo -e "${GREEN}Experiment statistics retrieved${NC}"
echo -e "  Control conversion rate: ${BLUE}$control_rate${NC}"
echo -e "  Treatment conversion rate: ${BLUE}$treatment_rate${NC}"

# Step 7: Summary
echo -e "\n${YELLOW}Step 7: Test Summary${NC}"
echo -e "${GREEN}Test completed successfully!${NC}"
echo -e "  Experiment: $EXPERIMENT_NAME"
echo -e "  Users assigned: $successful_assignments / $NUM_USERS"
echo -e "  Impressions tracked: $successful_impressions"
echo -e "  Conversions tracked: $successful_conversions"
echo -e "  Results stored in: $RESULTS_DIR"

echo -e "\n${BLUE}To view full experiment statistics:${NC}"
echo -e "  Visit: http://$HOST/api/docs and use credentials: $AUTH_USERNAME / $AUTH_PASSWORD"
echo -e "  Or run: curl -u '$AUTH_USERNAME:$AUTH_PASSWORD' '$API_URL/experiments/$EXPERIMENT_NAME/stats?include_analysis=true'"

exit 0
