// Main Chat Window Component

import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  IconButton,
  Chip,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  Upload as UploadIcon,
  Clear as ClearIcon,
  RocketLaunch as PipelineIcon,
} from '@mui/icons-material';
import { useChatStore } from '../../stores/chatStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { uploadFile, startWorkflow } from '../../services/api';
import type { WorkflowUpdate } from '../../types';
import { ApprovalList } from '../HITL/ApprovalList';
import { QueryInput } from '../QueryInterface/QueryInput';
import { PipelineStarter } from '../Workflow/PipelineStarter';
import { ETLProgressCard } from '../Workflow/ETLProgressCard';

export const ChatWindow: React.FC = () => {
  const { 
    messages, 
    currentRun, 
    etlSteps,
    addMessage, 
    setCurrentRun, 
    updateCurrentRun, 
    updateETLStep,
    resetETLSteps,
    clearMessages 
  } = useChatStore();
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [pipelineDialogOpen, setPipelineDialogOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // WebSocket connection for real-time updates
  useWebSocket(currentRun?.run_id || null, (update: WorkflowUpdate) => {
    // Update progress
    if (currentRun) {
      updateCurrentRun({
        status: update.status as any,
        current_step: update.step,
        progress: update.progress,
        error: update.error,
      });

      // Update the specific step
      const stepStatus = 
        update.status === 'completed' ? 'completed' :
        update.status === 'failed' || update.status === 'error' ? 'error' :
        update.status === 'started' || update.status === 'running' || update.status === 'waiting' ? 'running' :
        'pending';
      
      updateETLStep(update.step, stepStatus, update.message);

      // If workflow is complete, mark all pending steps as completed
      if (update.type === 'workflow_complete') {
        etlSteps.forEach(step => {
          if (step.status === 'pending' || step.status === 'running') {
            updateETLStep(step.name, 'completed');
          }
        });
      }
    }
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentRun?.progress]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);

    try {
      addMessage({
        type: 'user',
        content: `Uploading file: ${file.name}`,
      });

      const response = await uploadFile(file);

      setCurrentRun({
        run_id: response.run_id,
        filename: response.filename,
        gcs_uri: response.gcs_uri,
        status: 'pending',
        current_step: 'initialized',
        progress: 0,
      });

      addMessage({
        type: 'agent',
        content: `File uploaded successfully! Run ID: ${response.run_id}`,
      });

      addMessage({
        type: 'agent',
        content: 'Would you like to start processing this file?',
      });
    } catch (error: any) {
      addMessage({
        type: 'error',
        content: `Upload failed: ${error.response?.data?.detail || error.message}`,
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleStartWorkflow = async () => {
    if (!currentRun) return;

    try {
      addMessage({
        type: 'user',
        content: 'Start processing',
      });

      await startWorkflow(currentRun.run_id);

      addMessage({
        type: 'agent',
        content: 'Workflow started! You can monitor progress in real-time.',
      });
    } catch (error: any) {
      addMessage({
        type: 'error',
        content: `Failed to start workflow: ${error.response?.data?.detail || error.message}`,
      });
    }
  };

  const handleGCSWorkflowStarted = (runId: string, folderPath: string, files: string[]) => {
    // Reset ETL steps
    resetETLSteps();

    // Set the current run
    setCurrentRun({
      run_id: runId,
      folder_path: folderPath,
      gcs_uri: `gs://${folderPath}`,
      status: 'pending',
      current_step: 'initialized',
      progress: 0,
      source_type: 'gcs_folder',
    });

    // Add messages to chat
    addMessage({
      type: 'user',
      content: `Start ETL pipeline on folder: ${folderPath}`,
    });

    addMessage({
      type: 'agent',
      content: `🚀 ETL Pipeline initiated!\n\n📁 Source: ${folderPath}\n📄 Files: ${files.length > 0 ? files.join(', ') : 'Processing...'}\n🔑 Run ID: ${runId}`,
    });
  };

  const handleSend = () => {
    if (!input.trim()) return;

    addMessage({
      type: 'user',
      content: input,
    });

    if (input.toLowerCase().includes('start') && currentRun && currentRun.status === 'pending') {
      handleStartWorkflow();
    } else if (input.toLowerCase().includes('clear')) {
      clearMessages();
    } else if (input.toLowerCase().includes('pipeline') || input.toLowerCase().includes('etl')) {
      setPipelineDialogOpen(true);
      addMessage({
        type: 'agent',
        content: 'Opening the Pipeline Starter dialog...',
      });
    } else {
      addMessage({
        type: 'agent',
        content: 'I can help you with:\n\n🚀 **Start Pipeline** - Click the green button or type "pipeline"\n📤 **Upload CSV** - Upload individual files\n💬 **Query Data** - Ask questions after ETL completes\n\nClick "Start Pipeline" to select a GCS folder and begin!',
      });
    }

    setInput('');
  };

  const renderMessage = (message: typeof messages[0]) => {
    const isUser = message.type === 'user';
    const isError = message.type === 'error';

    // Skip system messages - they're now shown in the ETL Progress Card
    if (message.type === 'system') {
      return null;
    }

    if (message.type === 'hitl') {
      return (
        <Box sx={{ mb: 2 }}>
          <ApprovalList runId={message.runId!} />
        </Box>
      );
    }

    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          mb: 1,
        }}
      >
        <Paper
          sx={{
            p: 1.5,
            maxWidth: '70%',
            bgcolor: isError ? 'error.light' : isUser ? 'primary.main' : 'grey.100',
            color: isError || isUser ? 'white' : 'text.primary',
          }}
        >
          <Typography variant="body2" style={{ whiteSpace: 'pre-line' }}>
            {typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2)}
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.7, display: 'block', mt: 0.5 }}>
            {message.timestamp.toLocaleTimeString()}
          </Typography>
        </Paper>
      </Box>
    );
  };

  const isWorkflowActive = currentRun && 
    currentRun.status !== 'pending' && 
    currentRun.source_type === 'gcs_folder';

  const isWorkflowComplete = currentRun && 
    (currentRun.status === 'completed' || currentRun.status === 'success');

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, borderRadius: 0 }} elevation={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5">AIMagna ETL Agent</Typography>
            {currentRun && !isWorkflowActive && (
              <Box display="flex" gap={1} mt={1} flexWrap="wrap">
                <Chip label={currentRun.run_id} size="small" />
                <Chip 
                  label={currentRun.status} 
                  size="small" 
                  color={
                    currentRun.status === 'completed' || currentRun.status === 'success' ? 'success' : 
                    currentRun.status === 'failed' ? 'error' : 'primary'
                  } 
                />
              </Box>
            )}
          </Box>
          <IconButton onClick={clearMessages} title="Clear chat">
            <ClearIcon />
          </IconButton>
        </Box>
      </Paper>

      {/* Messages */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 2, bgcolor: 'grey.50' }}>
        {/* Regular chat messages */}
        {messages.map((message) => (
          <div key={message.id}>{renderMessage(message)}</div>
        ))}

        {/* ETL Progress Card - Single unified view */}
        {isWorkflowActive && (
          <ETLProgressCard
            runId={currentRun.run_id}
            folderPath={currentRun.folder_path}
            overallProgress={currentRun.progress}
            currentStep={currentRun.current_step}
            status={currentRun.status}
            steps={etlSteps}
            error={currentRun.error}
          />
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Query Interface - Shows when workflow is complete */}
      {isWorkflowComplete && (
        <Box sx={{ p: 2, bgcolor: 'success.50', borderTop: 2, borderColor: 'success.main' }}>
          <Typography variant="subtitle2" color="success.dark" gutterBottom>
            ✅ ETL Complete! Query your transformed data:
          </Typography>
          <QueryInput />
        </Box>
      )}

      {/* Input Area */}
      <Paper sx={{ p: 2, borderRadius: 0 }} elevation={3}>
        <Box display="flex" gap={1}>
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
          <Tooltip title="Start ETL pipeline from GCS bucket folder">
            <Button
              variant="contained"
              color="success"
              startIcon={<PipelineIcon />}
              onClick={() => setPipelineDialogOpen(true)}
              disabled={isWorkflowActive && !isWorkflowComplete}
            >
              Start Pipeline
            </Button>
          </Tooltip>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload CSV'}
          </Button>
          <TextField
            fullWidth
            size="small"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          />
          <Button
            variant="contained"
            endIcon={<SendIcon />}
            onClick={handleSend}
            disabled={!input.trim()}
          >
            Send
          </Button>
        </Box>
      </Paper>

      {/* Pipeline Starter Dialog */}
      <PipelineStarter
        open={pipelineDialogOpen}
        onClose={() => setPipelineDialogOpen(false)}
        onWorkflowStarted={handleGCSWorkflowStarted}
      />
    </Box>
  );
};
