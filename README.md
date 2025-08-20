# AirdropBot V2 🚀

A robust Telegram bot for managing airdrops with enhanced user verification, referral tracking, and Solana wallet integration. Built with Flask, SQLAlchemy, and designed for production deployment on AWS EC2.

## ✨ Features

- **Multi-step User Verification**: Telegram and Twitter account verification
- **Referral System**: Track and reward user referrals
- **Solana Wallet Integration**: Secure wallet submission and validation
- **Database Management**: PostgreSQL with SQLAlchemy ORM
- **Production Ready**: Configured for AWS EC2 with Gunicorn and Nginx
- **Auto-restart**: Systemd service management for 24/7 operation
- **Security**: Rate limiting, input validation, and secure configuration

## 🚀 Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- AWS CLI v2 installed and configured
- Python 3.8+ (for local development)
- PostgreSQL database (can be AWS RDS)
- Telegram Bot Token

### Deployment Options

#### Option 1: CloudFormation (Recommended for Production)
**Complete infrastructure-as-code deployment with monitoring and security**

```bash
git clone https://github.com/yourusername/airdropbotV2.git
cd airdropbotV2
./cloudformation-deploy.sh
```

#### Option 2: AWS CLI Script (Quick Testing)
**Automated deployment using AWS CLI commands**

```bash
git clone https://github.com/yourusername/airdropbotV2.git
cd airdropbotV2
./aws-deploy.sh
```

#### Option 3: Manual Deployment (Custom Setup)
**Step-by-step manual deployment for learning or customization**

```bash
git clone https://github.com/yourusername/airdropbotV2.git
cd airdropbotV2
./quick-start.sh  # Interactive setup
```

For detailed instructions, see:
- [INFRASTRUCTURE_GUIDE.md](INFRASTRUCTURE_GUIDE.md) - Complete infrastructure automation guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Manual deployment steps
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Verification checklist

## 📋 Additional Prerequisites

- **Server**: Ubuntu 22.04 LTS (recommended)
- **Python**: 3.8 or higher
- **Database**: PostgreSQL 12+
- **Telegram Bot**: Token from [@BotFather](https://t.me/BotFather)
- **AWS Account**: For EC2 deployment (optional for local development)

## 🛠️ Installation

### Option 1: Automated Deployment (Recommended)

For production deployment on Ubuntu EC2:

```bash
# Clone the repository
git clone <your-repo-url>
cd airdropbotV2

# Run the deployment script
./deploy.sh
```

### Option 2: Manual Setup

1. **Environment Setup**:
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit configuration
   nano .env
   ```

2. **Python Dependencies**:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Database Setup**:
   ```bash
   # Create PostgreSQL database
   sudo -u postgres createdb airdropbot
   
   # Update DATABASE_URL in .env
   ```

4. **Run Application**:
   ```bash
   # Development mode
   python3 app.py
   
   # Production mode (with Gunicorn)
   gunicorn -c gunicorn.conf.py wsgi:application
   ```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Telegram Bot Configuration
TELEGRAM_TOKEN=your_bot_token_here
WEBHOOK_URL=http://your-ec2-ip

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/airdropbot

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here

# Application Settings
POLLING_MODE=false
LOG_LEVEL=INFO
GUNICORN_WORKERS=2
```

See `.env.example` for all available options.

### Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Get your bot token
3. Set the webhook URL:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "http://YOUR-EC2-IP/webhook"}'
   ```

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Telegram  │───▶│    Nginx    │───▶│  Gunicorn   │
│   Webhook   │    │ (Port 80)   │    │   (Socket)  │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              ▼
                                    ┌─────────────┐
                                    │ Flask App   │
                                    │ (app.py)    │
                                    └─────────────┘
                                              │
                                              ▼
                                    ┌─────────────┐
                                    │ PostgreSQL  │
                                    │ Database    │
                                    └─────────────┘
```

## 📁 Project Structure

```
airdropbotV2/
├── app.py                 # Flask application (webhook mode)
├── bot.py                 # Original bot implementation
├── bot_fixed.py          # Enhanced bot with fixes
├── wsgi.py               # WSGI entry point
├── gunicorn.conf.py      # Gunicorn configuration
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── deploy.sh            # Automated deployment script
├── quick-start.sh       # Quick start guide
├── DEPLOYMENT_GUIDE.md  # Detailed deployment instructions
├── lib/
│   └── models.py        # Database models
├── config/
│   ├── airdropbot.service    # Systemd service file
│   └── nginx-airdropbot.conf # Nginx configuration
└── settings.py          # Bot messages and configuration
```

## 🔍 Monitoring & Maintenance

### Service Management

```bash
# Check service status
sudo systemctl status airdropbot

# Start/stop/restart service
sudo systemctl start airdropbot
sudo systemctl stop airdropbot
sudo systemctl restart airdropbot

# View logs
sudo journalctl -u airdropbot -f
```

### Health Checks

```bash
# Application health
curl http://localhost/health

# Nginx status
sudo systemctl status nginx

# Database connection
psql $DATABASE_URL -c "SELECT 1;"
```

### Log Files

- Application logs: `/var/log/airdropbot/app.log`
- Nginx access logs: `/var/log/nginx/airdropbot_access.log`
- Nginx error logs: `/var/log/nginx/airdropbot_error.log`
- System logs: `journalctl -u airdropbot`

## 🛡️ Security Features

- **Rate Limiting**: Prevents spam and abuse
- **Input Validation**: Sanitizes user inputs
- **Secure Headers**: CSRF protection and security headers
- **Environment Isolation**: Secrets managed via environment variables
- **Process Isolation**: Non-root user execution
- **Firewall Configuration**: Restricted port access

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**:
   ```bash
   # Check service status
   sudo systemctl status airdropbot
   
   # Check logs
   sudo journalctl -u airdropbot -n 50
   ```

2. **Database connection errors**:
   ```bash
   # Test database connection
   psql $DATABASE_URL -c "SELECT version();"
   ```

3. **Webhook issues**:
   ```bash
   # Check webhook status
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   
   # Reset webhook
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
        -d "url=http://YOUR-EC2-IP/webhook"
   ```

4. **Permission errors**:
   ```bash
   # Fix file permissions
   sudo chown -R airdropbot:airdropbot /opt/airdropbot
   chmod 600 .env
   ```

### Debug Mode

For development and debugging:

```bash
# Set debug mode in .env
FLASK_ENV=development
LOG_LEVEL=DEBUG

# Run in polling mode
POLLING_MODE=true
python3 app.py
```

## 📚 Documentation

- **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: Detailed step-by-step deployment instructions
- **[Quick Start](quick-start.sh)**: Interactive setup script
- **[Environment Configuration](.env.example)**: All available configuration options

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs for error messages
3. Ensure all environment variables are correctly set
4. Verify database connectivity
5. Check Telegram webhook configuration

## 🔄 Updates

To update the application:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart airdropbot
```

---

**Made with ❤️ for the Solana community**

For questions or support, please check the documentation or create an issue in the repository.