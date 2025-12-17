import { LayoutGrid, List } from 'lucide-react';

function ViewToggle({ viewMode, onViewChange }) {
  return (
    <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
      <button
        onClick={() => onViewChange('storyMap')}
        className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
          viewMode === 'storyMap'
            ? 'bg-white text-blue-600 shadow-sm font-medium'
            : 'text-gray-600 hover:text-gray-800'
        }`}
      >
        <LayoutGrid className="w-4 h-4" />
        <span>Story Map View</span>
      </button>
      <button
        onClick={() => onViewChange('epic')}
        className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
          viewMode === 'epic'
            ? 'bg-white text-blue-600 shadow-sm font-medium'
            : 'text-gray-600 hover:text-gray-800'
        }`}
      >
        <List className="w-4 h-4" />
        <span>Epic View</span>
      </button>
    </div>
  );
}

export default ViewToggle;

