import os
import json
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session, joinedload
from openai import OpenAI, RateLimitError, APIError, APITimeoutError, APIConnectionError

# Загрузка .env файла, если он существует
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv не установлен, используем только переменные окружения
    pass

# --- 1. НАСТРОЙКА (Конфигурация) ---
# Логирование
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Поддержка как OpenAI, так и Perplexity API
API_KEY = os.getenv("OPENAI_API_KEY", "") or os.getenv("PERPLEXITY_API_KEY", "")
API_PROVIDER = os.getenv("API_PROVIDER", "openai")  # "openai" или "perplexity"
API_MODEL = os.getenv("API_MODEL", "gpt-4o" if API_PROVIDER == "openai" else "sonar")
API_TEMPERATURE = float(os.getenv("API_TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.7")))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usm.db")

# CORS настройки - безопасные по умолчанию
ALLOWED_ORIGINS: List[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Инициализация DB
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Инициализация AI клиента
if API_KEY:
    if API_PROVIDER == "perplexity" or API_KEY.startswith("pplx-"):
        # Perplexity API использует совместимый с OpenAI формат, но другой base_url
        client = OpenAI(
            api_key=API_KEY,
            base_url="https://api.perplexity.ai"
        )
        API_PROVIDER = "perplexity"
        logger.info("Initialized Perplexity API client")
    else:
        # OpenAI API
        client = OpenAI(api_key=API_KEY)
        API_PROVIDER = "openai"
        logger.info("Initialized OpenAI API client")
else:
    client = None
    logger.warning("AI API key not configured. AI features will be unavailable.")

app = FastAPI(title="AI User Story Mapper", version="1.0.0")

# CORS для фронтенда - безопасная конфигурация
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
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

class StoryCreate(BaseModel):
    task_id: int
    release_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "Later"
    acceptance_criteria: Optional[List[str]] = []

class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    release_id: Optional[int] = None

class StoryMove(BaseModel):
    task_id: int
    release_id: Optional[int] = None
    position: int

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
    """Отправляет запрос в AI API (OpenAI или Perplexity) и получает структурированную карту"""
    
    if not client:
        logger.error("AI client not initialized")
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set OPENAI_API_KEY or PERPLEXITY_API_KEY environment variable."
        )
    
    # Валидация размера входных данных
    if len(requirements_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Requirements text is too short. Please provide at least 10 characters."
        )
    
    if len(requirements_text) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Requirements text is too long. Maximum 10000 characters allowed."
        )
    
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
        logger.info(f"Generating map for requirements (length: {len(requirements_text)} chars) using {API_PROVIDER}")
        
        # Подготовка параметров запроса
        request_params = {
            "model": API_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": API_TEMPERATURE,
            "timeout": 60.0,  # 60 секунд таймаут
        }
        
        # Perplexity поддерживает JSON mode, но может требовать другой формат
        if API_PROVIDER == "openai":
            request_params["response_format"] = {"type": "json_object"}
        else:
            # Для Perplexity добавляем инструкцию в промпт для JSON
            user_prompt = user_prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."
        
        completion = client.chat.completions.create(**request_params)
        
        response_text = completion.choices[0].message.content
        logger.info("Successfully received AI response")
        
        # Очистка ответа от возможных markdown форматирования (для Perplexity)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Убираем ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Убираем ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Убираем закрывающий ```
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text[:200]}")
            raise HTTPException(
                status_code=502,
                detail=f"Invalid JSON response from AI service. Response: {response_text[:200]}..."
            )
        
    except RateLimitError:
        logger.error(f"{API_PROVIDER.upper()} rate limit exceeded")
        raise HTTPException(
            status_code=429,
            detail=f"{API_PROVIDER.upper()} rate limit exceeded. Please try again later."
        )
    except APITimeoutError:
        logger.error(f"{API_PROVIDER.upper()} request timeout")
        raise HTTPException(
            status_code=504,
            detail="Request to AI service timed out. Please try again."
        )
    except APIConnectionError as e:
        logger.error(f"{API_PROVIDER.upper()} connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to AI service. Please check your internet connection."
        )
    except APIError as e:
        logger.error(f"{API_PROVIDER.upper()} API error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(e)}"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from AI: {e}")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error in AI generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.post("/generate-map")
def generate_map(req: RequirementsInput, db: Session = Depends(get_db)):
    """Генерирует карту пользовательских историй из текста требований"""
    
    # Валидация входных данных
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Requirements text cannot be empty")
    
    # 1. Получаем данные от AI
    try:
        ai_data = generate_ai_map(req.text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_map: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate map")
    
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
    # Исправление N+1 проблемы через eager loading
    project = db.query(Project)\
        .options(
            joinedload(Project.activities)
            .subqueryload(Activity.tasks)
            .subqueryload(UserTask.stories),
            joinedload(Project.releases)
        )\
        .filter(Project.id == project_id)\
        .first()
    
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

@app.post("/story", response_model=StoryResponse)
def create_story(story: StoryCreate, db: Session = Depends(get_db)):
    """Создает новую пользовательскую историю"""
    # Проверяем существование task
    task = db.query(UserTask).filter(UserTask.id == story.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Если release_id указан, проверяем его существование
    if story.release_id:
        release = db.query(Release).filter(Release.id == story.release_id).first()
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")
    
    # Определяем позицию (в конец списка)
    max_position = db.query(UserStory)\
        .filter(UserStory.task_id == story.task_id)\
        .filter(UserStory.release_id == story.release_id)\
        .count()
    
    new_story = UserStory(
        task_id=story.task_id,
        release_id=story.release_id,
        title=story.title,
        description=story.description,
        priority=story.priority or "Later",
        acceptance_criteria=story.acceptance_criteria or [],
        position=max_position
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return StoryResponse(
        id=new_story.id,
        title=new_story.title,
        description=new_story.description,
        priority=new_story.priority,
        acceptance_criteria=new_story.acceptance_criteria or [],
        release_id=new_story.release_id,
        position=new_story.position
    )

@app.put("/story/{story_id}", response_model=StoryResponse)
def update_story(story_id: int, story_update: StoryUpdate, db: Session = Depends(get_db)):
    """Обновляет существующую пользовательскую историю"""
    story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Обновляем только переданные поля
    if story_update.title is not None:
        story.title = story_update.title
    if story_update.description is not None:
        story.description = story_update.description
    if story_update.priority is not None:
        story.priority = story_update.priority
    if story_update.acceptance_criteria is not None:
        story.acceptance_criteria = story_update.acceptance_criteria
    if story_update.release_id is not None:
        # Проверяем существование release
        if story_update.release_id:
            release = db.query(Release).filter(Release.id == story_update.release_id).first()
            if not release:
                raise HTTPException(status_code=404, detail="Release not found")
        story.release_id = story_update.release_id
    
    db.commit()
    db.refresh(story)
    
    return StoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        priority=story.priority,
        acceptance_criteria=story.acceptance_criteria or [],
        release_id=story.release_id,
        position=story.position
    )

@app.delete("/story/{story_id}")
def delete_story(story_id: int, db: Session = Depends(get_db)):
    """Удаляет пользовательскую историю"""
    story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    task_id = story.task_id
    release_id = story.release_id
    position = story.position
    
    db.delete(story)
    db.commit()
    
    # Обновляем позиции остальных историй
    stories_to_update = db.query(UserStory)\
        .filter(UserStory.task_id == task_id)\
        .filter(UserStory.release_id == release_id)\
        .filter(UserStory.position > position)\
        .all()
    
    for s in stories_to_update:
        s.position -= 1
    
    db.commit()
    
    return {"status": "success", "message": "Story deleted"}

@app.patch("/story/{story_id}/move")
def move_story(story_id: int, move: StoryMove, db: Session = Depends(get_db)):
    """Перемещает пользовательскую историю в другую ячейку"""
    story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Проверяем существование task
    task = db.query(UserTask).filter(UserTask.id == move.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Если release_id указан, проверяем его существование
    if move.release_id:
        release = db.query(Release).filter(Release.id == move.release_id).first()
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")
    
    old_task_id = story.task_id
    old_release_id = story.release_id
    old_position = story.position
    
    # Если перемещаем в другую ячейку, обновляем позиции в старой ячейке
    if old_task_id != move.task_id or old_release_id != move.release_id:
        # Уменьшаем позиции в старой ячейке
        stories_to_update = db.query(UserStory)\
            .filter(UserStory.task_id == old_task_id)\
            .filter(UserStory.release_id == old_release_id)\
            .filter(UserStory.position > old_position)\
            .all()
        
        for s in stories_to_update:
            s.position -= 1
        
        # Увеличиваем позиции в новой ячейке после целевой позиции
        stories_to_shift = db.query(UserStory)\
            .filter(UserStory.task_id == move.task_id)\
            .filter(UserStory.release_id == move.release_id)\
            .filter(UserStory.position >= move.position)\
            .all()
        
        for s in stories_to_shift:
            s.position += 1
    
    # Обновляем историю
    story.task_id = move.task_id
    story.release_id = move.release_id
    story.position = move.position
    
    db.commit()
    db.refresh(story)
    
    return StoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        priority=story.priority,
        acceptance_criteria=story.acceptance_criteria or [],
        release_id=story.release_id,
        position=story.position
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

