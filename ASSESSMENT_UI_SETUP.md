# Assessment UI Setup Guide

Complete setup guide for the `/assessment` endpoint with Google OAuth authentication.

## 🚀 Quick Start

The assessment UI is now accessible at `http://your-vps-ip/api/v1/assessment` with Google OAuth authentication.

## 📋 Prerequisites

1. **Google Cloud Console Setup**
2. **Environment Variables**
3. **Database & Redis**
4. **SSL/HTTPS (Recommended)**

## 🔧 Google OAuth Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API (for OAuth)

### 2. Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Add authorized origins:
   ```
   http://your-vps-ip:8000
   https://your-domain.com
   ```
5. Add authorized redirect URIs:
   ```
   http://your-vps-ip:8000/api/v1/assessment
   https://your-domain.com/api/v1/assessment
   ```
6. Copy the **Client ID** and **Client Secret**

## ⚙️ Environment Configuration

### 1. Copy Environment Template
```bash
cp .env.example .env
```

### 2. Update Required Variables
```bash
# Required for Assessment UI
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
JWT_SECRET="your-super-secret-jwt-key"

# Database (Required)
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/leadshop"

# Redis (Required for Celery)
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/1"

# API Keys (Required for assessments)
GOOGLE_API_KEY="your-google-api-key"
OPENAI_API_KEY="your-openai-api-key"
SCREENSHOTONE_ACCESS_KEY="your-screenshotone-key"
```

## 🛠️ Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Services

**Start Redis:**
```bash
redis-server
```

**Start Celery Worker:**
```bash
celery -A src.core.celery_app worker --loglevel=info
```

**Start FastAPI Server:**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 🌐 Access the Assessment UI

### Local Development
```
http://localhost:8000/api/v1/assessment
```

### Production (VPS)
```
http://your-vps-ip:8000/api/v1/assessment
```

## 🔐 Authentication Flow

1. **User visits** `/api/v1/assessment`
2. **Google OAuth** sign-in required
3. **JWT token** issued for API access
4. **Assessment execution** with real-time progress
5. **Results display** with comprehensive data

## 📊 API Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/api/v1/assessment` | GET | Serve UI | No |
| `/api/v1/assessment/config` | GET | UI configuration | No |
| `/api/v1/assessment/auth/google` | POST | Google OAuth | No |
| `/api/v1/assessment/execute` | POST | Run assessment | Yes |
| `/api/v1/assessment/status/{task_id}` | GET | Check progress | Yes |

## 🧪 Testing the Setup

### 1. Test Authentication
```bash
curl -X GET http://your-vps-ip:8000/api/v1/assessment/config
```

### 2. Test UI Access
Visit `http://your-vps-ip:8000/api/v1/assessment` in browser

### 3. Test Google OAuth
1. Click "Sign in with Google"
2. Complete OAuth flow
3. Verify JWT token storage

### 4. Test Assessment
1. Enter URL: `https://example.com`
2. Click "Analyze Website"
3. Monitor real-time progress
4. View comprehensive results

## 🔒 Security Best Practices

### 1. HTTPS Setup (Recommended)
```bash
# Using Let's Encrypt with nginx
sudo apt install certbot nginx
sudo certbot --nginx -d your-domain.com
```

### 2. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 3. Environment Security
```bash
# Secure .env file
chmod 600 .env
chown app:app .env
```

## 🚨 Troubleshooting

### Google OAuth Issues
- **Invalid Client**: Check Client ID in environment
- **Redirect URI Mismatch**: Update authorized URIs in Google Console
- **Token Verification Failed**: Check Client Secret

### API Connection Issues
- **CORS Errors**: Update CORS settings in `main.py`
- **Database Connection**: Verify DATABASE_URL
- **Redis Connection**: Check Redis service status

### Assessment Execution Issues
- **Task Not Starting**: Check Celery worker status
- **API Key Errors**: Verify external API credentials
- **Timeout Issues**: Check component timeout settings

## 📈 Monitoring

### Health Check Endpoint
```bash
curl http://your-vps-ip:8000/health
```

### Celery Monitoring
```bash
# Monitor Celery tasks
celery -A src.core.celery_app status
celery -A src.core.celery_app monitor
```

### Application Logs
```bash
# View application logs
tail -f /var/log/leadshop/app.log
```

## 🎯 Production Deployment

### 1. Process Manager
```bash
# Using systemd
sudo cp configs/leadshop.service /etc/systemd/system/
sudo systemctl enable leadshop
sudo systemctl start leadshop
```

### 2. Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Database Migrations
```bash
# Run Alembic migrations
alembic upgrade head
```

## 🎉 Success!

Your assessment UI should now be accessible at:
- **Development**: `http://localhost:8000/api/v1/assessment`
- **Production**: `http://your-vps-ip:8000/api/v1/assessment`

Users can now:
1. ✅ Sign in with Google OAuth
2. ✅ Execute comprehensive website assessments  
3. ✅ Monitor real-time assessment progress
4. ✅ View detailed results with business impact metrics
5. ✅ Access all 8 assessment components including GBP data

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Verify environment configuration
4. Test individual API endpoints