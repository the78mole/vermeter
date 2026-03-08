from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "rental_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.worker.tasks.generate_bill_pdf": {"queue": "billing"},
        "app.worker.tasks.daily_aggregator": {"queue": "default"},
    },
    beat_schedule={
        "daily-meter-aggregator": {
            "task": "app.worker.tasks.daily_aggregator",
            "schedule": crontab(hour=2, minute=0),  # Run at 02:00 UTC daily
        },
    },
)
