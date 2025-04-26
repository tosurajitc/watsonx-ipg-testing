#!/bin/bash
# Health check script for watsonx-ipg-testing
# Verifies that the deployed application is running correctly

set -e  # Exit immediately if a command exits with a non-zero status

# Parse command line arguments
DEPLOY_URL=$1
MAX_RETRIES=10
RETRY_INTERVAL=5

if [ -z "$DEPLOY_URL" ]; then
    echo "Usage: $0 <deploy_url>"
    echo "  deploy_url: The URL of the deployed application"
    exit 1
fi

echo "Starting health check for $DEPLOY_URL"

# Function to check if application is healthy
check_health() {
    # This is a placeholder - replace with actual health check logic
    # For now, we'll just use curl to check if the URL returns a 200 status code
    
    # For local testing (without actual endpoint)
    if [[ $DEPLOY_URL == *"localhost"* ]]; then
        echo "Local deployment detected, simulating health check"
        return 0
    fi
    
    # Use curl to check HTTP status code
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $DEPLOY_URL/health)
    
    if [ "$HTTP_STATUS" -eq 200 ]; then
        echo "Health check passed: HTTP status $HTTP_STATUS"
        return 0
    else
        echo "Health check failed: HTTP status $HTTP_STATUS"
        return 1
    fi
}

# Try health check with retries
echo "Performing health check (will try up to $MAX_RETRIES times)"
for i in $(seq 1 $MAX_RETRIES); do
    echo "Health check attempt $i of $MAX_RETRIES"
    
    if check_health; then
        echo "Application is healthy"
        exit 0
    else
        echo "Application not healthy yet, retrying in $RETRY_INTERVAL seconds"
        sleep $RETRY_INTERVAL
    fi
done

echo "Health check failed after $MAX_RETRIES attempts"
exit 1
