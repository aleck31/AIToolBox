#!/bin/bash
# delete_test_resources.sh
# Script to delete AWS resources configured in .env file for testing environment

set -e  # Exit on error

# Text colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
AWS_PROFILE=""

# Function to display messages
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -p, --profile PROFILE_NAME  AWS CLI profile to use"
    echo "  -r, --region REGION         AWS region to use (overrides .env)"
    echo "  -h, --help                  Show this help message"
    echo
    echo "Example:"
    echo "  $0 --profile myprofile --region us-west-2"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        -r|--region)
            OVERRIDE_REGION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            warn "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to build AWS CLI command with profile if specified
aws_cmd() {
    if [ -z "$AWS_PROFILE" ]; then
        aws "$@"
    else
        aws --profile "$AWS_PROFILE" "$@"
    fi
}

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    log "Checking AWS CLI configuration..."
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it and try again."
    fi
    
    if [ -z "$AWS_PROFILE" ]; then
        if ! aws sts get-caller-identity &> /dev/null; then
            error "AWS CLI is not configured properly. Please run 'aws configure' first or specify a profile with --profile."
        fi
    else
        if ! aws --profile "$AWS_PROFILE" sts get-caller-identity &> /dev/null; then
            error "AWS profile '$AWS_PROFILE' is not configured properly. Please check your AWS credentials."
        fi
    fi
    
    success "AWS CLI is configured properly."
}

# Function to load environment variables from .env file
load_env_vars() {
    log "Loading environment variables from .env file..."
    
    ENV_FILE="../.env"
    if [ ! -f "$ENV_FILE" ]; then
        error ".env file not found at $ENV_FILE"
    fi
    
    # Source the .env file to get variables
    source "$ENV_FILE"
    
    # Override region if specified
    if [ ! -z "$OVERRIDE_REGION" ]; then
        AWS_REGION="$OVERRIDE_REGION"
        log "Using region from command line: $AWS_REGION"
    fi
    
    # Check required variables
    if [ -z "$AWS_REGION" ]; then
        error "AWS_REGION is not defined in .env file."
    fi
    
    if [ -z "$SETTING_TABLE" ]; then
        warn "SETTING_TABLE is not defined in .env file."
    fi
    
    if [ -z "$SESSION_TABLE" ]; then
        warn "SESSION_TABLE is not defined in .env file."
    fi
    
    if [ -z "$USER_POOL_ID" ]; then
        warn "USER_POOL_ID is not defined in .env file."
    fi
    
    success "Environment variables loaded successfully."
}

# Function to delete DynamoDB tables
delete_dynamodb_tables() {
    log "Deleting DynamoDB tables..."
    
    # Delete setting table if defined
    if [ ! -z "$SETTING_TABLE" ]; then
        log "Checking if table $SETTING_TABLE exists..."
        if aws_cmd dynamodb describe-table --table-name "$SETTING_TABLE" --region "$AWS_REGION" &> /dev/null; then
            log "Deleting DynamoDB table: $SETTING_TABLE"
            aws_cmd dynamodb delete-table --table-name "$SETTING_TABLE" --region "$AWS_REGION"
            success "Table $SETTING_TABLE deletion initiated."
        else
            warn "Table $SETTING_TABLE does not exist. Skipping."
        fi
    fi
    
    # Delete session table if defined
    if [ ! -z "$SESSION_TABLE" ]; then
        log "Checking if table $SESSION_TABLE exists..."
        if aws_cmd dynamodb describe-table --table-name "$SESSION_TABLE" --region "$AWS_REGION" &> /dev/null; then
            log "Deleting DynamoDB table: $SESSION_TABLE"
            aws_cmd dynamodb delete-table --table-name "$SESSION_TABLE" --region "$AWS_REGION"
            success "Table $SESSION_TABLE deletion initiated."
        else
            warn "Table $SESSION_TABLE does not exist. Skipping."
        fi
    fi
}

