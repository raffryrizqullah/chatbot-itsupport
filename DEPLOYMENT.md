<div align="center">

# 🚀 Deployment Guide

**Production Deployment untuk Chatbot IT Support RAG API**

[![VPS](https://img.shields.io/badge/VPS-Ubuntu_22.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![aaPanel](https://img.shields.io/badge/aaPanel-Server_Management-00A0E9?style=for-the-badge)](https://aapanel.com)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-Tunnel-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://cloudflare.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)

Panduan lengkap untuk deploy aplikasi ke VPS Ubuntu dengan aaPanel dan Cloudflare Tunnel

</div>

---

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [System Requirements](#-system-requirements)
- [Installation Steps](#-installation-steps)
  - [1. VPS & aaPanel Setup](#1-vps--aapanel-setup)
  - [2. Install Dependencies](#2-install-system-dependencies)
  - [3. PostgreSQL Setup](#3-postgresql-setup)
  - [4. Redis Setup](#4-redis-setup)
  - [5. Application Setup](#5-application-setup)
  - [6. Cloudflare R2 Setup](#6-cloudflare-r2-setup)
  - [7. Cloudflare Tunnel Setup](#7-cloudflare-tunnel-setup)
  - [8. Systemd Service](#8-systemd-service-setup)
  - [9. Create Admin User](#9-create-admin-user)
- [Verification](#-verification)
- [Monitoring & Logs](#-monitoring--logs)
- [Troubleshooting](#-troubleshooting)
- [Security Checklist](#-security-checklist)
- [Maintenance](#-maintenance)

---

## 🎯 Prerequisites

Sebelum memulai deployment, pastikan Anda memiliki:

- ✅ **VPS Ubuntu 22.04** (minimal 2GB RAM, 2 vCPU)
- ✅ **aaPanel** sudah terinstall di VPS
- ✅ **Domain** yang sudah terhubung ke Cloudflare
- ✅ **OpenAI API Key** ([Get it here](https://platform.openai.com/api-keys))
- ✅ **Pinecone API Key** ([Get it here](https://app.pinecone.io))
- ✅ **Cloudflare Account** dengan R2 enabled

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Ubuntu 22.04 LTS
- **RAM**: 2GB (recommended 4GB)
- **CPU**: 2 vCPU
- **Disk**: 20GB SSD
- **Python**: 3.10 or higher

### Required Services
- PostgreSQL 14+
- Redis 6+
- aaPanel 7.0+

---

## 🔧 Installation Steps

### 1. VPS & aaPanel Setup

#### Install aaPanel (jika belum)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install aaPanel
wget -O install.sh http://www.aapanel.com/script/install-ubuntu_6.0_en.sh && sudo bash install.sh aapanel
```

**Setelah instalasi:**
- Login ke aaPanel: `http://YOUR_VPS_IP:7800`
- Install App Store packages yang diperlukan

---

### 2. Install System Dependencies

Login ke VPS via SSH:

```bash
# Update package list
sudo apt update

# Install Python 3.10+ and development tools
sudo apt install -y python3.10 python3.10-venv python3-pip python3-dev

# Install system dependencies for PDF processing
sudo apt install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ind \
    libmagic-dev \
    build-essential \
    libpq-dev

# Verify installations
python3 --version
tesseract --version
```

---

### 3. PostgreSQL Setup

#### Via aaPanel

1. **Install PostgreSQL:**
   - Login ke aaPanel
   - Go to **App Store** → Search **PostgreSQL**
   - Install **PostgreSQL 14** atau versi terbaru

2. **Create Database:**
   - Go to **Database** → **PostgreSQL**
   - Click **Add Database**
   - Database name: `chatbot_db`
   - Username: `chatbot_user`
   - Password: `[generate secure password]`
   - Click **Submit**

3. **Save credentials** untuk `.env` nanti

#### Manual Setup (Alternative)

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE chatbot_db;
CREATE USER chatbot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
\q
EOF
```

---

### 4. Redis Setup

#### Via aaPanel

1. **Install Redis:**
   - Go to **App Store** → Search **Redis**
   - Install **Redis 7.x**

2. **Configure Redis (optional):**
   - Go to **App Store** → **Redis** → **Settings**
   - Enable persistence:
     ```conf
     save 900 1
     save 300 10
     save 60 10000
     appendonly yes
     ```
   - Restart Redis

#### Manual Setup (Alternative)

```bash
# Install Redis
sudo apt install -y redis-server

# Configure persistence
sudo nano /etc/redis/redis.conf
# Add these lines:
# save 900 1
# save 300 10
# appendonly yes

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return PONG
```

---

### 5. Application Setup

#### Create Application Directory

```bash
# Navigate to web root (aaPanel default)
cd /www/wwwroot

# Clone repository
git clone https://github.com/yourusername/chatbot-itsupport.git
cd chatbot-itsupport

# Or upload via SFTP to /www/wwwroot/chatbot-itsupport
```

#### Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Install Python Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Verify installation
pip list
```

#### Configure Environment Variables

```bash
# Copy production template
cp .env.production .env

# Edit environment file
nano .env
```

**Fill in these critical values:**

```env
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# Pinecone
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxx

# PostgreSQL (from step 3)
DATABASE_URL=postgresql+asyncpg://chatbot_user:your_password@localhost:5432/chatbot_db

# JWT Secret (generate new)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Cloudflare R2 (next step)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=chatbot-pdfs

# CORS (your domain)
CORS_ORIGINS=https://yourdomain.com

# Production settings
SERVER_RELOAD=false
ENABLE_DOCS=false  # Or true if you want docs accessible
```

**Generate JWT Secret:**
```bash
openssl rand -hex 32
```

#### Create Required Directories

```bash
# Create logs directory
mkdir -p logs

# Set permissions
sudo chown -R www:www /www/wwwroot/chatbot-itsupport
sudo chmod -R 755 /www/wwwroot/chatbot-itsupport
```

---

### 6. Cloudflare R2 Setup

#### Create R2 Bucket

1. **Login to Cloudflare Dashboard**
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Navigate to **R2 Object Storage**

2. **Create Bucket:**
   - Click **Create Bucket**
   - Bucket name: `chatbot-pdfs`
   - Location: **Automatic** (recommended)
   - Click **Create Bucket**

3. **Generate API Token:**
   - Go to **R2** → **Manage R2 API Tokens**
   - Click **Create API Token**
   - Token name: `chatbot-api-token`
   - Permissions: **Object Read & Write**
   - Click **Create API Token**

4. **Copy credentials:**
   - Account ID: `xxxxxxxxxxxxx`
   - Access Key ID: `xxxxxxxxxxxxx`
   - Secret Access Key: `xxxxxxxxxxxxx`

5. **Update `.env` file** dengan credentials di atas

---

### 7. Cloudflare Tunnel Setup

#### Install Cloudflared

```bash
# Download and install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Verify installation
cloudflared --version
```

#### Authenticate Cloudflared

```bash
# Login to Cloudflare
cloudflared tunnel login

# This will open browser for authentication
# Follow the instructions and select your domain
```

#### Create Tunnel

```bash
# Create tunnel
cloudflared tunnel create chatbot-api

# Note the Tunnel ID from output
# Tunnel credentials saved to: ~/.cloudflared/<TUNNEL_ID>.json
```

#### Configure Tunnel

```bash
# Create config directory
sudo mkdir -p /etc/cloudflared

# Create config file
sudo nano /etc/cloudflared/config.yml
```

**Add this configuration:**

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

**Replace:**
- `<TUNNEL_ID>` dengan tunnel ID Anda
- `api.yourdomain.com` dengan domain API Anda

#### Create DNS Record

```bash
# Route tunnel to your domain
cloudflared tunnel route dns chatbot-api api.yourdomain.com
```

#### Install Tunnel as Service

```bash
# Install cloudflared as systemd service
sudo cloudflared service install

# Start tunnel
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

---

### 8. Systemd Service Setup

#### Copy Systemd Service File

```bash
# Copy service file
sudo cp systemd/chatbot-itsupport.service /etc/systemd/system/

# Edit if needed (update paths/user)
sudo nano /etc/systemd/system/chatbot-itsupport.service
```

**Verify paths in service file:**
- `WorkingDirectory=/www/wwwroot/chatbot-itsupport`
- `ExecStart=/www/wwwroot/chatbot-itsupport/venv/bin/uvicorn ...`
- `User=www` (aaPanel default user)
- `Group=www`

#### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable chatbot-itsupport

# Start service
sudo systemctl start chatbot-itsupport

# Check status
sudo systemctl status chatbot-itsupport
```

**Expected output:**
```
● chatbot-itsupport.service - Chatbot IT Support API Service
   Loaded: loaded (/etc/systemd/system/chatbot-itsupport.service; enabled)
   Active: active (running) since ...
```

#### Service Management Commands

```bash
# Start service
sudo systemctl start chatbot-itsupport

# Stop service
sudo systemctl stop chatbot-itsupport

# Restart service
sudo systemctl restart chatbot-itsupport

# View logs
sudo journalctl -u chatbot-itsupport -f

# Check status
sudo systemctl status chatbot-itsupport
```

---

### 9. Create Admin User

#### Run Admin Creation Script

```bash
# Activate virtual environment
cd /www/wwwroot/chatbot-itsupport
source venv/bin/activate

# Run script
python scripts/create_admin.py
```

**Follow prompts:**
```
Enter admin username: admin
Enter admin email: admin@yourdomain.com
Enter admin full name: Admin User
Enter admin password: [secure password]
```

**Output:**
```
✓ Database tables created
✓ Admin user created successfully!
  ID: xxxxx-xxxx-xxxx
  Username: admin
  Email: admin@yourdomain.com
  Role: admin
```

---

## ✅ Verification

### 1. Check Services Status

```bash
# PostgreSQL
sudo systemctl status postgresql

# Redis
sudo systemctl status redis-server

# Cloudflared tunnel
sudo systemctl status cloudflared

# Application
sudo systemctl status chatbot-itsupport
```

### 2. Test API Endpoints

#### Root Endpoint
```bash
curl https://api.yourdomain.com/
```

**Expected response:**
```json
{
  "message": "Welcome to the Multi-modal RAG API! Documentation is available at https://api.yourdomain.com/docs",
  "version": "1.0.0",
  "status": "running",
  "docs_url": "https://api.yourdomain.com/docs"
}
```

#### Health Check
```bash
curl https://api.yourdomain.com/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-08T12:00:00.000000",
  "version": "1.0.0"
}
```

#### Login Test
```bash
curl -X POST "https://api.yourdomain.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"
```

**Expected response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Check Application Logs

```bash
# View application logs
tail -f /www/wwwroot/chatbot-itsupport/logs/app.log

# View error logs
tail -f /www/wwwroot/chatbot-itsupport/logs/error.log

# Or via journalctl
sudo journalctl -u chatbot-itsupport -f
```

**Look for:**
```
INFO:     Starting Multi-modal RAG API v1.0.0
INFO:     R2 storage client initialized for bucket: chatbot-pdfs
INFO:     Cleanup scheduler started (runs daily at 2:00 AM UTC)
INFO:     Database tables created successfully
INFO:     Application startup complete
```

---

## 📊 Monitoring & Logs

### Application Logs

```bash
# Real-time logs
tail -f /www/wwwroot/chatbot-itsupport/logs/app.log

# Last 100 lines
tail -n 100 /www/wwwroot/chatbot-itsupport/logs/app.log

# Search for errors
grep "ERROR" /www/wwwroot/chatbot-itsupport/logs/app.log
```

### System Logs

```bash
# Application service logs
sudo journalctl -u chatbot-itsupport -f

# Cloudflare tunnel logs
sudo journalctl -u cloudflared -f

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# Redis logs
sudo tail -f /var/log/redis/redis-server.log
```

### Resource Monitoring

```bash
# CPU and Memory usage
htop

# Disk usage
df -h

# PostgreSQL status
sudo -u postgres psql -c "SELECT version();"

# Redis status
redis-cli INFO server
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. **Service Won't Start**

**Symptoms:**
```bash
sudo systemctl status chatbot-itsupport
# Shows: failed
```

**Solutions:**
```bash
# Check logs
sudo journalctl -u chatbot-itsupport -n 50

# Common causes:
# - Missing dependencies
pip install -r requirements.txt

# - Wrong permissions
sudo chown -R www:www /www/wwwroot/chatbot-itsupport

# - Port already in use
sudo lsof -i :8000
```

#### 2. **Database Connection Error**

**Symptoms:**
```
ERROR: could not connect to database
```

**Solutions:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U chatbot_user -d chatbot_db -h localhost

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

#### 3. **Redis Connection Error**

**Symptoms:**
```
ERROR: Connection refused (Redis)
```

**Solutions:**
```bash
# Check Redis is running
sudo systemctl status redis-server

# Test connection
redis-cli ping

# Restart Redis
sudo systemctl restart redis-server
```

#### 4. **R2 Storage Error**

**Symptoms:**
```
StorageError: Failed to initialize R2 storage client
```

**Solutions:**
```bash
# Verify R2 credentials in .env
cat .env | grep R2_

# Test credentials with AWS CLI
pip install awscli
aws configure set aws_access_key_id YOUR_R2_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_R2_SECRET_KEY
aws s3 ls --endpoint-url https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
```

#### 5. **Cloudflare Tunnel Not Working**

**Symptoms:**
```
502 Bad Gateway when accessing domain
```

**Solutions:**
```bash
# Check tunnel status
sudo systemctl status cloudflared

# Test local API
curl http://localhost:8000/

# Restart tunnel
sudo systemctl restart cloudflared

# Check tunnel logs
sudo journalctl -u cloudflared -f
```

#### 6. **PDF Processing Errors**

**Symptoms:**
```
PDFProcessingError: Failed to process PDF
```

**Solutions:**
```bash
# Install missing dependencies
sudo apt install -y poppler-utils tesseract-ocr

# Verify tesseract
tesseract --version

# Check file permissions
ls -la /www/wwwroot/chatbot-itsupport
```

---

## 🔒 Security Checklist

### Application Security

- [ ] **Change default admin password** immediately after creation
- [ ] **Generate strong JWT_SECRET_KEY** (min 32 chars)
- [ ] **Disable API docs in production** (`ENABLE_DOCS=false`)
- [ ] **Use strong database passwords**
- [ ] **Enable Redis password** if exposed to network
- [ ] **Configure rate limiting** appropriately
- [ ] **Set restrictive CORS_ORIGINS**

### Server Security

```bash
# Enable UFW firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 7800/tcp  # aaPanel (optional, can be disabled)

# Disable password authentication (use SSH keys)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd

# Keep system updated
sudo apt update && sudo apt upgrade -y
```

### aaPanel Security

1. **Change default port:**
   - aaPanel → Settings → Panel Settings → Panel Port

2. **Enable SSL for aaPanel:**
   - Settings → SSL → Let's Encrypt

3. **Restrict IP access:**
   - Security → IP Whitelist

---

## 🔄 Maintenance

### Regular Tasks

#### Daily
```bash
# Check application logs for errors
tail -n 100 /www/wwwroot/chatbot-itsupport/logs/error.log | grep ERROR
```

#### Weekly
```bash
# Check disk usage
df -h

# Monitor R2 storage usage (Cloudflare Dashboard)
# Check application health
curl https://api.yourdomain.com/health
```

#### Monthly
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
cd /www/wwwroot/chatbot-itsupport
source venv/bin/activate
pip list --outdated

# Backup database
sudo -u postgres pg_dump chatbot_db > backup_$(date +%Y%m%d).sql

# Clean up old logs (optional)
find /www/wwwroot/chatbot-itsupport/logs -name "*.log" -mtime +30 -delete
```

### Updating Application

```bash
# Stop service
sudo systemctl stop chatbot-itsupport

# Backup current version
cd /www/wwwroot
tar -czf chatbot-itsupport-backup-$(date +%Y%m%d).tar.gz chatbot-itsupport/

# Pull latest changes
cd chatbot-itsupport
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Run database migrations (if any)
# alembic upgrade head

# Restart service
sudo systemctl restart chatbot-itsupport

# Verify
curl https://api.yourdomain.com/health
```

### Backup Strategy

```bash
# Automated backup script
sudo nano /usr/local/bin/backup-chatbot.sh
```

**Add:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/chatbot"
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump chatbot_db > $BACKUP_DIR/db_$DATE.sql

# Backup .env file
cp /www/wwwroot/chatbot-itsupport/.env $BACKUP_DIR/env_$DATE

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-chatbot.sh

# Add to crontab (daily 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-chatbot.sh
```

---

## 📞 Support & Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Redis Docs](https://redis.io/docs/)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

### Useful Commands

```bash
# Quick service restart all
sudo systemctl restart chatbot-itsupport cloudflared

# View all logs
sudo journalctl -u chatbot-itsupport -u cloudflared -f

# Check all service status
systemctl status chatbot-itsupport cloudflared postgresql redis-server

# Test API with authentication
TOKEN=$(curl -s -X POST "https://api.yourdomain.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password" | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" https://api.yourdomain.com/api/v1/users/me
```

---

<div align="center">

## 🎉 Deployment Complete!

Your Chatbot IT Support API is now running in production

**API URL**: `https://api.yourdomain.com`
**Documentation**: `https://api.yourdomain.com/docs`
**Health Check**: `https://api.yourdomain.com/health`

---

### Built with ❤️ using

FastAPI • PostgreSQL • Redis • OpenAI • Pinecone • Cloudflare

---

**Need help?** Check [Troubleshooting](#-troubleshooting) or review application logs

**Last Updated**: October 2025

</div>
