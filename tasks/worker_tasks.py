# tasks/worker_tasks.py
from celery import current_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import json
from datetime import datetime, timedelta

from .celery_app import celery_app
from app.database import SessionLocal, get_db
from app.models import Video, Publication, Campaign
from collectors.tiktok_collector import TikTokCollector
from collectors.youtube_collector import YouTubeCollector
from processors.video_processor import VideoProcessor
from processors.subtitle_generator import SubtitleGenerator
from processors.watermark_manager import WatermarkManager
from publishers.instagram_publisher import InstagramPublisher
from publishers.tiktok_publisher import TikTokPublisher
from analytics.metrics_collector import MetricsCollector
from dashboard.telegram_bot import TelegramNotifier

logger = get_task_logger(__name__)

def get_db_session():
    """Obter sessão do banco para tasks"""
    return SessionLocal()

@celery_app.task(bind=True)
async def collect_videos_task(self, hashtags: List[str], limit: int = 20):
    """Task para coletar vídeos virais"""
    logger.info(f"Iniciando coleta de vídeos para hashtags: {hashtags}")
    
    db = get_db_session()
    collected_count = 0
    
    try:
        # Configuração dos coletores
        config = {
            'api_key': os.getenv('YOUTUBE_API_KEY'),
            'target_resolution': '1080x1920',
            'max_duration': 60
        }
        
        collectors = [
            TikTokCollector(config),
            YouTubeCollector(config)
        ]
        
        for collector in collectors:
            try:
                # Coletar vídeos
                videos_data = await collector.collect_videos(hashtags, limit // len(collectors))
                
                for video_data in videos_data:
                    # Verificar se já existe
                    existing = db.query(Video).filter(
                        Video.source_id == video_data['source_id'],
                        Video.source_platform == video_data['source_platform']
                    ).first()
                    
                    if not existing:
                        # Salvar novo vídeo
                        video = Video(**video_data)
                        db.add(video)
                        db.commit()
                        collected_count += 1
                        
                        logger.info(f"Vídeo coletado: {video_data['source_id']} - {video_data['title'][:50]}")
                
            except Exception as e:
                logger.error(f"Erro no coletor {collector.platform}: {str(e)}")
                continue
        
        # Notificar via Telegram
        if collected_count > 0:
            notifier = TelegramNotifier()
            await notifier.send_notification(
                f"🎥 {collected_count} novos vídeos coletados!\n"
                f"Hashtags: {', '.join(hashtags)}"
            )
        
        logger.info(f"Coleta finalizada: {collected_count} vídeos coletados")
        return {"status": "success", "collected": collected_count}
        
    except Exception as e:
        logger.error(f"Erro na coleta de vídeos: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task(bind=True)
def process_pending_videos(self):
    """Task para processar vídeos coletados"""
    logger.info("Iniciando processamento de vídeos pendentes")
    
    db = get_db_session()
    processed_count = 0
    
    try:
        # Buscar vídeos para processar
        pending_videos = db.query(Video).filter(
            Video.status == "collected",
            Video.local_path.isnot(None)
        ).limit(5).all()  # Processar máximo 5 por vez
        
        if not pending_videos:
            logger.info("Nenhum vídeo pendente para processar")
            return {"status": "success", "processed": 0}
        
        # Configurar processadores
        config = {
            'target_resolution': '1080x1920',
            'max_duration': 60,
            'use_openai_api': bool(os.getenv('OPENAI_API_KEY')),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'brand_name': 'Pet Shop',
            'brand_color': '#FF6B6B'
        }
        
        video_processor = VideoProcessor(config)
        subtitle_generator = SubtitleGenerator(config)
        watermark_manager = WatermarkManager(config)
        
        for video in pending_videos:
            try:
                if not os.path.exists(video.local_path):
                    logger.warning(f"Arquivo não encontrado: {video.local_path}")
                    continue
                
                # Gerar legenda
                subtitle_text = subtitle_generator.generate_subtitles(video.local_path)
                if subtitle_text:
                    subtitle_text = subtitle_generator.clean_transcript(subtitle_text, 80)
                
                # Preparar CTA
                cta_text = "🛍️ Confira em nossa loja!"
                
                # Obter watermark
                watermark_path = watermark_manager.get_watermark_path("default")
                
                # Processar vídeo
                output_path = f"videos/ready/{video.source_platform}_{video.source_id}_processed.mp4"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                import asyncio
                processed_path = asyncio.run(video_processor.process_video(
                    input_path=video.local_path,
                    output_path=output_path,
                    subtitle_text=subtitle_text,
                    cta_text=cta_text,
                    watermark_path=watermark_path if os.path.exists(watermark_path) else None
                ))
                
                # Atualizar banco
                video.processed_path = processed_path
                video.status = "processed"
                video.processed_at = datetime.utcnow()
                db.commit()
                
                processed_count += 1
                logger.info(f"Vídeo processado: {video.source_id}")
                
            except Exception as e:
                logger.error(f"Erro ao processar vídeo {video.source_id}: {str(e)}")
                video.status = "error"
                db.commit()
                continue
        
        logger.info(f"Processamento finalizado: {processed_count} vídeos processados")
        return {"status": "success", "processed": processed_count}
        
    except Exception as e:
        logger.error(f"Erro no processamento de vídeos: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task(bind=True)
def publish_scheduled_videos(self):
    """Task para publicar vídeos nos horários programados"""
    logger.info("Iniciando publicação de vídeos programados")
    
    db = get_db_session()
    published_count = 0
    
    try:
        # Buscar vídeos prontos para publicar
        ready_videos = db.query(Video).filter(
            Video.status == "processed",
            Video.processed_path.isnot(None)
        ).order_by(Video.processed_at.desc()).limit(3).all()  # Máximo 3 por horário
        
        if not ready_videos:
            logger.info("Nenhum vídeo pronto para publicar")
            return {"status": "success", "published": 0}
        
        # Configurar publicadores
        config = {
            'instagram_access_token': os.getenv('INSTAGRAM_ACCESS_TOKEN'),
            'tiktok_access_token': os.getenv('TIKTOK_ACCESS_TOKEN'),
        }
        
        publishers = [
            InstagramPublisher(config),
            TikTokPublisher(config)
        ]
        
        for video in ready_videos:
            try:
                if not os.path.exists(video.processed_path):
                    logger.warning(f"Arquivo processado não encontrado: {video.processed_path}")
                    continue
                
                # Gerar caption
                caption = f"{video.title}\n\n"
                if video.hashtags:
                    hashtags_list = json.loads(video.hashtags)
                    caption += " ".join([f"#{tag}" for tag in hashtags_list[:10]])
                caption += "\n\n🛍️ Visite nossa loja!"
                
                # Publicar em cada plataforma
                for publisher in publishers:
                    try:
                        import asyncio
                        result = asyncio.run(publisher.publish_video(
                            video_path=video.processed_path,
                            caption=caption,
                            title=video.title
                        ))
                        
                        if result.get('success'):
                            # Salvar publicação
                            publication = Publication(
                                video_id=video.id,
                                platform=publisher.platform,
                                platform_post_id=result.get('post_id'),
                                post_url=result.get('post_url'),
                                caption=caption,
                                status="published",
                                published_at=datetime.utcnow()
                            )
                            
                            db.add(publication)
                            logger.info(f"Publicado no {publisher.platform}: {result.get('post_id')}")
                        
                    except Exception as e:
                        logger.error(f"Erro ao publicar no {publisher.platform}: {str(e)}")
                        continue
                
                # Atualizar status do vídeo
                video.status = "published"
                video.published_at = datetime.utcnow()
                db.commit()
                
                published_count += 1
                
            except Exception as e:
                logger.error(f"Erro ao publicar vídeo {video.source_id}: {str(e)}")
                continue
        
        # Notificar publicações
        if published_count > 0:
            notifier = TelegramNotifier()
            notifier.send_notification(
                f"📱 {published_count} vídeos publicados!\n"
                f"Horário: {datetime.now().strftime('%H:%M')}"
            )
        
        logger.info(f"Publicação finalizada: {published_count} vídeos publicados")
        return {"status": "success", "published": published_count}
        
    except Exception as e:
        logger.error(f"Erro na publicação de vídeos: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task(bind=True)
async def collect_analytics(self):
    """Task para coletar métricas de performance"""
    logger.info("Iniciando coleta de métricas")
    
    db = get_db_session()
    updated_count = 0
    
    try:
        # Buscar publicações para atualizar métricas
        publications = db.query(Publication).filter(
            Publication.status == "published",
            Publication.platform_post_id.isnot(None)
        ).order_by(Publication.published_at.desc()).limit(20).all()
        
        if not publications:
            logger.info("Nenhuma publicação para coletar métricas")
            return {"status": "success", "updated": 0}
        
        # Coletor de métricas
        metrics_collector = MetricsCollector()
        
        for publication in publications:
            try:
                # Coletar métricas da plataforma
                metrics = await metrics_collector.get_metrics(
                    platform=publication.platform,
                    post_id=publication.platform_post_id
                )
                
                if metrics:
                    # Atualizar publicação
                    publication.views = metrics.get('views', 0)
                    publication.likes = metrics.get('likes', 0)
                    publication.comments = metrics.get('comments', 0)
                    publication.shares = metrics.get('shares', 0)
                    
                    # Calcular engagement rate
                    if publication.views > 0:
                        total_engagement = publication.likes + publication.comments + publication.shares
                        publication.engagement_rate = (total_engagement / publication.views) * 100
                    
                    publication.last_metrics_update = datetime.utcnow()
                    db.commit()
                    
                    updated_count += 1
                    logger.info(f"Métricas atualizadas: {publication.platform} - {publication.platform_post_id}")
                
            except Exception as e:
                logger.error(f"Erro ao coletar métricas da publicação {publication.id}: {str(e)}")
                continue
        
        logger.info(f"Coleta de métricas finalizada: {updated_count} publicações atualizadas")
        return {"status": "success", "updated": updated_count}
        
    except Exception as e:
        logger.error(f"Erro na coleta de métricas: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task(bind=True)
def cleanup_old_files(self):
    """Task para limpeza de arquivos antigos"""
    logger.info("Iniciando limpeza de arquivos antigos")
    
    cleaned_files = 0
    freed_space = 0
    
    try:
        # Definir diretórios e idade limite
        directories = ['videos/raw', 'videos/processed']
        age_limit = timedelta(days=7)  # Arquivos mais antigos que 7 dias
        cutoff_date = datetime.now() - age_limit
        
        for directory in directories:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                try:
                    # Verificar idade do arquivo
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    if file_time < cutoff_date:
                        # Obter tamanho antes de deletar
                        file_size = os.path.getsize(filepath)
                        
                        # Deletar arquivo
                        os.remove(filepath)
                        
                        cleaned_files += 1
                        freed_space += file_size
                        
                        logger.info(f"Arquivo removido: {filepath}")
                
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo {filepath}: {str(e)}")
                    continue
        
        # Converter bytes para MB
        freed_mb = freed_space / (1024 * 1024)
        
        logger.info(f"Limpeza finalizada: {cleaned_files} arquivos removidos, {freed_mb:.2f}MB liberados")
        
        # Notificar se limpeza significativa
        if cleaned_files > 10:
            notifier = TelegramNotifier()
            notifier.send_notification(
                f"🗑️ Limpeza automática realizada!\n"
                f"Arquivos removidos: {cleaned_files}\n"
                f"Espaço liberado: {freed_mb:.2f}MB"
            )
        
        return {"status": "success", "cleaned_files": cleaned_files, "freed_mb": freed_mb}
        
    except Exception as e:
        logger.error(f"Erro na limpeza de arquivos: {str(e)}")
        return {"status": "error", "message": str(e)}

# Tarefas manuais/admin
@celery_app.task(bind=True)
def process_specific_video(self, video_id: int):
    """Processar um vídeo específico manualmente"""
    db = get_db_session()
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {"status": "error", "message": "Vídeo não encontrado"}
        
        # Reprocessar usando a mesma lógica da task automática
        return process_video_logic(video, db)
        
    except Exception as e:
        logger.error(f"Erro ao processar vídeo {video_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task(bind=True)
def publish_specific_video(self, video_id: int, platforms: List[str] = None):
    """Publicar um vídeo específico em plataformas selecionadas"""
    db = get_db_session()
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video or video.status != "processed":
            return {"status": "error", "message": "Vídeo não encontrado ou não processado"}
        
        platforms = platforms or ["instagram", "tiktok"]
        
        # Lógica de publicação específica
        return publish_video_logic(video, platforms, db)
        
    except Exception as e:
        logger.error(f"Erro ao publicar vídeo {video_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

@celery_app.task(bind=True)
def generate_performance_report(self, days: int = 7):
    """Gerar relatório de performance dos últimos N dias"""
    logger.info(f"Gerando relatório de performance dos últimos {days} dias")
    
    db = get_db_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Estatísticas gerais
        total_publications = db.query(Publication).filter(
            Publication.published_at >= cutoff_date
        ).count()
        
        # Métricas agregadas
        from sqlalchemy import func
        metrics = db.query(
            func.sum(Publication.views).label('total_views'),
            func.sum(Publication.likes).label('total_likes'),
            func.sum(Publication.comments).label('total_comments'),
            func.sum(Publication.shares).label('total_shares'),
            func.avg(Publication.engagement_rate).label('avg_engagement')
        ).filter(Publication.published_at >= cutoff_date).first()
        
        # Top performing posts
        top_posts = db.query(Publication).filter(
            Publication.published_at >= cutoff_date
        ).order_by(Publication.views.desc()).limit(5).all()
        
        # Métricas por plataforma
        platform_stats = db.query(
            Publication.platform,
            func.count(Publication.id).label('posts_count'),
            func.sum(Publication.views).label('platform_views'),
            func.avg(Publication.engagement_rate).label('platform_engagement')
        ).filter(
            Publication.published_at >= cutoff_date
        ).group_by(Publication.platform).all()
        
        # Montar relatório
        report = {
            "period": f"Últimos {days} dias",
            "total_publications": total_publications,
            "total_views": metrics.total_views or 0,
            "total_likes": metrics.total_likes or 0,
            "total_comments": metrics.total_comments or 0,
            "total_shares": metrics.total_shares or 0,
            "average_engagement": round(metrics.avg_engagement or 0, 2),
            "top_posts": [
                {
                    "platform": post.platform,
                    "post_id": post.platform_post_id,
                    "views": post.views,
                    "engagement_rate": round(post.engagement_rate, 2)
                }
                for post in top_posts
            ],
            "platform_performance": [
                {
                    "platform": stat.platform,
                    "posts_count": stat.posts_count,
                    "views": stat.platform_views,
                    "avg_engagement": round(stat.platform_engagement, 2)
                }
                for stat in platform_stats
            ]
        }
        
        # Enviar relatório via Telegram
        notifier = TelegramNotifier()
        notifier.send_performance_report(report)
        
        logger.info("Relatório de performance gerado e enviado")
        return {"status": "success", "report": report}
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

# Funções auxiliares
def process_video_logic(video, db):
    """Lógica compartilhada para processamento de vídeo"""
    # Implementar lógica de processamento aqui
    pass

def publish_video_logic(video, platforms, db):
    """Lógica compartilhada para publicação de vídeo"""
    # Implementar lógica de publicação aqui
    pass