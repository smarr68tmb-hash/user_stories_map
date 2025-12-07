import Skeleton from '../common/Skeleton';

const DEFAULT_ACTIVITIES = 3;
const DEFAULT_RELEASES = 3;

function StoryMapSkeleton({ activityWidths = {}, releases = [], taskColumnWidth = 220 }) {
  const activityEntries = Object.entries(activityWidths);
  const activitiesToRender =
    activityEntries.length > 0
      ? activityEntries
      : Array.from({ length: DEFAULT_ACTIVITIES }).map((_, idx) => [idx, taskColumnWidth * 2]);

  const releaseCount = releases?.length || DEFAULT_RELEASES;

  return (
    <div className="space-y-4">
      <div className="mb-4 flex justify-end">
        <Skeleton className="h-9 w-44" />
      </div>

      <div className="w-full overflow-x-auto">
        <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="sticky top-0 z-10 bg-gray-50 border-b-2 border-gray-300">
            <div className="flex border-b border-gray-200">
              <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-3" />
              {activitiesToRender.map(([key, width]) => (
                <div
                  key={`activity-skeleton-${key}`}
                  className="bg-blue-50 border-r border-gray-200 p-3 flex items-center justify-center"
                  style={{ width, minWidth: taskColumnWidth }}
                >
                  <Skeleton className="h-4 w-32" />
                </div>
              ))}
              <div className="flex-shrink-0 border-r border-gray-200">
                <Skeleton className="m-3 h-10 w-28" />
              </div>
            </div>
          </div>

          <div>
            {Array.from({ length: releaseCount }).map((_, releaseIdx) => (
              <div
                key={`release-skeleton-${releaseIdx}`}
                className="flex border-b border-gray-200 min-h-[180px] hover:bg-gray-50 transition"
              >
                <div className="w-32 flex-shrink-0 bg-gray-100 p-3 flex flex-col items-center justify-center text-gray-700 border-r-2 border-gray-300 gap-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-2 w-16" />
                </div>

                {activitiesToRender.map(([key, width]) => (
                  <div
                    key={`activity-body-skeleton-${releaseIdx}-${key}`}
                    className="flex"
                    style={{ width, flexShrink: 0 }}
                  >
                    <div className="w-[280px] flex-shrink-0 p-2 border-r border-dashed border-gray-200">
                      <div className="space-y-2">
                        <Skeleton className="h-20 w-full" />
                        <Skeleton className="h-14 w-full" />
                      </div>
                    </div>
                    <div className="w-[280px] flex-shrink-0 p-2 border-r border-dashed border-gray-200">
                      <div className="space-y-2">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-14 w-full" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default StoryMapSkeleton;

