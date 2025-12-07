import { Circle, Clock, Check } from 'lucide-react';

export const priorityVariantMap = {
  'MVP': 'mvp',
  'Release 1': 'release1',
  'Later': 'later',
};

export const statusLabels = {
  'todo': 'К выполнению',
  'in_progress': 'В работе',
  'done': 'Готово',
  'blocked': 'Заблокировано',
};

export const statusIcons = {
  'todo': <Circle className="w-4 h-4" />,
  'in_progress': <Clock className="w-4 h-4" />,
  'done': <Check className="w-4 h-4" />,
  'blocked': (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" strokeWidth="2" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" strokeWidth="2" />
    </svg>
  ),
};

export const getPriorityVariant = (priority) => priorityVariantMap[priority] || 'secondary';

