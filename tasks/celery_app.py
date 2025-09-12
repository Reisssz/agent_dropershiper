from celery import Celery
from celery.schedules import crontab
from app.config import settings
import os

# Configurar Celery
celery_app = Celery(
    'pet_agent',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['tasks.worker_tasks']
)

# Configuração
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Fortaleza',  # Timezone do Brasil
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos timeout
    task_soft_time_limit=25 * 60,  # 25 minutos soft timeout
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
)

# Agendamentos automáticos
celery_app.conf.beat_schedule = {
    # Coletar vídeos a cada 6 horas
    'collect-viral-videos': {
        'task': 'tasks.worker_tasks.collect_videos_task',
        'schedule': crontab(minute=0, hour='*/6'),  # 00:00, 06:00, 12:00, 18:00
        'args': (['#pet', '#gadgetspet', '#petshop', '#dogs', '#cats'], 20)
    },
    
    # Processar vídeos coletados a cada hora
    'process-videos': {
        'task': 'tasks.worker_tasks.process_pending_videos',
        'schedule': crontab(minute=30),  # Todo minuto 30 de cada hora
    },
    
    # Publicar vídeos 3x por dia
    'publish-morning': {
        'task': 'tasks.worker_tasks.publish_scheduled_videos',
        'schedule': crontab(hour=8, minute=0),  # 08:00
    },
    'publish-afternoon': {
        'task': 'tasks.worker_tasks.publish_scheduled_videos',
        'schedule': crontab(hour=14, minute=0),  # 14:00
    },
    'publish-evening': {
        'task': 'tasks.worker_tasks.publish_scheduled_videos',
        'schedule': crontab(hour=20, minute=0),  # 20:00
    },
    
    # Coletar métricas a cada 2 horas
    'collect-metrics': {
        'task': 'tasks.worker_tasks.collect_analytics',
        'schedule': crontab(minute=0, hour='*/2'),
    },
    
    # Limpeza de arquivos antigos diariamente
    'cleanup-old-files': {
        'task': 'tasks.worker_tasks.cleanup_old_files',
        'schedule': crontab(hour=3, minute=0),  # 03:00 todo dia
    },
}