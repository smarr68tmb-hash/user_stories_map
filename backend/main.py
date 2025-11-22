import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from openai import OpenAI

# --- 1. НАСТРОЙКА (Конфигурация) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = "sqlite:///./usm.db"

# Инициализация DB
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

app = FastAPI(title="AI User Story Mapper")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. БАЗА ДАННЫХ (SQLAlchemy Models) ---

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    raw_requirements = Column(Text)
    
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan", order_by="Activity.position")
    releases = relationship("Release", back_populates="project", cascade="all, delete-orphan", order_by="Release.position")


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String)
    position = Column(Integer, default=0)
    
    project = relationship("Project", back_populates="activities")
    tasks = relationship("UserTask", back_populates="activity", cascade="all, delete-orphan", order_by="UserTask.position")


class UserTask(Base):
    __tablename__ = "user_tasks"
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    title = Column(String)
    position = Column(Integer, default=0)
    
    activity = relationship("Activity", back_populates="tasks")
    stories = relationship("UserStory", back_populates="task", cascade="all, delete-orphan", order_by="UserStory.position")


class Release(Base):
    __tablename__ = "releases"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String)
    position = Column(Integer, default=0)
    
    project = relationship("Project", back_populates="releases")
    stories = relationship("UserStory", back_populates="release")


class UserStory(Base):
    __tablename__ = "user_stories"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("user_tasks.id"))
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    title = Column(String)
    description = Column(Text)
    priority = Column(String)
    acceptance_criteria = Column(JSON)
    position = Column(Integer, default=0)
    
    task = relationship("UserTask", back_populates="stories")
    release = relationship("Release", back_populates="stories")

# Создаем таблицы при запуске
Base.metadata.create_all(bind=engine)

# --- 3. СХЕМЫ ДАННЫХ (Pydantic) ---

class RequirementsInput(BaseModel):
    text: str

class StoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: Optional[str]
    acceptance_criteria: Optional[List[str]]
    release_id: Optional[int]
    position: int

class TaskResponse(BaseModel):
    id: int
    title: str
    position: int
    stories: List[StoryResponse]

class ActivityResponse(BaseModel):
    id: int
    title: str
    position: int
    tasks: List[TaskResponse]

class ReleaseResponse(BaseModel):
    id: int
    title: str
    position: int

class ProjectResponse(BaseModel):
    id: int
    name: str
    raw_requirements: Optional[str]
    activities: List[ActivityResponse]
    releases: List[ReleaseResponse]

# --- 4. ЛОГИКА И ЭНДПОИНТЫ ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_ai_map(requirements_text: str) -> dict:
    """Отправляет запрос в OpenAI и получает структурированную карту"""
    
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
    
    system_prompt = """You are an expert Product Manager and Business Analyst specializing in User Story Mapping (USM). 
Your goal is to analyze unstructured product requirements and convert them into a structured User Story Map in JSON format.

Strictly follow this JSON structure for the output. Do not add any conversational text, only the JSON object."""

    user_prompt = f"""Analyze the following product requirements provided within the triple quotes:

\"\"\"
{requirements_text}
\"\"\"

Your task is to:
1. Identify the main User Personas.
2. Create a "Backbone" of the map consisting of high-level "Activities" (User Goals) and sequential "User Tasks" (Steps to achieve goals).
3. Break down each User Task into specific "User Stories".
4. Assign a priority to each story: "MVP", "Release 1", or "Later".
5. Generate basic Acceptance Criteria (AC) for each story.

Return ONLY valid JSON in this exact structure:
{{
  "productName": "Suggested product name",
  "personas": ["List of personas identified"],
  "map": [
    {{
      "activity": "High-level activity (e.g., Account Management)",
      "tasks": [
        {{
          "taskTitle": "Specific user step (e.g., Sign Up)",
          "stories": [
            {{
              "title": "User story title (e.g., Sign up via Email)",
              "description": "As a [persona], I want to..., so that...",
              "priority": "MVP",
              "acceptanceCriteria": [
                "Criterion 1",
                "Criterion 2"
              ]
            }}
          ]
        }}
      ]
    }}
  ]
}}"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        response_text = completion.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

@app.post("/generate-map")
def generate_map(req: RequirementsInput, db: Session = Depends(get_db)):
    """Генерирует карту пользовательских историй из текста требований"""
    
    # 1. Получаем данные от AI
    ai_data = generate_ai_map(req.text)
    
    # 2. Создаем проект
    project = Project(name=ai_data.get("productName", "New Project"), raw_requirements=req.text)
    db.add(project)
    db.flush()
    
    # 3. Создаем стандартные релизы
    mvp_release = Release(project_id=project.id, title="MVP", position=0)
    release1 = Release(project_id=project.id, title="Release 1", position=1)
    later_release = Release(project_id=project.id, title="Later", position=2)
    db.add_all([mvp_release, release1, later_release])
    db.flush()
    
    # 4. Сохраняем структуру карты
    for act_idx, activity_item in enumerate(ai_data.get("map", [])):
        activity = Activity(
            project_id=project.id,
            title=activity_item.get("activity", ""),
            position=act_idx
        )
        db.add(activity)
        db.flush()
        
        for task_idx, task_item in enumerate(activity_item.get("tasks", [])):
            task = UserTask(
                activity_id=activity.id,
                title=task_item.get("taskTitle", ""),
                position=task_idx
            )
            db.add(task)
            db.flush()
            
            for story_idx, story_item in enumerate(task_item.get("stories", [])):
                # Определяем релиз по приоритету
                priority = story_item.get("priority", "Later").upper()
                if "MVP" in priority:
                    target_release = mvp_release
                elif "RELEASE" in priority or "1" in priority:
                    target_release = release1
                else:
                    target_release = later_release
                
                story = UserStory(
                    task_id=task.id,
                    release_id=target_release.id,
                    title=story_item.get("title", ""),
                    description=story_item.get("description", ""),
                    priority=story_item.get("priority", "Later"),
                    acceptance_criteria=story_item.get("acceptanceCriteria", []),
                    position=story_idx
                )
                db.add(story)
    
    db.commit()
    db.refresh(project)
    
    return {"status": "success", "project_id": project.id, "project_name": project.name}

@app.get("/project/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Возвращает полную структуру проекта для отрисовки на фронтенде"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Формируем ответ в нужном формате
    activities_data = []
    for activity in project.activities:
        tasks_data = []
        for task in activity.tasks:
            stories_data = []
            for story in task.stories:
                stories_data.append(StoryResponse(
                    id=story.id,
                    title=story.title,
                    description=story.description,
                    priority=story.priority,
                    acceptance_criteria=story.acceptance_criteria or [],
                    release_id=story.release_id,
                    position=story.position
                ))
            tasks_data.append(TaskResponse(
                id=task.id,
                title=task.title,
                position=task.position,
                stories=stories_data
            ))
        activities_data.append(ActivityResponse(
            id=activity.id,
            title=activity.title,
            position=activity.position,
            tasks=tasks_data
        ))
    
    releases_data = [
        ReleaseResponse(
            id=release.id,
            title=release.title,
            position=release.position
        )
        for release in project.releases
    ]
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        raw_requirements=project.raw_requirements,
        activities=activities_data,
        releases=releases_data
    )

@app.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    """Возвращает список всех проектов"""
    projects = db.query(Project).all()
    return [{"id": p.id, "name": p.name, "created_at": str(p.id)} for p in projects]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

