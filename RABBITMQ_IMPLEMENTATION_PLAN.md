# 🚀 RabbitMQ Implementation Plan - Продолжение

## Связанные документы
- **Основной гайд:** `RABBITMQ_COMPLETE_GUIDE.md` (Phases 1-2 с детальной архитектурой)
- **Этот документ:** Phases 3-7 (Workers, Frontend, Testing, Deployment)

---

# Phase 3: Workers Implementation

## 3.1. Map Generation Worker

### 3.1.1. Структура Worker

Создайте директорию для workers:

```bash
mkdir -p backend/workers
touch backend/workers/__init__.py
```

### 3.1.2. Полный код Map Worker

Создайте `backend/workers/map_worker.py`:

```python
#!/usr/bin/env python3
"""
RabbitMQ Consumer для генерации User Story Maps

Функции:
- Потребление сообщений из очереди ai.map.generation
- Two-stage AI processing (enhancement + generation)
- Сохранение результата в PostgreSQL
- Обновление статуса в Redis
- Graceful shutdown

Запуск:
    python workers/map_worker.py
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import settings
from utils.database import SessionLocal
from services.rabbitmq_service import rabbitmq_service
from services.ai_service import generate_ai_map, enhance_requirements
from services.job_service import JobService, JobStatus
from models import Project, Activity, UserTask, Release, UserStory

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/map_worker.log')
    ]
)
logger = logging.getLogger(__name__)


class MapGenerationWorker:
    """Worker для обработки AI генерации User Story Maps"""

    def __init__(self):
        self.running = False
        self.redis_client = None
        self.job_service: Optional[JobService] = None
        self.processed_count = 0
        self.failed_count = 0

    async def start(self):
        """Запуск worker"""
        logger.info("="*60)
        logger.info("🚀 Starting Map Generation Worker")
        logger.info(f"   Environment: {settings.ENVIRONMENT}")
        logger.info(f"   RabbitMQ: {settings._mask_url(settings.RABBITMQ_URL)}")
        logger.info("="*60)

        # Подключение к Redis
        try:
            import redis.asyncio as aioredis
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            self.job_service = JobService(self.redis_client)
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}")
            logger.warning("   Job status updates will be disabled")

        # Подключение к RabbitMQ
        await rabbitmq_service.connect()

        # Запуск consumer
        self.running = True
        logger.info("👀 Waiting for map generation requests...")
        logger.info("   Press Ctrl+C to stop\n")

        try:
            await rabbitmq_service.consume(
                queue_name="map_generation",
                callback=self.process_message
            )
        except KeyboardInterrupt:
            logger.info("\n⚠️ KeyboardInterrupt received")
        except Exception as e:
            logger.error(f"❌ Consumer error: {e}", exc_info=True)

    async def stop(self):
        """Graceful shutdown"""
        logger.info("\n" + "="*60)
        logger.info("🛑 Stopping Map Generation Worker")
        logger.info(f"   Processed: {self.processed_count}")
        logger.info(f"   Failed: {self.failed_count}")
        logger.info("="*60)

        self.running = False

        # Закрыть RabbitMQ
        await rabbitmq_service.disconnect()

        # Закрыть Redis
        if self.redis_client:
            await self.redis_client.close()

        logger.info("✅ Worker stopped gracefully")

    async def process_message(self, message_data: dict):
        """
        Обработка одного сообщения из RabbitMQ

        Message format:
        {
            "job_id": "uuid",
            "user_id": 123,
            "requirements_text": "...",
            "use_enhancement": true,
            "created_at": "2025-12-01T10:00:00Z"
        }
        """
        job_id = message_data.get("job_id")
        user_id = message_data.get("user_id")
        requirements_text = message_data.get("requirements_text")
        use_enhancement = message_data.get("use_enhancement", True)

        logger.info("="*60)
        logger.info(f"📨 Processing job: {job_id}")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Text length: {len(requirements_text)} chars")
        logger.info(f"   Enhancement: {'enabled' if use_enhancement else 'disabled'}")
        logger.info("="*60)

        # Обновление статуса: processing
        if self.job_service:
            await self.job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.PROCESSING
            )

        db: Session = SessionLocal()
        start_time = asyncio.get_event_loop().time()

        try:
            # ==========================================
            # Stage 1: Enhancement (опционально)
            # ==========================================
            generation_text = requirements_text
            enhancement_data = None

            if use_enhancement:
                try:
                    logger.info("🔄 Stage 1: Enhancing requirements...")
                    enhancement_data = enhance_requirements(
                        requirements_text,
                        self.redis_client
                    )

                    confidence = enhancement_data.get("confidence", 0)
                    logger.info(f"   Confidence: {confidence:.2f}")

                    if confidence >= 0.7 and not enhancement_data.get("fallback"):
                        generation_text = enhancement_data.get("enhanced_text", requirements_text)
                        logger.info("   ✅ Using enhanced text")

                        # Log improvements
                        added = enhancement_data.get("added_aspects", [])
                        if added:
                            logger.info(f"   Added aspects: {', '.join(added[:3])}")
                    else:
                        logger.info("   ℹ️ Using original text (low confidence)")

                except Exception as e:
                    logger.warning(f"   ⚠️ Enhancement failed: {e}")
                    logger.warning("   Continuing with original text")

            # ==========================================
            # Stage 2: AI Generation
            # ==========================================
            logger.info("🤖 Stage 2: Generating User Story Map...")

            ai_data = generate_ai_map(
                generation_text,
                redis_client=self.redis_client
            )

            # Validate AI response
            if not ai_data or not isinstance(ai_data, dict):
                raise ValueError("Invalid AI response format")

            if "map" not in ai_data or not isinstance(ai_data["map"], list):
                raise ValueError("AI response missing 'map' field")

            logger.info(f"   ✅ Map generated")
            logger.info(f"   Product: {ai_data.get('productName', 'N/A')}")
            logger.info(f"   Activities: {len(ai_data.get('map', []))}")

            # ==========================================
            # Stage 3: Save to Database
            # ==========================================
            logger.info("💾 Saving to database...")

            project = self._save_project_to_db(
                db=db,
                user_id=user_id,
                ai_data=ai_data,
                requirements_text=requirements_text
            )

            logger.info(f"   ✅ Project created: ID={project.id}")

            # Count stories
            story_count = 0
            for activity in ai_data.get("map", []):
                for task in activity.get("tasks", []):
                    story_count += len(task.get("stories", []))

            logger.info(f"   Stories created: {story_count}")

            # ==========================================
            # Stage 4: Update job status
            # ==========================================
            elapsed_time = asyncio.get_event_loop().time() - start_time

            if self.job_service:
                await self.job_service.update_job_status(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    result={
                        "project_id": project.id,
                        "project_name": project.name,
                        "activities_count": len(ai_data.get("map", [])),
                        "stories_count": story_count,
                        "processing_time": f"{elapsed_time:.2f}s",
                        "used_enhancement": use_enhancement
                    }
                )

            self.processed_count += 1

            logger.info(f"✅ Job {job_id} completed successfully in {elapsed_time:.2f}s")
            logger.info("")

        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)

            logger.error("="*60)
            logger.error(f"❌ Job {job_id} failed after {elapsed_time:.2f}s")
            logger.error(f"   Error: {error_msg}")
            logger.error("="*60, exc_info=True)

            # Update job status: failed
            if self.job_service:
                await self.job_service.update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=error_msg
                )

            self.failed_count += 1

            # Re-raise для NACK (сообщение вернется в очередь)
            raise

        finally:
            db.close()

    def _save_project_to_db(
        self,
        db: Session,
        user_id: int,
        ai_data: dict,
        requirements_text: str
    ) -> Project:
        """
        Сохранение проекта и всей структуры в PostgreSQL

        Структура:
        Project
          └── Activities
                └── Tasks
                      └── Stories

        Returns:
            Project: Созданный проект
        """
        try:
            # Create project
            project = Project(
                name=ai_data.get("productName", "New Project"),
                raw_requirements=requirements_text,
                user_id=user_id
            )
            db.add(project)
            db.flush()  # Получить project.id

            # Create releases
            mvp_release = Release(project_id=project.id, title="MVP", position=0)
            release1 = Release(project_id=project.id, title="Release 1", position=1)
            later_release = Release(project_id=project.id, title="Later", position=2)

            db.add_all([mvp_release, release1, later_release])
            db.flush()

            # Create map structure
            for act_idx, activity_item in enumerate(ai_data.get("map", [])):
                if not isinstance(activity_item, dict):
                    logger.warning(f"Skipping invalid activity at index {act_idx}")
                    continue

                activity = Activity(
                    project_id=project.id,
                    title=activity_item.get("activity", "Untitled Activity"),
                    position=act_idx
                )
                db.add(activity)
                db.flush()

                for task_idx, task_item in enumerate(activity_item.get("tasks", [])):
                    if not isinstance(task_item, dict):
                        logger.warning(f"Skipping invalid task at {act_idx}.{task_idx}")
                        continue

                    task = UserTask(
                        activity_id=activity.id,
                        title=task_item.get("taskTitle", "Untitled Task"),
                        position=task_idx
                    )
                    db.add(task)
                    db.flush()

                    for story_idx, story_item in enumerate(task_item.get("stories", [])):
                        if not isinstance(story_item, dict):
                            logger.warning(f"Skipping invalid story at {act_idx}.{task_idx}.{story_idx}")
                            continue

                        # Determine release based on priority
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
                            title=story_item.get("title", "Untitled Story"),
                            description=story_item.get("description", ""),
                            priority=story_item.get("priority", "Later"),
                            acceptance_criteria=story_item.get("acceptanceCriteria", []),
                            position=story_idx,
                            status="todo"  # Default status
                        )
                        db.add(story)

            # Commit all changes
            db.commit()
            db.refresh(project)

            return project

        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise


# ==========================================
# Signal handlers для graceful shutdown
# ==========================================

worker: Optional[MapGenerationWorker] = None

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM"""
    logger.info(f"\n⚠️ Received signal {signum}")
    if worker:
        asyncio.create_task(worker.stop())
        sys.exit(0)


async def main():
    """Entry point"""
    global worker

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start worker
    worker = MapGenerationWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️ KeyboardInterrupt in main()")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        await worker.stop()


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Run worker
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
```

### 3.1.3. Тестирование Map Worker

Создайте тестовый скрипт `backend/test_map_worker.py`:

```python
"""
Тест Map Worker

Публикует тестовое сообщение и запускает worker для обработки
"""
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

async def test_worker():
    from services.rabbitmq_service import publish_ai_map_generation, rabbitmq_service

    print("\n🧪 Testing Map Worker\n")

    # Connect to RabbitMQ
    await rabbitmq_service.connect()

    # Publish test message
    job_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"📤 Publishing test job: {job_id}")

    await publish_ai_map_generation(
        job_id=job_id,
        user_id=1,  # Make sure user with ID=1 exists in DB
        requirements_text="""
        Приложение для управления задачами (To-Do List).

        Роли:
        - Пользователь: создает, редактирует, удаляет задачи
        - Администратор: управляет пользователями

        Функции:
        - Создание задачи с названием, описанием, дедлайном
        - Отметка задачи как выполненной
        - Фильтрация по статусу (все, активные, выполненные)
        - Поиск по названию
        """,
        use_enhancement=False,
        priority=9
    )

    print(f"✅ Message published")
    print(f"\n👉 Now run the worker:")
    print(f"   cd backend")
    print(f"   python workers/map_worker.py")
    print(f"\nWorker will process the message and create a project in DB\n")

    await rabbitmq_service.disconnect()

if __name__ == "__main__":
    asyncio.run(test_worker())
```

**Запуск теста:**

Terminal 1 - Publish test message:
```bash
cd backend
python test_map_worker.py
```

Terminal 2 - Run worker:
```bash
cd backend
python workers/map_worker.py
```

**Ожидаемый вывод worker:**
```
============================================================
🚀 Starting Map Generation Worker
   Environment: development
   RabbitMQ: amqps://vrcptkqu:***@hawk-01.rmq.cloudamqp.com/vrcptkqu
============================================================
✅ Connected to Redis
✅ RabbitMQ connected successfully
👀 Waiting for map generation requests...
   Press Ctrl+C to stop

============================================================
📨 Processing job: test-20251201-100000
   User ID: 1
   Text length: 456 chars
   Enhancement: disabled
============================================================
🤖 Stage 2: Generating User Story Map...
   ✅ Map generated
   Product: To-Do List Manager
   Activities: 3
💾 Saving to database...
   ✅ Project created: ID=123
   Stories created: 12
✅ Job test-20251201-100000 completed successfully in 25.43s
```

