# AIMagna ETL Agent - React Chatbot UI

A production-ready React chatbot interface for the AIMagna multi-agent ETL system that transforms commercial lending data from operational schemas to BigQuery star schemas.

## Features

- **Interactive Chat Interface**: Upload CSV files and interact with the ETL pipeline through natural language
- **Real-Time Workflow Updates**: WebSocket-based live progress tracking for all 8 agent operations
- **Web-Based HITL Approval**: Review and approve/reject AI-generated column mappings directly in the UI
- **Natural Language Queries**: Ask questions about transformed data using Vertex AI Gemini (e.g., "What are total payments by borrower?")
- **Visual Results**: Query results displayed in interactive tables with pagination and sorting
- **Mock Mode**: Development mode that works without GCP credentials

## Architecture

### Backend (Python + FastAPI)
- **NL Agent API**: 10 REST endpoints + WebSocket for real-time updates
- **Orchestrator Agent**: Coordinates 7 specialized agents with progress broadcasting
- **HITL Agent**: Web-based approval system using Firestore state management
- **NL-to-SQL Service**: Vertex AI Gemini integration for natural language queries

### Frontend (React + TypeScript)
- **Chat Interface**: Material-UI based conversational UI
- **HITL Approval**: Interactive approval cards with bulk actions
- **Query Interface**: NL-to-SQL conversion with syntax-highlighted SQL preview
- **WebSocket Integration**: Real-time workflow updates

### GCP Services
- **BigQuery**: Target data warehouse for transformed data
- **Cloud Storage**: CSV file storage and staging
- **Vertex AI**: Gemini LLM for NL-to-SQL and semantic embeddings
- **Firestore**: Workflow state and HITL approval persistence

## Quick Start

### Prerequisites
- **macOS** (or Linux with modifications)
- **Python 3.8+** and **pip3**
- **Node.js 18+** and **npm**
- **GCP Service Account** (optional for full functionality)

### Installation

```bash
# Clone the repository
cd Sample-DataSet-CommercialLending

# Run automated setup script
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Create Python virtual environment
2. Install all backend dependencies
3. Install all frontend dependencies
4. Verify GCP access (if credentials configured)
5. Create startup scripts

### Running the Application

**Option 1: Start both services together**
```bash
./start_all.sh
```

**Option 2: Start services separately**
```bash
# Terminal 1: Backend
./start_backend.sh

# Terminal 2: Frontend
./start_frontend.sh
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **WebSocket**: ws://localhost:8000/ws/{run_id}

## User Workflow

### 1. Upload CSV Files
- Drag and drop CSV files into the chat interface
- Files are uploaded to Google Cloud Storage
- System generates a unique `run_id` for tracking

### 2. Start ETL Pipeline
- Click "Start Processing" button
- Orchestrator executes 7 agents in sequence:
  1. **Profiler Agent** (5-15%): Analyzes source data structure
  2. **Mapper Agent** (15-40%): Generates column mappings using AI embeddings
  3. **HITL Agent** (40-50%): Requests human approval for mappings
  4. **Transform Agent** (50-70%): Applies approved transformations
  5. **Validator Agent** (70-85%): Validates data quality
  6. **Feedback Agent** (85-95%): Logs results and metrics
  7. **Completion** (95-100%): Finalizes workflow

### 3. Review HITL Mappings
- AI-generated column mappings appear as cards in chat
- Each card shows:
  - Source column → Target column
  - Confidence score (color-coded: green ≥90%, yellow ≥80%, gray <80%)
  - AI rationale for the mapping
- Actions:
  - **Approve** individual mappings
  - **Reject** individual mappings
  - **Approve All** mappings at once
  - **Reject All** mappings at once
  - **Approve High Confidence** (≥90%) only
- Submit all decisions to continue pipeline

### 4. Query Transformed Data
- Type natural language questions (e.g., "What are total payments by industry?")
- System converts to BigQuery SQL using Vertex AI Gemini
- Review generated SQL with syntax highlighting
- Execute query to see results in interactive table
- Export results as CSV (up to 1000 rows)

## API Endpoints

### File Management
- `POST /upload` - Upload CSV files to GCS

