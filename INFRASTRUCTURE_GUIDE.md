# AirdropBot V2 - Infrastructure as Code Guide

This guide provides multiple automated approaches to deploy AirdropBot V2 on AWS, eliminating the need for manual EC2 setup steps.

## 🚀 Quick Start Options

### Option 1: CloudFormation (Recommended)
**Best for:** Production deployments, infrastructure management, team environments

```bash
# One-command deployment
./cloudformation-deploy.sh
```

### Option 2: AWS CLI Script
**Best for:** Quick testing, development environments, learning

```bash
# Automated CLI deployment
./aws-deploy.sh
```

### Option 3: Manual Deployment
**Best for:** Custom configurations, learning AWS services

Follow the detailed steps in `DEPLOYMENT_GUIDE.md`

---

## 📋 Prerequisites

### Required Tools
- **AWS CLI v2** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **jq** - JSON processor for parsing AWS responses
- **curl** - For testing endpoints
- **Git** - For cloning repositories

### AWS Account Setup
1. **AWS Account** with appropriate permissions
2. **AWS CLI configured** with credentials:
   ```bash
   aws configure
   ```
3. **Required IAM permissions:**
   - EC2 (create instances, security groups, key pairs)
   - CloudFormation (create/update stacks)
   - IAM (create roles, policies)
   - Secrets Manager (create/read secrets)
   - CloudWatch (create log groups, alarms)

### Installation Commands
```bash
# macOS
brew install awscli jq

# Ubuntu/Debian
sudo apt update
sudo apt install -y awscli jq curl git

# Amazon Linux 2
sudo yum install -y aws-cli jq curl git
```

---

## 🏗️ CloudFormation Deployment (Recommended)

### Features
- ✅ **Complete Infrastructure**: VPC, Security Groups, IAM Roles, CloudWatch
- ✅ **Secrets Management**: Secure storage of sensitive data
- ✅ **Monitoring**: Built-in CloudWatch logs and alarms
- ✅ **Auto-scaling Ready**: Prepared for future scaling
- ✅ **Rollback Support**: Easy rollback on failures
- ✅ **Resource Tagging**: Proper resource organization

### Quick Deployment
```bash
# Make script executable (if not already)
chmod +x cloudformation-deploy.sh

# Run deployment
./cloudformation-deploy.sh
```

### What Gets Created
| Resource Type | Purpose | Count |
|---------------|---------|-------|
| VPC | Isolated network environment | 1 |
| Subnet | Public subnet for EC2 | 1 |
| Internet Gateway | Internet access | 1 |
| Security Group | Firewall rules | 1 |
| EC2 Instance | Application server | 1 |
| Elastic IP | Static public IP | 1 |
| IAM Role | Instance permissions | 1 |
| Secrets Manager | Secure credential storage | 1 |
| CloudWatch Logs | Application logging | 1 |
| CloudWatch Alarms | Monitoring alerts | 2 |

