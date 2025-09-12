# tasks/scheduler.py
from celery.schedules import crontab
from .celery_app import celery_app
import json
from datetime import datetime
from app.database import SessionLocal
from app.models import Campaign

class TaskScheduler:
    """Gerenciador de agendamentos dinâmicos"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def update_campaign_schedule(self, campaign_id: int, schedule_config: dict):
        """Atualizar agendamento de uma campanha"""
        try:
            # Buscar campanha
            campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return False
            
            # Criar agendamentos personalizados
            schedule_name = f"campaign-{campaign_id}"
            
            # Definir horários de postagem baseados na configuração
            posts_per_day = schedule_config.get('posts_per_day', 3)
            active_hours = schedule_config.get('active_hours', [8, 14, 20])
            
            # Remover agendamento anterior se existir
            if schedule_name in celery_app.conf.beat_schedule:
                del celery_app.conf.beat_schedule[schedule_name]
            
            # Criar novos agendamentos
            for i, hour in enumerate(active_hours[:posts_per_day]):
                task_name = f"{schedule_name}-{i}"
                celery_app.conf.beat_schedule[task_name] = {
                    'task': 'tasks.worker_tasks.publish_campaign_videos',
                    'schedule': crontab(hour=hour, minute=0),
                    'args': (campaign_id,)
                }
            
            return True
            
        except Exception as e:
            print(f"Erro ao atualizar agendamento da campanha: {str(e)}")
            return False
        
        finally:
            self.db.close()
    
    def pause_campaign(self, campaign_id: int):
        """Pausar agendamentos de uma campanha"""
        schedule_name = f"campaign-{campaign_id}"
        
        # Remover todos os agendamentos da campanha
        keys_to_remove = [key for key in celery_app.conf.beat_schedule.keys() 
                         if key.startswith(schedule_name)]
        
        for key in keys_to_remove:
            del celery_app.conf.beat_schedule[key]
        
        return len(keys_to_remove) > 0
    
    def get_active_schedules(self):
        """Listar agendamentos ativos"""
        return list(celery_app.conf.beat_schedule.keys())