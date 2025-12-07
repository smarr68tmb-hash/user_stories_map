import { useCallback, useState } from 'react';

export function useScopedLoading(initialKeys = []) {
  const [loading, setLoading] = useState(() =>
    initialKeys.reduce((acc, key) => ({ ...acc, [key]: {} }), {})
  );

  const setScopedLoading = useCallback((key, id, value) => {
    setLoading((prev) => {
      const currentKeyState = prev[key] || {};
      return {
        ...prev,
        [key]: { ...currentKeyState, [id]: value },
      };
    });
  }, []);

  return { loading, setScopedLoading };
}

export function useDraftMap(defaultDraft) {
  const [drafts, setDrafts] = useState({});

  const ensureDraft = useCallback(
    (id) => {
      setDrafts((prev) => (prev[id] ? prev : { ...prev, [id]: { ...defaultDraft } }));
    },
    [defaultDraft],
  );

  const updateDraft = useCallback(
    (id, patch) => {
      setDrafts((prev) => ({
        ...prev,
        [id]: { ...(prev[id] || defaultDraft), ...patch },
      }));
    },
    [defaultDraft],
  );

  const resetDraft = useCallback(
    (id) => {
      setDrafts((prev) => ({
        ...prev,
        [id]: { ...defaultDraft },
      }));
    },
    [defaultDraft],
  );

  return { drafts, ensureDraft, updateDraft, resetDraft };
}
