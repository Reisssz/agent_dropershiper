import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Publication, Video

class PerformanceAnalyzer:
    """Analisador de performance e insights"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_overview_stats(self, days: int = 30) -> Dict[str, Any]:
        """Estatísticas gerais dos últimos N dias"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Contadores básicos
        total_posts = self.db.query(Publication).filter(
            Publication.published_at >= cutoff_date
        ).count()
        
        # Métricas agregadas
        metrics = self.db.query(
            func.sum(Publication.views).label('total_views'),
            func.sum(Publication.likes).label('total_likes'),
            func.sum(Publication.comments).label('total_comments'),
            func.sum(Publication.shares).label('total_shares'),
            func.avg(Publication.engagement_rate).label('avg_engagement')
        ).filter(Publication.published_at >= cutoff_date).first()
        
        # Posts por plataforma
        platform_stats = self.db.query(
            Publication.platform,
            func.count(Publication.id).label('count'),
            func.sum(Publication.views).label('views'),
            func.avg(Publication.engagement_rate).label('engagement')
        ).filter(
            Publication.published_at >= cutoff_date
        ).group_by(Publication.platform).all()
        
        return {
            'period_days': days,
            'total_posts': total_posts,
            'total_views': int(metrics.total_views or 0),
            'total_likes': int(metrics.total_likes or 0),
            'total_comments': int(metrics.total_comments or 0),
            'total_shares': int(metrics.total_shares or 0),
            'avg_engagement_rate': round(float(metrics.avg_engagement or 0), 2),
            'platform_breakdown': [
                {
                    'platform': stat.platform,
                    'posts': stat.count,
                    'views': int(stat.views or 0),
                    'avg_engagement': round(float(stat.engagement or 0), 2)
                }
                for stat in platform_stats
            ]
        }
    
    def get_top_performing_content(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """Conteúdo com melhor performance"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        top_posts = self.db.query(Publication, Video).join(
            Video, Publication.video_id == Video.id
        ).filter(
            Publication.published_at >= cutoff_date
        ).order_by(Publication.views.desc()).limit(limit).all()
        
        result = []
        for pub, video in top_posts:
            result.append({
                'video_title': video.title[:50] + '...' if len(video.title) > 50 else video.title,
                'platform': pub.platform,
                'views': pub.views,
                'likes': pub.likes,
                'comments': pub.comments,
                'engagement_rate': round(pub.engagement_rate, 2),
                'published_at': pub.published_at.strftime('%d/%m/%Y %H:%M'),
                'post_url': pub.post_url
            })
        
        return result
    
    def get_engagement_trends(self, days: int = 30) -> Dict[str, Any]:
        """Tendências de engajamento ao longo do tempo"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Dados diários
        daily_stats = self.db.query(
            func.date(Publication.published_at).label('date'),
            func.count(Publication.id).label('posts'),
            func.sum(Publication.views).label('views'),
            func.sum(Publication.likes).label('likes'),
            func.avg(Publication.engagement_rate).label('engagement')
        ).filter(
            Publication.published_at >= cutoff_date
        ).group_by(
            func.date(Publication.published_at)
        ).order_by('date').all()
        
        # Converter para formato de gráfico
        dates = [stat.date.strftime('%d/%m') for stat in daily_stats]
        posts_count = [stat.posts for stat in daily_stats]
        views_count = [int(stat.views or 0) for stat in daily_stats]
        likes_count = [int(stat.likes or 0) for stat in daily_stats]
        engagement_rates = [round(float(stat.engagement or 0), 2) for stat in daily_stats]
        
        return {
            'dates': dates,
            'posts': posts_count,
            'views': views_count,
            'likes': likes_count,
            'engagement_rates': engagement_rates
        }
    
    def get_hashtag_performance(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Performance das hashtags mais usadas"""
        
        # Buscar vídeos com hashtags e suas métricas
        videos_with_hashtags = self.db.query(Video, Publication).join(
            Publication, Video.id == Publication.video_id
        ).filter(
            Video.hashtags.isnot(None),
            Publication.views > 0
        ).all()
        
        hashtag_metrics = {}
        
        for video, pub in videos_with_hashtags:
            try:
                import json
                hashtags = json.loads(video.hashtags) if video.hashtags else []
                
                for hashtag in hashtags:
                    tag = hashtag.lower().strip('#')
                    if tag not in hashtag_metrics:
                        hashtag_metrics[tag] = {
                            'hashtag': f'#{tag}',
                            'usage_count': 0,
                            'total_views': 0,
                            'total_likes': 0,
                            'total_engagement': 0
                        }
                    
                    hashtag_metrics[tag]['usage_count'] += 1
                    hashtag_metrics[tag]['total_views'] += pub.views
                    hashtag_metrics[tag]['total_likes'] += pub.likes
                    hashtag_metrics[tag]['total_engagement'] += pub.likes + pub.comments + pub.shares
                    
            except Exception as e:
                continue