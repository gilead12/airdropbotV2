# AirdropBot V2 - AWS EC2 Deployment Guide

This guide provides step-by-step instructions for deploying the AirdropBot V2 application to a production-ready AWS EC2 environment.

## Prerequisites

- AWS Account with EC2 access
- Basic knowledge of Linux command line
- SSH client installed on your local machine

## Phase 1: Infrastructure Provisioning

### 1.1 Launch EC2 Instance

1. **Login to AWS Console** and navigate to EC2 Dashboard
2. **Launch Instance** with the following specifications:
   - **AMI**: Ubuntu Server 22.04 LTS (Free Tier Eligible)
   - **Instance Type**: t2.micro (Free Tier)
   - **Key Pair**: Create new key pair named `airdropbot-keypair`
   - **Storage**: 8 GB gp2 (default)

### 1.2 Configure Security Group

Create a new security group with the following inbound rules:

| Type  | Protocol | Port Range | Source    | Description           |
|-------|----------|------------|-----------|----------------------|
| SSH   | TCP      | 22         | My IP     | SSH access           |
| HTTP  | TCP      | 80         | 0.0.0.0/0 | Web traffic          |
| HTTPS | TCP      | 443        | 0.0.0.0/0 | Secure web traffic   |

### 1.3 Download Key Pair

- Download the `.pem` file and store it securely
- Set proper permissions: `chmod 400 airdropbot-keypair.pem`

## Phase 2: Server Environment Configuration

### 2.1 Connect to EC2 Instance

```bash
ssh -i "airdropbot-keypair.pem" ubuntu@your-ec2-public-ip
```

### 2.2 Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.3 Install System Dependencies

```bash
# Install Python 3, pip, venv, git, and nginx
sudo apt install -y python3 python3-pip python3-venv git nginx

# Install PostgreSQL client (optional, for database connectivity)
sudo apt install -y postgresql-client
```

## Phase 3: Application Deployment & Setup

### 3.1 Clone Repository

```bash
# Navigate to home directory
cd /home/ubuntu

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/airdropbotV2.git
cd airdropbotV2
```

### 3.2 Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3.3 Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Install Gunicorn for production WSGI server
pip install gunicorn
```

### 3.4 Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

Update the `.env` file with your actual values:
```env
TELEGRAM_TOKEN=your_actual_telegram_bot_token
DATABASE_URL=postgresql://username:password@your-rds-endpoint:5432/database_name
```

## Phase 4: Production Service Configuration

### 4.1 Create Gunicorn Configuration

Create `/home/ubuntu/airdropbotV2/gunicorn.conf.py`:

```python
bind = "unix:/home/ubuntu/airdropbotV2/airdropbot.sock"
workers = 2
user = "ubuntu"
group = "ubuntu"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### 4.2 Create Flask WSGI Entry Point

Create `/home/ubuntu/airdropbotV2/wsgi.py`:

```python
#!/usr/bin/env python3
from bot_fixed import app

if __name__ == "__main__":
    app.run()
```

### 4.3 Create Systemd Service File

Create `/etc/systemd/system/airdropbot.service`:

```ini
[Unit]
Description=AirdropBot V2 Gunicorn Application
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/airdropbotV2
Environment="PATH=/home/ubuntu/airdropbotV2/venv/bin"
EnvironmentFile=/home/ubuntu/airdropbotV2/.env
ExecStart=/home/ubuntu/airdropbotV2/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.4 Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable airdropbot

# Start the service
sudo systemctl start airdropbot

# Check service status
sudo systemctl status airdropbot
```

## Phase 5: Web Traffic Routing & Security

### 5.1 Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/airdropbot`:

```nginx
server {
    listen 80;
    server_name your-ec2-public-ip;

    location / {
        proxy_pass http://unix:/home/ubuntu/airdropbotV2/airdropbot.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### 5.2 Enable Nginx Site

```bash
# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/airdropbot /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Enable nginx to start on boot
sudo systemctl enable nginx
```

## Phase 6: Final Integration

### 6.1 Set Telegram Webhook

Update your bot's webhook to point to your EC2 instance:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "http://your-ec2-public-ip/webhook"}'
```

### 6.2 Verify Deployment

1. **Check service status**:
   ```bash
   sudo systemctl status airdropbot
   sudo systemctl status nginx
   ```

2. **Check logs**:
   ```bash
   sudo journalctl -u airdropbot -f
   sudo tail -f /var/log/nginx/access.log
   ```

3. **Test webhook**:
   ```bash
   curl http://your-ec2-public-ip/health
   ```

## Maintenance Commands

### Update Application
```bash
cd /home/ubuntu/airdropbotV2
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart airdropbot
```

### View Logs
```bash
# Application logs
sudo journalctl -u airdropbot -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Service Management
```bash
# Start/Stop/Restart service
sudo systemctl start airdropbot
sudo systemctl stop airdropbot
sudo systemctl restart airdropbot

# Check service status
sudo systemctl status airdropbot
```

## Security Considerations

1. **Firewall**: Consider enabling UFW firewall
2. **SSL/TLS**: Set up Let's Encrypt for HTTPS
3. **Database**: Use AWS RDS for production database
4. **Secrets**: Store sensitive data in AWS Secrets Manager
5. **Monitoring**: Set up CloudWatch for monitoring

## Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `sudo journalctl -u airdropbot`
2. **Permission denied**: Ensure correct file permissions and ownership
3. **Socket file issues**: Check if socket file exists and has correct permissions
4. **Database connection**: Verify DATABASE_URL in .env file

### Health Checks

```bash
# Check if socket file exists
ls -la /home/ubuntu/airdropbotV2/airdropbot.sock

# Test Gunicorn directly
cd /home/ubuntu/airdropbotV2
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

This deployment guide ensures a production-ready, secure, and maintainable setup for your AirdropBot V2 application on AWS EC2.