---

## 3.2. Wireframe Generation Worker

### 3.2.1. Полный код Wireframe Worker

Создайте `backend/workers/wireframe_worker.py`:

```python
#!/usr/bin/env python3
"""
RabbitMQ Consumer для генерации Wireframes/Прототипов

Функции:
- Потребление из очереди ai.wireframe.generation
- Генерация UI описаний через GPT-4
- Генерация изображений через DALL-E 3
- Загрузка в Cloudinary
- Обновление прогресса в Redis

Зависимости:
- OpenAI API (GPT-4 + DALL-E 3)
- Cloudinary (optional, для permanent storage)

Запуск:
    python workers/wireframe_worker.py
"""
import asyncio
import logging
import signal
import sys
import io
import base64
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import settings
from utils.database import SessionLocal
from services.rabbitmq_service import rabbitmq_service
from services.job_service import JobService, JobStatus
from models import UserStory, UserTask, Activity

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/wireframe_worker.log')
    ]
)
logger = logging.getLogger(__name__)


class WireframeGenerationWorker:
    """Worker для генерации UI wireframes из User Stories"""

    def __init__(self):
        self.running = False
        self.redis_client = None
        self.job_service: Optional[JobService] = None
        self.openai_client = None
        self.cloudinary_configured = False
        self.processed_count = 0
        self.failed_count = 0

    async def start(self):
        """Запуск worker"""
        logger.info("="*60)
        logger.info("🎨 Starting Wireframe Generation Worker")
        logger.info(f"   Environment: {settings.ENVIRONMENT}")
        logger.info("="*60)

        # Redis
        try:
            import redis.asyncio as aioredis
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            self.job_service = JobService(self.redis_client)
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}")

        # OpenAI
        if not settings.OPENAI_API_KEY:
            logger.error("❌ OPENAI_API_KEY not set!")
            logger.error("   Wireframe generation requires OpenAI API")
            sys.exit(1)

        from openai import OpenAI
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("✅ OpenAI client initialized")

        # Cloudinary (optional)
        if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
            import cloudinary
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
            self.cloudinary_configured = True
            logger.info("✅ Cloudinary configured")
        else:
            logger.warning("⚠️ Cloudinary not configured")
            logger.warning("   Will use temporary OpenAI image URLs")

        # RabbitMQ
        await rabbitmq_service.connect()

        # Start consuming
        self.running = True
        logger.info("👀 Waiting for wireframe generation requests...\n")

        try:
            await rabbitmq_service.consume(
                queue_name="wireframe_generation",
                callback=self.process_message
            )
        except KeyboardInterrupt:
            logger.info("\n⚠️ KeyboardInterrupt received")
        except Exception as e:
            logger.error(f"❌ Consumer error: {e}", exc_info=True)

    async def stop(self):
        """Graceful shutdown"""
        logger.info("\n" + "="*60)
        logger.info("🛑 Stopping Wireframe Worker")
        logger.info(f"   Processed: {self.processed_count}")
        logger.info(f"   Failed: {self.failed_count}")
        logger.info("="*60)

        self.running = False
        await rabbitmq_service.disconnect()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("✅ Worker stopped")

    async def process_message(self, message_data: dict):
        """
        Обработка wireframe generation request

        Message format:
        {
            "job_id": "uuid",
            "user_id": 123,
            "project_id": 456,
            "story_ids": [1, 2, 3],
            "style": "low-fidelity",
            "platform": "web"
        }
        """
        job_id = message_data.get("job_id")
        user_id = message_data.get("user_id")
        project_id = message_data.get("project_id")
        story_ids = message_data.get("story_ids", [])
        style = message_data.get("style", "low-fidelity")
        platform = message_data.get("platform", "web")

        logger.info("="*60)
        logger.info(f"🎨 Processing wireframe job: {job_id}")
        logger.info(f"   User: {user_id}, Project: {project_id}")
        logger.info(f"   Stories: {len(story_ids)}, Style: {style}, Platform: {platform}")
        logger.info("="*60)

        # Update status
        if self.job_service:
            await self.job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.PROCESSING
            )

        db: Session = SessionLocal()
        start_time = asyncio.get_event_loop().time()
        wireframes = []

        try:
            # Load stories from DB
            stories = db.query(UserStory)\
                .filter(UserStory.id.in_(story_ids))\
                .all()

            if not stories:
                raise ValueError(f"No stories found for IDs: {story_ids}")

            logger.info(f"📚 Loaded {len(stories)} stories from database")

            # Generate wireframe for each story
            for idx, story in enumerate(stories, 1):
                logger.info(f"\n{'─'*60}")
                logger.info(f"🎨 Wireframe {idx}/{len(stories)}: {story.title}")
                logger.info(f"{'─'*60}")

                try:
                    wireframe_data = await self._generate_wireframe_for_story(
                        story=story,
                        style=style,
                        platform=platform,
                        db=db
                    )

                    wireframes.append(wireframe_data)

                    # Update progress
                    if self.job_service:
                        await self.job_service.update_job_status(
                            job_id=job_id,
                            status=JobStatus.PROCESSING,
                            result={
                                "progress": f"{idx}/{len(stories)}",
                                "completed_wireframes": wireframes
                            }
                        )

                    logger.info(f"✅ Wireframe {idx} completed")

                except Exception as e:
                    logger.error(f"❌ Failed to generate wireframe {idx}: {e}")
                    # Continue with next story
                    wireframes.append({
                        "story_id": story.id,
                        "story_title": story.title,
                        "error": str(e),
                        "status": "failed"
                    })

            # Calculate stats
            successful = len([w for w in wireframes if "error" not in w])
            failed = len([w for w in wireframes if "error" in w])
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Update final status
            if self.job_service:
                await self.job_service.update_job_status(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    result={
                        "wireframes": wireframes,
                        "total_count": len(wireframes),
                        "successful": successful,
                        "failed": failed,
                        "style": style,
                        "platform": platform,
                        "processing_time": f"{elapsed_time:.2f}s"
                    }
                )

            self.processed_count += 1

            logger.info("\n" + "="*60)
            logger.info(f"✅ Job {job_id} completed in {elapsed_time:.2f}s")
            logger.info(f"   Successful: {successful}/{len(wireframes)}")
            if failed > 0:
                logger.warning(f"   Failed: {failed}/{len(wireframes)}")
            logger.info("="*60 + "\n")

        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)

            logger.error("="*60)
            logger.error(f"❌ Job {job_id} failed after {elapsed_time:.2f}s")
            logger.error(f"   Error: {error_msg}")
            logger.error("="*60, exc_info=True)

            if self.job_service:
                await self.job_service.update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=error_msg
                )

            self.failed_count += 1
            raise

        finally:
            db.close()

    async def _generate_wireframe_for_story(
        self,
        story: UserStory,
        style: str,
        platform: str,
        db: Session
    ) -> Dict:
        """
        Генерация wireframe для одной User Story

        Pipeline:
        1. Load context (Activity, Task)
        2. Generate UI description (GPT-4)
        3. Generate image (DALL-E 3)
        4. Upload to Cloudinary (optional)

        Returns:
            Dict with wireframe data (image_url, description, etc.)
        """

        # Step 1: Load context
        task = db.query(UserTask).filter(UserTask.id == story.task_id).first()
        activity = None
        if task:
            activity = db.query(Activity).filter(Activity.id == task.activity_id).first()

        # Step 2: Generate UI description
        logger.info("   📝 Generating UI description with GPT-4...")

        ui_description_prompt = self._build_ui_description_prompt(
            story=story,
            task=task,
            activity=activity,
            style=style,
            platform=platform
        )

        ui_description_response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Ты - эксперт UI/UX дизайнер. Создаёшь детальные описания интерфейсов для wireframes."
                },
                {
                    "role": "user",
                    "content": ui_description_prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )

        ui_description = ui_description_response.choices[0].message.content
        logger.info(f"   ✅ UI description: {ui_description[:80]}...")

        # Step 3: Generate image with DALL-E 3
        logger.info("   🖼️  Generating image with DALL-E 3...")

        image_prompt = self._build_image_prompt(ui_description, style, platform)

        image_response = self.openai_client.images.generate(
            model=settings.WIREFRAME_DALLE_MODEL,
            prompt=image_prompt,
            size=settings.WIREFRAME_IMAGE_SIZE,
            quality=settings.WIREFRAME_IMAGE_QUALITY,
            n=1
        )

        temp_image_url = image_response.data[0].url
        logger.info(f"   ✅ Image generated")

        # Step 4: Upload to Cloudinary (if configured)
        permanent_url = temp_image_url

        if self.cloudinary_configured:
            try:
                logger.info("   ☁️  Uploading to Cloudinary...")

                import cloudinary.uploader

                upload_result = cloudinary.uploader.upload(
                    temp_image_url,
                    folder=f"wireframes/project_{story.task.activity.project_id}",
                    public_id=f"story_{story.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    resource_type="image"
                )

                permanent_url = upload_result.get("secure_url")
                logger.info(f"   ✅ Uploaded to Cloudinary")

            except Exception as e:
                logger.warning(f"   ⚠️ Cloudinary upload failed: {e}")
                logger.warning("   Using temporary OpenAI URL")

        return {
            "story_id": story.id,
            "story_title": story.title,
            "ui_description": ui_description,
            "image_url": permanent_url,
            "style": style,
            "platform": platform,
            "created_at": datetime.utcnow().isoformat()
        }

    def _build_ui_description_prompt(
        self,
        story: UserStory,
        task: Optional[UserTask],
        activity: Optional[Activity],
        style: str,
        platform: str
    ) -> str:
        """Формирование промпта для генерации UI описания"""

        context = f"""
User Story:
Название: {story.title}
Описание: {story.description}

Acceptance Criteria:
{chr(10).join(f"  • {c}" for c in (story.acceptance_criteria or ['Нет критериев']))}

Контекст:
Activity: {activity.title if activity else 'N/A'}
Task: {task.title if task else 'N/A'}

Параметры:
Стиль: {style}
Платформа: {platform}
"""

        prompt = f"""Создай детальное описание UI интерфейса для следующей User Story:

{context}

ТРЕБОВАНИЯ:

1. **Структура экрана:**
   - Header (навигация, логотип, меню)
   - Main content (основной функционал)
   - Footer (дополнительные элементы)

2. **UI Элементы:**
   - Перечисли все кнопки, поля ввода, карточки, списки
   - Укажи их расположение и назначение
   - Добавь labels и placeholder текст

3. **Навигация:**
   - Откуда пользователь попадает на этот экран
   - Куда может перейти с этого экрана

4. **Платформа ({platform}):**
   - web: адаптивная сетка, меню в header
   - mobile: вертикальная прокрутка, bottom navigation
   - desktop: sidebar, toolbars

5. **Стиль ({style}):**
   - low-fidelity: базовая структура, блоки, простота
   - high-fidelity: детальный дизайн, цвета, типографика
   - component: фокус на отдельном UI компоненте

ФОРМАТ ОТВЕТА:
Текстовое описание в 4-6 абзацев на РУССКОМ языке.
Будь конкретным и детальным.
"""
        return prompt

    def _build_image_prompt(
        self,
        ui_description: str,
        style: str,
        platform: str
    ) -> str:
        """Формирование промпта для DALL-E 3"""

        style_instructions = {
            "low-fidelity": "Black and white wireframe sketch. Simple rectangles, lines, and basic shapes. Minimal detail. Hand-drawn aesthetic. No colors, no images, just structural layout.",
            "high-fidelity": "Detailed UI mockup with realistic design. Modern interface with clean typography, appropriate color scheme, icons, and visual hierarchy. Professional look and feel.",
            "component": "Isolated UI component on white background. Focus on single element (button, form, card). Clean, professional design with annotations."
        }

        platform_instructions = {
            "web": "Desktop web interface. Browser window frame. Responsive grid layout. Standard web UI patterns (navbar, cards, forms).",
            "mobile": "Mobile app interface. iPhone or Android screen mockup. Portrait orientation. Touch-friendly buttons and navigation. Bottom tab bar or hamburger menu.",
            "desktop": "Desktop application window. Native OS style (Windows/Mac). Menu bar, toolbar, sidebar. Multi-panel layout."
        }

        prompt = f"""Create a {style_instructions.get(style, 'wireframe')} for a {platform_instructions.get(platform, 'interface')}.

UI DESCRIPTION:
{ui_description}

TECHNICAL REQUIREMENTS:
- Style: {style}
- Platform: {platform}
- Clear visual hierarchy
- All UI elements from description should be visible
- Use realistic placeholder text (no lorem ipsum)
- Professional, clean design
- Focus on usability and clarity

IMPORTANT:
- Create only the interface, no people or hands interacting with it
- No text watermarks or logos
- Crisp, high-contrast for readability
"""
        return prompt


# Signal handlers
worker: Optional[WireframeGenerationWorker] = None

def signal_handler(signum, frame):
    logger.info(f"\n⚠️ Received signal {signum}")
    if worker:
        asyncio.create_task(worker.stop())
        sys.exit(0)


async def main():
    global worker

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    worker = WireframeGenerationWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️ KeyboardInterrupt in main()")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        await worker.stop()


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
```

