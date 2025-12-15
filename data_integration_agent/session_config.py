# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Session Persistence Configuration for Data Integration Agent.

This module provides persistent session storage using ADK's DatabaseSessionService
with Cloud SQL PostgreSQL. Sessions are retained for 30 days.

Environment Variables:
    SESSION_DB_URL: PostgreSQL connection string for Cloud SQL
                    Format: postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
                    
    If not set, falls back to InMemorySessionService (non-persistent, for local dev).
"""

import os
import logging

logger = logging.getLogger(__name__)


def get_session_service():
    """
    Get the appropriate SessionService based on environment configuration.
    
    Returns:
        - DatabaseSessionService if SESSION_DB_URL is configured (persistent, 30-day retention)
        - InMemorySessionService otherwise (ephemeral, for local development)
    """
    db_url = os.environ.get("SESSION_DB_URL")
    
    if db_url:
        try:
            from google.adk.sessions import DatabaseSessionService
            
            logger.info("✅ Using DatabaseSessionService for persistent sessions (30-day retention)")
            print("✅ Session persistence: Cloud SQL PostgreSQL (30-day retention)")
            
            return DatabaseSessionService(db_url=db_url)
            
        except ImportError as e:
            logger.warning(f"⚠️ DatabaseSessionService not available: {e}")
            logger.warning("   Install with: pip install sqlalchemy asyncpg cloud-sql-python-connector[asyncpg]")
            print(f"⚠️ DatabaseSessionService import failed: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DatabaseSessionService: {e}")
            print(f"❌ Session DB connection failed: {e}")
    
    # Fallback to in-memory (non-persistent)
    try:
        from google.adk.sessions import InMemorySessionService
        
        logger.info("⚠️ Using InMemorySessionService (sessions will be lost on restart)")
        print("⚠️ Session persistence: In-memory only (set SESSION_DB_URL for persistence)")
        
        return InMemorySessionService()
        
    except ImportError:
        logger.warning("⚠️ InMemorySessionService not available, using None")
        print("⚠️ No session service available")
        return None


# Session cleanup SQL for PostgreSQL (run as scheduled job)
SESSION_CLEANUP_SQL = """
-- Delete sessions older than 30 days
-- Run this as a Cloud Scheduler + Cloud Functions job daily
DELETE FROM adk_sessions 
WHERE update_time < NOW() - INTERVAL '30 days';

-- Vacuum to reclaim space (optional, run weekly)
-- VACUUM ANALYZE adk_sessions;
"""
