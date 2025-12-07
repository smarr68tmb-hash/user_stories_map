// Pure helper functions to manipulate project tree immutably

export function addActivity(project, activity) {
  return {
    ...project,
    activities: [...project.activities, activity],
  };
}

export function updateActivity(project, activityId, updates) {
  return {
    ...project,
    activities: project.activities.map((activity) =>
      activity.id === activityId ? { ...activity, ...updates } : activity
    ),
  };
}

export function removeActivity(project, activityId) {
  return {
    ...project,
    activities: project.activities.filter((activity) => activity.id !== activityId),
  };
}

export function addTask(project, activityId, task) {
  return {
    ...project,
    activities: project.activities.map((activity) =>
      activity.id === activityId
        ? { ...activity, tasks: [...activity.tasks, task] }
        : activity
    ),
  };
}

export function updateTask(project, taskId, updates) {
  return {
    ...project,
    activities: project.activities.map((activity) => ({
      ...activity,
      tasks: activity.tasks.map((task) =>
        task.id === taskId ? { ...task, ...updates } : task
      ),
    })),
  };
}

export function removeTask(project, taskId) {
  return {
    ...project,
    activities: project.activities.map((activity) => ({
      ...activity,
      tasks: activity.tasks.filter((task) => task.id !== taskId),
    })),
  };
}

export function moveTask(project, activityId, taskId, newPosition) {
  return {
    ...project,
    activities: project.activities.map((activity) => {
      if (activity.id !== activityId) return activity;
      const tasks = [...activity.tasks];
      const fromIndex = tasks.findIndex((t) => t.id === taskId);
      if (fromIndex === -1) return activity;
      const [task] = tasks.splice(fromIndex, 1);
      const targetIndex = Math.max(0, Math.min(newPosition, tasks.length));
      tasks.splice(targetIndex, 0, task);
      return { ...activity, tasks };
    }),
  };
}

export function addStory(project, taskId, releaseId, story) {
  return {
    ...project,
    activities: project.activities.map((activity) => ({
      ...activity,
      tasks: activity.tasks.map((task) => {
        if (task.id !== taskId) return task;
        return {
          ...task,
          stories: [...task.stories, { ...story, release_id: releaseId }],
        };
      }),
    })),
  };
}

export function updateStory(project, storyId, updates) {
  return {
    ...project,
    activities: project.activities.map((activity) => ({
      ...activity,
      tasks: activity.tasks.map((task) => ({
        ...task,
        stories: task.stories.map((story) =>
          story.id === storyId ? { ...story, ...updates } : story
        ),
      })),
    })),
  };
}

export function removeStory(project, storyId) {
  return {
    ...project,
    activities: project.activities.map((activity) => ({
      ...activity,
      tasks: activity.tasks.map((task) => ({
        ...task,
        stories: task.stories.filter((story) => story.id !== storyId),
      })),
    })),
  };
}

export function updateStoryStatus(project, storyId, status) {
  return updateStory(project, storyId, { status });
}

function findStoryLocation(project, storyId) {
  for (let activityIndex = 0; activityIndex < project.activities.length; activityIndex++) {
    const activity = project.activities[activityIndex];
    for (let taskIndex = 0; taskIndex < activity.tasks.length; taskIndex++) {
      const task = activity.tasks[taskIndex];
      const storyIndex = task.stories.findIndex((s) => s.id === storyId);
      if (storyIndex !== -1) {
        const story = task.stories[storyIndex];
        return { activity, task, story, activityIndex, taskIndex, storyIndex };
      }
    }
  }
  return null;
}

export function moveStory(project, storyId, targetTaskId, targetReleaseId, targetPosition = 0) {
  const location = findStoryLocation(project, storyId);
  if (!location) return project;

  const { story: foundStory, task: sourceTask } = location;
  const sourceReleaseId = foundStory.release_id;

  return {
    ...project,
    activities: project.activities.map((act) => ({
      ...act,
      tasks: act.tasks.map((task) => {
        const isSourceTask = task.id === sourceTask.id;
        const isTargetTask = task.id === targetTaskId;

        if (!isSourceTask && !isTargetTask) {
          return task;
        }

        // Start from a mutable copy
        let stories = [...task.stories];

        if (isSourceTask) {
          stories = stories.filter((s) => s.id !== storyId);
        }

        // Prepare helper to renumber positions inside a single release
        const renumberRelease = (list, releaseId) =>
          list.map((s, idx) => (s.release_id === releaseId ? { ...s, position: idx } : s));

        // Insert into target release bucket (could be the same task)
        if (isTargetTask) {
          const targetStories = stories.filter((s) => s.release_id === targetReleaseId);
          const otherStories = stories.filter((s) => s.release_id !== targetReleaseId);

          const insertIndex = Math.max(0, Math.min(targetPosition, targetStories.length));
          const storyToInsert = { ...foundStory, task_id: targetTaskId, release_id: targetReleaseId };

          const nextTargetStories = [...targetStories];
          nextTargetStories.splice(insertIndex, 0, storyToInsert);

          const renumberedTarget = renumberRelease(nextTargetStories, targetReleaseId);
          return { ...task, stories: [...otherStories, ...renumberedTarget] };
        }

        // If we moved away from this task, renumber the source release positions
        const sourceStories = stories.filter((s) => s.release_id === sourceReleaseId);
        const otherStories = stories.filter((s) => s.release_id !== sourceReleaseId);
        const renumberedSource = renumberRelease(sourceStories, sourceReleaseId);

        return { ...task, stories: [...otherStories, ...renumberedSource] };
      }),
    })),
  };
}

