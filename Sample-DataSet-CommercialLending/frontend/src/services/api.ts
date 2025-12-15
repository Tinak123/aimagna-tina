// API Service for communicating with the FastAPI backend

import axios from 'axios';
import type { HITLMapping, QueryResult, NLQueryResponse, GCSFolder, GCSFile, FolderStructure } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// File upload
export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

// Start workflow
export const startWorkflow = async (runId: string) => {
  const response = await api.post('/workflow/start', { run_id: runId });
  return response.data;
};

// List GCS bucket folders
export const listGCSFolders = async (): Promise<{ bucket: string; folders: GCSFolder[]; count: number }> => {
  const response = await api.get('/gcs/folders');
  return response.data;
};

// List files in a GCS folder
export const listFolderFiles = async (folderPath: string): Promise<{ bucket: string; folder: string; files: GCSFile[]; count: number }> => {
  const response = await api.get(`/gcs/folders/${encodeURIComponent(folderPath)}/files`);
  return response.data;
};

// Get folder structure including subfolders
export const getFolderStructure = async (folderPath: string): Promise<FolderStructure> => {
  const response = await api.get(`/gcs/folders/${encodeURIComponent(folderPath)}/structure`);
  return response.data;
};

// Start workflow from GCS folder
export const startWorkflowFromGCS = async (folderPath: string) => {
  const response = await api.post('/workflow/start-from-gcs', { folder_path: folderPath });
  return response.data;
};

// Get workflow status
export const getWorkflowStatus = async (runId: string) => {
  const response = await api.get(`/workflow/status/${runId}`);
  return response.data;
};

// Get HITL mappings
export const getHITLMappings = async (runId: string): Promise<HITLMapping[]> => {
  const response = await api.get(`/hitl/mappings/${runId}`);
  return response.data.mappings;
};

// Submit HITL approvals
export const submitHITLApprovals = async (
  runId: string,
  approvals: Array<{ mapping_id: string; status: string }>
) => {
  const response = await api.post(`/hitl/approve/${runId}`, {
    approvals,
  });
  return response.data;
};

// Natural language to SQL
export const convertNLToSQL = async (query: string): Promise<NLQueryResponse> => {
  const response = await api.post('/query/nl2sql', { query });
  return response.data;
};

// Execute SQL query
export const executeQuery = async (sql: string): Promise<QueryResult> => {
  const response = await api.post('/query/execute', { sql });
  return response.data;
};

// Ask a question (NL to SQL + Execute + Interpret)
export interface AskQuestionResponse {
  status: string;
  question: string;
  sql: string;
  interpretation: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  total_bytes_processed?: number;
  error?: string;
}

export const askQuestion = async (question: string): Promise<AskQuestionResponse> => {
  const response = await api.post('/query/ask', { question });
  return response.data;
};

// Get target schema
export const getTargetSchema = async () => {
  const response = await api.get('/schema/target');
  return response.data;
};

// List all runs
export const listRuns = async (limit: number = 10, offset: number = 0) => {
  const response = await api.get('/runs', { params: { limit, offset } });
  return response.data;
};

export default api;