### Configuration Options
The script will prompt for:
- **AWS Region** (default: us-east-1)
- **Stack Name** (default: airdropbot-v2-stack)
- **Instance Type** (t2.micro, t2.small, t2.medium)
- **Key Pair Name** (for SSH access)
- **Repository URL** (your bot's Git repository)
- **Telegram Bot Token** (securely stored)
- **Database URL** (PostgreSQL connection string)
- **Environment** (production, staging, development)

### Advanced Usage
```bash
# Deploy with custom parameters
aws cloudformation create-stack \
  --stack-name my-airdropbot \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=InstanceType,ParameterValue=t2.small \
    ParameterKey=Environment,ParameterValue=production \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2
```

---

## ⚡ AWS CLI Script Deployment

### Features
- ✅ **Fast Setup**: Quick deployment for testing
- ✅ **Interactive**: Guided configuration
- ✅ **Flexible**: Easy to modify and customize
- ✅ **Educational**: Shows individual AWS CLI commands

### Quick Deployment
```bash
# Make script executable (if not already)
chmod +x aws-deploy.sh

# Run deployment
./aws-deploy.sh
```

### What the Script Does
1. **Prerequisites Check**: Verifies AWS CLI and credentials
2. **Key Pair Management**: Creates or uses existing SSH key pair
3. **Security Group**: Creates firewall rules (SSH, HTTP, HTTPS)
4. **EC2 Instance**: Launches Ubuntu 22.04 LTS instance
5. **Application Setup**: Installs dependencies and configures bot
6. **Service Configuration**: Sets up systemd and Nginx
7. **Verification**: Tests deployment and provides access information

---

## 🔧 Customization Options

### Environment Variables
Both deployment methods support these configurations:

```bash
# Core Settings
TELEGRAM_TOKEN="your_bot_token"
DATABASE_URL="postgresql://user:pass@host:5432/db"
WEBHOOK_URL="https://your-domain.com/webhook"

# Application Settings
FLASK_ENV="production"
LOG_LEVEL="INFO"
GUNICORN_WORKERS="2"

# Security Settings
SECRET_KEY="your_secret_key"
ALLOWED_HOSTS="*"
CORS_ORIGINS="*"
```

### Instance Types
| Type | vCPUs | Memory | Network | Use Case |
|------|-------|--------|---------|----------|
| t2.micro | 1 | 1 GB | Low-Moderate | Development, Free Tier |
| t2.small | 1 | 2 GB | Low-Moderate | Small production |
| t2.medium | 2 | 4 GB | Low-Moderate | Medium production |
| t3.micro | 2 | 1 GB | Up to 5 Gbps | Better performance |
| t3.small | 2 | 2 GB | Up to 5 Gbps | Recommended production |

### Regions
Choose the region closest to your users:
- **us-east-1** (N. Virginia) - Default, lowest latency to many services
- **us-west-2** (Oregon) - West Coast US
- **eu-west-1** (Ireland) - Europe
- **ap-southeast-1** (Singapore) - Asia Pacific

---

## 📊 Monitoring and Management

### CloudWatch Integration
Both deployment methods include:

**Log Groups:**
- `/aws/ec2/airdropbot` - Application logs
- Nginx access and error logs
- System logs

**Metrics:**
- CPU utilization
- Memory usage
- Disk usage
- Network I/O

**Alarms:**
- High CPU usage (>80%)
- Instance status check failures

### Accessing Logs
```bash
# View application logs
aws logs tail /aws/ec2/airdropbot --follow

# SSH to instance
ssh -i your-keypair.pem ubuntu@your-instance-ip

# Check service status
sudo systemctl status airdropbot
sudo systemctl status nginx
```

---

## 🔒 Security Best Practices

### Implemented Security Features
- **VPC Isolation**: Private network environment
- **Security Groups**: Restrictive firewall rules
- **IAM Roles**: Least privilege access
- **Secrets Manager**: Encrypted credential storage
- **HTTPS Ready**: SSL/TLS configuration prepared
- **Regular Updates**: Automated security patches

### Additional Security Recommendations
1. **Enable CloudTrail** for API logging
2. **Use AWS WAF** for web application firewall
3. **Enable GuardDuty** for threat detection
4. **Regular Security Scans** with AWS Inspector
5. **Backup Strategy** with AWS Backup

---

## 🚨 Troubleshooting

### Common Issues

#### 1. CloudFormation Stack Creation Failed
```bash
# Check stack events
aws cloudformation describe-stack-events --stack-name airdropbot-v2-stack

# View failed resources
aws cloudformation describe-stack-resources --stack-name airdropbot-v2-stack --query 'StackResources[?ResourceStatus==`CREATE_FAILED`]'
```

#### 2. Instance Not Responding
```bash
# Check instance status
aws ec2 describe-instance-status --instance-ids i-1234567890abcdef0

# View system logs
aws ec2 get-console-output --instance-id i-1234567890abcdef0
```

#### 3. Application Not Starting
```bash
# SSH to instance
ssh -i keypair.pem ubuntu@instance-ip

# Check service logs
sudo journalctl -u airdropbot -f
sudo tail -f /var/log/nginx/error.log
```

#### 4. Health Check Failing
```bash
# Test locally on instance
curl http://localhost/health

# Check Gunicorn process
sudo systemctl status airdropbot
ps aux | grep gunicorn
```

### Getting Help
- **AWS Support**: Use AWS Support Center
- **CloudFormation**: Check AWS CloudFormation documentation
- **EC2**: Review EC2 troubleshooting guides
- **Application Logs**: Check `/var/log/airdropbot/`

---

## 💰 Cost Optimization

### Free Tier Usage
- **EC2**: 750 hours/month of t2.micro (first 12 months)
- **EBS**: 30 GB of storage
- **Data Transfer**: 15 GB outbound
- **CloudWatch**: 10 custom metrics, 5 GB log ingestion

### Cost Estimates (Monthly)
| Component | t2.micro | t2.small | t2.medium |
|-----------|----------|----------|-----------|
| EC2 Instance | $8.50 | $17.00 | $34.00 |
| EBS Storage (8GB) | $0.80 | $0.80 | $0.80 |
| Elastic IP | $3.65 | $3.65 | $3.65 |
| Data Transfer | $0.09/GB | $0.09/GB | $0.09/GB |
| **Total (approx.)** | **$13** | **$21** | **$38** |

### Cost Optimization Tips
1. **Use t2.micro** for development/testing
2. **Stop instances** when not in use
3. **Use Spot Instances** for non-critical workloads
4. **Monitor usage** with AWS Cost Explorer
5. **Set billing alerts** to avoid surprises

---

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# SSH to instance
ssh -i keypair.pem ubuntu@instance-ip

# Update code
cd /home/ubuntu/airdropbotV2
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Restart services
sudo systemctl restart airdropbot
```

### Updating Infrastructure
```bash
# Update CloudFormation stack
aws cloudformation update-stack \
  --stack-name airdropbot-v2-stack \
  --template-body file://cloudformation-template.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### Backup Strategy
1. **Code**: Git repository (automatic)
2. **Database**: Regular PostgreSQL dumps
3. **Configuration**: Store in version control
4. **AMI Snapshots**: Create custom AMIs

---

## 🗑️ Cleanup

### CloudFormation Cleanup
```bash
# Delete entire stack
aws cloudformation delete-stack --stack-name airdropbot-v2-stack

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name airdropbot-v2-stack
```

### Manual Cleanup (CLI Script)
```bash
# Terminate instance
aws ec2 terminate-instances --instance-ids i-1234567890abcdef0

# Delete security group
aws ec2 delete-security-group --group-id sg-1234567890abcdef0

# Delete key pair
aws ec2 delete-key-pair --key-name airdropbot-keypair
```

---

## 📚 Additional Resources

### Documentation
- [AWS CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
- [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/)
- [EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Templates and Examples
- `cloudformation-template.yaml` - Complete infrastructure template
- `cloudformation-deploy.sh` - Automated deployment script
- `aws-deploy.sh` - CLI-based deployment script
- `DEPLOYMENT_GUIDE.md` - Manual deployment guide

### Support
- **GitHub Issues**: Report bugs and feature requests
- **AWS Support**: Technical support for AWS services
- **Community**: Join our Discord/Telegram for help

---

## 🎯 Next Steps

1. **Choose your deployment method** based on your needs
2. **Prepare your environment** with required tools
3. **Configure your bot** with Telegram token and database
4. **Deploy using your preferred method**
5. **Monitor and maintain** your deployment
6. **Scale as needed** based on usage

**Happy Deploying! 🚀**