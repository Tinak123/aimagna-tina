#!/bin/bash

# AIMagna ETL Agent - Automated Setup Script
# This script sets up both backend and frontend environments

set -e  # Exit on any error

echo "========================================"
echo "AIMagna ETL Agent - Setup Script"
echo "========================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${YELLOW}Warning: This script is optimized for macOS${NC}"
fi

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check for Python 3
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_status "Found Python $PYTHON_VERSION"

# Check for pip3
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip3 first."
    exit 1
fi
print_status "Found pip3"

# Check for Node.js and npm
echo ""
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node --version)
print_status "Found Node.js $NODE_VERSION"

if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm first."
    exit 1
fi

NPM_VERSION=$(npm --version)
print_status "Found npm $NPM_VERSION"

# Step 1: Backend Setup
echo ""
echo "========================================"
echo "Step 1: Setting up Python Backend"
echo "========================================"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_warning "Virtual environment already exists, skipping creation"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo "Upgrading pip..."
pip3 install --upgrade pip > /dev/null 2>&1
print_status "pip upgraded"

# Install Python dependencies
echo "Installing Python dependencies (this may take a few minutes)..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    print_status "Python dependencies installed"
else
    print_error "requirements.txt not found!"
    exit 1
fi

# Step 2: Check .env file
echo ""
echo "========================================"
echo "Step 2: Checking Environment Configuration"
echo "========================================"

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Please create one based on .env file in the project."
    echo ""
    echo "Required environment variables:"
    echo "  - GCP_PROJECT_ID"
    echo "  - GCP_REGION"
    echo "  - BIGQUERY_DATASET"
    echo "  - GCS_BUCKET"
    echo ""
else
    print_status ".env file exists"
fi

# Check for GCP authentication
echo ""
echo "Checking GCP authentication..."

# Function to check if Application Default Credentials exist
check_adc() {
    # Check if ADC file exists
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
        return 0
    fi
    # Check if running on GCE/Cloud Run (metadata server available)
    if curl -s -f -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

GCP_AUTH_AVAILABLE=false

# First check for service account key (legacy)
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    print_status "Service account key found at $GOOGLE_APPLICATION_CREDENTIALS"
    GCP_AUTH_AVAILABLE=true
# Then check for Application Default Credentials (gcloud auth)
elif check_adc; then
    print_status "Application Default Credentials found (gcloud auth)"
    GCP_AUTH_AVAILABLE=true
else
    print_warning "No GCP credentials found. System will run in MOCK MODE."
    echo ""
    echo "           To enable full GCP functionality, run:"
    echo "             gcloud auth application-default login"
    echo ""
fi

# Step 3: Verify GCP Access (if credentials exist)
if [ "$GCP_AUTH_AVAILABLE" = true ]; then
    echo ""
    echo "========================================"
    echo "Step 3: Verifying GCP Access"
    echo "========================================"

    echo "Testing BigQuery connection..."
    if python3 -c "from google.cloud import bigquery; bigquery.Client()" 2>/dev/null; then
        print_status "BigQuery connection successful"
    else
        print_warning "BigQuery connection failed (will use mock mode)"
    fi

    echo "Testing GCS connection..."
    if python3 -c "from google.cloud import storage; storage.Client()" 2>/dev/null; then
        print_status "GCS connection successful"
    else
        print_warning "GCS connection failed (will use mock mode)"
    fi

    echo "Testing Firestore connection..."
    if python3 -c "from google.cloud import firestore; firestore.Client()" 2>/dev/null; then
        print_status "Firestore connection successful"
    else
        print_warning "Firestore connection failed (will use mock mode)"
    fi
else
    print_warning "Skipping GCP verification (no credentials configured)"
fi

# Step 4: Frontend Setup
echo ""
echo "========================================"
echo "Step 4: Setting up React Frontend"
echo "========================================"

if [ ! -d "frontend" ]; then
    print_error "frontend/ directory not found!"
    exit 1
fi

cd frontend

# Install frontend dependencies
echo "Installing frontend dependencies (this may take a few minutes)..."
if [ -f "package.json" ]; then
    npm install
    print_status "Frontend dependencies installed"
else
    print_error "package.json not found in frontend/"
    exit 1
fi

# Create frontend .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating frontend .env file..."
    cat > .env << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_GCP_PROJECT_ID=ccibt-hack25ww7-713
EOF
    print_status "Frontend .env file created"
else
    print_status "Frontend .env file already exists"
fi

cd ..

# Step 5: Create startup scripts
echo ""
echo "========================================"
echo "Step 5: Creating Startup Scripts"
echo "========================================"

# Create backend startup script
cat > start_backend.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
uvicorn src.nl_agent.main:app --reload --host 0.0.0.0 --port 8000
EOF
chmod +x start_backend.sh
print_status "Created start_backend.sh"

# Create frontend startup script
cat > start_frontend.sh << 'EOF'
#!/bin/bash
cd frontend
npm run dev
EOF
chmod +x start_frontend.sh
print_status "Created start_frontend.sh"

# Create combined startup script
cat > start_all.sh << 'EOF'
#!/bin/bash

# Start backend in background
echo "Starting backend..."
./start_backend.sh > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Start frontend
echo "Starting frontend..."
./start_frontend.sh

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
EOF
chmod +x start_all.sh
print_status "Created start_all.sh"

# Final summary
echo ""
echo "========================================"
echo "Setup Complete! 🎉"
echo "========================================"
echo ""
echo "To start the application:"
echo ""
echo "Option 1: Start both services together"
echo "  $ ./start_all.sh"
echo ""
echo "Option 2: Start services separately"
echo "  Terminal 1 (Backend):"
echo "    $ ./start_backend.sh"
echo "  Terminal 2 (Frontend):"
echo "    $ ./start_frontend.sh"
echo ""
echo "Access Points:"
echo "  Frontend:     http://localhost:5173"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo ""
if [ "$GCP_AUTH_AVAILABLE" != true ]; then
    print_warning "Running in MOCK MODE (no GCP credentials)"
    echo "           To enable full GCP functionality:"
    echo "           1. Run: gcloud auth application-default login"
    echo "           2. Set your project: gcloud config set project YOUR-PROJECT-ID"
    echo "           3. Restart the application"
    echo ""
fi
echo "For detailed documentation, see README.md and SETUP.md"
echo ""
