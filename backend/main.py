import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, JSON, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session, joinedload
from sqlalchemy.sql import func
from openai import OpenAI, RateLimitError, APIError, APITimeoutError, APIConnectionError
from jose import JWTError, jwt
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis

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
# Логирование (инициализируем первым, чтобы использовать в Sentry)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация Sentry (опционально)
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
        )
        logger.info("Sentry initialized")
    except ImportError:
        logger.warning("Sentry SDK not installed. Error tracking disabled.")
else:
    logger.info("Sentry DSN not configured. Error tracking disabled.")

# Поддержка как OpenAI, так и Perplexity API
API_KEY = os.getenv("OPENAI_API_KEY", "") or os.getenv("PERPLEXITY_API_KEY", "")

# Определяем провайдера: сначала проверяем переменную, потом по формату ключа
API_PROVIDER = os.getenv("API_PROVIDER", "")
if not API_PROVIDER:
    if API_KEY.startswith("pplx-"):
        API_PROVIDER = "perplexity"
    elif API_KEY.startswith("sk-"):
        API_PROVIDER = "openai"
    else:
        API_PROVIDER = "openai"  # По умолчанию

# Устанавливаем модель по умолчанию в зависимости от провайдера
# Актуальные модели Perplexity (2025): sonar, sonar-pro, sonar-reasoning, llama-3.1-sonar-large-128k-online
if API_PROVIDER == "perplexity":
    DEFAULT_MODEL = "sonar"  # Базовая модель Perplexity, всегда доступна
else:
    DEFAULT_MODEL = "gpt-4o"  # OpenAI по умолчанию

API_MODEL = os.getenv("API_MODEL", DEFAULT_MODEL)
API_TEMPERATURE = float(os.getenv("API_TEMPERATURE", os.getenv("OPENAI_TEMPERATURE", "0.7")))
# DATABASE_URL должен быть установлен в production (Supabase PostgreSQL)
# Если не установлен, используем SQLite только для локальной разработки
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usm.db")

# Предупреждение, если используется SQLite в production-подобной среде
if DATABASE_URL.startswith("sqlite"):
    logger.warning("⚠️ SQLite используется! Для production установите DATABASE_URL на PostgreSQL (Supabase).")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# CORS настройки - безопасные по умолчанию
ALLOWED_ORIGINS: List[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Инициализация DB
# Для PostgreSQL не нужен check_same_thread
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Инициализация Redis
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connected successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS для фронтенда - безопасная конфигурация
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

# --- 2. БАЗА ДАННЫХ (SQLAlchemy Models) ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="refresh_tokens")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, index=True)
    raw_requirements = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="projects")
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

# Authentication schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

# Project schemas
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

# Authentication utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int, db: Session) -> str:
    """Создает refresh токен и сохраняет его в БД"""
    expires_delta = timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    
    # Генерируем случайный токен (можно использовать JWT, но random string безопаснее для revoke)
    import secrets
    token_str = secrets.token_urlsafe(64)
    
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token_str,
        expires_at=expire
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return token_str

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
        token_data = TokenData(user_id=user_id)
    except ValueError:
        raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise credentials_exception
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_cache_key(requirements_text: str) -> str:
    """Генерирует ключ для кеша на основе текста требований"""
    import hashlib
    text_hash = hashlib.sha256(requirements_text.encode()).hexdigest()
    return f"ai_map:{text_hash}"

def generate_ai_map(requirements_text: str, use_cache: bool = True) -> dict:
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
    
    # Проверяем кеш перед запросом к AI
    cache_key = get_cache_key(requirements_text)
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info("Using cached AI response")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")
    
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
            result = json.loads(response_text)
            
            # Сохранение в кеш Redis (TTL 24 часа)
            if use_cache and redis_client:
                try:
                    redis_client.setex(
                        cache_key,
                        86400,  # 24 часа
                        json.dumps(result)
                    )
                    logger.info("Result cached in Redis")
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")
            
            return result
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

# --- Health Check Endpoints ---
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness check - проверяет подключение к БД"""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        db_status = "error"
        raise HTTPException(status_code=503, detail="Database not ready")
    
    redis_status = "ok" if redis_client and redis_client.ping() else "unavailable"
    
    return {
        "status": "ready" if db_status == "ok" else "not_ready",
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# --- Authentication Endpoints ---
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверка существования пользователя
    db_user = get_user_by_email(db, email=user_data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создание пользователя
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        is_active=db_user.is_active,
        created_at=db_user.created_at
    )

@app.post("/token", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Логин и получение JWT токена"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(user.id, db)
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
def refresh_token_endpoint(request: Request, token_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Обновление access токена с помощью refresh токена"""
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token_data.refresh_token).first()
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    if refresh_token.revoked:
        # Возможно, попытка повторного использования - стоит бить тревогу
        raise HTTPException(status_code=401, detail="Token revoked")
        
    if refresh_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
        
    # Генерируем новый access token
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(refresh_token.user_id)}, expires_delta=access_token_expires
    )
    
    # Ротация refresh токена (удаляем старый, создаем новый)
    refresh_token.revoked = True
    new_refresh_token = create_refresh_token(refresh_token.user_id, db)
    
    db.commit()
    
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@app.post("/logout")
def logout(token_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Отзыв refresh токена"""
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token_data.refresh_token).first()
    if refresh_token:
        refresh_token.revoked = True
        db.commit()
    return {"message": "Logged out successfully"}

@app.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

# --- Project Endpoints ---
@app.post("/generate-map")
@limiter.limit("10/hour")
def generate_map(req: RequirementsInput, request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
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
    
    # 2. Создаем проект (привязываем к текущему пользователю)
    project = Project(
        name=ai_data.get("productName", "New Project"),
        raw_requirements=req.text,
        user_id=current_user.id
    )
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
def get_project(project_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
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
        .filter(Project.user_id == current_user.id)\
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
def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Возвращает список проектов пользователя с пагинацией"""
    projects = db.query(Project)\
        .filter(Project.user_id == current_user.id)\
        .order_by(Project.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    total = db.query(Project).filter(Project.user_id == current_user.id).count()
    return {
        "items": [{"id": p.id, "name": p.name, "created_at": p.created_at.isoformat()} for p in projects],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.post("/story", response_model=StoryResponse)
@limiter.limit("30/minute")
def create_story(story: StoryCreate, request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Создает новую пользовательскую историю"""
    # Проверяем существование task и владельца проекта
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == story.task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Если release_id указан, проверяем его существование и владельца
    if story.release_id:
        release = db.query(Release)\
            .join(Project)\
            .filter(Release.id == story.release_id)\
            .filter(Project.user_id == current_user.id)\
            .first()
        if not release:
            raise HTTPException(status_code=404, detail="Release not found or access denied")
    
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
@limiter.limit("30/minute")
def update_story(story_id: int, story_update: StoryUpdate, request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Обновляет существующую пользовательскую историю"""
    # Проверяем владельца проекта
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
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
@limiter.limit("30/minute")
def delete_story(story_id: int, request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Удаляет пользовательскую историю"""
    # Проверяем владельца проекта
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
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
@limiter.limit("30/minute")
def move_story(story_id: int, move: StoryMove, request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Перемещает пользовательскую историю в другую ячейку"""
    # Проверяем владельца проекта для исходной истории
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
    # Проверяем существование task и владельца для целевой ячейки
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == move.task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
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

