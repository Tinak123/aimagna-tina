// Natural Language Query Input Component

import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Card,
  CardContent,
  Chip,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  AutoAwesome as AIIcon,
  Code as CodeIcon,
  TableChart as TableIcon,
} from '@mui/icons-material';
import { askQuestion, type AskQuestionResponse } from '../../services/api';
import { useChatStore } from '../../stores/chatStore';

export const QueryInput: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<AskQuestionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const { addMessage } = useChatStore();

  const handleAskQuestion = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      addMessage({
        type: 'user',
        content: question,
      });

      const response = await askQuestion(question);
      setResult(response);

      if (response.status === 'success') {
        // Add the AI interpretation as a message
        addMessage({
          type: 'agent',
          content: `📊 **Analysis Result:**\n\n${response.interpretation}`,
        });
      } else {
        addMessage({
          type: 'error',
          content: `Failed to answer question: ${response.error}`,
        });
      }
    } catch (error: any) {
      addMessage({
        type: 'error',
        content: `Error: ${error.message}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAskQuestion();
    }
  };

  return (
    <Box>
      {/* Question Input */}
      <Box display="flex" gap={1} mb={2}>
        <TextField
          fullWidth
          placeholder="Ask a question about your data (e.g., 'What are total payments by borrower?')"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyPress={handleKeyPress}
          multiline
          maxRows={3}
          sx={{ bgcolor: 'white' }}
        />
        <Button
          variant="contained"
          color="primary"
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AIIcon />}
          onClick={handleAskQuestion}
          disabled={loading || !question.trim()}
          sx={{ minWidth: 140 }}
        >
          {loading ? 'Thinking...' : 'Ask AI'}
        </Button>
      </Box>

      {/* Results */}
      {result && result.status === 'success' && (
        <Card variant="outlined" sx={{ bgcolor: 'background.paper' }}>
          <CardContent>
            {/* AI Interpretation */}
            <Box display="flex" alignItems="flex-start" gap={1} mb={2}>
              <AIIcon color="primary" sx={{ mt: 0.5 }} />
              <Box>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  AI Answer
                </Typography>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                  {result.interpretation}
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Summary Stats */}
            <Box display="flex" gap={1} mb={2} flexWrap="wrap">
              <Chip 
                icon={<TableIcon />} 
                label={`${result.row_count} rows`} 
                size="small" 
                variant="outlined"
              />
              {result.total_bytes_processed && (
                <Chip 
                  label={`${(result.total_bytes_processed / 1024).toFixed(1)} KB processed`} 
                  size="small" 
                  variant="outlined"
                />
              )}
            </Box>

            {/* Expandable Details */}
            <Accordion 
              expanded={showDetails} 
              onChange={() => setShowDetails(!showDetails)}
              elevation={0}
              sx={{ bgcolor: 'grey.50' }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" gap={1}>
                  <CodeIcon fontSize="small" />
                  <Typography variant="body2">View SQL & Raw Data</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {/* SQL Query */}
                <Typography variant="subtitle2" gutterBottom>
                  Generated SQL:
                </Typography>
                <Paper
                  sx={{
                    p: 1.5,
                    bgcolor: 'grey.900',
                    color: 'grey.100',
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    overflow: 'auto',
                    mb: 2,
                    maxHeight: 150,
                  }}
                >
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{result.sql}</pre>
                </Paper>

                {/* Results Table */}
                {result.row_count > 0 && (
                  <>
                    <Typography variant="subtitle2" gutterBottom>
                      Raw Results:
                    </Typography>
                    <TableContainer component={Paper} sx={{ maxHeight: 300 }}>
                      <Table stickyHeader size="small">
                        <TableHead>
                          <TableRow>
                            {result.columns.map((col: string) => (
                              <TableCell key={col} sx={{ fontWeight: 'bold', bgcolor: 'grey.100' }}>
                                {col}
                              </TableCell>
                            ))}
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {result.rows.slice(0, 50).map((row: any[], idx: number) => (
                            <TableRow key={idx} hover>
                              {row.map((cell, cellIdx) => (
                                <TableCell key={cellIdx}>
                                  {cell === null ? (
                                    <Typography variant="caption" color="text.secondary">
                                      NULL
                                    </Typography>
                                  ) : typeof cell === 'number' ? (
                                    cell.toLocaleString()
                                  ) : (
                                    String(cell)
                                  )}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                    {result.row_count > 50 && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        Showing first 50 of {result.row_count} rows
                      </Typography>
                    )}
                  </>
                )}
              </AccordionDetails>
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {result && result.status === 'error' && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Query Failed</Typography>
          <Typography variant="body2">{result.error}</Typography>
        </Alert>
      )}

      {/* Sample Questions */}
      {!result && !loading && (
        <Box mt={2}>
          <Typography variant="caption" color="text.secondary" gutterBottom display="block">
            Try asking:
          </Typography>
          <Box display="flex" gap={1} flexWrap="wrap">
            {[
              "What are the total payments by borrower?",
              "How many loans are in each status?",
              "What is the average loan amount by industry?",
            ].map((sample) => (
              <Chip
                key={sample}
                label={sample}
                size="small"
                variant="outlined"
                onClick={() => setQuestion(sample)}
                sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
              />
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
};