### Workflow Control
- `POST /workflow/start` - Start ETL pipeline
- `GET /workflow/status/{run_id}` - Get current workflow status
- `WebSocket /ws/{run_id}` - Real-time workflow updates

### HITL Approval
- `GET /hitl/mappings/{run_id}` - Get pending HITL approvals
- `POST /hitl/approve/{run_id}` - Submit approval decisions

### Natural Language Queries
- `POST /query/nl2sql` - Convert natural language to SQL
- `POST /query/execute` - Execute SQL query on BigQuery

### Metadata
- `GET /schema/target` - Get target schema metadata
- `GET /runs` - List all workflow runs

## Configuration

### Backend Configuration (.env)
```bash
# GCP Configuration
GCP_PROJECT_ID="ccibt-hack25ww7-713"
GCP_REGION="us-central1"
BIGQUERY_DATASET="commercial_lending"
GCS_BUCKET="demo-data-transformation"
# No GOOGLE_APPLICATION_CREDENTIALS needed when using gcloud auth

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

### Frontend Configuration (frontend/.env)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_GCP_PROJECT_ID=ccibt-hack25ww7-713
```

## GCP Setup (Optional)

For full functionality, you need GCP access with these roles:
- BigQuery Admin
- Storage Admin
- Vertex AI User
- Cloud Datastore User

### Steps (Using gcloud auth - Recommended):
1. Install Google Cloud SDK if not already installed
2. Login with Application Default Credentials:
   ```bash
   gcloud auth application-default login
   ```
3. Set your project:
   ```bash
   gcloud config set project YOUR-PROJECT-ID
   ```
4. Update `.env` file with your GCP_PROJECT_ID
5. Restart the application

### Alternative: Service Account Key (Legacy/CI-CD)
1. Create service account in GCP Console
2. Download JSON key file
3. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

**Without credentials**: System runs in **mock mode** for development.

## Technology Stack

### Backend
- **FastAPI 0.104** - Async web framework
- **Python SocketIO 5.10** - WebSocket support
- **Google Cloud Libraries** - BigQuery, Storage, Firestore, Vertex AI
- **Pydantic 2.5** - Data validation

### Frontend
- **React 18** - UI framework
- **TypeScript 5** - Type safety
- **Material-UI 5** - Component library
- **Vite 4** - Build tool
- **Zustand 4** - State management
- **Socket.io Client 4** - WebSocket client
- **Axios 1.6** - HTTP client
- **React Query** - Server state caching

## Project Structure

```
Sample-DataSet-CommercialLending/
├── src/
│   ├── nl_agent/
│   │   ├── main.py                 # FastAPI app with 10 endpoints
│   │   ├── websocket_manager.py    # WebSocket connection manager
│   │   └── nl2sql_service.py       # Vertex AI Gemini NL-to-SQL
│   ├── orchestrator_agent/
│   │   └── main.py                 # Workflow coordinator
│   ├── hitl_agent/
│   │   └── main.py                 # Human-in-the-loop approval
│   ├── core_tools/
│   │   └── state_store.py          # Firestore state management
│   └── [other agents...]
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface/      # Chat UI components
│   │   │   ├── HITL/               # Approval UI components
│   │   │   └── QueryInterface/     # Query UI components
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── services/               # API clients
│   │   ├── stores/                 # Zustand stores
│   │   └── types/                  # TypeScript types
│   └── package.json
├── requirements.txt                # Python dependencies
├── .env                           # Backend configuration
├── setup.sh                       # Automated setup script
├── start_backend.sh               # Backend startup script
├── start_frontend.sh              # Frontend startup script
└── start_all.sh                   # Combined startup script
```

## Troubleshooting

