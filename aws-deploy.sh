#!/bin/bash

# AirdropBot V2 - AWS CLI Automated Deployment Script
# This script automates the entire AWS EC2 deployment process using AWS CLI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
KEY_PAIR_NAME="airdropbot-keypair"
SECURITY_GROUP_NAME="airdropbot-sg"
INSTANCE_TYPE="t2.micro"
REGION="us-east-1"
AMI_ID="ami-0c02fb55956c7d316"  # Ubuntu 22.04 LTS (update as needed)
REPO_URL="https://github.com/yourusername/airdropbotV2.git"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "  AirdropBot V2 - AWS CLI Deployment"
    echo "=========================================="
    echo -e "${NC}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        echo "Install instructions: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed. Installing jq for JSON parsing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install jq
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update && sudo apt-get install -y jq
        fi
    fi
    
    log_success "Prerequisites check passed"
}

get_my_ip() {
    log_info "Getting your public IP address..."
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    if [[ -z "$MY_IP" ]]; then
        log_error "Failed to get your public IP address"
        exit 1
    fi
    log_success "Your public IP: $MY_IP"
}

create_key_pair() {
    log_info "Creating EC2 key pair..."
    
    # Check if key pair already exists
    if aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" --region "$REGION" &> /dev/null; then
        log_warning "Key pair '$KEY_PAIR_NAME' already exists"
        read -p "Do you want to delete and recreate it? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            aws ec2 delete-key-pair --key-name "$KEY_PAIR_NAME" --region "$REGION"
            log_info "Deleted existing key pair"
        else
            log_info "Using existing key pair"
            return
        fi
    fi
    
    # Create new key pair
    aws ec2 create-key-pair \
        --key-name "$KEY_PAIR_NAME" \
        --region "$REGION" \
        --query 'KeyMaterial' \
        --output text > "${KEY_PAIR_NAME}.pem"
    
    # Set proper permissions
    chmod 400 "${KEY_PAIR_NAME}.pem"
    
    log_success "Key pair created and saved as ${KEY_PAIR_NAME}.pem"
}

create_security_group() {
    log_info "Creating security group..."
    
    # Get default VPC ID
    VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=isDefault,Values=true" \
        --region "$REGION" \
        --query 'Vpcs[0].VpcId' \
        --output text)
    
    if [[ "$VPC_ID" == "None" ]]; then
        log_error "No default VPC found"
        exit 1
    fi
    
    # Check if security group already exists
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
        --region "$REGION" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "None")
    
    if [[ "$SECURITY_GROUP_ID" != "None" ]]; then
        log_warning "Security group '$SECURITY_GROUP_NAME' already exists"
        log_info "Using existing security group: $SECURITY_GROUP_ID"
        return
    fi
    
    # Create security group
    SECURITY_GROUP_ID=$(aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Security group for AirdropBot V2" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)
    
    # Add inbound rules
    # SSH access from your IP
    aws ec2 authorize-security-group-ingress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port 22 \
        --cidr "${MY_IP}/32" \
        --region "$REGION"
    
    # HTTP access from anywhere
    aws ec2 authorize-security-group-ingress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port 80 \
        --cidr "0.0.0.0/0" \
        --region "$REGION"
    
    # HTTPS access from anywhere
    aws ec2 authorize-security-group-ingress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port 443 \
        --cidr "0.0.0.0/0" \
        --region "$REGION"
    
    log_success "Security group created: $SECURITY_GROUP_ID"
}

launch_ec2_instance() {
    log_info "Launching EC2 instance..."
    
    # Create user data script for initial setup
    USER_DATA=$(cat << 'EOF'
#!/bin/bash
yum update -y
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nginx postgresql-client
EOF
)
    
    # Launch instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --count 1 \
        --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_PAIR_NAME" \
        --security-group-ids "$SECURITY_GROUP_ID" \
        --user-data "$USER_DATA" \
        --region "$REGION" \
        --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=AirdropBot-V2}]' \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    log_success "Instance launched: $INSTANCE_ID"
    
    # Wait for instance to be running
    log_info "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --region "$REGION" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    log_success "Instance is running. Public IP: $PUBLIC_IP"
    
    # Wait a bit more for SSH to be ready
    log_info "Waiting for SSH to be ready..."
    sleep 60
}

deploy_application() {
    log_info "Deploying application to EC2 instance..."
    
    # Create deployment script
    cat > deploy_remote.sh << 'EOF'
#!/bin/bash
set -e

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql-client

# Clone repository
cd /home/ubuntu
if [ -d "airdropbotV2" ]; then
    cd airdropbotV2
    git pull origin main
else
    git clone REPO_URL_PLACEHOLDER
    cd airdropbotV2
fi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment template
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# Create systemd service
sudo cp config/airdropbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable airdropbot

# Configure Nginx
sudo cp config/nginx-airdropbot.conf /etc/nginx/sites-available/airdropbot
sudo ln -sf /etc/nginx/sites-available/airdropbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# Set proper permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/airdropbotV2
chmod 600 .env

echo "Deployment completed. Please update .env file with your actual values."
EOF
    
    # Replace placeholder with actual repo URL
    sed -i "s|REPO_URL_PLACEHOLDER|$REPO_URL|g" deploy_remote.sh
    
    # Copy deployment script to instance
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no deploy_remote.sh ubuntu@"$PUBLIC_IP":/tmp/
    
    # Execute deployment script
    ssh -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" 'chmod +x /tmp/deploy_remote.sh && /tmp/deploy_remote.sh'
    
    log_success "Application deployed successfully"
}

