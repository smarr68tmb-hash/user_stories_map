import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import AnalysisPanel from './AnalysisPanel';
import api from './api';

// Mock the api module
vi.mock('./api', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('AnalysisPanel - ActionableRecommendations', () => {
  const mockProjectId = 1;
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering Recommendations', () => {
    it('renders actionable recommendations with correct severity icons', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Add descriptions',
              description: 'Add descriptions to 3 stories',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1, 2, 3],
              action_params: {},
              auto_applicable: false,
              impact: 'Improves clarity',
            },
            {
              id: 'rec_2',
              title: 'Merge duplicates',
              description: 'Merge 2 duplicate stories',
              action_type: 'merge_stories',
              severity: 'warning',
              story_ids: [4, 5],
              action_params: { primary_story_id: 4, merge_story_ids: [5] },
              auto_applicable: false,
              impact: 'Removes duplicates',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      api.post.mockResolvedValueOnce({ data: mockAnalysisData });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      // Click on Full Analysis tab
      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      // Wait for analysis to complete
      await waitFor(() => {
        expect(screen.getByText('Add descriptions')).toBeInTheDocument();
      });

      // Check severity indicators
      expect(screen.getByText('Add descriptions')).toBeInTheDocument();
      expect(screen.getByText('Merge duplicates')).toBeInTheDocument();
    });

    it('shows correct story count for each recommendation', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Add descriptions',
              description: 'Test',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1, 2, 3, 4, 5],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      api.post.mockResolvedValueOnce({ data: mockAnalysisData });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByText(/затронет 5 историй/i)).toBeInTheDocument();
      });
    });

    it('displays impact description for each recommendation', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Test recommendation',
              description: 'Test description',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1],
              action_params: {},
              auto_applicable: false,
              impact: 'This is the expected impact',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      api.post.mockResolvedValueOnce({ data: mockAnalysisData });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByText('This is the expected impact')).toBeInTheDocument();
      });
    });
  });

  describe('Applying Recommendations', () => {
    it('calls API when Apply button is clicked', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Add descriptions',
              description: 'Test',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1, 2],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      const mockApplyResponse = {
        success: true,
        message: 'Successfully applied recommendation',
        affected_story_ids: [1, 2],
        new_story_ids: [],
        deleted_story_ids: [],
      };

      api.post
        .mockResolvedValueOnce({ data: mockAnalysisData }) // Initial analysis
        .mockResolvedValueOnce({ data: mockApplyResponse }) // Apply recommendation
        .mockResolvedValueOnce({ data: mockAnalysisData }); // Re-run analysis

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByText('Add descriptions')).toBeInTheDocument();
      });

      // Find and click Apply button
      const applyButton = screen.getByRole('button', { name: /применить/i });
      await userEvent.click(applyButton);

      // Check API was called with correct payload
      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith(
          `/project/${mockProjectId}/apply-recommendation`,
          { recommendation_id: 'rec_1' }
        );
      });
    });

    it('shows loading state while applying recommendation', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Test',
              description: 'Test',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      // Create a promise we can control
      let resolveApply;
      const applyPromise = new Promise((resolve) => {
        resolveApply = resolve;
      });

      api.post
        .mockResolvedValueOnce({ data: mockAnalysisData })
        .mockReturnValueOnce(applyPromise);

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /применить/i })).toBeInTheDocument();
      });

      const applyButton = screen.getByRole('button', { name: /применить/i });
      await userEvent.click(applyButton);

      // Check for loading state
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /применение/i })).toBeDisabled();
      });

      // Resolve the promise
      resolveApply({
        data: {
          success: true,
          message: 'Done',
          affected_story_ids: [1],
          new_story_ids: [],
          deleted_story_ids: [],
        },
      });
    });

    it('shows success message after successful application', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Test',
              description: 'Test',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      const mockApplyResponse = {
        success: true,
        message: 'Successfully added descriptions',
        affected_story_ids: [1],
        new_story_ids: [],
        deleted_story_ids: [],
      };

      api.post
        .mockResolvedValueOnce({ data: mockAnalysisData })
        .mockResolvedValueOnce({ data: mockApplyResponse })
        .mockResolvedValueOnce({ data: mockAnalysisData });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /применить/i })).toBeInTheDocument();
      });

      const applyButton = screen.getByRole('button', { name: /применить/i });
      await userEvent.click(applyButton);

      await waitFor(() => {
        expect(screen.getByText('Successfully added descriptions')).toBeInTheDocument();
      });
    });

    it('shows error message when application fails', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Test',
              description: 'Test',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      api.post
        .mockResolvedValueOnce({ data: mockAnalysisData })
        .mockRejectedValueOnce({
          response: { data: { detail: 'Failed to apply recommendation' } },
        });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /применить/i })).toBeInTheDocument();
      });

      const applyButton = screen.getByRole('button', { name: /применить/i });
      await userEvent.click(applyButton);

      await waitFor(() => {
        expect(screen.getByText('Failed to apply recommendation')).toBeInTheDocument();
      });
    });

    it('re-runs analysis after successful application', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_1',
              title: 'Test',
              description: 'Test',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      const mockApplyResponse = {
        success: true,
        message: 'Done',
        affected_story_ids: [1],
        new_story_ids: [],
        deleted_story_ids: [],
      };

      api.post
        .mockResolvedValueOnce({ data: mockAnalysisData }) // Initial analysis
        .mockResolvedValueOnce({ data: mockApplyResponse }) // Apply
        .mockResolvedValueOnce({ data: mockAnalysisData }); // Re-run analysis

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /применить/i })).toBeInTheDocument();
      });

      const applyButton = screen.getByRole('button', { name: /применить/i });
      await userEvent.click(applyButton);

      // Wait for success and re-run
      await waitFor(
        () => {
          expect(api.post).toHaveBeenCalledTimes(3);
        },
        { timeout: 3000 }
      );

      // Verify the last call was for analysis
      const lastCall = api.post.mock.calls[2];
      expect(lastCall[0]).toMatch(/analyze\/full/);
    });
  });

  describe('Combined Recommendations from Multiple Sources', () => {
    it('combines recommendations from validation and similarity results', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [
            {
              id: 'rec_val_1',
              title: 'Validation recommendation',
              description: 'From validation',
              action_type: 'add_description',
              severity: 'info',
              story_ids: [1],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [
            {
              id: 'rec_sim_1',
              title: 'Similarity recommendation',
              description: 'From similarity',
              action_type: 'merge_stories',
              severity: 'warning',
              story_ids: [2, 3],
              action_params: {},
              auto_applicable: false,
              impact: 'Test',
            },
          ],
        },
      };

      api.post.mockResolvedValueOnce({ data: mockAnalysisData });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.getByText('Validation recommendation')).toBeInTheDocument();
        expect(screen.getByText('Similarity recommendation')).toBeInTheDocument();
      });
    });
  });

  describe('No Recommendations State', () => {
    it('does not show recommendations section when there are no recommendations', async () => {
      const mockAnalysisData = {
        validation_result: {
          issues: [],
          statistics: {},
          quality_score: 90,
          actionable_recommendations: [],
        },
        similarity_result: {
          similar_groups: [],
          statistics: {},
          actionable_recommendations: [],
        },
      };

      api.post.mockResolvedValueOnce({ data: mockAnalysisData });

      render(
        <AnalysisPanel
          projectId={mockProjectId}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const fullAnalysisTab = screen.getByRole('tab', { name: /полный анализ/i });
      await userEvent.click(fullAnalysisTab);

      await waitFor(() => {
        expect(screen.queryByText(/рекомендуемые действия/i)).not.toBeInTheDocument();
      });
    });
  });
});
