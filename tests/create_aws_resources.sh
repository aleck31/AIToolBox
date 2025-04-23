#!/bin/bash
# create_test_resources.sh
# Script to create AWS resources for testing environment based on .env configuration

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
    echo "  -h, --help                  Show this help message"
    echo
    echo "Example:"
    echo "  $0 --profile myprofile"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--profile)
            AWS_PROFILE="$2"
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
    
    # Check required variables
    if [ -z "$AWS_REGION" ]; then
        error "AWS_REGION is not defined in .env file."
    fi
    
    if [ -z "$SETTING_TABLE" ]; then
        error "SETTING_TABLE is not defined in .env file."
    fi
    
    if [ -z "$SESSION_TABLE" ]; then
        error "SESSION_TABLE is not defined in .env file."
    fi
    
    if [ -z "$USER_POOL_NAME" ]; then
        error "USER_POOL_NAME is not defined in .env file."
    fi
    
    if [ -z "$CLIENT_NAME" ]; then
        error "CLIENT_NAME is not defined in .env file."
    fi
    
    success "Environment variables loaded successfully."
}

# Function to create DynamoDB tables
create_dynamodb_tables() {
    log "Creating DynamoDB tables..."
    
    # Check if tables already exist and skip creation if they do
    for TABLE_NAME in "$SETTING_TABLE" "$SESSION_TABLE"; do
        log "Checking if table $TABLE_NAME already exists..."
        if aws_cmd dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
            warn "Table $TABLE_NAME already exists. Skipping creation."
            
            # If it's the session table, make sure TTL is enabled
            if [ "$TABLE_NAME" == "$SESSION_TABLE" ]; then
                log "Ensuring TTL is enabled on existing session table..."
                aws_cmd dynamodb update-time-to-live \
                    --table-name "$SESSION_TABLE" \
                    --time-to-live-specification "Enabled=true, AttributeName=expiration_time" \
                    --region "$AWS_REGION" &> /dev/null || true
            fi
            
            continue
        fi
        
        # Create table if it doesn't exist
        log "Creating DynamoDB table: $TABLE_NAME"
        if [ "$TABLE_NAME" == "$SETTING_TABLE" ]; then
            # Create setting table
            aws_cmd dynamodb create-table \
                --table-name "$TABLE_NAME" \
                --attribute-definitions AttributeName=setting_name,AttributeType=S AttributeName=type,AttributeType=S \
                --key-schema AttributeName=setting_name,KeyType=HASH AttributeName=type,KeyType=RANGE \
                --billing-mode PAY_PER_REQUEST \
                --region "$AWS_REGION" \
                --tags Key=Environment,Value=Test Key=Project,Value=AIToolbox
        else
            # Create session table
            aws_cmd dynamodb create-table \
                --table-name "$TABLE_NAME" \
                --attribute-definitions AttributeName=session_id,AttributeType=S \
                --key-schema AttributeName=session_id,KeyType=HASH \
                --billing-mode PAY_PER_REQUEST \
                --region "$AWS_REGION" \
                --tags Key=Environment,Value=Test Key=Project,Value=AIToolbox
            
            # Wait for table to become active before enabling TTL
            log "Waiting for table $TABLE_NAME to become active..."
            MAX_RETRIES=30  # 60 seconds max wait time
            RETRY_COUNT=0
            while true; do
                STATUS=$(aws_cmd dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" --query "Table.TableStatus" --output text 2>/dev/null)
                if [ "$STATUS" == "ACTIVE" ]; then
                    success "Table $TABLE_NAME is now active."
                    break
                fi
                echo -n "."
                sleep 2
                RETRY_COUNT=$((RETRY_COUNT+1))
                if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
                    warn "Timed out waiting for table $TABLE_NAME to become active. Continuing anyway..."
                    break
                fi
            done
            
            # Enable TTL on session table after it's active
            log "Enabling TTL on session table..."
            aws_cmd dynamodb update-time-to-live \
                --table-name "$TABLE_NAME" \
                --time-to-live-specification "Enabled=true, AttributeName=expiration_time" \
                --region "$AWS_REGION"
        fi
    done
    
    success "DynamoDB tables setup completed."
}

# Function to create Cognito User Pool and Client
create_cognito_resources() {
    log "Creating Cognito resources..."
    
    # Check if we have permission to list user pools
    if ! aws_cmd cognito-idp list-user-pools --max-results 1 --region "$AWS_REGION" &> /dev/null; then
        warn "No permission to list Cognito User Pools. Skipping Cognito resource check."
        warn "Will attempt to create resources directly. This may fail if you don't have sufficient permissions."
    fi
    
    # Check if User Pool ID is already defined in .env and valid
    if [ ! -z "$USER_POOL_ID" ]; then
        log "Checking if User Pool $USER_POOL_ID exists..."
        if aws_cmd cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --region "$AWS_REGION" &> /dev/null; then
            warn "User Pool $USER_POOL_ID already exists. Skipping creation."
            
            # Check if Client ID is already defined and valid
            if [ ! -z "$CLIENT_ID" ]; then
                log "Checking if Client $CLIENT_ID exists..."
                if aws_cmd cognito-idp describe-user-pool-client --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" --region "$AWS_REGION" &> /dev/null; then
                    warn "Client $CLIENT_ID already exists. Skipping creation."
                    success "Using existing Cognito resources."
                    return
                fi
            fi
            
            # Create new client if needed
            log "Creating User Pool Client: $CLIENT_NAME"
            CLIENT_RESULT=$(aws_cmd cognito-idp create-user-pool-client \
                --user-pool-id "$USER_POOL_ID" \
                --client-name "$CLIENT_NAME" \
                --no-generate-secret \
                --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
                --region "$AWS_REGION")
            
            # Extract Client ID
            CLIENT_ID=$(echo $CLIENT_RESULT | jq -r '.UserPoolClient.ClientId')
            
            if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" == "null" ]; then
                error "Failed to create User Pool Client."
            fi
            
            log "Client ID: $CLIENT_ID"
            
            # Update .env file with new client ID
            log "Updating .env file with new client ID..."
            sed -i "s/CLIENT_ID=.*/CLIENT_ID=$CLIENT_ID/" "../.env"
            
            success "Cognito client created successfully."
            return
        fi
    fi
    
    # Try to find existing user pool with the same name if we have permission
    EXISTING_POOL_ID=""
    if aws_cmd cognito-idp list-user-pools --max-results 1 --region "$AWS_REGION" &> /dev/null; then
        log "Checking for existing User Pools with name: $USER_POOL_NAME"
        EXISTING_POOL_ID=$(aws_cmd cognito-idp list-user-pools --max-results 60 --region "$AWS_REGION" | jq -r ".UserPools[] | select(.Name == \"$USER_POOL_NAME\") | .Id" | head -1)
    fi
    
    if [ ! -z "$EXISTING_POOL_ID" ]; then
        # Use the existing pool
        USER_POOL_ID=$EXISTING_POOL_ID
        warn "Found existing User Pool with name $USER_POOL_NAME. Using ID: $USER_POOL_ID"
    else
        # Create User Pool
        log "Creating Cognito User Pool: $USER_POOL_NAME"
        USER_POOL_RESULT=$(aws_cmd cognito-idp create-user-pool \
            --pool-name "$USER_POOL_NAME" \
            --auto-verified-attributes email \
            --schema '[{"Name":"email","Required":true,"Mutable":true}]' \
            --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":false}}' \
            --region "$AWS_REGION")
        
        # Extract User Pool ID
        USER_POOL_ID=$(echo $USER_POOL_RESULT | jq -r '.UserPool.Id')
        
        if [ -z "$USER_POOL_ID" ] || [ "$USER_POOL_ID" == "null" ]; then
            error "Failed to create User Pool."
        fi
        
        log "User Pool ID: $USER_POOL_ID"
        
        # Create demo user
        log "Creating demo user..."
        USER_USERNAME="demo"
        USER_EMAIL="demo@example.com"
        USER_PASSWORD="Demo@1357!"
        
        aws_cmd cognito-idp admin-create-user \
            --user-pool-id "$USER_POOL_ID" \
            --username "$USER_USERNAME" \
            --user-attributes Name=email,Value="$USER_EMAIL" Name=email_verified,Value=true \
            --temporary-password "$USER_PASSWORD" \
            --region "$AWS_REGION"
            
        # Set permanent password for the user
        log "Setting permanent password for demo user..."
        aws_cmd cognito-idp admin-set-user-password \
            --user-pool-id "$USER_POOL_ID" \
            --username "$USER_USERNAME" \
            --password "$USER_PASSWORD" \
            --permanent \
            --region "$AWS_REGION"
    fi
    
    # Create User Pool Client
    log "Creating User Pool Client: $CLIENT_NAME"
    CLIENT_RESULT=$(aws_cmd cognito-idp create-user-pool-client \
        --user-pool-id "$USER_POOL_ID" \
        --client-name "$CLIENT_NAME" \
        --no-generate-secret \
        --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
        --region "$AWS_REGION")
    
    # Extract Client ID
    CLIENT_ID=$(echo $CLIENT_RESULT | jq -r '.UserPoolClient.ClientId')
    
    if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" == "null" ]; then
        error "Failed to create User Pool Client."
    fi
    
    log "Client ID: $CLIENT_ID"
    
    # Update .env file with new resource IDs
    log "Updating .env file with new resource IDs..."
    sed -i "s/USER_POOL_ID=.*/USER_POOL_ID=$USER_POOL_ID/" "../.env"
    sed -i "s/CLIENT_ID=.*/CLIENT_ID=$CLIENT_ID/" "../.env"
    
    success "Cognito resources setup completed."
}

# Function to wait for resources to be ready
wait_for_resources() {
    log "Waiting for resources to be ready..."
    
    # No need to wait for DynamoDB tables here as we already wait in the create_dynamodb_tables function
    
    success "All resources are ready."
}

# Main function
main() {
    log "Starting creation of test resources..."
    
    # Check AWS CLI
    check_aws_cli
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed. Please install it and try again."
    fi
    
    # Load environment variables
    load_env_vars
    
    # Create resources
    create_dynamodb_tables
    create_cognito_resources
    
    # Wait for resources to be ready
    wait_for_resources
    
    success "All test resources have been created successfully!"
    log "You can now run your application with the new test environment."
    log "If demo user was created:"
    log "  Username: demo"
    log "  Email: demo@example.com"
    log "  Password: Demo@1357!"
}

# Run main function
main
