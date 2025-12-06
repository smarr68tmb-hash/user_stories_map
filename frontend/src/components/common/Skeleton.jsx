function Skeleton({ className = '', variant = 'text', width, height, style }) {
  const baseClass = 'animate-pulse bg-gray-200 rounded';

  const variantStyles = {
    text: 'h-4 w-full',
    title: 'h-5 w-3/4',
    card: 'rounded-card p-4',
    avatar: 'rounded-full w-10 h-10',
    button: 'h-9 w-24 rounded-button',
    circle: 'rounded-full',
  };

  const combinedStyle = {
    ...style,
    ...(width && { width }),
    ...(height && { height }),
  };

  return (
    <div
      className={`${baseClass} ${variantStyles[variant] || ''} ${className}`.trim()}
      style={combinedStyle}
      aria-hidden="true"
    />
  );
}

// Skeleton for story cards
export function StoryCardSkeleton() {
  return (
    <div className="p-3 rounded-lg shadow-sm border bg-white">
      <div className="flex items-start gap-2">
        <Skeleton variant="circle" width="28px" height="28px" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="title" />
          <Skeleton variant="text" className="w-2/3" />
        </div>
      </div>
      <div className="flex gap-2 mt-3 ml-9">
        <Skeleton variant="button" className="w-12 h-5" />
        <Skeleton variant="button" className="w-8 h-5" />
      </div>
    </div>
  );
}

// Skeleton for activity headers
export function ActivityHeaderSkeleton({ columns = 3 }) {
  return (
    <div className="flex border-b border-gray-200">
      <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-2">
        <Skeleton variant="text" className="w-16 mx-auto" />
      </div>
      {Array.from({ length: columns }).map((_, i) => (
        <div key={i} className="w-[220px] bg-blue-50 border-r border-gray-200 p-3">
          <Skeleton variant="title" className="mx-auto" />
        </div>
      ))}
    </div>
  );
}

// Skeleton for story map grid
export function StoryMapSkeleton({ rows = 3, columns = 3 }) {
  return (
    <div className="animate-pulse">
      {/* Header skeleton */}
      <ActivityHeaderSkeleton columns={columns} />

      {/* Grid skeleton */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="flex border-b border-gray-200">
          <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-3">
            <Skeleton variant="text" className="w-16" />
          </div>
          {Array.from({ length: columns }).map((_, colIdx) => (
            <div
              key={colIdx}
              className="w-[220px] border-r border-gray-200 p-2 space-y-2"
            >
              <StoryCardSkeleton />
              {colIdx % 2 === 0 && <StoryCardSkeleton />}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default Skeleton;

