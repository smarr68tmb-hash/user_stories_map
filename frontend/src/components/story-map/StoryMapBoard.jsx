import ActivityHeader from './ActivityHeader';
import ReleaseRow from './ReleaseRow';

function StoryMapBoard({
  filteredProject,
  activityWidths,
  taskColumnWidth,
  activityHeaderProps,
  releaseRowProps,
}) {
  const { releaseProgress, ...storyRowProps } = releaseRowProps;

  return (
    <div className="w-full overflow-x-auto">
      <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
        <ActivityHeader
          {...activityHeaderProps}
          activities={filteredProject.activities}
          activityWidths={activityWidths}
          taskColumnWidth={taskColumnWidth}
        />

        <div>
          {filteredProject.releases.map((release) => (
            <ReleaseRow
              key={release.id}
              release={release}
              activities={filteredProject.activities}
              progress={releaseProgress[release.id] || { total: 0, done: 0, percent: 0 }}
              activityWidths={activityWidths}
              taskColumnWidth={taskColumnWidth}
              {...storyRowProps}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default StoryMapBoard;

