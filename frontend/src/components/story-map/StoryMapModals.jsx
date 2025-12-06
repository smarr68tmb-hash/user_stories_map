import EditStoryModal from '../../EditStoryModal';
import AIAssistant from '../../AIAssistant';
import AnalysisPanel from '../../AnalysisPanel';

function StoryMapModals({
  editingStory,
  releases,
  onCloseEdit,
  onSaveStory,
  onDeleteStory,
  aiAssistantOpen,
  aiAssistantStory,
  aiAssistantTaskId,
  aiAssistantReleaseId,
  onCloseAI,
  onStoryImproved,
  analysisPanelOpen,
  onCloseAnalysis,
  projectId,
}) {
  return (
    <>
      <EditStoryModal
        story={editingStory}
        releases={releases}
        isOpen={!!editingStory}
        onClose={onCloseEdit}
        onSave={onSaveStory}
        onDelete={onDeleteStory}
      />

      {aiAssistantOpen && aiAssistantStory && (
        <AIAssistant
          story={aiAssistantStory}
          taskId={aiAssistantTaskId}
          releaseId={aiAssistantReleaseId}
          isOpen={aiAssistantOpen}
          onClose={onCloseAI}
          onStoryImproved={onStoryImproved}
        />
      )}

      <AnalysisPanel
        projectId={projectId}
        isOpen={analysisPanelOpen}
        onClose={onCloseAnalysis}
      />
    </>
  );
}

export default StoryMapModals;