# Function to delete Cognito User Pool
delete_cognito_resources() {
    log "Deleting Cognito resources..."
    
    # Check if we have permission to access Cognito
    if ! aws_cmd cognito-idp help &> /dev/null; then
        warn "No permission to access Cognito or Cognito is not available. Skipping Cognito resource deletion."
        return
    fi
    
    # Delete user pool if defined
    if [ ! -z "$USER_POOL_ID" ]; then
        log "Checking if User Pool $USER_POOL_ID exists..."
        if aws_cmd cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --region "$AWS_REGION" &> /dev/null; then
            # First, list and delete all user pool clients
            log "Listing user pool clients..."
            CLIENT_IDS=$(aws_cmd cognito-idp list-user-pool-clients --user-pool-id "$USER_POOL_ID" --region "$AWS_REGION" --query "UserPoolClients[].ClientId" --output text)
            
            for CLIENT_ID in $CLIENT_IDS; do
                log "Deleting user pool client: $CLIENT_ID"
                aws_cmd cognito-idp delete-user-pool-client --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" --region "$AWS_REGION"
            done
            
            # Then delete the user pool
            log "Deleting Cognito User Pool: $USER_POOL_ID"
            aws_cmd cognito-idp delete-user-pool --user-pool-id "$USER_POOL_ID" --region "$AWS_REGION"
            success "User Pool $USER_POOL_ID deletion initiated."
        else
            warn "User Pool $USER_POOL_ID does not exist. Skipping."
        fi
    fi
}

# Function to wait for resource deletion
wait_for_deletion() {
    log "Waiting for resources to be deleted..."
    
    # Wait for DynamoDB tables to be deleted
    if [ ! -z "$SETTING_TABLE" ]; then
        log "Waiting for table $SETTING_TABLE to be deleted..."
        MAX_RETRIES=30  # 60 seconds max wait time
        RETRY_COUNT=0
        while aws_cmd dynamodb describe-table --table-name "$SETTING_TABLE" --region "$AWS_REGION" &> /dev/null; do
            echo -n "."
            sleep 2
            RETRY_COUNT=$((RETRY_COUNT+1))
            if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
                warn "Timed out waiting for table $SETTING_TABLE to be deleted. It may still be in progress."
                break
            fi
        done
        echo ""
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            success "Table $SETTING_TABLE deleted successfully."
        fi
    fi
    
    if [ ! -z "$SESSION_TABLE" ]; then
        log "Waiting for table $SESSION_TABLE to be deleted..."
        MAX_RETRIES=30  # 60 seconds max wait time
        RETRY_COUNT=0
        while aws_cmd dynamodb describe-table --table-name "$SESSION_TABLE" --region "$AWS_REGION" &> /dev/null; do
            echo -n "."
            sleep 2
            RETRY_COUNT=$((RETRY_COUNT+1))
            if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
                warn "Timed out waiting for table $SESSION_TABLE to be deleted. It may still be in progress."
                break
            fi
        done
        echo ""
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            success "Table $SESSION_TABLE deleted successfully."
        fi
    fi
    
    # Note: Cognito User Pools deletion can't be easily waited for with the AWS CLI
    # We'll just wait a fixed amount of time
    if [ ! -z "$USER_POOL_ID" ]; then
        log "Waiting for User Pool deletion to complete (this may take a few minutes)..."
        sleep 15  # Increased wait time
        success "Resource deletion completed."
    fi
}

# Main function
main() {
    log "Starting cleanup of test resources..."
    
    # Check AWS CLI
    check_aws_cli
    
    # Load environment variables
    load_env_vars
    
    # Delete resources
    delete_dynamodb_tables
    delete_cognito_resources
    
    # Wait for deletion to complete
    wait_for_deletion
    
    # Update .env file to remove deleted resource IDs
    log "Updating .env file to remove deleted resource IDs..."
    sed -i "s/USER_POOL_ID=.*/USER_POOL_ID=/" "../.env"
    sed -i "s/CLIENT_ID=.*/CLIENT_ID=/" "../.env"
    
    success "All test resources have been deleted successfully!"
    log "You can now create a new test environment."
}

# Run main function
main