### 3.2.2. Конфигурация DALL-E стоимости

**Важно понимать стоимость:**

```python
# backend/utils/cost_calculator.py
"""
Калькулятор стоимости AI операций
"""

class AIServiceCost:
    """Расчет стоимости AI запросов"""

    # OpenAI Pricing (as of 2025)
    GPT4_INPUT_COST = 0.03 / 1000  # $0.03 per 1K tokens
    GPT4_OUTPUT_COST = 0.06 / 1000  # $0.06 per 1K tokens

    DALLE3_STANDARD_1024 = 0.040  # $0.04 per image (1024x1024, standard)
    DALLE3_HD_1024 = 0.080        # $0.08 per image (1024x1024, HD)

    @staticmethod
    def calculate_wireframe_cost(
        num_stories: int,
        quality: str = "standard"
    ) -> dict:
        """
        Расчет стоимости генерации wireframes

        Args:
            num_stories: Количество историй
            quality: standard или hd

        Returns:
            Dict с детализацией стоимости
        """
        # Примерно 500 tokens на UI description
        gpt4_tokens = num_stories * 500
        gpt4_cost = (gpt4_tokens / 1000) * (
            AIServiceCost.GPT4_INPUT_COST + AIServiceCost.GPT4_OUTPUT_COST
        )

        # DALL-E стоимость
        dalle_cost_per_image = (
            AIServiceCost.DALLE3_HD_1024
            if quality == "hd"
            else AIServiceCost.DALLE3_STANDARD_1024
        )
        dalle_cost = num_stories * dalle_cost_per_image

        total_cost = gpt4_cost + dalle_cost

        return {
            "num_stories": num_stories,
            "gpt4_cost": round(gpt4_cost, 4),
            "dalle_cost": round(dalle_cost, 4),
            "total_cost": round(total_cost, 4),
            "cost_per_wireframe": round(total_cost / num_stories, 4)
        }


# Example usage
if __name__ == "__main__":
    # Calculate cost for 5 wireframes
    cost = AIServiceCost.calculate_wireframe_cost(5, "standard")

    print("💰 Wireframe Generation Cost Estimate:")
    print(f"   Stories: {cost['num_stories']}")
    print(f"   GPT-4 (descriptions): ${cost['gpt4_cost']}")
    print(f"   DALL-E 3 (images): ${cost['dalle_cost']}")
    print(f"   Total: ${cost['total_cost']}")
    print(f"   Per wireframe: ${cost['cost_per_wireframe']}")

    # Output:
    # 💰 Wireframe Generation Cost Estimate:
    #    Stories: 5
    #    GPT-4 (descriptions): $0.0225
    #    DALL-E 3 (images): $0.2
    #    Total: $0.2225
    #    Per wireframe: $0.0445
```

---

## 3.3. Supervisor для Workers (Production)

Для production нужен process manager для автоматического рестарта workers.

### 3.3.1. Systemd Service Files (Linux)

Создайте `/etc/systemd/system/usm-map-worker.service`:

```ini
[Unit]
Description=USM Map Generation Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/usm-service/backend
Environment="PATH=/var/www/usm-service/backend/venv/bin"
ExecStart=/var/www/usm-service/backend/venv/bin/python workers/map_worker.py

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/usm/map-worker.log
StandardError=append:/var/log/usm/map-worker-error.log

[Install]
WantedBy=multi-user.target
```

Создайте `/etc/systemd/system/usm-wireframe-worker.service`:

```ini
[Unit]
Description=USM Wireframe Generation Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/usm-service/backend
Environment="PATH=/var/www/usm-service/backend/venv/bin"
ExecStart=/var/www/usm-service/backend/venv/bin/python workers/wireframe_worker.py

Restart=always
RestartSec=10

StandardOutput=append:/var/log/usm/wireframe-worker.log
StandardError=append:/var/log/usm/wireframe-worker-error.log

[Install]
WantedBy=multi-user.target
```

**Управление:**

```bash
# Enable services
sudo systemctl enable usm-map-worker
sudo systemctl enable usm-wireframe-worker

# Start
sudo systemctl start usm-map-worker
sudo systemctl start usm-wireframe-worker

# Status
sudo systemctl status usm-map-worker
sudo systemctl status usm-wireframe-worker

# Logs
sudo journalctl -u usm-map-worker -f
sudo journalctl -u usm-wireframe-worker -f

# Stop
sudo systemctl stop usm-map-worker
sudo systemctl stop usm-wireframe-worker

# Restart
sudo systemctl restart usm-map-worker
sudo systemctl restart usm-wireframe-worker
```

### 3.3.2. Supervisor (Alternative)

Установка:
```bash
pip install supervisor
```

Конфигурация `supervisord.conf`:

```ini
[supervisord]
nodaemon=false
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:usm-map-worker]
command=/var/www/usm-service/backend/venv/bin/python workers/map_worker.py
directory=/var/www/usm-service/backend
user=www-data
autostart=true
autorestart=true
startsecs=10
startretries=3
stdout_logfile=/var/log/usm/map-worker.log
stderr_logfile=/var/log/usm/map-worker-error.log

[program:usm-wireframe-worker]
command=/var/www/usm-service/backend/venv/bin/python workers/wireframe_worker.py
directory=/var/www/usm-service/backend
user=www-data
autostart=true
autorestart=true
startsecs=10
startretries=3
stdout_logfile=/var/log/usm/wireframe-worker.log
stderr_logfile=/var/log/usm/wireframe-worker-error.log
```

**Управление:**

```bash
# Start supervisor
supervisord -c supervisord.conf

# Control workers
supervisorctl start usm-map-worker
supervisorctl start usm-wireframe-worker
supervisorctl status
supervisorctl restart all
supervisorctl stop all
```

---

## 3.4. Масштабирование Workers

### 3.4.1. Запуск нескольких экземпляров

RabbitMQ автоматически распределяет сообщения между workers (Competing Consumers Pattern).

**Terminal 1:**
```bash
python workers/map_worker.py
```

**Terminal 2:**
```bash
python workers/map_worker.py
```

**Terminal 3:**
```bash
python workers/map_worker.py
```

Теперь 3 worker'а будут обрабатывать сообщения параллельно!

### 3.4.2. Docker Compose для масштабирования

```yaml
# docker-compose.workers.yml
version: '3.8'

services:
  map-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    environment:
      - WORKER_TYPE=map
      - RABBITMQ_URL=${RABBITMQ_URL}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - rabbitmq
    restart: unless-stopped
    deploy:
      replicas: 3  # 3 экземпляра

  wireframe-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    environment:
      - WORKER_TYPE=wireframe
      - RABBITMQ_URL=${RABBITMQ_URL}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME}
      - CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY}
      - CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET}
    depends_on:
      - rabbitmq
    restart: unless-stopped
    deploy:
      replicas: 2  # 2 экземпляра
```

Запуск:
```bash
docker-compose -f docker-compose.workers.yml up --scale map-worker=3 --scale wireframe-worker=2
```

---

# Phase 4: Frontend Integration

## 4.1. Backend API Endpoints

### 4.1.1. Async Map Generation Endpoint

Обновите `backend/api/projects.py` для добавления async endpoint:

```python
# backend/api/projects.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime

from utils.database import get_db
from services.rabbitmq_service import publish_ai_map_generation
from services.job_service import JobService, get_job_service
from schemas import ProjectCreateAsync, JobStatusResponse
from utils.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/generate-async", response_model=JobStatusResponse)
async def create_project_async(
    request: ProjectCreateAsync,
    current_user = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service)
):
    """
    Асинхронная генерация User Story Map через RabbitMQ

    Returns:
        JobStatusResponse с job_id для отслеживания статуса
    """
    try:
        # Generate unique job ID
        job_id = f"map-{uuid.uuid4()}"

        # Create initial job record in Redis
        await job_service.create_job(
            job_id=job_id,
            job_type="map_generation",
            user_id=current_user.id,
            metadata={
                "requirements_length": len(request.requirements_text),
                "use_enhancement": request.use_enhancement,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # Publish message to RabbitMQ
        await publish_ai_map_generation(
            job_id=job_id,
            user_id=current_user.id,
            requirements_text=request.requirements_text,
            use_enhancement=request.use_enhancement,
            priority=request.priority or 5
        )

        return JobStatusResponse(
            job_id=job_id,
            status="pending",
            message="Map generation request queued successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue map generation: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    current_user = Depends(get_current_user)
):
    """
    Получение статуса асинхронной задачи

    Statuses:
    - pending: В очереди
    - processing: Обрабатывается worker'ом
    - completed: Успешно завершено
    - failed: Ошибка
    """
    try:
        job_data = await job_service.get_job_status(job_id)

        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Verify user owns this job
        if job_data.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return JobStatusResponse(**job_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )
```

### 4.1.2. Wireframe Generation Endpoint

Создайте `backend/api/wireframes.py`:

```python
# backend/api/wireframes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from utils.database import get_db
from services.rabbitmq_service import publish_wireframe_generation
from services.job_service import JobService, get_job_service
from schemas import WireframeGenerateRequest, JobStatusResponse
from utils.auth import get_current_user
from models import UserStory, Project

router = APIRouter(prefix="/wireframes", tags=["Wireframes"])


@router.post("/generate", response_model=JobStatusResponse)
async def generate_wireframes(
    request: WireframeGenerateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    job_service: JobService = Depends(get_job_service)
):
    """
    Генерация wireframes для выбранных User Stories

    Args:
        request:
            - project_id: ID проекта
            - story_ids: Список ID историй (max 10)
            - style: low-fidelity | high-fidelity | component
            - platform: web | mobile | desktop
    """
    try:
        # Validate project ownership
        project = db.query(Project).filter(
            Project.id == request.project_id,
            Project.user_id == current_user.id
        ).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )

        # Validate story IDs
        stories = db.query(UserStory).filter(
            UserStory.id.in_(request.story_ids)
        ).all()

        if len(stories) != len(request.story_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some story IDs are invalid"
            )

        # Limit stories per request
        max_stories = 10
        if len(request.story_ids) > max_stories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_stories} stories per request"
            )

        # Generate job ID
        job_id = f"wireframe-{uuid.uuid4()}"

        # Create job in Redis
        await job_service.create_job(
            job_id=job_id,
            job_type="wireframe_generation",
            user_id=current_user.id,
            metadata={
                "project_id": request.project_id,
                "story_count": len(request.story_ids),
                "style": request.style,
                "platform": request.platform
            }
        )

        # Publish to RabbitMQ
        await publish_wireframe_generation(
            job_id=job_id,
            user_id=current_user.id,
            project_id=request.project_id,
            story_ids=request.story_ids,
            style=request.style,
            platform=request.platform,
            priority=request.priority or 5
        )

        return JobStatusResponse(
            job_id=job_id,
            status="pending",
            message=f"Wireframe generation queued for {len(request.story_ids)} stories"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue wireframe generation: {str(e)}"
        )


@router.get("/jobs/{job_id}/wireframes")
async def get_wireframes(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    current_user = Depends(get_current_user)
):
    """
    Получение сгенерированных wireframes
    """
    try:
        job_data = await job_service.get_job_status(job_id)

        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Verify ownership
        if job_data.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        if job_data.get("status") != "completed":
            return {
                "status": job_data.get("status"),
                "message": "Wireframes are still being generated",
                "wireframes": []
            }

        wireframes = job_data.get("result", {}).get("wireframes", [])

        return {
            "status": "completed",
            "wireframes": wireframes,
            "total_count": len(wireframes),
            "successful": len([w for w in wireframes if "error" not in w]),
            "failed": len([w for w in wireframes if "error" in w])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

### 4.1.3. Pydantic Schemas

Обновите `backend/schemas.py`:

```python
# backend/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ProjectCreateAsync(BaseModel):
    """Request для async генерации проекта"""
    requirements_text: str = Field(..., min_length=10, max_length=50000)
    use_enhancement: bool = True
    priority: Optional[int] = Field(5, ge=0, le=10)


