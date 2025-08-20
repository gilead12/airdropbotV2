#!/bin/bash

# AirdropBot V2 - CloudFormation Deployment Script
# This script deploys the complete infrastructure using AWS CloudFormation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="airdropbot-v2-stack"
TEMPLATE_FILE="cloudformation-template.yaml"
REGION="us-east-1"
KEY_PAIR_NAME="airdropbot-keypair"
INSTANCE_TYPE="t2.micro"
REPOSITORY_URL="https://github.com/yourusername/airdropbotV2.git"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check if CloudFormation template exists
    if [ ! -f "$TEMPLATE_FILE" ]; then
        print_error "CloudFormation template '$TEMPLATE_FILE' not found."
        exit 1
    fi
    
    print_success "Prerequisites check passed."
}

# Function to get user input
get_user_input() {
    print_status "Gathering deployment configuration..."
    
    # Get AWS region
    read -p "Enter AWS region (default: $REGION): " input_region
    REGION=${input_region:-$REGION}
    
    # Get stack name
    read -p "Enter stack name (default: $STACK_NAME): " input_stack
    STACK_NAME=${input_stack:-$STACK_NAME}
    
    # Get key pair name
    read -p "Enter key pair name (default: $KEY_PAIR_NAME): " input_keypair
    KEY_PAIR_NAME=${input_keypair:-$KEY_PAIR_NAME}
    
    # Get instance type
    echo "Available instance types:"
    echo "  1) t2.micro (Free Tier)"
    echo "  2) t2.small"
    echo "  3) t2.medium"
    read -p "Select instance type (1-3, default: 1): " instance_choice
    
    case $instance_choice in
        2) INSTANCE_TYPE="t2.small" ;;
        3) INSTANCE_TYPE="t2.medium" ;;
        *) INSTANCE_TYPE="t2.micro" ;;
    esac
    
    # Get repository URL
    read -p "Enter repository URL (default: $REPOSITORY_URL): " input_repo
    REPOSITORY_URL=${input_repo:-$REPOSITORY_URL}
    
    # Get Telegram token
    while [ -z "$TELEGRAM_TOKEN" ]; do
        read -s -p "Enter Telegram Bot Token: " TELEGRAM_TOKEN
        echo
        if [ -z "$TELEGRAM_TOKEN" ]; then
            print_error "Telegram token is required."
        fi
    done
    
    # Get database URL
    read -p "Enter Database URL (default: postgresql://user:password@localhost/airdropbot): " DATABASE_URL
    DATABASE_URL=${DATABASE_URL:-"postgresql://user:password@localhost/airdropbot"}
    
    # Get environment
    echo "Select environment:"
    echo "  1) production"
    echo "  2) staging"
    echo "  3) development"
    read -p "Select environment (1-3, default: 1): " env_choice
    
    case $env_choice in
        2) ENVIRONMENT="staging" ;;
        3) ENVIRONMENT="development" ;;
        *) ENVIRONMENT="production" ;;
    esac
    
    print_success "Configuration gathered successfully."
}

# Function to check if key pair exists
check_key_pair() {
    print_status "Checking if key pair '$KEY_PAIR_NAME' exists..."
    
    if aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" --region "$REGION" &> /dev/null; then
        print_success "Key pair '$KEY_PAIR_NAME' already exists."
    else
        print_warning "Key pair '$KEY_PAIR_NAME' does not exist."
        read -p "Do you want to create it? (y/n): " create_keypair
        
        if [[ $create_keypair =~ ^[Yy]$ ]]; then
            print_status "Creating key pair '$KEY_PAIR_NAME'..."
            aws ec2 create-key-pair --key-name "$KEY_PAIR_NAME" --region "$REGION" --query 'KeyMaterial' --output text > "${KEY_PAIR_NAME}.pem"
            chmod 400 "${KEY_PAIR_NAME}.pem"
            print_success "Key pair created and saved as '${KEY_PAIR_NAME}.pem'"
        else
            print_error "Key pair is required for deployment. Exiting."
            exit 1
        fi
    fi
}

# Function to validate CloudFormation template
validate_template() {
    print_status "Validating CloudFormation template..."
    
    if aws cloudformation validate-template --template-body file://$TEMPLATE_FILE --region "$REGION" &> /dev/null; then
        print_success "Template validation passed."
    else
        print_error "Template validation failed."
        aws cloudformation validate-template --template-body file://$TEMPLATE_FILE --region "$REGION"
        exit 1
    fi
}

# Function to deploy stack
deploy_stack() {
    print_status "Deploying CloudFormation stack '$STACK_NAME'..."
    
    # Check if stack already exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
        print_warning "Stack '$STACK_NAME' already exists."
        read -p "Do you want to update it? (y/n): " update_stack
        
        if [[ $update_stack =~ ^[Yy]$ ]]; then
            OPERATION="update-stack"
            print_status "Updating existing stack..."
        else
            print_error "Deployment cancelled."
            exit 1
        fi
    else
        OPERATION="create-stack"
        print_status "Creating new stack..."
    fi
    
    # Deploy the stack
    aws cloudformation $OPERATION \
        --stack-name "$STACK_NAME" \
        --template-body file://$TEMPLATE_FILE \
        --parameters \
            ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR_NAME" \
            ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
            ParameterKey=RepositoryURL,ParameterValue="$REPOSITORY_URL" \
            ParameterKey=TelegramToken,ParameterValue="$TELEGRAM_TOKEN" \
            ParameterKey=DatabaseURL,ParameterValue="$DATABASE_URL" \
            ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region "$REGION" \
        --tags \
            Key=Project,Value=AirdropBot \
            Key=Environment,Value="$ENVIRONMENT" \
            Key=DeployedBy,Value="$(whoami)" \
            Key=DeployedAt,Value="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    
    if [ $? -eq 0 ]; then
        print_success "Stack deployment initiated successfully."
    else
        print_error "Stack deployment failed."
        exit 1
    fi
}