setup_environment_config() {
    log_info "Setting up environment configuration..."
    
    # Create a temporary .env file with placeholders
    cat > temp_env << EOF
# Telegram Bot Configuration
TELEGRAM_TOKEN=your_bot_token_here
WEBHOOK_URL=http://$PUBLIC_IP

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/airdropbot

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Application Settings
POLLING_MODE=false
LOG_LEVEL=INFO
GUNICORN_WORKERS=2
EOF
    
    # Copy to instance
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no temp_env ubuntu@"$PUBLIC_IP":/home/ubuntu/airdropbotV2/.env
    
    # Clean up
    rm temp_env
    
    log_success "Environment configuration uploaded"
}

start_services() {
    log_info "Starting services..."
    
    # Start the application service
    ssh -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" << 'EOF'
sudo systemctl start airdropbot
sudo systemctl status airdropbot --no-pager
EOF
    
    log_success "Services started"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Test health endpoint
    sleep 10
    if curl -f "http://$PUBLIC_IP/health" &> /dev/null; then
        log_success "Health check passed"
    else
        log_warning "Health check failed - this might be normal if .env is not configured yet"
    fi
    
    # Check service status
    ssh -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" << 'EOF'
echo "=== Service Status ==="
sudo systemctl status airdropbot --no-pager
echo "\n=== Nginx Status ==="
sudo systemctl status nginx --no-pager
EOF
}

print_next_steps() {
    log_info "Deployment Summary:"
    echo
    echo "🎉 Your AirdropBot V2 has been deployed to AWS EC2!"
    echo
    echo "📋 Instance Details:"
    echo "   Instance ID: $INSTANCE_ID"
    echo "   Public IP: $PUBLIC_IP"
    echo "   Key Pair: ${KEY_PAIR_NAME}.pem"
    echo "   Security Group: $SECURITY_GROUP_ID"
    echo
    echo "🔧 Next Steps:"
    echo "1. Configure your .env file:"
    echo "   ssh -i ${KEY_PAIR_NAME}.pem ubuntu@$PUBLIC_IP"
    echo "   cd airdropbotV2"
    echo "   nano .env"
    echo
    echo "2. Update these values in .env:"
    echo "   - TELEGRAM_TOKEN (from @BotFather)"
    echo "   - DATABASE_URL (your PostgreSQL connection)"
    echo
    echo "3. Restart the service after configuration:"
    echo "   sudo systemctl restart airdropbot"
    echo
    echo "4. Set your Telegram webhook:"
    echo "   curl -X POST 'https://api.telegram.org/bot<TOKEN>/setWebhook' \\"
    echo "        -H 'Content-Type: application/json' \\"
    echo "        -d '{\"url\": \"http://$PUBLIC_IP/webhook\"}'"
    echo
    echo "🔍 Useful Commands:"
    echo "   # Connect to instance:"
    echo "   ssh -i ${KEY_PAIR_NAME}.pem ubuntu@$PUBLIC_IP"
    echo
    echo "   # Check logs:"
    echo "   sudo journalctl -u airdropbot -f"
    echo
    echo "   # Test health:"
    echo "   curl http://$PUBLIC_IP/health"
    echo
    echo "💡 Your bot will be accessible at: http://$PUBLIC_IP"
    echo
}

cleanup_on_error() {
    log_error "Deployment failed. Cleaning up resources..."
    
    if [[ -n "$INSTANCE_ID" ]]; then
        log_info "Terminating instance: $INSTANCE_ID"
        aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$REGION"
    fi
    
    if [[ -n "$SECURITY_GROUP_ID" ]] && [[ "$SECURITY_GROUP_ID" != "None" ]]; then
        log_info "Deleting security group: $SECURITY_GROUP_ID"
        aws ec2 delete-security-group --group-id "$SECURITY_GROUP_ID" --region "$REGION"
    fi
    
    if [[ -f "${KEY_PAIR_NAME}.pem" ]]; then
        log_info "Deleting key pair from AWS"
        aws ec2 delete-key-pair --key-name "$KEY_PAIR_NAME" --region "$REGION"
        rm -f "${KEY_PAIR_NAME}.pem"
    fi
}

# Main execution
main() {
    print_banner
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Prompt for configuration
    echo "This script will deploy AirdropBot V2 to AWS EC2."
    echo "Please ensure you have:"
    echo "1. AWS CLI configured with appropriate permissions"
    echo "2. Your repository URL ready"
    echo "3. Telegram bot token from @BotFather"
    echo
    
    read -p "Enter your repository URL (default: $REPO_URL): " input_repo
    if [[ -n "$input_repo" ]]; then
        REPO_URL="$input_repo"
    fi
    
    read -p "Enter AWS region (default: $REGION): " input_region
    if [[ -n "$input_region" ]]; then
        REGION="$input_region"
    fi
    
    read -p "Do you want to proceed with deployment? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites
    get_my_ip
    create_key_pair
    create_security_group
    launch_ec2_instance
    deploy_application
    setup_environment_config
    start_services
    verify_deployment
    print_next_steps
    
    log_success "🎉 AWS CLI deployment completed successfully!"
}

# Run main function
main "$@"