class WireframeGenerateRequest(BaseModel):
    """Request для генерации wireframes"""
    project_id: int
    story_ids: List[int] = Field(..., min_items=1, max_items=10)
    style: str = Field("low-fidelity", pattern="^(low-fidelity|high-fidelity|component)$")
    platform: str = Field("web", pattern="^(web|mobile|desktop)$")
    priority: Optional[int] = Field(5, ge=0, le=10)


class JobStatusResponse(BaseModel):
    """Response с статусом задачи"""
    job_id: str
    status: str  # pending | processing | completed | failed
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    progress: Optional[str] = None  # "3/10" для прогресса
```

### 4.1.4. WebSocket Server для Real-time Updates

Создайте `backend/api/websocket.py`:

```python
# backend/api/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import asyncio
import logging
import json

from services.job_service import JobService, get_job_service
from utils.auth import verify_websocket_token

router = APIRouter()
logger = logging.getLogger(__name__)

# Active WebSocket connections: {user_id: Set[WebSocket]}
active_connections: Dict[int, Set[WebSocket]] = {}


class ConnectionManager:
    """Менеджер WebSocket соединений"""

    @staticmethod
    async def connect(user_id: int, websocket: WebSocket):
        """Добавить соединение"""
        await websocket.accept()

        if user_id not in active_connections:
            active_connections[user_id] = set()

        active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user_id={user_id}, total={len(active_connections[user_id])}")

    @staticmethod
    async def disconnect(user_id: int, websocket: WebSocket):
        """Удалить соединение"""
        if user_id in active_connections:
            active_connections[user_id].discard(websocket)

            if not active_connections[user_id]:
                del active_connections[user_id]

        logger.info(f"WebSocket disconnected: user_id={user_id}")

    @staticmethod
    async def send_to_user(user_id: int, message: dict):
        """Отправить сообщение всем соединениям пользователя"""
        if user_id not in active_connections:
            return

        disconnected = set()

        for websocket in active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.add(websocket)

        # Remove disconnected sockets
        for ws in disconnected:
            active_connections[user_id].discard(ws)