# Function to wait for stack completion
wait_for_stack() {
    print_status "Waiting for stack deployment to complete..."
    print_status "This may take 10-15 minutes. Please be patient."
    
    # Wait for stack to complete
    aws cloudformation wait stack-${OPERATION%-stack}-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
    
    if [ $? -eq 0 ]; then
        print_success "Stack deployment completed successfully!"
    else
        print_error "Stack deployment failed or timed out."
        print_status "Checking stack events for details..."
        aws cloudformation describe-stack-events \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
            --output table
        exit 1
    fi
}

# Function to get stack outputs
get_stack_outputs() {
    print_status "Retrieving deployment information..."
    
    # Get stack outputs
    OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    if [ "$OUTPUTS" != "null" ] && [ "$OUTPUTS" != "[]" ]; then
        echo
        print_success "=== DEPLOYMENT SUCCESSFUL ==="
        echo
        
        # Extract key information
        INSTANCE_ID=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="InstanceId") | .OutputValue')
        PUBLIC_IP=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="PublicIP") | .OutputValue')
        WEBHOOK_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="WebhookURL") | .OutputValue')
        HEALTH_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="HealthCheckURL") | .OutputValue')
        SSH_COMMAND=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="SSHCommand") | .OutputValue')
        
        echo "📋 Deployment Details:"
        echo "   Stack Name: $STACK_NAME"
        echo "   Region: $REGION"
        echo "   Instance ID: $INSTANCE_ID"
        echo "   Public IP: $PUBLIC_IP"
        echo
        echo "🔗 URLs:"
        echo "   Webhook URL: $WEBHOOK_URL"
        echo "   Health Check: $HEALTH_URL"
        echo
        echo "🔑 SSH Access:"
        echo "   Command: $SSH_COMMAND"
        echo
        echo "📊 Monitoring:"
        echo "   CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$REGION#logsV2:log-groups/log-group/%2Faws%2Fec2%2Fairdropbot"
        echo "   EC2 Console: https://console.aws.amazon.com/ec2/home?region=$REGION#Instances:instanceId=$INSTANCE_ID"
        echo
        
        # Save deployment info to file
        cat > deployment-info.txt << EOF
AirdropBot V2 Deployment Information
====================================
Deployment Date: $(date)
Stack Name: $STACK_NAME
Region: $REGION
Instance ID: $INSTANCE_ID
Public IP: $PUBLIC_IP
Webhook URL: $WEBHOOK_URL
Health Check URL: $HEALTH_URL
SSH Command: $SSH_COMMAND

Next Steps:
1. Wait 2-3 minutes for the application to fully start
2. Test the health check: curl $HEALTH_URL
3. Set up your Telegram webhook: $WEBHOOK_URL
4. Monitor logs in CloudWatch
5. SSH to instance if needed: $SSH_COMMAND
EOF
        
        print_success "Deployment information saved to 'deployment-info.txt'"
    else
        print_warning "No stack outputs found. The deployment may have issues."
    fi
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    if [ -n "$HEALTH_URL" ]; then
        print_status "Testing health check endpoint..."
        
        # Wait a bit for the application to start
        sleep 30
        
        for i in {1..5}; do
            if curl -f -s "$HEALTH_URL" > /dev/null; then
                print_success "Health check passed! Application is running."
                return 0
            else
                print_warning "Health check attempt $i/5 failed. Retrying in 30 seconds..."
                sleep 30
            fi
        done
        
        print_warning "Health check failed after 5 attempts. The application may still be starting."
        print_status "You can manually check later with: curl $HEALTH_URL"
    fi
}

# Function to show next steps
show_next_steps() {
    echo
    print_success "=== NEXT STEPS ==="
    echo
    echo "1. 🔍 Verify the deployment:"
    echo "   curl $HEALTH_URL"
    echo
    echo "2. 🤖 Set up Telegram webhook:"
    echo "   curl -X POST \"https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook\" \\"
    echo "        -H \"Content-Type: application/json\" \\"
    echo "        -d '{\"url\": \"$WEBHOOK_URL\"}'"
    echo
    echo "3. 📊 Monitor your application:"
    echo "   - CloudWatch Logs: AWS Console > CloudWatch > Log Groups > /aws/ec2/airdropbot"
    echo "   - EC2 Instance: AWS Console > EC2 > Instances > $INSTANCE_ID"
    echo
    echo "4. 🔧 SSH to your instance (if needed):"
    echo "   $SSH_COMMAND"
    echo
    echo "5. 🗑️  Clean up (when done testing):"
    echo "   aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
    echo
    print_success "Deployment completed successfully! 🎉"
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Deployment failed. Check the error messages above."
        print_status "You can check CloudFormation events with:"
        echo "aws cloudformation describe-stack-events --stack-name $STACK_NAME --region $REGION"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    echo "🚀 AirdropBot V2 - CloudFormation Deployment"
    echo "============================================"
    echo
    
    check_prerequisites
    get_user_input
    check_key_pair
    validate_template
    deploy_stack
    wait_for_stack
    get_stack_outputs
    verify_deployment
    show_next_steps
}

# Run main function
main "$@"