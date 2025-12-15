// ETL Progress Card - Shows unified progress for all ETL steps

import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Chip,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as PendingIcon,
  Loop as RunningIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
} from '@mui/icons-material';

interface ETLStep {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  message?: string;
  progress?: number;
}

interface ETLProgressCardProps {
  runId: string;
  folderPath?: string;
  overallProgress: number;
  currentStep: string;
  status: string;
  steps: ETLStep[];
  error?: string;
}

const ETL_STEPS = [
  { name: 'download', label: 'Download from GCS' },
  { name: 'profiler', label: 'Data Profiling' },
  { name: 'staging', label: 'Staging to BigQuery' },
  { name: 'mapper', label: 'Schema Mapping' },
  { name: 'hitl', label: 'Human Approval' },
  { name: 'create_tables', label: 'Create Target Tables' },
  { name: 'transform', label: 'Generate Transforms' },
  { name: 'execute', label: 'Execute Transforms' },
  { name: 'validator', label: 'Data Validation' },
  { name: 'feedback', label: 'Capture Feedback' },
  { name: 'cleanup', label: 'Cleanup' },
];

export const ETLProgressCard: React.FC<ETLProgressCardProps> = ({
  runId,
  folderPath,
  overallProgress,
  currentStep,
  status,
  steps,
  error,
}) => {
  const [expanded, setExpanded] = React.useState(true);

  const getStepStatus = (stepName: string): 'pending' | 'running' | 'completed' | 'error' => {
    const step = steps.find(s => s.name === stepName);
    if (step) return step.status;
    
    // Infer status from current step
    const stepIndex = ETL_STEPS.findIndex(s => s.name === stepName);
    const currentIndex = ETL_STEPS.findIndex(s => s.name === currentStep);
    
    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return status === 'failed' ? 'error' : 'running';
    return 'pending';
  };

  const getStepMessage = (stepName: string): string | undefined => {
    const step = steps.find(s => s.name === stepName);
    return step?.message;
  };

  const getStepIcon = (stepStatus: 'pending' | 'running' | 'completed' | 'error') => {
    switch (stepStatus) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'running':
        return <RunningIcon color="primary" sx={{ animation: 'spin 1s linear infinite' }} />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const isComplete = status === 'completed' || status === 'success';
  const isFailed = status === 'failed' || status === 'error';

  return (
    <Card 
      sx={{ 
        mb: 2, 
        border: 2, 
        borderColor: isComplete ? 'success.main' : isFailed ? 'error.main' : 'primary.main',
        bgcolor: isComplete ? 'success.50' : isFailed ? 'error.50' : 'background.paper',
      }}
    >
      <CardContent>
        {/* Header */}
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6" fontWeight="bold">
              🚀 ETL Pipeline
            </Typography>
            <Chip 
              label={isComplete ? 'Completed' : isFailed ? 'Failed' : 'Running'} 
              size="small"
              color={isComplete ? 'success' : isFailed ? 'error' : 'primary'}
            />
          </Box>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>

        {/* Run Info */}
        <Box display="flex" gap={2} mb={2} flexWrap="wrap">
          <Chip label={`Run: ${runId}`} size="small" variant="outlined" />
          {folderPath && <Chip label={`📁 ${folderPath}`} size="small" variant="outlined" />}
        </Box>

        {/* Overall Progress */}
        <Box mb={2}>
          <Box display="flex" justifyContent="space-between" mb={0.5}>
            <Typography variant="body2" fontWeight="medium">
              Overall Progress
            </Typography>
            <Typography variant="body2" color="primary">
              {overallProgress}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={overallProgress} 
            sx={{ 
              height: 10, 
              borderRadius: 5,
              bgcolor: 'grey.200',
              '& .MuiLinearProgress-bar': {
                bgcolor: isComplete ? 'success.main' : isFailed ? 'error.main' : 'primary.main',
              }
            }}
          />
        </Box>

        {/* Error Display */}
        {error && (
          <Box sx={{ bgcolor: 'error.100', p: 1.5, borderRadius: 1, mb: 2 }}>
            <Typography variant="body2" color="error.dark">
              <strong>Error:</strong> {error}
            </Typography>
          </Box>
        )}

        {/* Steps */}
        <Collapse in={expanded}>
          <Stepper orientation="vertical" activeStep={-1}>
            {ETL_STEPS.map((step) => {
              const stepStatus = getStepStatus(step.name);
              const message = getStepMessage(step.name);
              
              return (
                <Step key={step.name} completed={stepStatus === 'completed'}>
                  <StepLabel
                    StepIconComponent={() => getStepIcon(stepStatus)}
                    optional={
                      message && stepStatus !== 'pending' ? (
                        <Typography variant="caption" color="text.secondary">
                          {message}
                        </Typography>
                      ) : null
                    }
                  >
                    <Typography 
                      variant="body2"
                      color={
                        stepStatus === 'running' ? 'primary.main' : 
                        stepStatus === 'completed' ? 'success.main' :
                        stepStatus === 'error' ? 'error.main' : 'text.secondary'
                      }
                      fontWeight={stepStatus === 'running' ? 'bold' : 'normal'}
                    >
                      {step.label}
                    </Typography>
                  </StepLabel>
                </Step>
              );
            })}
          </Stepper>
        </Collapse>

        {/* Completion Message */}
        {isComplete && (
          <Box sx={{ bgcolor: 'success.100', p: 2, borderRadius: 1, mt: 2, textAlign: 'center' }}>
            <Typography variant="body1" color="success.dark" fontWeight="bold">
              ✅ ETL Pipeline completed successfully!
            </Typography>
            <Typography variant="body2" color="success.dark">
              You can now query your transformed data below.
            </Typography>
          </Box>
        )}
      </CardContent>

      {/* CSS for spinning animation */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Card>
  );
};

