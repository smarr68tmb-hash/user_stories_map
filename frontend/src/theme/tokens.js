// Centralized visual tokens for statuses, priorities and severities.
// Use these instead of hard-coded Tailwind color classes to keep the UI consistent.

export const STATUS_TOKENS = {
  todo: {
    label: 'Todo',
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    badgeStrong: 'bg-amber-200 text-amber-900 border-amber-300',
    surface: 'bg-amber-50 border-amber-200 hover:border-amber-300',
    surfaceMuted: 'bg-amber-50 border-amber-200',
    indicator: 'bg-amber-400',
    ring: 'ring-amber-200 focus:ring-amber-300 focus:ring-offset-1',
    control: {
      active: 'bg-amber-500 border-amber-500 text-white',
      idle: 'bg-white border-amber-300 text-amber-600 hover:border-amber-400',
    },
  },
  in_progress: {
    label: 'In Progress',
    badge: 'bg-blue-100 text-blue-800 border-blue-300',
    badgeStrong: 'bg-blue-200 text-blue-900 border-blue-300',
    surface: 'bg-blue-50 border-blue-200 hover:border-blue-300',
    surfaceMuted: 'bg-blue-50 border-blue-200',
    indicator: 'bg-blue-500',
    ring: 'ring-blue-200 focus:ring-blue-300 focus:ring-offset-1',
    control: {
      active: 'bg-blue-500 border-blue-500 text-white',
      idle: 'bg-white border-blue-300 text-blue-600 hover:border-blue-400',
    },
  },
  done: {
    label: 'Done',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    badgeStrong: 'bg-emerald-200 text-emerald-900 border-emerald-300',
    surface: 'bg-emerald-50 border-emerald-200 hover:border-emerald-300',
    surfaceMuted: 'bg-emerald-50 border-emerald-200',
    indicator: 'bg-emerald-500',
    ring: 'ring-emerald-200 focus:ring-emerald-300 focus:ring-offset-1',
    control: {
      active: 'bg-emerald-500 border-emerald-500 text-white',
      idle: 'bg-white border-emerald-300 text-emerald-600 hover:border-emerald-400',
    },
  },
  blocked: {
    label: 'Blocked',
    badge: 'bg-rose-100 text-rose-800 border-rose-300',
    badgeStrong: 'bg-rose-200 text-rose-900 border-rose-300',
    surface: 'bg-rose-50 border-rose-200 hover:border-rose-300',
    surfaceMuted: 'bg-rose-50 border-rose-200',
    indicator: 'bg-rose-500',
    ring: 'ring-rose-200 focus:ring-rose-300 focus:ring-offset-1',
    control: {
      active: 'bg-rose-500 border-rose-500 text-white',
      idle: 'bg-white border-rose-300 text-rose-600 hover:border-rose-400',
    },
  },
};

export const STATUS_FLOW = ['todo', 'in_progress', 'done'];

export const STATUS_OPTIONS = [
  { value: 'todo', label: STATUS_TOKENS.todo.label },
  { value: 'in_progress', label: STATUS_TOKENS.in_progress.label },
  { value: 'done', label: STATUS_TOKENS.done.label },
  { value: 'blocked', label: STATUS_TOKENS.blocked.label },
];

export const getStatusToken = (status) => STATUS_TOKENS[status] || STATUS_TOKENS.todo;

export const PRIORITY_TOKENS = {
  low: {
    label: 'Low',
    badge: 'bg-gray-100 text-gray-700 border-gray-300',
    badgeStrong: 'bg-gray-200 text-gray-800 border-gray-300',
    surface: 'bg-gray-50 border-gray-200 hover:border-gray-300',
    strong: 'bg-gray-700 text-white border-gray-700',
  },
  medium: {
    label: 'Medium',
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    badgeStrong: 'bg-amber-200 text-amber-900 border-amber-300',
    surface: 'bg-amber-50 border-amber-200 hover:border-amber-300',
    strong: 'bg-amber-500 text-white border-amber-500',
  },
  high: {
    label: 'High',
    badge: 'bg-rose-100 text-rose-800 border-rose-300',
    badgeStrong: 'bg-rose-200 text-rose-900 border-rose-300',
    surface: 'bg-rose-50 border-rose-200 hover:border-rose-300',
    strong: 'bg-rose-500 text-white border-rose-500',
  },
};

