// Type definitions for the AIMagna ETL Chatbot

export interface ETLStep {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  message?: string;
  progress?: number;
}

export interface WorkflowRun {
  run_id: string;
  filename?: string;
  folder_path?: string;
  gcs_uri: string;
  status: 'pending' | 'profiling' | 'mapping' | 'hitl' | 'transforming' | 'validating' | 'completed' | 'failed' | 'success';
  current_step: string;
  progress: number;
  error?: string;
  source_type?: 'upload' | 'gcs_folder';
  steps?: ETLStep[];
}

export interface GCSFolder {
  name: string;
  path: string;
  gcs_uri: string;
}

export interface GCSFile {
  name: string;
  path: string;
  gcs_uri: string;
  size: number;
  updated: string | null;
}

export interface SubfolderInfo {
  name: string;
  path: string;
  gcs_uri: string;
  files: GCSFile[];
  csv_count?: number;
  sql_count?: number;
  has_schema?: boolean;
  total_files: number;
}

export interface FolderStructure {
  bucket: string;
  folder: string;
  gcs_uri: string;
  subfolders: SubfolderInfo[];
  source_folder: SubfolderInfo | null;
  target_folder: SubfolderInfo | null;
  ready_for_etl: boolean;
}

export interface WorkflowUpdate {
  type: string;
  step: string;
  status: string;
  progress: number;
  message: string;
  data?: any;
  timestamp?: string;
  error?: string;
}

export interface HITLMapping {
  mapping_id: string;
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  confidence: number;
  rationale: string;
  status: 'pending' | 'approved' | 'rejected';
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'agent' | 'system' | 'hitl' | 'query_result' | 'error';
  content: any;
  timestamp: Date;
  runId?: string;
}

export interface QueryResult {
  status: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  total_bytes_processed?: number;
  error?: string;
}

export interface NLQueryResponse {
  sql: string;
  explanation: string;
  status: string;
  error?: string;
}
