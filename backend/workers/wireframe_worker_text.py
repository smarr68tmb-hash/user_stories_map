#!/usr/bin/env python3
"""
RabbitMQ Consumer для генерации Text-based Wireframes

Функции:
- Потребление из очереди ai.wireframe.generation
- Генерация ASCII/Markdown UI wireframes через AI (Gemini/Groq/Perplexity)
- Создание структурированных описаний UI
- Сохранение в database
- Обновление прогресса в Redis

Не требует OpenAI/DALL-E - работает с любым текстовым AI провайдером

Запуск:
    python workers/wireframe_worker_text.py
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import settings
from utils.database import SessionLocal
from services.rabbitmq_service import rabbitmq_service
from services.ai_service import generate_ai_response
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


class TextWireframeWorker:
    """Worker для генерации text-based wireframes из User Stories"""

    def __init__(self):
        self.running = False
        self.redis_client = None
        self.job_service: Optional[JobService] = None
        self.processed_count = 0
        self.failed_count = 0

    async def start(self):
        """Запуск worker"""
        logger.info("="*60)
        logger.info("🎨 Starting Text Wireframe Generation Worker")
        logger.info(f"   Environment: {settings.ENVIRONMENT}")
        logger.info(f"   AI Provider: {settings.API_PROVIDER}")
        logger.info(f"   Model: {settings.API_MODEL}")
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

        # Check AI provider
        if not settings.get_api_key():
            logger.error("❌ No AI API key configured!")
            logger.error("   Set GEMINI_API_KEY, GROQ_API_KEY, or PERPLEXITY_API_KEY")
            sys.exit(1)

        logger.info(f"✅ AI client ready ({settings.API_PROVIDER})")

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
        Генерация text-based wireframe для одной User Story

        Pipeline:
        1. Load context (Activity, Task)
        2. Generate ASCII wireframe + UI description with AI
        3. Return structured data

        Returns:
            Dict with wireframe data (ascii_wireframe, ui_description, elements, etc.)
        """

        # Step 1: Load context
        task = db.query(UserTask).filter(UserTask.id == story.task_id).first()
        activity = None
        if task:
            activity = db.query(Activity).filter(Activity.id == task.activity_id).first()

        # Step 2: Generate wireframe with AI
        logger.info("   📝 Generating text wireframe with AI...")

        prompt = self._build_wireframe_prompt(
            story=story,
            task=task,
            activity=activity,
            style=style,
            platform=platform
        )

        # Use existing AI service (works with Gemini/Groq/Perplexity)
        ai_response = generate_ai_response(
            prompt=prompt,
            redis_client=self.redis_client,
            temperature=0.7
        )

        logger.info(f"   ✅ Wireframe generated ({len(ai_response)} chars)")

        # Parse response to extract components
        wireframe_data = self._parse_wireframe_response(ai_response)

        # Add metadata
        wireframe_data.update({
            "story_id": story.id,
            "story_title": story.title,
            "style": style,
            "platform": platform,
            "created_at": datetime.utcnow().isoformat()
        })

        return wireframe_data

    def _build_wireframe_prompt(
        self,
        story: UserStory,
        task: Optional[UserTask],
        activity: Optional[Activity],
        style: str,
        platform: str
    ) -> str:
        """Формирование промпта для генерации text-based wireframe"""

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

        style_instructions = {
            "low-fidelity": "Простая ASCII схема с базовыми блоками, минимум деталей",
            "high-fidelity": "Детальная ASCII схема с конкретными элементами и labels",
            "component": "Фокус на одном UI компоненте с детальным описанием"
        }

        platform_instructions = {
            "web": "Desktop web интерфейс (navbar, cards, sidebar)",
            "mobile": "Mobile app интерфейс (portrait, bottom navigation, swipe gestures)",
            "desktop": "Native desktop приложение (menu bar, toolbar, panels)"
        }

        prompt = f"""Создай text-based wireframe (ASCII схема + описание) для следующей User Story:

{context}

ТРЕБОВАНИЯ:

1. **ASCII Wireframe:**
   - Используй box-drawing characters: ┌─┐│└┘├┤┬┴┼
   - Покажи структуру экрана визуально
   - Обозначь основные UI блоки: Header, Content, Footer
   - Стиль: {style_instructions.get(style, '')}
   - Платформа: {platform_instructions.get(platform, '')}

2. **Описание Layout:**
   - Опиши структуру экрана текстом
   - Перечисли все разделы (Header, Main, Sidebar, Footer)
   - Укажи их назначение

3. **UI Элементы:**
   Список всех UI компонентов в формате:
   - [Type] Label/Text (placeholder, если есть)

   Примеры:
   - [Input] Email (placeholder: "user@example.com")
   - [Button] Register (primary, top-right)
   - [Link] Forgot password? (below password field)

4. **Навигация:**
   - Откуда попадаем на этот экран
   - Куда можно перейти с этого экрана
   - Основные user flows

ФОРМАТ ОТВЕТА (СТРОГО СОБЛЮДАЙ):

```ascii
[ASCII wireframe схема здесь]
```

## Layout Description
[Текстовое описание структуры]

## UI Elements
[Список всех элементов]

## Navigation
[Описание навигации]

## Additional Notes
[Дополнительные замечания по UX, если есть]

Будь конкретным, детальным и профессиональным. Опиши экран так, чтобы фронтенд-разработчик мог его реализовать.
"""
        return prompt

    def _parse_wireframe_response(self, ai_response: str) -> Dict:
        """
        Парсинг AI ответа для извлечения компонентов

        Returns:
            {
                "ascii_wireframe": "...",
                "layout_description": "...",
                "ui_elements": [...],
                "navigation": "...",
                "notes": "..."
            }
        """
        result = {
            "full_text": ai_response,
            "ascii_wireframe": "",
            "layout_description": "",
            "ui_elements": [],
            "navigation": "",
            "notes": ""
        }

        # Extract ASCII wireframe
        import re
        ascii_match = re.search(r'```ascii\n(.*?)```', ai_response, re.DOTALL)
        if ascii_match:
            result["ascii_wireframe"] = ascii_match.group(1).strip()

        # Extract sections
        layout_match = re.search(r'## Layout Description\n(.*?)(?=##|$)', ai_response, re.DOTALL)
        if layout_match:
            result["layout_description"] = layout_match.group(1).strip()

        elements_match = re.search(r'## UI Elements\n(.*?)(?=##|$)', ai_response, re.DOTALL)
        if elements_match:
            elements_text = elements_match.group(1).strip()
            # Parse elements list
            result["ui_elements"] = [
                line.strip() for line in elements_text.split('\n')
                if line.strip() and line.strip().startswith('-')
            ]

        nav_match = re.search(r'## Navigation\n(.*?)(?=##|$)', ai_response, re.DOTALL)
        if nav_match:
            result["navigation"] = nav_match.group(1).strip()

        notes_match = re.search(r'## Additional Notes\n(.*?)$', ai_response, re.DOTALL)
        if notes_match:
            result["notes"] = notes_match.group(1).strip()

        return result


# Signal handlers
worker: Optional[TextWireframeWorker] = None

def signal_handler(signum, frame):
    logger.info(f"\n⚠️ Received signal {signum}")
    if worker:
        asyncio.create_task(worker.stop())
        sys.exit(0)


async def main():
    global worker

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    worker = TextWireframeWorker()

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
