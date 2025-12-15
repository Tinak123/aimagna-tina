# AIMagna ETL Agent - Detailed Setup Guide

This guide provides comprehensive step-by-step instructions for setting up the AIMagna ETL Agent React Chatbot UI.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [GCP Prerequisites](#gcp-prerequisites)
3. [Automated Setup](#automated-setup)
4. [Manual Setup](#manual-setup)
5. [Configuration](#configuration)
6. [Verification](#verification)
7. [Running the Application](#running-the-application)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Operating System
- **macOS** (primary support)
- **Linux** (Ubuntu 20.04+, minor modifications needed)
- **Windows** (via WSL2, manual setup required)

### Software Prerequisites

#### Required
- **Python 3.8 or higher**
  ```bash
  python3 --version  # Should show 3.8.0 or higher
  ```
- **pip3** (Python package manager)
  ```bash
  pip3 --version
  ```
- **Node.js 18 or higher**
  ```bash
  node --version  # Should show v18.0.0 or higher
  ```
- **npm** (Node package manager)
  ```bash
  npm --version  # Should show 8.0.0 or higher
  ```

#### Optional (for GCP functionality)
- **Google Cloud SDK**
  ```bash
  gcloud --version
  ```

### Hardware Requirements
- **RAM**: Minimum 4GB, recommended 8GB+
- **Disk Space**: 2GB free space
- **CPU**: Modern multi-core processor recommended

---

## GCP Prerequisites

### Option 1: Full GCP Functionality

#### 1. Create GCP Project
```bash
gcloud projects create YOUR-PROJECT-ID
gcloud config set project YOUR-PROJECT-ID
```

#### 2. Enable Required APIs
```bash
# Enable all required APIs
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable firestore.googleapis.com
```

#### 3. Authenticate with Google Cloud (Recommended)

**Option A: User Account Authentication (Recommended for Development)**

Use Application Default Credentials with your Google account - no service account key file needed:

```bash
# Login with your Google account
gcloud auth application-default login

# Set your project
gcloud config set project YOUR-PROJECT-ID

# Set quota project (optional, helps avoid billing issues)
gcloud auth application-default set-quota-project YOUR-PROJECT-ID
```

This creates credentials at `~/.config/gcloud/application_default_credentials.json` that the client libraries automatically detect.

**Ensure your user account has the required IAM roles:**
```bash
# Get your user email
export USER_EMAIL=$(gcloud config get-value account)

# Grant required roles to your user account
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="user:${USER_EMAIL}" \
  --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="user:${USER_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="user:${USER_EMAIL}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="user:${USER_EMAIL}" \
  --role="roles/datastore.user"
```

**Option B: Service Account with Key File (Legacy/CI-CD)**

Only use this if you need a service account key file (e.g., for CI/CD pipelines):

```bash
# Create service account
gcloud iam service-accounts create aimagna-etl-agent \
  --display-name="AIMagna ETL Agent Service Account"

# Get service account email
export SA_EMAIL="aimagna-etl-agent@YOUR-PROJECT-ID.iam.gserviceaccount.com"

# Grant required roles
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"

# Create and download key file (avoid if possible - use Option A instead)
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=${SA_EMAIL}

# Set environment variable to point to the key file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

#### 4. Create GCS Bucket
```bash
gsutil mb -p YOUR-PROJECT-ID -l us-central1 gs://YOUR-BUCKET-NAME
```

#### 5. Create BigQuery Dataset
```bash
bq --location=us-central1 mk --dataset YOUR-PROJECT-ID:commercial_lending
```

#### 6. Initialize Firestore
```bash
gcloud firestore databases create --region=us-central1
```

### Option 2: Mock Mode (Development Only)
Skip all GCP setup. The system will run in mock mode with simulated data.

---

## Automated Setup

The easiest way to set up the project is using the automated setup script.

### Step 1: Navigate to Project Directory
```bash
cd Sample-DataSet-CommercialLending
```

### Step 2: Make Setup Script Executable
```bash
chmod +x setup.sh
```

### Step 3: Run Setup Script
```bash
./setup.sh
```

The script will:
1. ✓ Check Python and Node.js installations
2. ✓ Create Python virtual environment
3. ✓ Install backend dependencies
4. ✓ Install frontend dependencies
5. ✓ Verify GCP access (if credentials provided)
6. ✓ Create startup scripts

### Expected Output
```
========================================
AIMagna ETL Agent - Setup Script
========================================

Checking Python installation...
✓ Found Python 3.11.5
✓ Found pip3

Checking Node.js installation...
✓ Found Node.js v20.10.0
✓ Found npm 10.2.3

========================================
Step 1: Setting up Python Backend
========================================
✓ Virtual environment created
✓ Virtual environment activated
✓ pip upgraded
✓ Python dependencies installed

========================================
Step 2: Checking Environment Configuration
========================================
⚠ .env file not found. Please create one based on .env template.

Required environment variables:
  - GCP_PROJECT_ID
  - GCP_REGION
  - BIGQUERY_DATASET
  - GCS_BUCKET

Checking GCP authentication...
✓ Application Default Credentials found (gcloud auth)

========================================
Step 3: Verifying GCP Access
========================================
Testing BigQuery connection...
✓ BigQuery connection successful

========================================
Step 4: Setting up React Frontend
========================================
✓ Frontend dependencies installed
✓ Frontend .env file created

========================================
Step 5: Creating Startup Scripts
========================================
✓ Created start_backend.sh
✓ Created start_frontend.sh
✓ Created start_all.sh

========================================
Setup Complete! 🎉
========================================
```

---

## Manual Setup

If the automated setup fails or you prefer manual installation:

### Backend Setup

#### 1. Create Virtual Environment
```bash
python3 -m venv venv
```

#### 2. Activate Virtual Environment
```bash
# macOS/Linux
source venv/bin/activate

# Windows (WSL)
source venv/bin/activate
```

#### 3. Upgrade pip
```bash
pip3 install --upgrade pip
```

#### 4. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

**Dependencies installed:**
- `fastapi[all]==0.104.1` - Web framework
- `uvicorn[standard]==0.24.0` - ASGI server
- `python-socketio==5.10.0` - WebSocket support
- `google-cloud-bigquery` - BigQuery client
- `google-cloud-storage` - GCS client
- `google-cloud-aiplatform` - Vertex AI client
- `google-cloud-firestore==2.13.1` - Firestore client
- `google-auth==2.25.0` - Authentication
- `pandas` - Data processing
- `pydantic==2.5.0` - Data validation
- `python-multipart==0.0.6` - File upload support
- `aiofiles==23.2.1` - Async file operations
- `websockets==12.0` - WebSocket protocol
- `python-dotenv` - Environment variable loading

### Frontend Setup

#### 1. Navigate to Frontend Directory
```bash
cd frontend
```

#### 2. Install Node Dependencies
```bash
npm install
```

**Dependencies installed:**
- `react@18.2.0` - UI library
- `typescript@5.2.2` - Type safety
- `@mui/material@5.14.18` - Material-UI components
- `@mui/icons-material@5.14.18` - Material-UI icons
- `@tanstack/react-query@5.12.2` - Server state management
- `axios@1.6.2` - HTTP client
- `socket.io-client@4.7.2` - WebSocket client
- `zustand@4.4.7` - State management
- `@emotion/react@11.11.1` - CSS-in-JS
- `@emotion/styled@11.11.0` - Styled components

#### 3. Return to Root Directory
```bash
cd ..
```

---

## Configuration

### Backend Configuration

#### 1. Create `.env` File
```bash
cp .env.example .env  # If example exists
# OR
nano .env  # Create new file
```

#### 2. Configure Environment Variables

**For Mock Mode (Development without GCP):**
```bash
# GCP Configuration (placeholders - will run in mock mode)
GCP_PROJECT_ID="ccibt-hack25ww7-713"
GCP_REGION="us-central1"
BIGQUERY_DATASET="commercial_lending"
GCS_BUCKET="demo-data-transformation"

# Vertex AI
VERTEX_AI_INDEX_ENDPOINT_ID="409486717486104576"

# API Configuration
API_HOST="0.0.0.0"
API_PORT=8000
CORS_ORIGINS="http://localhost:5173,http://localhost:3000"

# Firestore Collections
FIRESTORE_COLLECTION_RUNS="workflow_runs"
FIRESTORE_COLLECTION_HITL="hitl_approvals"

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

# NL Query Settings
MAX_QUERY_RESULTS=1000
QUERY_TIMEOUT_SECONDS=30
```

**For Development/Production with GCP (Using gcloud auth - Recommended):**

First, authenticate using gcloud:
```bash
gcloud auth application-default login
gcloud config set project your-actual-project-id
```

Then configure `.env`:
```bash
# GCP Configuration
GCP_PROJECT_ID="your-actual-project-id"
GCP_REGION="us-central1"
BIGQUERY_DATASET="commercial_lending"
GCS_BUCKET="your-bucket-name"
# No GOOGLE_APPLICATION_CREDENTIALS needed - uses gcloud auth automatically!

# Vertex AI
VERTEX_AI_INDEX_ENDPOINT_ID="your-endpoint-id"

# API Configuration
API_HOST="0.0.0.0"
API_PORT=8000
CORS_ORIGINS="http://localhost:5173,http://localhost:3000"

# Firestore Collections
FIRESTORE_COLLECTION_RUNS="workflow_runs"
FIRESTORE_COLLECTION_HITL="hitl_approvals"

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

# NL Query Settings
MAX_QUERY_RESULTS=1000
QUERY_TIMEOUT_SECONDS=30
```

**For CI/CD or Service Account Key (Legacy):**
```bash
# GCP Configuration
GCP_PROJECT_ID="your-actual-project-id"
GCP_REGION="us-central1"
BIGQUERY_DATASET="commercial_lending"
GCS_BUCKET="your-bucket-name"
GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account-key.json"

# ... rest of configuration same as above
```

### Frontend Configuration

#### 1. Create `frontend/.env` File
```bash
cd frontend
nano .env
```

#### 2. Add Configuration
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_GCP_PROJECT_ID=ccibt-hack25ww7-713
```

**Note**: Change URLs for production deployment.

---

## Verification

### 1. Verify Python Environment
```bash
# Activate virtual environment
source venv/bin/activate

# Check Python version
python3 --version

# Verify imports
python3 << EOF
import fastapi
import google.cloud.bigquery
import google.cloud.storage
import google.cloud.firestore
print("✓ All Python imports successful")
EOF
```

### 2. Verify GCP Access (Optional)
```bash
# Verify gcloud auth is configured
gcloud auth application-default print-access-token

# Test GCP connections
python3 -c "from google.cloud import bigquery; bigquery.Client(); print('✓ BigQuery OK')"
python3 -c "from google.cloud import storage; storage.Client(); print('✓ GCS OK')"
python3 -c "from google.cloud import firestore; firestore.Client(); print('✓ Firestore OK')"
```

### 3. Verify Frontend Dependencies
```bash
cd frontend
npm list --depth=0
cd ..
```

### 4. Test Backend Server
```bash
# Start backend
source venv/bin/activate
uvicorn src.nl_agent.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for startup
sleep 3

# Test API
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Stop backend
kill $BACKEND_PID
```

### 5. Test Frontend Build
```bash
cd frontend
npm run build
cd ..
```

---

## Running the Application

### Option 1: Using Startup Scripts

#### Start Both Services
```bash
./start_all.sh
```

#### Start Services Separately
```bash
# Terminal 1: Backend
./start_backend.sh

# Terminal 2: Frontend
./start_frontend.sh
```

### Option 2: Manual Commands

#### Backend (Terminal 1)
```bash
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
uvicorn src.nl_agent.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

### Access the Application

1. **Frontend UI**: Open browser to http://localhost:5173
2. **Backend API**: http://localhost:8000
3. **API Documentation**: http://localhost:8000/docs
4. **Alternative API Docs**: http://localhost:8000/redoc

---

## Troubleshooting

### Issue: "Command not found: python3"
**Solution:**
```bash
# Install Python 3
# macOS
brew install python3

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip
```

### Issue: "Command not found: node"
**Solution:**
```bash
# Install Node.js
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Issue: "Permission denied: ./setup.sh"
**Solution:**
```bash
chmod +x setup.sh
```

### Issue: "Port 8000 already in use"
**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# OR change port in .env
API_PORT=8001
```

### Issue: "Port 5173 already in use"
**Solution:**
```bash
# Find process using port 5173
lsof -i :5173

# Kill the process
kill -9 <PID>
```

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution:**
```bash
source venv/bin/activate
pip3 install -r requirements.txt
```

### Issue: "npm ERR! code ENOENT"
**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: GCP Authentication Errors
**Solution:**

**Option A: Using gcloud auth (Recommended)**
```bash
# Login with Application Default Credentials
gcloud auth application-default login

# Set your project
gcloud config set project YOUR-PROJECT-ID

# Verify authentication works
gcloud auth application-default print-access-token

# Test GCP connection
python3 -c "from google.cloud import bigquery; bigquery.Client(); print('✓ Authentication working')"
```

**Option B: Using Service Account Key (Legacy)**
```bash
# Verify credentials file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# Test authentication
gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
gcloud config set project YOUR-PROJECT-ID

# Verify project
gcloud config get-value project
```

### Issue: "Cannot connect to WebSocket"
**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in `.env`
3. Check browser console for errors
4. Try different browser
5. Disable browser extensions

### Issue: Firestore Connection Failed
**Solution:**
```bash
# Enable Firestore API
gcloud services enable firestore.googleapis.com

# Create Firestore database
gcloud firestore databases create --region=us-central1

# Verify permissions
gcloud projects get-iam-policy YOUR-PROJECT-ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:YOUR-SA-EMAIL"
```

### Issue: Frontend Build Fails
**Solution:**
```bash
cd frontend

# Clear cache
rm -rf node_modules .vite dist

# Reinstall
npm install

# Try build again
npm run build
```

### Issue: Backend Logs Show Import Errors
**Solution:**
```bash
# Deactivate and reactivate venv
deactivate
source venv/bin/activate

# Reinstall all dependencies
pip3 install --upgrade -r requirements.txt
```

---

## Next Steps

After successful setup:

1. **Read User Guide**: Check `CHATBOT_UI.md` for usage instructions
2. **Explore API Docs**: Visit http://localhost:8000/docs
3. **Upload Test Data**: Try uploading a CSV file
4. **Run Workflow**: Start an ETL pipeline
5. **Query Data**: Test natural language queries

---

## Advanced Configuration

### Custom Port Configuration
```bash
# Backend
API_PORT=9000

# Frontend (frontend/vite.config.ts)
server: { port: 3000 }
```

### Production Environment Variables
```bash
# .env.production
API_HOST="0.0.0.0"
CORS_ORIGINS="https://yourdomain.com"
```

### Docker Deployment
```dockerfile
# Dockerfile (create new file)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.nl_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Support

For additional help:
- Review `CHATBOT_UI.md` for feature documentation
- Check API docs at http://localhost:8000/docs
- Review backend logs: `tail -f backend.log`
- Check browser console for frontend errors

---

## Maintenance

### Updating Dependencies

#### Backend
```bash
source venv/bin/activate
pip3 install --upgrade -r requirements.txt
```

#### Frontend
```bash
cd frontend
npm update
npm audit fix
```

### Backing Up Configuration
```bash
# Backup .env files
cp .env .env.backup
cp frontend/.env frontend/.env.backup

# Backup service account key (if using legacy auth)
# cp service-account-key.json service-account-key.json.backup
```

---

**Setup Complete!** You're ready to use the AIMagna ETL Agent Chatbot UI.