### Backend won't start
- Check Python version: `python3 --version` (need 3.8+)
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip3 install -r requirements.txt`
- Check `.env` file exists and has correct values
- Check port 8000 is not already in use: `lsof -i :8000`

### Frontend won't start
- Check Node version: `node --version` (need 18+)
- Delete `node_modules` and reinstall: `cd frontend && rm -rf node_modules && npm install`
- Check port 5173 is not already in use: `lsof -i :5173`
- Verify `frontend/.env` file exists

### GCP authentication errors
- Run `gcloud auth application-default login` to authenticate
- Verify authentication: `gcloud auth application-default print-access-token`
- Verify GCP project ID matches in `.env`
- Test connection: `python3 -c "from google.cloud import bigquery; bigquery.Client()"`
- If using service account key, check: `ls -la $GOOGLE_APPLICATION_CREDENTIALS`

### WebSocket connection fails
- Check backend is running on port 8000
- Verify CORS settings in `.env`
- Check browser console for connection errors
- Try refreshing the page
- Check firewall settings

### HITL approval stuck
- Check Firestore is accessible (or mock mode enabled)
- Verify `run_id` is correct
- Check backend logs for Firestore errors
- Verify all mappings have been reviewed before submitting

### Query execution fails
- Check BigQuery dataset exists: `commercial_lending`
- Verify SQL syntax is correct
- Check query timeout settings (default 30s)
- Ensure tables have been created by the ETL pipeline

## Development

### Running Tests
```bash
# Backend tests (when implemented)
source venv/bin/activate
pytest tests/

# Frontend tests (when implemented)
cd frontend
npm test
```

### Adding New Agents
1. Create agent file in `src/{agent_name}_agent/main.py`
2. Add agent call in `src/orchestrator_agent/main.py`
3. Add progress broadcasting for the new agent
4. Update frontend progress tracking

### Modifying Target Schema
1. Update `src/nl_agent/nl2sql_service.py` schema context
2. Update BigQuery table definitions
3. Update mapper agent semantic mappings

### Debugging Tips
- **Backend logs**: Check `backend.log` file
- **Frontend logs**: Check browser console (F12)
- **WebSocket messages**: Use browser dev tools Network tab
- **API requests**: Check `/docs` endpoint for Swagger UI
- **State inspection**: Use React DevTools

## Mock Mode vs Production Mode

### Mock Mode (No GCP Credentials)
- File uploads store metadata only (no actual GCS upload)
- Workflow executes with simulated progress updates
- HITL approval uses in-memory storage
- NL-to-SQL returns example queries
- Query execution returns sample data

### Production Mode (With GCP Credentials)
- Files uploaded to Google Cloud Storage
- Workflow executes real ETL agents
- HITL approval uses Firestore
- NL-to-SQL uses Vertex AI Gemini
- Query execution runs against BigQuery

## Performance Considerations

- **File Upload**: Max 50MB per file (configurable)
- **Query Results**: Limited to 1000 rows (configurable)
- **WebSocket Timeout**: 300 seconds (5 minutes)
- **HITL Timeout**: 3600 seconds (1 hour)
- **Concurrent Workflows**: Unlimited (each has unique run_id)

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Rotate service account keys** regularly
3. **Use principle of least privilege** for GCP roles
4. **Enable HTTPS** in production
5. **Implement authentication** for production deployment
6. **Sanitize user inputs** in queries
7. **Rate limit API endpoints** in production

## Deployment to Production

### Backend (Cloud Run)
```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/aimagna-backend

# Deploy to Cloud Run
gcloud run deploy aimagna-backend \
  --image gcr.io/PROJECT_ID/aimagna-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Frontend (Firebase Hosting)
```bash
cd frontend
npm run build
firebase deploy --only hosting
```

### Environment Variables for Production
Update `.env` files with production URLs and credentials.

## Contributing

1. Follow existing code structure
2. Add type hints to all Python functions
3. Use TypeScript for all frontend code
4. Test both mock mode and GCP mode
5. Update documentation for new features
6. Write tests for new functionality

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Check `SETUP.md` for detailed setup instructions
- Review API documentation at http://localhost:8000/docs
- Check backend logs: `tail -f backend.log`
- Check browser console for frontend errors
- Review existing issues on GitHub

## Changelog

### Version 1.0.0 (Initial Release)
- React chatbot UI with Material-UI
- 10 FastAPI endpoints for workflow management
- WebSocket real-time updates
- Web-based HITL approval system
- Natural language query interface using Vertex AI Gemini
- Mock mode for development without GCP credentials
- Automated setup script
- Comprehensive documentation

## Acknowledgments

Built with:
- Google Cloud Platform
- FastAPI
- React & TypeScript
- Material-UI
- Vertex AI Gemini
- WebSocket (Socket.io)
