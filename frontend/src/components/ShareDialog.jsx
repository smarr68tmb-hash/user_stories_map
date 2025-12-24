import { useState, useEffect } from 'react';
import { X, Copy, Check, Share2, Trash2 } from 'lucide-react';
import { projects } from '../api';
import { useToast } from '../hooks/useToast';
import { useProjectRefreshContext } from '../context/ProjectRefreshContext';

export default function ShareDialog({ projectId, isOpen, onClose, currentShareUrl = null }) {
  const toast = useToast();
  const { refreshProject } = useProjectRefreshContext();
  const [shareUrl, setShareUrl] = useState(currentShareUrl);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setShareUrl(currentShareUrl);
  }, [currentShareUrl]);

  const handleCreateShareLink = async () => {
    setLoading(true);
    try {
      const response = await projects.createShareLink(projectId);
      setShareUrl(response.data.share_url);
      // Обновляем проект чтобы получить share_token
      await refreshProject();
      toast.success('✅ Share link создан!');
    } catch (error) {
      console.error('Failed to create share link:', error);
      toast.error('❌ Не удалось создать share link');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteShareLink = async () => {
    setLoading(true);
    try {
      await projects.deleteShareLink(projectId);
      setShareUrl(null);
      // Обновляем проект чтобы убрать share_token
      await refreshProject();
      toast.success('✅ Share link отключен');
    } catch (error) {
      console.error('Failed to delete share link:', error);
      toast.error('❌ Не удалось отключить share link');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = async () => {
    if (!shareUrl) return;
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success('✅ Ссылка скопирована в буфер обмена');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      toast.error('❌ Не удалось скопировать ссылку');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Share2 className="w-5 h-5" />
            Поделиться проектом
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-4">
          {shareUrl ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Публичная ссылка
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={shareUrl}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm"
                  />
                  <button
                    onClick={handleCopyLink}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-2"
                    disabled={loading}
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4" />
                        Скопировано
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        Копировать
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <p className="text-sm text-blue-800">
                  <strong>ℹ️ Важно:</strong> Любой, у кого есть эта ссылка, сможет просмотреть ваш проект.
                  Вы можете отключить ссылку в любой момент.
                </p>
              </div>

              <button
                onClick={handleDeleteShareLink}
                disabled={loading}
                className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                Отключить share link
              </button>
            </>
          ) : (
            <>
              <div className="text-center py-4">
                <p className="text-gray-600 mb-4">
                  Создайте публичную ссылку для просмотра проекта без авторизации.
                </p>
                <button
                  onClick={handleCreateShareLink}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto"
                >
                  <Share2 className="w-4 h-4" />
                  {loading ? 'Создание...' : 'Создать share link'}
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}

