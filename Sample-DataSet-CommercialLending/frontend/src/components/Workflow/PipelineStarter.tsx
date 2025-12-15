// Pipeline Starter Component - Select GCS folder and start ETL pipeline

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  CircularProgress,
  Alert,
  Box,
  Chip,
  Divider,
  IconButton,
  Collapse,
  Paper,
} from '@mui/material';
import {
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  CloudQueue as CloudIcon,
  InsertDriveFile as FileIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  DataObject as SchemaIcon,
  TableChart as TableIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { listGCSFolders, getFolderStructure, startWorkflowFromGCS } from '../../services/api';
import type { GCSFolder, FolderStructure, SubfolderInfo } from '../../types';

interface PipelineStarterProps {
  open: boolean;
  onClose: () => void;
  onWorkflowStarted: (runId: string, folderPath: string, files: string[]) => void;
}

export const PipelineStarter: React.FC<PipelineStarterProps> = ({
  open,
  onClose,
  onWorkflowStarted,
}) => {
  const [folders, setFolders] = useState<GCSFolder[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<GCSFolder | null>(null);
  const [folderStructure, setFolderStructure] = useState<FolderStructure | null>(null);
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStructure, setLoadingStructure] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bucket, setBucket] = useState<string>('');

  // Fetch folders when dialog opens
  useEffect(() => {
    if (open) {
      fetchFolders();
    }
  }, [open]);

  const fetchFolders = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listGCSFolders();
      setFolders(response.folders);
      setBucket(response.bucket);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load folders');
    } finally {
      setLoading(false);
    }
  };

  const fetchFolderStructure = async (folder: GCSFolder) => {
    setLoadingStructure(true);
    try {
      const structure = await getFolderStructure(folder.name);
      setFolderStructure(structure);
    } catch (err: any) {
      console.error('Failed to load folder structure:', err);
      setFolderStructure(null);
    } finally {
      setLoadingStructure(false);
    }
  };

  const handleFolderClick = async (folder: GCSFolder) => {
    setSelectedFolder(folder);
    
    // Toggle expanded state
    if (expandedFolder === folder.name) {
      setExpandedFolder(null);
      setFolderStructure(null);
    } else {
      setExpandedFolder(folder.name);
      await fetchFolderStructure(folder);
    }
  };

  const handleStartPipeline = async () => {
    if (!selectedFolder) return;

    setStarting(true);
    setError(null);
    
    try {
      const response = await startWorkflowFromGCS(selectedFolder.name);
      const files = response.csv_files || response.files || [];
      onWorkflowStarted(response.run_id, selectedFolder.name, files);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start pipeline');
    } finally {
      setStarting(false);
    }
  };

  const handleClose = () => {
    setSelectedFolder(null);
    setExpandedFolder(null);
    setFolderStructure(null);
    setError(null);
    onClose();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const renderSubfolder = (subfolder: SubfolderInfo, type: 'source' | 'target') => {
    const isSource = type === 'source';
    const icon = isSource ? <TableIcon color="primary" /> : <SchemaIcon color="secondary" />;
    const fileCount = isSource ? subfolder.csv_count : subfolder.sql_count;
    const fileType = isSource ? 'CSV' : 'SQL';
    
    return (
      <Paper 
        key={subfolder.path} 
        variant="outlined" 
        sx={{ 
          p: 1.5, 
          mb: 1,
          bgcolor: isSource ? 'primary.50' : 'secondary.50',
          borderColor: isSource ? 'primary.200' : 'secondary.200',
        }}
      >
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          {icon}
          <Typography variant="subtitle2" fontWeight="bold">
            {subfolder.name}
          </Typography>
          <Chip 
            label={`${fileCount} ${fileType}`} 
            size="small" 
            color={isSource ? 'primary' : 'secondary'}
            variant="outlined"
          />
          {isSource && subfolder.has_schema && (
            <Chip 
              label="schema.json ✓" 
              size="small" 
              color="success"
              variant="outlined"
            />
          )}
        </Box>
        
        <Box sx={{ pl: 2, maxHeight: 150, overflow: 'auto' }}>
          {subfolder.files.slice(0, 10).map((file) => (
            <Box
              key={file.path}
              display="flex"
              alignItems="center"
              gap={1}
              py={0.3}
            >
              <FileIcon fontSize="small" sx={{ opacity: 0.6 }} />
              <Typography variant="caption" sx={{ flex: 1 }}>
                {file.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatFileSize(file.size)}
              </Typography>
            </Box>
          ))}
          {subfolder.files.length > 10 && (
            <Typography variant="caption" color="text.secondary" sx={{ pl: 3 }}>
              ... and {subfolder.files.length - 10} more files
            </Typography>
          )}
        </Box>
      </Paper>
    );
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '500px' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            <CloudIcon color="primary" />
            <Typography variant="h6">Start ETL Pipeline</Typography>
          </Box>
          <IconButton onClick={fetchFolders} disabled={loading} size="small" title="Refresh folders">
            <RefreshIcon />
          </IconButton>
        </Box>
        {bucket && (
          <Typography variant="caption" color="text.secondary">
            Bucket: {bucket}
          </Typography>
        )}
      </DialogTitle>
      
      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" py={4}>
            <CircularProgress />
            <Typography sx={{ ml: 2 }}>Loading folders...</Typography>
          </Box>
        ) : folders.length === 0 ? (
          <Alert severity="info">
            No folders found in the bucket. Upload data folders to get started.
          </Alert>
        ) : (
          <Box display="flex" gap={2}>
            {/* Folder List */}
            <Box sx={{ width: '40%', borderRight: 1, borderColor: 'divider', pr: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Select a data folder:
              </Typography>
              
              <List sx={{ bgcolor: 'background.paper' }} dense>
                {folders.map((folder) => (
                  <ListItem key={folder.path} disablePadding>
                    <ListItemButton
                      onClick={() => handleFolderClick(folder)}
                      selected={selectedFolder?.name === folder.name}
                      sx={{
                        borderRadius: 1,
                        mb: 0.5,
                        border: selectedFolder?.name === folder.name ? 2 : 1,
                        borderColor: selectedFolder?.name === folder.name ? 'primary.main' : 'divider',
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        {selectedFolder?.name === folder.name ? (
                          <FolderOpenIcon color="primary" />
                        ) : (
                          <FolderIcon color="action" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={folder.name}
                        primaryTypographyProps={{
                          fontWeight: selectedFolder?.name === folder.name ? 'bold' : 'normal',
                          fontSize: '0.9rem'
                        }}
                      />
                      {selectedFolder?.name === folder.name && (
                        <ExpandLessIcon color="action" fontSize="small" />
                      )}
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Box>

            {/* Folder Structure Details */}
            <Box sx={{ width: '60%', pl: 1 }}>
              {!selectedFolder ? (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%" py={4}>
                  <Typography color="text.secondary">
                    ← Select a folder to view its structure
                  </Typography>
                </Box>
              ) : loadingStructure ? (
                <Box display="flex" justifyContent="center" alignItems="center" py={4}>
                  <CircularProgress size={24} sx={{ mr: 1 }} />
                  <Typography>Loading folder structure...</Typography>
                </Box>
              ) : folderStructure ? (
                <>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {selectedFolder.name}
                    </Typography>
                    {folderStructure.ready_for_etl ? (
                      <Chip 
                        icon={<CheckIcon />} 
                        label="Ready for ETL" 
                        color="success" 
                        size="small"
                      />
                    ) : (
                      <Chip 
                        icon={<WarningIcon />} 
                        label="Missing source files" 
                        color="warning" 
                        size="small"
                      />
                    )}
                  </Box>

                  {folderStructure.source_folder ? (
                    renderSubfolder(folderStructure.source_folder, 'source')
                  ) : (
                    <Alert severity="warning" sx={{ mb: 1 }}>
                      No Source-Schema-DataSets folder found
                    </Alert>
                  )}

                  {folderStructure.target_folder ? (
                    renderSubfolder(folderStructure.target_folder, 'target')
                  ) : (
                    <Alert severity="info" sx={{ mb: 1 }}>
                      No Target-Schema folder found (will use default)
                    </Alert>
                  )}

                  {folderStructure.ready_for_etl && (
                    <Alert severity="success" sx={{ mt: 2 }}>
                      <strong>Ready to start!</strong> Found {folderStructure.source_folder?.csv_count} CSV file(s) 
                      {folderStructure.target_folder && ` and ${folderStructure.target_folder.sql_count} target schema(s)`}.
                    </Alert>
                  )}
                </>
              ) : (
                <Alert severity="info">
                  No subfolders found. Expected structure:
                  <br />
                  <code>folder/Source-Schema-DataSets/</code> (CSV files)
                  <br />
                  <code>folder/Target-Schema/</code> (SQL files)
                </Alert>
              )}
            </Box>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} disabled={starting}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleStartPipeline}
          disabled={!folderStructure?.ready_for_etl || starting || loading}
          startIcon={starting ? <CircularProgress size={20} color="inherit" /> : <PlayIcon />}
        >
          {starting ? 'Starting...' : 'Start Pipeline'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