const PRIORITY_ALIASES = {
  low: 'low',
  later: 'low',
  medium: 'medium',
  med: 'medium',
  high: 'high',
  mvp: 'high',
  'release 1': 'medium',
  release1: 'medium',
};

export const getPriorityToken = (priority) => {
  const key = priority?.toString().toLowerCase();
  const resolvedKey = key ? PRIORITY_ALIASES[key] || key : null;
  return PRIORITY_TOKENS[resolvedKey] || PRIORITY_TOKENS.low;
};

export const SEVERITY_TOKENS = {
  low: {
    label: 'Low',
    badge: 'bg-sky-100 text-sky-800 border-sky-300',
    badgeStrong: 'bg-sky-200 text-sky-900 border-sky-300',
    surface: 'bg-sky-50 border-sky-200 hover:border-sky-300',
    strong: 'bg-sky-500 text-white border-sky-500',
    textButton: 'text-sky-600 hover:text-sky-800 hover:bg-sky-100',
  },
  medium: {
    label: 'Medium',
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    badgeStrong: 'bg-amber-200 text-amber-900 border-amber-300',
    surface: 'bg-amber-50 border-amber-200 hover:border-amber-300',
    strong: 'bg-amber-500 text-white border-amber-500',
    textButton: 'text-amber-600 hover:text-amber-800 hover:bg-amber-100',
  },
  high: {
    label: 'High',
    badge: 'bg-orange-100 text-orange-800 border-orange-300',
    badgeStrong: 'bg-orange-200 text-orange-900 border-orange-300',
    surface: 'bg-orange-50 border-orange-200 hover:border-orange-300',
    strong: 'bg-orange-500 text-white border-orange-500',
    textButton: 'text-orange-600 hover:text-orange-800 hover:bg-orange-100',
  },
  critical: {
    label: 'Critical',
    badge: 'bg-rose-100 text-rose-800 border-rose-300',
    badgeStrong: 'bg-rose-200 text-rose-900 border-rose-300',
    surface: 'bg-rose-50 border-rose-200 hover:border-rose-300',
    strong: 'bg-rose-500 text-white border-rose-500',
    textButton: 'text-rose-600 hover:text-rose-800 hover:bg-rose-100',
  },
};

export const getSeverityToken = (severity) => {
  const key = severity?.toString().toLowerCase();
  return SEVERITY_TOKENS[key] || SEVERITY_TOKENS.medium;
};

// Text color tokens for content
export const TEXT_TOKENS = {
  primary: 'text-gray-800',
  secondary: 'text-gray-700',
  muted: 'text-gray-500',
  subtle: 'text-gray-400',
  inverse: 'text-white',
  done: 'text-gray-500 line-through',
};

// Action button tokens for common UI actions
export const ACTION_TOKENS = {
  ai: {
    button: 'bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600',
    buttonSmall: 'bg-gradient-to-r from-purple-500 to-blue-500 text-white px-3 py-1.5 min-h-[32px] rounded hover:from-purple-600 hover:to-blue-600',
  },
  edit: {
    textButton: 'text-blue-600 hover:text-blue-800 hover:bg-blue-100',
    iconButton: 'text-blue-600 hover:text-blue-800 hover:bg-blue-200',
  },
  delete: {
    textButton: 'text-rose-600 hover:text-rose-800 hover:bg-rose-100',
    iconButton: 'text-rose-600 hover:text-rose-800 hover:bg-rose-200',
  },
  add: {
    textButton: 'text-emerald-600 hover:text-emerald-800 hover:bg-emerald-100',
    iconButton: 'text-emerald-600 hover:text-emerald-800 hover:bg-emerald-200',
    button: 'bg-emerald-600 text-white hover:bg-emerald-700',
  },
  cancel: {
    textButton: 'text-gray-600 hover:text-gray-800 hover:bg-gray-100',
    button: 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300',
  },
};

// Surface tokens for containers
export const SURFACE_TOKENS = {
  card: 'bg-white border border-gray-200',
  cardHover: 'bg-white border border-gray-200 hover:border-gray-300 hover:shadow-sm',
  muted: 'bg-gray-50 border border-gray-200',
  subtle: 'bg-gray-100 border border-gray-200',
  input: 'bg-white border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500',
};

// Small badge for counts, metadata
export const META_BADGE = 'text-[10px] text-gray-700 bg-white/80 px-1.5 py-0.5 rounded border border-gray-200';

