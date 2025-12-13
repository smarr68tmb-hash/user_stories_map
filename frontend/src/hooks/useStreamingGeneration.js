/**
 * useStreamingGeneration Hook
 *
 * Manages SSE (Server-Sent Events) connection for real-time map generation.
 *
 * Features:
 * - Real-time progress updates (0-100%)
 * - Stage tracking (enhancing → generating → validating → saving)
 * - Analysis results (duplicates, score, issues)
 * - Auto-show notifications
 * - Error handling
 *
 * Events:
 * - enhancing: Stage 1 progress
 * - enhanced: Enhanced text result
 * - generating: Stage 2 progress + counts
 * - validating: Stage 3 progress
 * - analysis: Results (duplicates, score, issues) ← AUTO-SHOW!
 * - saving: DB save progress
 * - complete: Final result with project_id
 * - error: Error message
 */

import { useState, useCallback, useRef } from 'react';

export function useStreamingGeneration() {
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('idle'); // idle | enhancing | generating | validating | saving | complete | error
  const [analysisResults, setAnalysisResults] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);

  // Statistics from generation
  const [stats, setStats] = useState(null);

  const eventSourceRef = useRef(null);

  /**
   * Start streaming generation
   *
   * @param {string} requirements - Requirements text
   * @param {boolean} useEnhancement - Whether to use enhancement stage
   * @param {boolean} useAgent - Whether to use AI Agent
   * @returns {Promise<number>} - Project ID
   */
  const generateWithStreaming = useCallback(async (requirements, useEnhancement = false, useAgent = false) => {
    // Reset state
    setProgress(0);
    setStage('idle');
    setAnalysisResults(null);
    setStats(null);
    setError(null);
    setIsStreaming(true);

    return new Promise((resolve, reject) => {
      try {
        // Build query params
        const params = new URLSearchParams({
          text: requirements,
          skip_enhancement: !useEnhancement,
          use_agent: useAgent
        });

        // Create EventSource for SSE
        const eventSource = new EventSource(
          `/api/generate-map/stream?${params.toString()}`,
          { withCredentials: true }
        );

        eventSourceRef.current = eventSource;

        // Handle SSE messages
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[SSE]', data.type, data);

            switch (data.type) {
              case 'enhancing':
                setStage('enhancing');
                setProgress(data.progress || 10);
                break;

              case 'enhanced':
                setProgress(data.progress || 20);
                // Could show enhanced text if needed
                break;

              case 'generating':
                setStage('generating');
                setProgress(data.progress || 50);

                // Update stats if provided
                if (data.activities !== undefined) {
                  setStats({
                    activities: data.activities,
                    tasks: data.tasks,
                    stories: data.stories
                  });
                }
                break;

              case 'validating':
                setStage('validating');
                setProgress(data.progress || 80);
                break;

              case 'analysis':
                setProgress(data.progress || 85);

                // Store analysis results
                const analysisData = {
                  duplicates: data.duplicates || 0,
                  similar: data.similar || 0,
                  score: data.score || 0,
                  issues: data.issues || [],
                  totalIssues: data.total_issues || 0
                };

                setAnalysisResults(analysisData);

                // AUTO-SHOW notification handled by parent component
                break;

              case 'saving':
                setStage('saving');
                setProgress(data.progress || 90);
                break;

              case 'complete':
                setStage('complete');
                setProgress(100);
                setIsStreaming(false);

                // Store final stats
                if (data.stats) {
                  setStats(data.stats);
                }

                // Close connection
                eventSource.close();

                // Resolve with project_id
                resolve({
                  projectId: data.project_id,
                  projectName: data.project_name,
                  stats: data.stats
                });
                break;

              case 'error':
                setStage('error');
                setError(data.message || 'Unknown error');
                setIsStreaming(false);
                eventSource.close();
                reject(new Error(data.message || 'Generation failed'));
                break;

              default:
                console.warn('[SSE] Unknown event type:', data.type);
            }
          } catch (err) {
            console.error('[SSE] Error parsing event:', err);
          }
        };

        // Handle errors
        eventSource.onerror = (err) => {
          console.error('[SSE] Connection error:', err);
          setStage('error');
          setError('Connection lost. Please try again.');
          setIsStreaming(false);
          eventSource.close();
          reject(new Error('SSE connection failed'));
        };

      } catch (err) {
        console.error('[SSE] Setup error:', err);
        setStage('error');
        setError(err.message);
        setIsStreaming(false);
        reject(err);
      }
    });
  }, []);

  /**
   * Cancel ongoing streaming
   */
  const cancelStreaming = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
    setStage('idle');
  }, []);

  return {
    // State
    progress,
    stage,
    analysisResults,
    stats,
    isStreaming,
    error,

    // Methods
    generateWithStreaming,
    cancelStreaming
  };
}
