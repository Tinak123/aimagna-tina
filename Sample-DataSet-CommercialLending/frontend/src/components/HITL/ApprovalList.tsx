// HITL Approval List Component

import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Chip,
  Alert,
  Grid,
} from '@mui/material';
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
} from '@mui/icons-material';
import { getHITLMappings, submitHITLApprovals } from '../../services/api';
import type { HITLMapping } from '../../types';
import { useChatStore } from '../../stores/chatStore';

interface ApprovalListProps {
  runId: string;
}

export const ApprovalList: React.FC<ApprovalListProps> = ({ runId }) => {
  const [mappings, setMappings] = useState<HITLMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [decisions, setDecisions] = useState<Record<string, 'approved' | 'rejected'>>({});
  const { addMessage } = useChatStore();

  useEffect(() => {
    loadMappings();
  }, [runId]);

  const loadMappings = async () => {
    try {
      const data = await getHITLMappings(runId);
      setMappings(data);
      setLoading(false);
    } catch (error: any) {
      console.error('Error loading HITL mappings:', error);
      addMessage({
        type: 'error',
        content: `Failed to load mappings: ${error.message}`,
      });
      setLoading(false);
    }
  };

  const handleApprove = (mappingId: string) => {
    setDecisions((prev) => ({ ...prev, [mappingId]: 'approved' }));
  };

  const handleReject = (mappingId: string) => {
    setDecisions((prev) => ({ ...prev, [mappingId]: 'rejected' }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);

    try {
      const approvals = Object.entries(decisions).map(([mapping_id, status]) => ({
        mapping_id,
        status,
      }));

      await submitHITLApprovals(runId, approvals);

      addMessage({
        type: 'agent',
        content: `Submitted ${approvals.length} approvals. Workflow will continue automatically.`,
      });
    } catch (error: any) {
      addMessage({
        type: 'error',
        content: `Failed to submit approvals: ${error.message}`,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveAll = () => {
    const allDecisions: Record<string, 'approved'> = {};
    mappings.forEach((mapping) => {
      allDecisions[mapping.mapping_id] = 'approved';
    });
    setDecisions(allDecisions);
  };

  const handleRejectAll = () => {
    const allDecisions: Record<string, 'rejected'> = {};
    mappings.forEach((mapping) => {
      allDecisions[mapping.mapping_id] = 'rejected';
    });
    setDecisions(allDecisions);
  };

  const handleApproveHighConfidence = () => {
    const highConfDecisions: Record<string, 'approved' | 'rejected'> = {};
    mappings.forEach((mapping) => {
      if (mapping.confidence >= 0.9) {
        highConfDecisions[mapping.mapping_id] = 'approved';
      }
    });
    setDecisions(highConfDecisions);
  };

  if (loading) {
    return <LinearProgress />;
  }

  const reviewedCount = Object.keys(decisions).length;
  const allReviewed = reviewedCount === mappings.length;

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Review Mapping Candidates
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Please review and approve/reject the AI-generated column mappings below.
          </Typography>

          <Box display="flex" gap={1} mt={2} mb={2}>
            <Button size="small" variant="outlined" onClick={handleApproveAll}>
              Approve All
            </Button>
            <Button size="small" variant="outlined" onClick={handleRejectAll}>
              Reject All
            </Button>
            <Button size="small" variant="outlined" onClick={handleApproveHighConfidence}>
              Approve High Confidence (&gt;90%)
            </Button>
          </Box>

          <Alert severity="info" sx={{ mb: 2 }}>
            Reviewed: {reviewedCount} / {mappings.length}
            {allReviewed && ' - Ready to submit!'}
          </Alert>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        {mappings.map((mapping) => {
          const decision = decisions[mapping.mapping_id];
          const confidence = Math.round(mapping.confidence * 100);

          return (
            <Grid item xs={12} md={6} key={mapping.mapping_id}>
              <Card
                sx={{
                  border: decision
                    ? decision === 'approved'
                      ? '2px solid green'
                      : '2px solid red'
                    : '1px solid',
                  borderColor: decision ? undefined : 'divider',
                }}
              >
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Chip
                      label={`${confidence}% confidence`}
                      size="small"
                      color={confidence >= 90 ? 'success' : confidence >= 80 ? 'warning' : 'default'}
                    />
                    {decision && (
                      <Chip
                        label={decision}
                        size="small"
                        color={decision === 'approved' ? 'success' : 'error'}
                      />
                    )}
                  </Box>

                  <Typography variant="body2" color="text.secondary">
                    Source:
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    <strong>{mapping.source_table}</strong>.{mapping.source_column}
                  </Typography>

                  <Typography variant="body2" color="text.secondary">
                    Target:
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    <strong>{mapping.target_table}</strong>.{mapping.target_column}
                  </Typography>

                  <Typography variant="caption" display="block" color="text.secondary" mb={2}>
                    {mapping.rationale}
                  </Typography>

                  <Box display="flex" gap={1}>
                    <Button
                      size="small"
                      variant={decision === 'approved' ? 'contained' : 'outlined'}
                      color="success"
                      startIcon={<ApproveIcon />}
                      onClick={() => handleApprove(mapping.mapping_id)}
                      fullWidth
                    >
                      Approve
                    </Button>
                    <Button
                      size="small"
                      variant={decision === 'rejected' ? 'contained' : 'outlined'}
                      color="error"
                      startIcon={<RejectIcon />}
                      onClick={() => handleReject(mapping.mapping_id)}
                      fullWidth
                    >
                      Reject
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      <Box mt={3}>
        <Button
          variant="contained"
          size="large"
          fullWidth
          onClick={handleSubmit}
          disabled={!allReviewed || submitting}
        >
          {submitting ? 'Submitting...' : `Submit ${reviewedCount} Decisions`}
        </Button>
      </Box>
    </Box>
  );
};