@router.websocket("/ws/jobs")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    job_service: JobService = Depends(get_job_service)
):
    """
    WebSocket endpoint для получения job updates в реальном времени

    URL: ws://localhost:8000/ws/jobs?token=<JWT_TOKEN>

    Messages:
    Client -> Server:
    {
        "action": "subscribe",
        "job_id": "map-uuid-123"
    }

    Server -> Client:
    {
        "type": "job_update",
        "job_id": "map-uuid-123",
        "status": "processing",
        "progress": "3/10",
        "result": {...}
    }
    """
    try:
        # Verify JWT token
        user_data = await verify_websocket_token(token)
        user_id = user_data.get("user_id")

        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Connect
        await ConnectionManager.connect(user_id, websocket)

        # Subscribe to job updates
        subscribed_jobs = set()

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "subscribe":
                    job_id = data.get("job_id")

                    if job_id:
                        subscribed_jobs.add(job_id)
                        logger.info(f"User {user_id} subscribed to job {job_id}")

                        # Send current status
                        job_data = await job_service.get_job_status(job_id)

                        if job_data and job_data.get("user_id") == user_id:
                            await websocket.send_json({
                                "type": "job_update",
                                "job_id": job_id,
                                **job_data
                            })

                elif action == "unsubscribe":
                    job_id = data.get("job_id")
                    subscribed_jobs.discard(job_id)
                    logger.info(f"User {user_id} unsubscribed from job {job_id}")

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally: user_id={user_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

    finally:
        if 'user_id' in locals():
            await ConnectionManager.disconnect(user_id, websocket)


# Background task to broadcast job updates
async def broadcast_job_updates(job_service: JobService):
    """
    Периодически проверяет обновления jobs и отправляет их через WebSocket

    АЛЬТЕРНАТИВА: Worker может публиковать события в Redis Pub/Sub,
    и этот task подписан на эти события.
    """
    while True:
        try:
            # Get all active jobs (from Redis)
            # For each updated job, send to subscribed users
            # Implementation depends on Redis Pub/Sub or polling strategy

            await asyncio.sleep(2)  # Poll every 2 seconds

        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await asyncio.sleep(5)
```

### 4.1.5. Регистрация роутов

Обновите `backend/main.py`:

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import projects, wireframes, websocket
from config import settings

app = FastAPI(title="USM Service API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(wireframes.router)
app.include_router(websocket.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

---

## 4.2. Frontend Integration

### 4.2.1. API Client Updates

Обновите `frontend/src/api.js`:

```javascript
// frontend/src/api.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ==========================================
// Async Map Generation
// ==========================================

/**
 * Create User Story Map asynchronously via RabbitMQ
 * @param {string} requirementsText - Requirements text
 * @param {boolean} useEnhancement - Use two-stage AI processing
 * @param {number} priority - Message priority (0-10)
 * @returns {Promise<{job_id: string, status: string}>}
 */
export const createProjectAsync = async (requirementsText, useEnhancement = true, priority = 5) => {
  const response = await api.post('/projects/generate-async', {
    requirements_text: requirementsText,
    use_enhancement: useEnhancement,
    priority,
  });
  return response.data;
};

/**
 * Get job status
 * @param {string} jobId
 * @returns {Promise<JobStatusResponse>}
 */
export const getJobStatus = async (jobId) => {
  const response = await api.get(`/projects/jobs/${jobId}`);
  return response.data;
};

// ==========================================
// Wireframe Generation
// ==========================================

/**
 * Generate wireframes for User Stories
 * @param {number} projectId
 * @param {number[]} storyIds - Array of story IDs (max 10)
 * @param {string} style - "low-fidelity" | "high-fidelity" | "component"
 * @param {string} platform - "web" | "mobile" | "desktop"
 * @returns {Promise<{job_id: string}>}
 */
export const generateWireframes = async (projectId, storyIds, style = 'low-fidelity', platform = 'web') => {
  const response = await api.post('/wireframes/generate', {
    project_id: projectId,
    story_ids: storyIds,
    style,
    platform,
  });
  return response.data;
};

/**
 * Get generated wireframes
 * @param {string} jobId
 * @returns {Promise<{wireframes: Array}>}
 */
export const getWireframes = async (jobId) => {
  const response = await api.get(`/wireframes/jobs/${jobId}/wireframes`);
  return response.data;
};

// ==========================================
// WebSocket Connection
// ==========================================

/**
 * Connect to WebSocket for real-time job updates
 * @param {function} onMessage - Callback for messages
 * @returns {WebSocket}
 */
export const connectWebSocket = (onMessage) => {
  const token = localStorage.getItem('access_token');
  const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs?token=${token}`);

  ws.onopen = () => {
    console.log('✅ WebSocket connected');
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('WebSocket message parse error:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
  };

  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
  };

  return ws;
};

/**
 * Subscribe to job updates via WebSocket
 * @param {WebSocket} ws
 * @param {string} jobId
 */
export const subscribeToJob = (ws, jobId) => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      action: 'subscribe',
      job_id: jobId,
    }));
  }
};

export default api;
```

### 4.2.2. React Hook для Job Polling

Создайте `frontend/src/hooks/useJobStatus.js`:

```javascript
// frontend/src/hooks/useJobStatus.js
import { useState, useEffect, useRef } from 'react';
import { getJobStatus } from '../api';

/**
 * Hook для отслеживания статуса асинхронной задачи
 *
 * @param {string} jobId - Job ID
 * @param {number} pollingInterval - Интервал опроса (ms), default 3000
 * @returns {object} { status, result, error, progress, isLoading, isCompleted, isFailed }
 */
export const useJobStatus = (jobId, pollingInterval = 3000) => {
  const [status, setStatus] = useState('pending');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const intervalRef = useRef(null);

  useEffect(() => {
    if (!jobId) {
      setIsLoading(false);
      return;
    }

    const fetchStatus = async () => {
      try {
        const data = await getJobStatus(jobId);

        setStatus(data.status);
        setProgress(data.progress || null);

        if (data.status === 'completed') {
          setResult(data.result);
          setIsLoading(false);
          clearInterval(intervalRef.current);
        } else if (data.status === 'failed') {
          setError(data.error || 'Job failed');
          setIsLoading(false);
          clearInterval(intervalRef.current);
        }
      } catch (err) {
        console.error('Failed to fetch job status:', err);
        setError(err.message);
        setIsLoading(false);
        clearInterval(intervalRef.current);
      }
    };

    // Initial fetch
    fetchStatus();

    // Start polling
    intervalRef.current = setInterval(fetchStatus, pollingInterval);

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [jobId, pollingInterval]);

  return {
    status,
    result,
    error,
    progress,
    isLoading,
    isCompleted: status === 'completed',
    isFailed: status === 'failed',
  };
};
```

### 4.2.3. React Component для Async Map Generation

Создайте `frontend/src/components/AsyncMapGenerator.jsx`:

```jsx
// frontend/src/components/AsyncMapGenerator.jsx
import React, { useState } from 'react';
import { createProjectAsync } from '../api';
import { useJobStatus } from '../hooks/useJobStatus';
import { useNavigate } from 'react-router-dom';
import './AsyncMapGenerator.css';

export const AsyncMapGenerator = () => {
  const [requirements, setRequirements] = useState('');
  const [useEnhancement, setUseEnhancement] = useState(true);
  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  // Poll job status
  const { status, result, error, progress, isCompleted, isFailed } = useJobStatus(jobId);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (requirements.length < 10) {
      alert('Requirements must be at least 10 characters');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await createProjectAsync(requirements, useEnhancement);
      setJobId(response.job_id);
      console.log('✅ Job queued:', response.job_id);
    } catch (err) {
      console.error('Failed to create project:', err);
      alert('Failed to create project: ' + err.message);
      setIsSubmitting(false);
    }
  };

  // Redirect when completed
  React.useEffect(() => {
    if (isCompleted && result?.project_id) {
      console.log('✅ Project created:', result.project_id);
      setTimeout(() => {
        navigate(`/projects/${result.project_id}`);
      }, 2000);
    }
  }, [isCompleted, result, navigate]);

  return (
    <div className="async-map-generator">
      <h2>Generate User Story Map (Async)</h2>

      {!jobId ? (
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="requirements">Project Requirements:</label>
            <textarea
              id="requirements"
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="Describe your project requirements..."
              rows={12}
              required
              minLength={10}
            />
          </div>

          <div className="form-group checkbox">
            <label>
              <input
                type="checkbox"
                checked={useEnhancement}
                onChange={(e) => setUseEnhancement(e.target.checked)}
              />
              Use AI Enhancement (Two-stage processing)
            </label>
          </div>

          <button type="submit" disabled={isSubmitting || requirements.length < 10}>
            {isSubmitting ? 'Submitting...' : 'Generate Map (Async)'}
          </button>
        </form>
      ) : (
        <div className="job-status">
          <h3>Job Status: {status}</h3>

          <div className={`status-badge status-${status}`}>
            {status.toUpperCase()}
          </div>

          {progress && (
            <div className="progress-info">
              <p>Progress: {progress}</p>
            </div>
          )}

          {status === 'pending' && (
            <div className="status-message">
              <p>⏳ Your request is queued and waiting for processing...</p>
              <div className="spinner"></div>
            </div>
          )}

          {status === 'processing' && (
            <div className="status-message">
              <p>🤖 AI is generating your User Story Map...</p>
              <div className="spinner"></div>
            </div>
          )}

          {isCompleted && (
            <div className="status-message success">
              <p>✅ Map generated successfully!</p>
              <p>Project ID: {result?.project_id}</p>
              <p>Activities: {result?.activities_count}</p>
              <p>Stories: {result?.stories_count}</p>
              <p>Processing time: {result?.processing_time}</p>
              <p>Redirecting to project...</p>
            </div>
          )}

          {isFailed && (
            <div className="status-message error">
              <p>❌ Generation failed</p>
              <p className="error-detail">{error}</p>
              <button onClick={() => {
                setJobId(null);
                setIsSubmitting(false);
              }}>
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

### 4.2.4. CSS для Async Component

Создайте `frontend/src/components/AsyncMapGenerator.css`:

```css
/* frontend/src/components/AsyncMapGenerator.css */
.async-map-generator {
  max-width: 800px;
  margin: 40px auto;
  padding: 30px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.async-map-generator h2 {
  margin-bottom: 24px;
  color: #333;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #555;
}

.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
  resize: vertical;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  font-weight: normal;
}

.form-group.checkbox input {
  margin-right: 8px;
}

button {
  padding: 12px 24px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s;
}

button:hover:not(:disabled) {
  background: #45a049;
}

button:disabled {
  background: #cccccc;
  cursor: not-allowed;
}

/* Job Status */
.job-status {
  text-align: center;
  padding: 40px 20px;
}

.status-badge {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 20px;
  font-weight: 600;
  margin: 20px 0;
  text-transform: uppercase;
}

.status-badge.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-badge.status-processing {
  background: #cfe2ff;
  color: #084298;
}

.status-badge.status-completed {
  background: #d1e7dd;
  color: #0f5132;
}

.status-badge.status-failed {
  background: #f8d7da;
  color: #842029;
}

.status-message {
  margin-top: 30px;
  padding: 20px;
  border-radius: 8px;
  background: #f8f9fa;
}

.status-message.success {
  background: #d1e7dd;
  color: #0f5132;
}

.status-message.error {
  background: #f8d7da;
  color: #842029;
}

.error-detail {
  margin: 10px 0;
  padding: 10px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
}

/* Spinner */
.spinner {
  margin: 20px auto;
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

---

## 4.3. Wireframe Generator Component

### 4.3.1. React Component

Создайте `frontend/src/components/WireframeGenerator.jsx`:

```jsx
// frontend/src/components/WireframeGenerator.jsx
import React, { useState, useEffect } from 'react';
import { generateWireframes, getWireframes } from '../api';
import { useJobStatus } from '../hooks/useJobStatus';
import './WireframeGenerator.css';

/**
 * Компонент для генерации wireframes из User Stories
 *
 * Props:
 * @param {number} projectId - ID проекта
 * @param {Array} stories - Массив User Stories для выбора
 */
export const WireframeGenerator = ({ projectId, stories }) => {
  const [selectedStories, setSelectedStories] = useState([]);
  const [style, setStyle] = useState('low-fidelity');
  const [platform, setPlatform] = useState('web');
  const [jobId, setJobId] = useState(null);
  const [wireframes, setWireframes] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { status, result, error, progress, isCompleted, isFailed } = useJobStatus(jobId);

  const handleStoryToggle = (storyId) => {
    setSelectedStories((prev) =>
      prev.includes(storyId)
        ? prev.filter((id) => id !== storyId)
        : [...prev, storyId]
    );
  };

  const handleSelectAll = () => {
    if (selectedStories.length === stories.length) {
      setSelectedStories([]);
    } else {
      setSelectedStories(stories.slice(0, 10).map((s) => s.id));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (selectedStories.length === 0) {
      alert('Please select at least one story');
      return;
    }

    if (selectedStories.length > 10) {
      alert('Maximum 10 stories per request');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await generateWireframes(projectId, selectedStories, style, platform);
      setJobId(response.job_id);
      console.log('✅ Wireframe job queued:', response.job_id);
    } catch (err) {
      console.error('Failed to generate wireframes:', err);
      alert('Failed to generate wireframes: ' + err.message);
      setIsSubmitting(false);
    }
  };

  // Fetch wireframes when completed
  useEffect(() => {
    if (isCompleted && jobId) {
      const fetchWireframes = async () => {
        try {
          const data = await getWireframes(jobId);
          setWireframes(data.wireframes || []);
        } catch (err) {
          console.error('Failed to fetch wireframes:', err);
        }
      };

      fetchWireframes();
    }
  }, [isCompleted, jobId]);

  return (
    <div className="wireframe-generator">
      <h2>🎨 Generate Wireframes</h2>

      {!jobId ? (
        <form onSubmit={handleSubmit}>
          {/* Story Selection */}
          <div className="form-section">
            <h3>Select Stories (max 10)</h3>

            <button type="button" onClick={handleSelectAll} className="btn-secondary">
              {selectedStories.length === stories.length ? 'Deselect All' : 'Select All'}
            </button>

            <div className="story-list">
              {stories.map((story) => (
                <label key={story.id} className="story-item">
                  <input
                    type="checkbox"
                    checked={selectedStories.includes(story.id)}
                    onChange={() => handleStoryToggle(story.id)}
                    disabled={
                      !selectedStories.includes(story.id) && selectedStories.length >= 10
                    }
                  />
                  <span className="story-title">{story.title}</span>
                  <span className="story-priority">{story.priority}</span>
                </label>
              ))}
            </div>

            <p className="selection-count">
              Selected: {selectedStories.length} / {Math.min(stories.length, 10)}
            </p>
          </div>

          {/* Style Selection */}
          <div className="form-section">
            <h3>Wireframe Style</h3>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  name="style"
                  value="low-fidelity"
                  checked={style === 'low-fidelity'}
                  onChange={(e) => setStyle(e.target.value)}
                />
                Low-Fidelity (Simple wireframe sketch)
              </label>
              <label>
                <input
                  type="radio"
                  name="style"
                  value="high-fidelity"
                  checked={style === 'high-fidelity'}
                  onChange={(e) => setStyle(e.target.value)}
                />
                High-Fidelity (Detailed mockup)
              </label>
              <label>
                <input
                  type="radio"
                  name="style"
                  value="component"
                  checked={style === 'component'}
                  onChange={(e) => setStyle(e.target.value)}
                />
                Component (Isolated UI element)
              </label>
            </div>
          </div>

          {/* Platform Selection */}
          <div className="form-section">
            <h3>Platform</h3>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  name="platform"
                  value="web"
                  checked={platform === 'web'}
                  onChange={(e) => setPlatform(e.target.value)}
                />
                Web (Desktop browser)
              </label>
              <label>
                <input
                  type="radio"
                  name="platform"
                  value="mobile"
                  checked={platform === 'mobile'}
                  onChange={(e) => setPlatform(e.target.value)}
                />
                Mobile (iOS/Android app)
              </label>
              <label>
                <input
                  type="radio"
                  name="platform"
                  value="desktop"
                  checked={platform === 'desktop'}
                  onChange={(e) => setPlatform(e.target.value)}
                />
                Desktop (Native application)
              </label>
            </div>
          </div>

          {/* Cost Estimate */}
          <div className="cost-estimate">
            <p>
              💰 Estimated cost: ~${(selectedStories.length * 0.0445).toFixed(2)} USD
            </p>
            <small>(GPT-4 + DALL-E 3)</small>
          </div>

          <button type="submit" disabled={isSubmitting || selectedStories.length === 0}>
            {isSubmitting ? 'Generating...' : 'Generate Wireframes'}
          </button>
        </form>
      ) : (
        <div className="job-status">
          <h3>Generation Status</h3>

          <div className={`status-badge status-${status}`}>{status.toUpperCase()}</div>

          {progress && <p>Progress: {progress}</p>}

          {status === 'pending' && (
            <div className="status-message">
              <p>⏳ Queued for processing...</p>
              <div className="spinner"></div>
            </div>
          )}

          {status === 'processing' && (
            <div className="status-message">
              <p>🎨 Generating wireframes with GPT-4 + DALL-E 3...</p>
              <div className="spinner"></div>
            </div>
          )}

          {isCompleted && wireframes.length > 0 && (
            <div className="wireframes-grid">
              <h3>✅ Generated Wireframes</h3>

              {wireframes.map((wf, idx) => (
                <div key={idx} className="wireframe-card">
                  {wf.error ? (
                    <div className="wireframe-error">
                      <p>❌ Failed: {wf.story_title}</p>
                      <small>{wf.error}</small>
                    </div>
                  ) : (
                    <>
                      <h4>{wf.story_title}</h4>
                      <img src={wf.image_url} alt={wf.story_title} />
                      <p className="ui-description">{wf.ui_description}</p>
                      <div className="wireframe-meta">
                        <span>Style: {wf.style}</span>
                        <span>Platform: {wf.platform}</span>
                      </div>
                      <a href={wf.image_url} target="_blank" rel="noopener noreferrer">
                        Open Full Size
                      </a>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {isFailed && (
            <div className="status-message error">
              <p>❌ Generation failed</p>
              <p>{error}</p>
              <button onClick={() => {
                setJobId(null);
                setIsSubmitting(false);
              }}>
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

---

Продолжаю добавлять **Phase 5: Testing** в следующем сообщении...
# Phase 5: Testing

## 5.1. Unit Tests для Workers

### 5.1.1. Test Map Worker

Создайте `backend/tests/test_map_worker.py`:

```python
# backend/tests/test_map_worker.py
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from workers.map_worker import MapGenerationWorker
from models import Project, Activity, UserTask, UserStory


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    redis_client = AsyncMock()
    redis_client.ping = AsyncMock(return_value=True)
    return redis_client


@pytest.fixture
def mock_job_service(mock_redis_client):
    """Mock JobService"""
    from services.job_service import JobService
    return JobService(mock_redis_client)


@pytest.fixture
def worker(mock_redis_client, mock_job_service):
    """Create MapGenerationWorker instance"""
    worker = MapGenerationWorker()
    worker.redis_client = mock_redis_client
    worker.job_service = mock_job_service
    return worker


@pytest.fixture
def sample_message():
    """Sample RabbitMQ message"""
    return {
        "job_id": "test-job-123",
        "user_id": 1,
        "requirements_text": "Sample requirements for testing",
        "use_enhancement": False
    }


@pytest.fixture
def sample_ai_data():
    """Sample AI generation response"""
    return {
        "productName": "Test Product",
        "map": [
            {
                "activity": "User Management",
                "tasks": [
                    {
                        "taskTitle": "User Registration",
                        "stories": [
                            {
                                "title": "As a user, I can create an account",
                                "description": "User registration flow",
                                "priority": "MVP",
                                "acceptanceCriteria": [
                                    "Email validation works",
                                    "Password strength check"
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


class TestMapGenerationWorker:
    """Tests for MapGenerationWorker"""

    @pytest.mark.asyncio
    async def test_process_message_success(
        self,
        worker,
        sample_message,
        sample_ai_data,
        mock_job_service
    ):
        """Test successful message processing"""
        with patch('workers.map_worker.generate_ai_map', return_value=sample_ai_data), \
             patch('workers.map_worker.SessionLocal') as mock_session:
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_session.return_value = mock_db
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.flush = Mock()
            mock_db.commit = Mock()
            mock_db.close = Mock()
            mock_db.refresh = Mock()
            
            # Process message
            await worker.process_message(sample_message)
            
            # Assertions
            assert worker.processed_count == 1
            assert worker.failed_count == 0
            
            # Verify database operations
            mock_db.add.assert_called()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_ai_failure(
        self,
        worker,
        sample_message,
        mock_job_service
    ):
        """Test message processing with AI generation failure"""
        with patch('workers.map_worker.generate_ai_map', side_effect=Exception("AI API Error")), \
             patch('workers.map_worker.SessionLocal') as mock_session:
            
            mock_db = Mock(spec=Session)
            mock_session.return_value = mock_db
            mock_db.close = Mock()
            
            # Should raise exception
            with pytest.raises(Exception) as exc_info:
                await worker.process_message(sample_message)
            
            assert "AI API Error" in str(exc_info.value)
            assert worker.failed_count == 1
            
            # Verify database cleanup
            mock_db.close.assert_called_once()

    def test_save_project_to_db(self, worker, sample_ai_data):
        """Test project saving to database"""
        mock_db = Mock(spec=Session)
        
        # Mock project creation
        mock_project = Mock(spec=Project)
        mock_project.id = 123
        
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Save project
        result = worker._save_project_to_db(
            db=mock_db,
            user_id=1,
            ai_data=sample_ai_data,
            requirements_text="Test requirements"
        )
        
        # Assertions
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()
        assert isinstance(result, Mock)

    @pytest.mark.asyncio
    async def test_enhancement_flow(
        self,
        worker,
        sample_message,
        sample_ai_data
    ):
        """Test with enhancement enabled"""
        message_with_enhancement = {
            **sample_message,
            "use_enhancement": True
        }
        
        mock_enhancement = {
            "enhanced_text": "Enhanced requirements",
            "confidence": 0.9,
            "added_aspects": ["Security", "Performance"]
        }
        
        with patch('workers.map_worker.enhance_requirements', return_value=mock_enhancement), \
             patch('workers.map_worker.generate_ai_map', return_value=sample_ai_data), \
             patch('workers.map_worker.SessionLocal') as mock_session:
            
            mock_db = Mock(spec=Session)
            mock_session.return_value = mock_db
            mock_db.add = Mock()
            mock_db.flush = Mock()
            mock_db.commit = Mock()
            mock_db.close = Mock()
            mock_db.refresh = Mock()
            
            await worker.process_message(message_with_enhancement)
            
            assert worker.processed_count == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 5.1.2. Test Wireframe Worker

Создайте `backend/tests/test_wireframe_worker.py`:

```python
# backend/tests/test_wireframe_worker.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from workers.wireframe_worker import WireframeGenerationWorker
from models import UserStory, UserTask, Activity


@pytest.fixture
def worker():
    """Create WireframeGenerationWorker instance"""
    worker = WireframeGenerationWorker()
    worker.redis_client = AsyncMock()
    worker.openai_client = Mock()
    worker.cloudinary_configured = False
    return worker


@pytest.fixture
def sample_wireframe_message():
    """Sample wireframe generation message"""
    return {
        "job_id": "wireframe-test-123",
        "user_id": 1,
        "project_id": 10,
        "story_ids": [1, 2, 3],
        "style": "low-fidelity",
        "platform": "web"
    }


@pytest.fixture
def mock_story():
    """Mock UserStory"""
    story = Mock(spec=UserStory)
    story.id = 1
    story.title = "User can login"
    story.description = "Login functionality"
    story.acceptance_criteria = ["Validate email", "Check password"]
    story.task_id = 1
    return story


@pytest.fixture
def mock_task():
    """Mock UserTask"""
    task = Mock(spec=UserTask)
    task.id = 1
    task.title = "Authentication"
    task.activity_id = 1
    return task


@pytest.fixture
def mock_activity():
    """Mock Activity"""
    activity = Mock(spec=Activity)
    activity.id = 1
    activity.title = "User Management"
    activity.project_id = 10
    return activity


class TestWireframeGenerationWorker:
    """Tests for WireframeGenerationWorker"""

    @pytest.mark.asyncio
    async def test_generate_wireframe_for_story(
        self,
        worker,
        mock_story,
        mock_task,
        mock_activity
    ):
        """Test wireframe generation for a single story"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_task,
            mock_activity
        ]
        
        # Mock OpenAI responses
        mock_gpt_response = Mock()
        mock_gpt_response.choices = [Mock()]
        mock_gpt_response.choices[0].message.content = "UI description for login screen"
        
        mock_dalle_response = Mock()
        mock_dalle_response.data = [Mock()]
        mock_dalle_response.data[0].url = "https://example.com/wireframe.png"
        
        worker.openai_client.chat.completions.create = Mock(return_value=mock_gpt_response)
        worker.openai_client.images.generate = Mock(return_value=mock_dalle_response)
        
        # Generate wireframe
        result = await worker._generate_wireframe_for_story(
            story=mock_story,
            style="low-fidelity",
            platform="web",
            db=mock_db
        )
        
        # Assertions
        assert result["story_id"] == 1
        assert result["story_title"] == "User can login"
        assert "image_url" in result
        assert "ui_description" in result
        assert result["style"] == "low-fidelity"
        assert result["platform"] == "web"

    def test_build_ui_description_prompt(
        self,
        worker,
        mock_story,
        mock_task,
        mock_activity
    ):
        """Test UI description prompt building"""
        prompt = worker._build_ui_description_prompt(
            story=mock_story,
            task=mock_task,
            activity=mock_activity,
            style="high-fidelity",
            platform="mobile"
        )
        
        # Check prompt contains essential elements
        assert "User can login" in prompt
        assert "Login functionality" in prompt
        assert "Authentication" in prompt
        assert "User Management" in prompt
        assert "high-fidelity" in prompt
        assert "mobile" in prompt

    def test_build_image_prompt(self, worker):
        """Test DALL-E image prompt building"""
        ui_description = "Login screen with email field, password field, and submit button"
        
        prompt = worker._build_image_prompt(
            ui_description=ui_description,
            style="low-fidelity",
            platform="web"
        )
        
        # Check prompt structure
        assert "wireframe" in prompt.lower()
        assert ui_description in prompt
        assert "low-fidelity" in prompt or "wireframe" in prompt
        assert "web" in prompt or "browser" in prompt

    @pytest.mark.asyncio
    async def test_process_message_success(
        self,
        worker,
        sample_wireframe_message,
        mock_story
    ):
        """Test successful wireframe message processing"""
        with patch('workers.wireframe_worker.SessionLocal') as mock_session, \
             patch.object(worker, '_generate_wireframe_for_story', new_callable=AsyncMock) as mock_gen:
            
            mock_db = Mock()
            mock_session.return_value = mock_db
            
            # Mock database query
            mock_db.query.return_value.filter.return_value.all.return_value = [
                mock_story, mock_story, mock_story
            ]
            mock_db.close = Mock()
            
            # Mock wireframe generation
            mock_gen.return_value = {
                "story_id": 1,
                "story_title": "Test story",
                "image_url": "https://example.com/wf.png",
                "ui_description": "Test UI"
            }
            
            # Mock job service
            worker.job_service = AsyncMock()
            
            # Process message
            await worker.process_message(sample_wireframe_message)
            
            # Assertions
            assert worker.processed_count == 1
            assert worker.failed_count == 0
            mock_db.close.assert_called_once()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 5.2. Integration Tests

### 5.2.1. RabbitMQ Integration Test

Создайте `backend/tests/integration/test_rabbitmq_flow.py`:

```python
# backend/tests/integration/test_rabbitmq_flow.py
import pytest
import asyncio
from datetime import datetime

from services.rabbitmq_service import rabbitmq_service, publish_ai_map_generation
from services.job_service import JobService
import redis.asyncio as aioredis


@pytest.fixture
async def redis_client():
    """Real Redis client for integration tests"""
    client = await aioredis.from_url(
        "redis://localhost:6379/1",  # Test database
        encoding="utf-8",
        decode_responses=True
    )
    yield client
    await client.flushdb()  # Clean up
    await client.close()


@pytest.fixture
async def job_service(redis_client):
    """JobService with real Redis"""
    return JobService(redis_client)


class TestRabbitMQIntegration:
    """Integration tests for RabbitMQ flow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_publish_and_consume_message(self, job_service):
        """Test full message publishing and consuming flow"""
        job_id = f"integration-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Connect to RabbitMQ
        await rabbitmq_service.connect()
        
        try:
            # Create job in Redis
            await job_service.create_job(
                job_id=job_id,
                job_type="map_generation",
                user_id=999,
                metadata={"test": True}
            )
            
            # Publish message
            await publish_ai_map_generation(
                job_id=job_id,
                user_id=999,
                requirements_text="Integration test requirements",
                use_enhancement=False,
                priority=9
            )
            
            print(f"✅ Message published: {job_id}")
            
            # Check job status
            status = await job_service.get_job_status(job_id)
            assert status is not None
            assert status["status"] == "pending"
            assert status["user_id"] == 999
            
            print(f"✅ Job status verified: {status}")
            
        finally:
            await rabbitmq_service.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_topology(self):
        """Test queue topology setup"""
        await rabbitmq_service.connect()
        
        try:
            # Queues should exist
            assert rabbitmq_service.channel is not None
            assert rabbitmq_service.exchange is not None
            
            # Test publishing to different queues
            test_id = f"topology-test-{datetime.now().timestamp()}"
            
            # Map generation queue
            await rabbitmq_service.publish(
                routing_key="ai.map.generation",
                message_body={"test_id": test_id, "type": "map"},
                priority=5
            )
            
            # Wireframe generation queue
            await rabbitmq_service.publish(
                routing_key="ai.wireframe.generation",
                message_body={"test_id": test_id, "type": "wireframe"},
                priority=5
            )
            
            print("✅ Messages published to different queues")
            
        finally:
            await rabbitmq_service.disconnect()


# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
```

### 5.2.2. End-to-End Test

Создайте `backend/tests/e2e/test_async_map_generation.py`:

```python
# backend/tests/e2e/test_async_map_generation.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from utils.database import Base
from models import User, Project


# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(setup_database):
    """Create test user"""
    db = TestingSessionLocal()
    user = User(email="test@example.com", hashed_password="testpassword")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    
    yield user_id
    
    # Cleanup
    db = TestingSessionLocal()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers"""
    # Mock JWT token generation
    return {"Authorization": f"Bearer test-token-{test_user}"}


class TestAsyncMapGenerationE2E:
    """End-to-end tests for async map generation"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_full_async_flow(self, auth_headers):
        """Test complete async map generation flow"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Submit async map generation request
            response = await client.post(
                "/projects/generate-async",
                json={
                    "requirements_text": "E2E test project requirements",
                    "use_enhancement": False,
                    "priority": 7
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "job_id" in data
            assert data["status"] == "pending"
            
            job_id = data["job_id"]
            print(f"✅ Job created: {job_id}")
            
            # Step 2: Poll job status
            max_attempts = 30
            for i in range(max_attempts):
                await asyncio.sleep(2)
                
                status_response = await client.get(
                    f"/projects/jobs/{job_id}",
                    headers=auth_headers
                )
                
                assert status_response.status_code == 200
                status_data = status_response.json()
                
                print(f"   Attempt {i+1}: {status_data['status']}")
                
                if status_data["status"] == "completed":
                    assert "result" in status_data
                    assert "project_id" in status_data["result"]
                    print(f"✅ Project created: {status_data['result']['project_id']}")
                    break
                
                elif status_data["status"] == "failed":
                    pytest.fail(f"Job failed: {status_data.get('error')}")
                
            else:
                pytest.fail(f"Job did not complete after {max_attempts} attempts")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_wireframe_generation_flow(self, auth_headers, test_user):
        """Test wireframe generation E2E flow"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First, create a project with stories
            db = TestingSessionLocal()
            
            # Create sample project (simplified)
            project = Project(
                name="E2E Test Project",
                raw_requirements="Test",
                user_id=test_user
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            
            project_id = project.id
            db.close()
            
            # Generate wireframes
            response = await client.post(
                "/wireframes/generate",
                json={
                    "project_id": project_id,
                    "story_ids": [1, 2],
                    "style": "low-fidelity",
                    "platform": "web"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "job_id" in data
            job_id = data["job_id"]
            
            print(f"✅ Wireframe job created: {job_id}")


# Run E2E tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
```

---

## 5.3. Запуск тестов

### 5.3.1. Конфигурация pytest

Создайте `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (fast)
    integration: Integration tests (require Redis/RabbitMQ)
    e2e: End-to-end tests (full stack)
    slow: Slow tests
asyncio_mode = auto
```

### 5.3.2. Зависимости для тестирования

Обновите `backend/requirements.txt`:

```txt
# Testing dependencies
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx==0.25.2
faker==20.1.0
```

### 5.3.3. Команды запуска

```bash
# All unit tests
cd backend
pytest tests/ -v -m unit

# Integration tests (требуют запущенных Redis и RabbitMQ)
pytest tests/ -v -m integration

# E2E tests (требуют полный стек)
pytest tests/ -v -m e2e

# Все тесты с coverage
pytest tests/ -v --cov=. --cov-report=html

# Конкретный тест
pytest tests/test_map_worker.py::TestMapGenerationWorker::test_process_message_success -v
```

---

# Phase 6: Production Deployment

## 6.1. Environment Variables

### 6.1.1. Production .env template

Создайте `backend/.env.production.template`:

```bash
# ============================================
# Production Environment Variables Template
# ============================================

# Environment
ENVIRONMENT=production

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://user:password@db.supabase.co:5432/postgres

# Redis (Upstash)
REDIS_URL=rediss://default:password@redis.upstash.io:6379

# RabbitMQ (CloudAMQP)
CLOUDAMQP_URL=amqps://user:pass@hawk-01.rmq.cloudamqp.com/vhost
RABBITMQ_ENABLED=true

# AI API Keys
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
PERPLEXITY_API_KEY=pplx-...
API_PROVIDER=groq
API_MODEL=llama-3.3-70b-versatile

# Cloudinary (for wireframes)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=123456789
CLOUDINARY_API_SECRET=secret

# JWT Security
JWT_SECRET_KEY=<generate-secure-random-string-min-32-chars>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://your-domain.com

# Logging
LOG_LEVEL=INFO

# Sentry (optional)
SENTRY_DSN=https://...@sentry.io/...

# Wireframe Settings
WIREFRAME_DALLE_MODEL=dall-e-3
WIREFRAME_IMAGE_SIZE=1024x1024
WIREFRAME_IMAGE_QUALITY=standard
WIREFRAME_MAX_STORIES=10
```

### 6.1.2. Генерация JWT Secret

```bash
# Generate secure JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Output example:
# Xk7mP9vN2qR5tY8wZ0aB3cD6eF9hJ1kL4mN7pQ0sT3uV6xY9zA2bC5dE8fG1hI4jK7
```

---

## 6.2. Deployment на Render.com

### 6.2.1. Backend API Deployment

Создайте `render.yaml`:

```yaml
# render.yaml
services:
  # FastAPI Backend
  - type: web
    name: usm-backend
    env: python
    region: oregon
    plan: starter  # Free tier
    buildCommand: "cd backend && pip install -r requirements.txt"
    startCommand: "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        fromDatabase:
          name: usm-db
          property: connectionString
      - key: REDIS_URL
        sync: false  # Set manually
      - key: CLOUDAMQP_URL
        sync: false  # Set manually
      - key: RABBITMQ_ENABLED
        value: true
      - key: OPENAI_API_KEY
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: ALLOWED_ORIGINS
        value: https://usm-frontend.vercel.app
    healthCheckPath: /health

  # Map Generation Worker
  - type: worker
    name: usm-map-worker
    env: python
    region: oregon
    plan: starter
    buildCommand: "cd backend && pip install -r requirements.txt"
    startCommand: "cd backend && python workers/map_worker.py"
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        fromDatabase:
          name: usm-db
          property: connectionString
      - key: REDIS_URL
        sync: false
      - key: CLOUDAMQP_URL
        sync: false
      - key: RABBITMQ_ENABLED
        value: true
      - key: OPENAI_API_KEY
        sync: false
      - key: GROQ_API_KEY
        sync: false

  # Wireframe Generation Worker
  - type: worker
    name: usm-wireframe-worker
    env: python
    region: oregon
    plan: starter
    buildCommand: "cd backend && pip install -r requirements.txt"
    startCommand: "cd backend && python workers/wireframe_worker.py"
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        fromDatabase:
          name: usm-db
          property: connectionString
      - key: REDIS_URL
        sync: false
      - key: CLOUDAMQP_URL
        sync: false
      - key: RABBITMQ_ENABLED
        value: true
      - key: OPENAI_API_KEY
        sync: false
      - key: CLOUDINARY_CLOUD_NAME
        sync: false
      - key: CLOUDINARY_API_KEY
        sync: false
      - key: CLOUDINARY_API_SECRET
        sync: false

databases:
  - name: usm-db
    plan: starter  # Free PostgreSQL
    region: oregon
```

### 6.2.2. Пошаговая инструкция Render

**Шаг 1: Подготовка репозитория**

```bash
# Убедитесь, что все изменения закоммичены
git add .
git commit -m "Add RabbitMQ integration with workers"
git push origin main
```

**Шаг 2: Создание Blueprint на Render**

1. Зайдите на https://render.com
2. Нажмите **New +** → **Blueprint**
3. Подключите ваш GitHub/GitLab репозиторий
4. Render автоматически найдет `render.yaml`
5. Нажмите **Apply**

**Шаг 3: Настройка Environment Variables**

Для каждого service установите секреты:

```bash
# Backend API
REDIS_URL=rediss://default:xxx@redis.upstash.io:6379
CLOUDAMQP_URL=amqps://xxx@hawk-01.rmq.cloudamqp.com/xxx
OPENAI_API_KEY=sk-xxx
GROQ_API_KEY=gsk_xxx
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=123456
CLOUDINARY_API_SECRET=secret

# Workers - те же самые переменные
```

**Шаг 4: Проверка деплоя**

```bash
# Check backend health
curl https://usm-backend.onrender.com/health

# Expected: {"status": "ok"}
```

**Шаг 5: Мониторинг логов**

В Render Dashboard → Logs для каждого сервиса:

```
Backend API logs:
✅ RabbitMQ connected successfully
✅ Connected to Redis
INFO: Uvicorn running on http://0.0.0.0:10000

Map Worker logs:
🚀 Starting Map Generation Worker
✅ Connected to Redis
✅ RabbitMQ connected successfully
👀 Waiting for map generation requests...

Wireframe Worker logs:
🎨 Starting Wireframe Generation Worker
✅ Connected to Redis
✅ OpenAI client initialized
✅ Cloudinary configured
👀 Waiting for wireframe generation requests...
```

---

## 6.3. Frontend Deployment на Vercel

### 6.3.1. Vercel Configuration

Создайте `frontend/vercel.json`:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "vite",
  "env": {
    "VITE_API_URL": "https://usm-backend.onrender.com",
    "VITE_WS_URL": "wss://usm-backend.onrender.com"
  }
}
```

### 6.3.2. Деплой на Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
cd frontend
vercel --prod

# Set environment variables
vercel env add VITE_API_URL production
# Enter: https://usm-backend.onrender.com

vercel env add VITE_WS_URL production
# Enter: wss://usm-backend.onrender.com
```

**Альтернатива через Vercel Dashboard:**

1. Зайдите на https://vercel.com
2. Импортируйте проект из GitHub
3. Настройте Build settings:
   - Framework Preset: **Vite**
   - Root Directory: **frontend**
   - Build Command: **npm run build**
   - Output Directory: **dist**
4. Добавьте Environment Variables:
   - `VITE_API_URL`: `https://usm-backend.onrender.com`
   - `VITE_WS_URL`: `wss://usm-backend.onrender.com`
5. Deploy

---

## 6.4. CI/CD Pipeline

### 6.4.1. GitHub Actions Workflow

Создайте `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Backend Tests
  backend-test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:testpassword@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  # Frontend Tests
  frontend-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run linting
        run: |
          cd frontend
          npm run lint
      
      - name: Run tests
        run: |
          cd frontend
          npm run test
      
      - name: Build
        run: |
          cd frontend
          npm run build

  # Deploy to Render (on main branch)
  deploy:
    needs: [backend-test, frontend-test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Trigger Render Deploy
        env:
          RENDER_DEPLOY_HOOK: ${{ secrets.RENDER_DEPLOY_HOOK }}
        run: |
          curl -X POST $RENDER_DEPLOY_HOOK
```

### 6.4.2. Настройка Deploy Hook

**В Render Dashboard:**

1. Settings → Build & Deploy
2. Скопируйте **Deploy Hook URL**
3. Добавьте в GitHub Secrets как `RENDER_DEPLOY_HOOK`

**Автоматический деплой:**

Теперь каждый push в `main` будет:
1. ✅ Запускать тесты
2. ✅ Проверять линтинг
3. ✅ Деплоить на Render (если тесты прошли)

---

## 6.5. Database Migrations

### 6.5.1. Alembic Setup

```bash
cd backend
pip install alembic

# Initialize Alembic
alembic init alembic

# Edit alembic.ini
# sqlalchemy.url = postgresql://user:pass@host/db
```

### 6.5.2. Create Migration

```bash
# Auto-generate migration from models
alembic revision --autogenerate -m "Add RabbitMQ job tracking"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### 6.5.3. Production Migration Script

Создайте `backend/scripts/migrate.sh`:

```bash
#!/bin/bash
# Production migration script

set -e

echo "🔄 Running database migrations..."

cd /app/backend
alembic upgrade head

echo "✅ Migrations completed successfully"
```

Добавьте в `render.yaml`:

```yaml
services:
  - type: web
    name: usm-backend
    preDeployCommand: "cd backend && chmod +x scripts/migrate.sh && ./scripts/migrate.sh"
    # ... rest of config
```

---

## 6.6. Масштабирование Workers

### 6.6.1. Horizontal Scaling на Render

**Опция 1: Через Render Dashboard**

1. Workers → usm-map-worker → Settings
2. Scaling: Increase instance count
3. Save changes

**Опция 2: Через render.yaml**

```yaml
services:
  - type: worker
    name: usm-map-worker
    scaling:
      minInstances: 2
      maxInstances: 5
      targetMemoryPercent: 70
      targetCPUPercent: 80
```

### 6.6.2. Auto-scaling Strategy

```python
# backend/workers/autoscaler.py
"""
Auto-scaling logic based on queue depth

Monitors RabbitMQ queue length and adjusts worker count
"""
import asyncio
import aio_pika
from config import settings


async def get_queue_depth(queue_name: str) -> int:
    """Get current message count in queue"""
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.get_queue(queue_name)
    message_count = queue.declaration_result.message_count
    await connection.close()
    return message_count


async def monitor_queue():
    """Monitor queue and log metrics for scaling decisions"""
    while True:
        try:
            map_depth = await get_queue_depth("map_generation")
            wireframe_depth = await get_queue_depth("wireframe_generation")
            
            print(f"📊 Queue Depth - Map: {map_depth}, Wireframe: {wireframe_depth}")
            
            # Scaling recommendations
            if map_depth > 50:
                print("⚠️ RECOMMENDATION: Scale up map workers")
            elif map_depth < 5:
                print("ℹ️ RECOMMENDATION: Can scale down map workers")
            
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(monitor_queue())
```

---

# Phase 7: Monitoring & Troubleshooting

## 7.1. Logging Strategy

### 7.1.1. Structured Logging

Обновите logging configuration в `backend/config.py`:

```python
# backend/config.py
import logging
import sys
from datetime import datetime


def setup_logging():
    """Configure structured logging for production"""
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    json_formatter = logging.Formatter(
        fmt='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # Console handler (for Render logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    
    # File handler (for persistent logs)
    file_handler = logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Disable noisy loggers
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Call at startup
setup_logging()
```

### 7.1.2. Application Metrics

Создайте `backend/utils/metrics.py`:

```python
# backend/utils/metrics.py
"""
Application metrics collector

Tracks:
- Request counts
- Response times
- Worker performance
- Queue depths
- Error rates
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsCollector:
    """In-memory metrics collector (для простоты)"""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.worker_metrics = defaultdict(lambda: {
            "processed": 0,
            "failed": 0,
            "total_time": 0.0
        })
    
    def record_request(self, endpoint: str, method: str, status_code: int, response_time: float):
        """Record HTTP request"""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if status_code >= 500:
            self.error_count += 1
        
        logger.info(
            f"REQUEST | {method} {endpoint} | {status_code} | {response_time:.3f}s"
        )
    
    def record_worker_job(self, worker_type: str, success: bool, duration: float):
        """Record worker job completion"""
        metrics = self.worker_metrics[worker_type]
        
        if success:
            metrics["processed"] += 1
        else:
            metrics["failed"] += 1
        
        metrics["total_time"] += duration
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        return {
            "requests": {
                "total": self.request_count,
                "errors": self.error_count,
                "error_rate": f"{(self.error_count / max(self.request_count, 1)) * 100:.2f}%",
                "avg_response_time": f"{avg_response_time:.3f}s"
            },
            "workers": dict(self.worker_metrics)
        }
    
    def reset(self):
        """Reset metrics"""
        self.__init__()


# Global instance
metrics = MetricsCollector()


# Middleware для FastAPI
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware для сбора метрик HTTP запросов"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            response_time=duration
        )
        
        return response
```

Добавьте в `main.py`:

```python
# backend/main.py
from utils.metrics import MetricsMiddleware, metrics

app.add_middleware(MetricsMiddleware)

@app.get("/metrics")
async def get_metrics():
    """Endpoint для просмотра метрик"""
    return metrics.get_summary()
```

---

## 7.2. Health Checks

### 7.2.1. Comprehensive Health Check

Обновите `backend/main.py`:

```python
# backend/main.py
from fastapi import FastAPI, status
from typing import Dict
import asyncio

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict:
    """
    Comprehensive health check
    
    Checks:
    - API responsiveness
    - Database connection
    - Redis connection
    - RabbitMQ connection
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check Database
    try:
        from utils.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        import redis.asyncio as aioredis
        redis_client = await aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check RabbitMQ
    try:
        from services.rabbitmq_service import rabbitmq_service
        if rabbitmq_service.connection and not rabbitmq_service.connection.is_closed:
            health_status["checks"]["rabbitmq"] = "ok"
        else:
            health_status["checks"]["rabbitmq"] = "disconnected"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["rabbitmq"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Kubernetes liveness probe - проверяет, что приложение живо"""
    return {"status": "alive"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe():
    """Kubernetes readiness probe - проверяет готовность принимать трафик"""
    try:
        from utils.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "ready"}
    except:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Not ready")
```

---

## 7.3. Error Tracking с Sentry

### 7.3.1. Sentry Integration

```bash
pip install sentry-sdk[fastapi]
```

Обновите `backend/main.py`:

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% transaction sampling
        profiles_sample_rate=0.1,
    )
    logger.info("✅ Sentry initialized")
```

Добавьте в workers:

```python
# backend/workers/map_worker.py
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
    )
```

---

## 7.4. Monitoring Dashboard

### 7.4.1. RabbitMQ Management UI

CloudAMQP предоставляет встроенный management UI:

**URL:** https://customer.cloudamqp.com/instance

**Метрики:**
- Message rates (publish/deliver/ack)
- Queue depths
- Consumer utilization
- Connection count
- Memory usage

### 7.4.2. Simple Status Dashboard

Создайте `backend/api/admin.py`:

```python
# backend/api/admin.py
from fastapi import APIRouter, Depends
from typing import Dict
import aio_pika

from config import settings
from services.rabbitmq_service import rabbitmq_service
from utils.auth import admin_required

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def get_dashboard(current_user = Depends(admin_required)) -> Dict:
    """
    Admin dashboard with system status
    
    Requires admin role
    """
    dashboard = {
        "system": {
            "environment": settings.ENVIRONMENT,
            "rabbitmq_enabled": settings.RABBITMQ_ENABLED,
        },
        "queues": {},
        "workers": {}
    }
    
    # Get queue stats
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        
        for queue_name in ["map_generation", "wireframe_generation", "bulk_improve"]:
            try:
                queue = await channel.get_queue(queue_name)
                result = queue.declaration_result
                
                dashboard["queues"][queue_name] = {
                    "messages": result.message_count,
                    "consumers": result.consumer_count
                }
            except:
                dashboard["queues"][queue_name] = {"error": "Queue not found"}
        
        await connection.close()
        
    except Exception as e:
        dashboard["queues"]["error"] = str(e)
    
    return dashboard


@router.post("/queues/{queue_name}/purge")
async def purge_queue(
    queue_name: str,
    current_user = Depends(admin_required)
):
    """Очистить очередь (admin only)"""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        queue = await channel.get_queue(queue_name)
        await queue.purge()
        await connection.close()
        
        return {"message": f"Queue {queue_name} purged successfully"}
        
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 7.5. Common Errors & Solutions

### 7.5.1. Troubleshooting Guide

#### Error 1: RabbitMQ Connection Failed

**Симптомы:**
```
❌ RabbitMQ connection error: [Errno -2] Name or service not known
```

**Решения:**

1. **Проверьте URL:**
```bash
# Test connection
python3 -c "
import pika
params = pika.URLParameters('amqps://user:pass@host/vhost')
connection = pika.BlockingConnection(params)
print('✅ Connected')
connection.close()
"
```

2. **Проверьте CloudAMQP Dashboard:**
   - Instance running?
   - Connection limit не превышен?

3. **Firewall / Network:**
```bash
# Test connectivity
telnet hawk-01.rmq.cloudamqp.com 5671
```

4. **Environment Variable:**
```bash
# Verify in Render
echo $CLOUDAMQP_URL
```

---

#### Error 2: Worker Not Processing Messages

**Симптомы:**
```
Worker running, but messages stay in queue
```

**Решения:**

1. **Check Worker Logs:**
```bash
# Render Dashboard → Worker logs
# Look for:
✅ RabbitMQ connected successfully
👀 Waiting for map generation requests...
```

2. **Check Queue Binding:**
```python
# Test queue setup
python3 backend/scripts/test_queue_setup.py
```

3. **Check Consumer Acknowledgment:**
```python
# В worker коде, убедитесь что:
await rabbitmq_service.consume(
    queue_name="map_generation",
    callback=self.process_message  # ✅ Correct
)
```

4. **Dead Letter Queue:**
```python
# Check DLQ for failed messages
python3 backend/scripts/check_dlq.py
```

---

#### Error 3: Database Connection Pool Exhausted

**Симптомы:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Решения:**

1. **Увеличить Pool Size:**
```python
# backend/utils/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Default: 5
    max_overflow=40,     # Default: 10
    pool_pre_ping=True,  # Проверка соединений
    pool_recycle=3600    # Recycle connections every hour
)
```

2. **Ensure Session Cleanup:**
```python
# В workers всегда используйте:
db = SessionLocal()
try:
    # ... database operations
finally:
    db.close()  # ✅ CRITICAL
```

3. **Monitor Active Connections:**
```sql
-- PostgreSQL
SELECT count(*) FROM pg_stat_activity WHERE datname = 'your_db';
```

---

#### Error 4: Redis Connection Lost

**Симптомы:**
```
redis.exceptions.ConnectionError: Error while reading from socket
```

**Решения:**

1. **Use Connection Pool:**
```python
# backend/services/job_service.py
import redis.asyncio as aioredis

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True
)

redis_client = aioredis.Redis(connection_pool=redis_pool)
```

2. **Add Retry Logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def get_job_status(job_id: str):
    return await redis_client.get(f"job:{job_id}")
```

3. **Check Upstash Limits:**
   - Free tier: 10,000 commands/day
   - Upgrade if exceeded

---

#### Error 5: OpenAI Rate Limit

**Симптомы:**
```
openai.RateLimitError: Rate limit reached for gpt-4o
```

**Решения:**

1. **Implement Retry with Backoff:**
```python
# backend/services/ai_service.py
from openai import OpenAI, RateLimitError
import time

def generate_with_retry(prompt: str, max_retries=3):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response
            
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

2. **Use Fallback Provider:**
```python
# Automatic fallback to Groq
try:
    response = openai_generate(prompt)
except RateLimitError:
    logger.warning("OpenAI rate limited, falling back to Groq")
    response = groq_generate(prompt)
```

3. **Check Usage Dashboard:**
   - https://platform.openai.com/usage
   - Monitor daily spend
   - Set usage limits

---

#### Error 6: DALL-E Image Generation Failed

**Симптомы:**
```
openai.BadRequestError: Your request was rejected as a result of our safety system
```

**Решения:**

1. **Review Content Policy:**
   - Avoid violent/adult content
   - Use professional UI terminology

2. **Sanitize Prompts:**
```python
def sanitize_dalle_prompt(prompt: str) -> str:
    """Remove potentially problematic words"""
    blocked_words = ["violent", "nude", "blood", ...]
    
    for word in blocked_words:
        prompt = prompt.replace(word, "")
    
    return prompt
```

3. **Fallback to Placeholder:**
```python
try:
    image_url = generate_dalle_image(prompt)
except BadRequestError as e:
    logger.error(f"DALL-E rejected prompt: {e}")
    # Use placeholder or skip
    image_url = "https://placehold.co/1024x1024?text=Wireframe+Unavailable"
```

---

#### Error 7: Cloudinary Upload Failed

**Симптомы:**
```
cloudinary.exceptions.Error: Upload failed
```

**Решения:**

1. **Check Credentials:**
```python
# Test Cloudinary
import cloudinary
cloudinary.config(
    cloud_name="xxx",
    api_key="xxx",
    api_secret="xxx"
)

result = cloudinary.uploader.upload("https://example.com/test.png")
print(result)
```

2. **Check Quota:**
   - Free tier: 25 GB storage, 25 GB bandwidth/month
   - https://cloudinary.com/console

3. **Handle Upload Errors:**
```python
try:
    result = cloudinary.uploader.upload(temp_url)
    permanent_url = result["secure_url"]
except Exception as e:
    logger.warning(f"Cloudinary upload failed: {e}")
    # Fall back to OpenAI temporary URL
    permanent_url = temp_url  # Expires in 1 hour
```

---

## 7.6. Performance Optimization

### 7.6.1. Database Query Optimization

**Problem:** N+1 queries при загрузке проектов

**Solution:** Use eager loading

```python
# ❌ N+1 queries
projects = db.query(Project).all()
for project in projects:
    activities = project.activities  # N queries

# ✅ Single query
from sqlalchemy.orm import joinedload

projects = db.query(Project)\
    .options(
        joinedload(Project.activities)
            .joinedload(Activity.tasks)
            .joinedload(UserTask.stories)
    )\
    .all()
```

### 7.6.2. Redis Caching

**Cache AI Responses:**

```python
# backend/services/ai_service.py
import hashlib
import json

async def generate_ai_map_cached(requirements_text: str, redis_client):
    """Generate map with caching"""
    
    # Generate cache key
    cache_key = f"ai_map:{hashlib.md5(requirements_text.encode()).hexdigest()}"
    
    # Check cache
    cached = await redis_client.get(cache_key)
    if cached:
        logger.info("✅ Cache hit")
        return json.loads(cached)
    
    # Generate
    result = generate_ai_map(requirements_text)
    
    # Cache for 24 hours
    await redis_client.setex(cache_key, 86400, json.dumps(result))
    
    return result
```

### 7.6.3. Worker Concurrency

**Increase prefetch count:**

```python
# backend/workers/map_worker.py
await rabbitmq_service.channel.set_qos(prefetch_count=3)  # Process 3 messages concurrently
```

**Use asyncio.gather for parallel processing:**

```python
# Process multiple stories in parallel
async def process_multiple_stories(stories):
    tasks = [
        generate_wireframe_for_story(story)
        for story in stories
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

---

## 7.7. Backup & Recovery

### 7.7.1. Database Backup

```bash
# Backup PostgreSQL (Supabase)
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20251206.sql
```

### 7.7.2. Redis Persistence

Upstash Redis автоматически делает backups.

**Manual export:**

```python
# backend/scripts/export_redis.py
import asyncio
import redis.asyncio as aioredis
import json

async def export_all_jobs():
    client = await aioredis.from_url(settings.REDIS_URL)
    
    keys = await client.keys("job:*")
    jobs = {}
    
    for key in keys:
        value = await client.get(key)
        jobs[key] = value
    
    with open("redis_backup.json", "w") as f:
        json.dump(jobs, f, indent=2)
    
    await client.close()
    print(f"✅ Exported {len(jobs)} jobs")

asyncio.run(export_all_jobs())
```

---

## 7.8. Final Checklist

### Pre-Production Checklist:

- [ ] ✅ All environment variables set in Render
- [ ] ✅ JWT_SECRET_KEY is secure (32+ chars)
- [ ] ✅ Database migrations applied
- [ ] ✅ RabbitMQ queues created and bound
- [ ] ✅ Workers running and processing test messages
- [ ] ✅ Health checks returning 200 OK
- [ ] ✅ CORS configured with production frontend URL
- [ ] ✅ Sentry error tracking enabled
- [ ] ✅ CloudAMQP instance not in free trial mode (if using heavily)
- [ ] ✅ Cloudinary quota sufficient for expected wireframe volume
- [ ] ✅ Frontend deployed on Vercel with correct API_URL
- [ ] ✅ SSL/TLS enabled (https://)
- [ ] ✅ Rate limiting configured (optional but recommended)
- [ ] ✅ Monitoring dashboard accessible
- [ ] ✅ Backup strategy in place
- [ ] ✅ Documentation updated

### Go-Live Checklist:

1. **Smoke Test:**
```bash
# Test async map generation
curl -X POST https://usm-backend.onrender.com/projects/generate-async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requirements_text": "Test project", "use_enhancement": false}'

# Expected: {"job_id": "map-...", "status": "pending"}
```

2. **Monitor Logs:**
```bash
# Check all services in Render Dashboard
- Backend API: healthy
- Map Worker: waiting for requests
- Wireframe Worker: waiting for requests
```

3. **Test Frontend:**
```bash
# Visit https://your-app.vercel.app
# Submit test project
# Verify WebSocket connection
# Confirm map generation completes
```

4. **Monitor Metrics:**
```bash
# Check https://usm-backend.onrender.com/metrics
# Response times < 500ms
# Error rate < 1%
```

---

# 🎉 Поздравляем! Implementation Complete!

Вы успешно реализовали:

✅ **Phase 1-2:** RabbitMQ Architecture & Backend Infrastructure  
✅ **Phase 3:** Map & Wireframe Workers  
✅ **Phase 4:** Frontend Integration with WebSocket  
✅ **Phase 5:** Comprehensive Testing Suite  
✅ **Phase 6:** Production Deployment на Render & Vercel  
✅ **Phase 7:** Monitoring, Logging & Troubleshooting  

## Следующие шаги:

1. **Мониторинг производительности** в первую неделю
2. **Оптимизация** на основе метрик
3. **Масштабирование** workers по необходимости
4. **Добавление новых фич** (bulk improve queue, analytics, etc.)

---

**📚 Полная документация:**
- `RABBITMQ_COMPLETE_GUIDE.md` - Phases 1-2 (Architecture, Setup, Backend)
- `RABBITMQ_IMPLEMENTATION_PLAN.md` - Phases 3-7 (Workers, Frontend, Testing, Deploy, Monitoring)

**💬 Support:**
- CloudAMQP Dashboard: https://customer.cloudamqp.com
- Render Dashboard: https://dashboard.render.com
- Sentry: https://sentry.io
- GitHub Issues для багов

Удачи с проектом! 🚀
