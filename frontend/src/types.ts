export type Identifier = number | string;

export type Status = 'todo' | 'in_progress' | 'done' | 'blocked';

export type Priority =
  | 'low'
  | 'medium'
  | 'high'
  | 'mvp'
  | 'later'
  | 'release 1'
  | 'release1'
  | 'MVP'
  | 'Later';

export type WireframeStatus = 'idle' | 'pending' | 'success' | 'error';

export interface Story {
  id: Identifier;
  title: string;
  description?: string | null;
  priority?: Priority | null;
  acceptance_criteria?: string[] | null;
  release_id: number | null;
  position?: number | null;
  status?: Status | null;
}

export interface Task {
  id: Identifier;
  title: string;
  position?: number | null;
  stories: Story[];
}

export interface Activity {
  id: Identifier;
  title: string;
  position?: number | null;
  tasks: Task[];
}

export interface Release {
  id: number;
  title: string;
  position?: number | null;
}

export interface Project {
  id: Identifier;
  name: string;
  raw_requirements?: string | null;
  activities: Activity[];
  releases: Release[];
  wireframe_markdown?: string | null;
  wireframe_generated_at?: string | null;
  wireframe_status?: WireframeStatus | null;
  wireframe_error?: string | null;
}

export interface WireframeResponse {
  markdown: string | null;
  status: WireframeStatus | null;
  generated_at?: string | null;
  error?: string | null;
  job_status?: string | null;
}

export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface EnhancementResponse {
  original_text: string;
  enhanced_text: string;
  added_aspects: string[];
  missing_info: string[];
  detected_product_type: string;
  detected_roles: string[];
  confidence: number;
  fallback: boolean;
}

export interface GenerateMapResponse {
  project_id: number;
}

export interface TokenResponse {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
}

export interface ActivityPayload {
  project_id: number;
  title: string;
  position?: number;
}

export interface TaskPayload {
  activity_id: number;
  title: string;
  position?: number;
}

export interface StoryPayload {
  task_id: number;
  release_id: number | null;
  title: string;
  description?: string;
  priority?: Priority;
  acceptance_criteria?: string[];
  status?: Status;
}

