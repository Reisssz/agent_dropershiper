# analytics/metrics_collector.py
import requests
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

class MetricsCollector:
    """Coletor de métricas de performance das redes sociais"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.instagram_token = self.config.get('instagram_access_token')
        self.facebook_token = self.config.get('facebook_access_token')
        self.youtube_api_key = self.config.get('youtube_api_key')
    
    async def get_metrics(self, platform: str, post_id: str) -> Optional[Dict[str, Any]]:
        """Obter métricas de um post específico"""
        
        collectors = {
            'instagram': self._get_instagram_metrics,
            'facebook': self._get_facebook_metrics,
            'youtube': self._get_youtube_metrics,
            'tiktok': self._get_tiktok_metrics
        }
        
        collector = collectors.get(platform.lower())
        if not collector:
            return None
        
        try:
            return await collector(post_id)
        except Exception as e:
            print(f"Erro ao coletar métricas {platform}: {str(e)}")
            return None
    
    async def _get_instagram_metrics(self, post_id: str) -> Dict[str, Any]:
        """Coletar métricas do Instagram"""
        
        if not self.instagram_token:
            return {}
        
        try:
            # Instagram Graph API
            url = f"https://graph.facebook.com/v18.0/{post_id}"
            params = {
                'fields': 'insights.metric(impressions,reach,profile_visits,likes,comments,saves,shares)',
                'access_token': self.instagram_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'insights' in data:
                insights = data['insights']['data']
                metrics = {}
                
                for insight in insights:
                    metric_name = insight['name']
                    metric_value = insight['values'][0]['value'] if insight['values'] else 0
                    
                    if metric_name == 'impressions':
                        metrics['views'] = metric_value
                    elif metric_name == 'likes':
                        metrics['likes'] = metric_value
                    elif metric_name == 'comments':
                        metrics['comments'] = metric_value
                    elif metric_name == 'shares':
                        metrics['shares'] = metric_value
                
                return metrics
            
            # Fallback: dados básicos do post
            basic_url = f"https://graph.facebook.com/v18.0/{post_id}"
            basic_params = {
                'fields': 'like_count,comments_count',
                'access_token': self.instagram_token
            }
            
            basic_response = requests.get(basic_url, params=basic_params)
            basic_data = basic_response.json()
            
            return {
                'likes': basic_data.get('like_count', 0),
                'comments': basic_data.get('comments_count', 0),
                'views': 0,
                'shares': 0
            }
            
        except Exception as e:
            print(f"Erro ao coletar métricas Instagram: {str(e)}")
            return {}
    
    async def _get_facebook_metrics(self, post_id: str) -> Dict[str, Any]:
        """Coletar métricas do Facebook"""
        
        if not self.facebook_token:
            return {}
        
        try:
            url = f"https://graph.facebook.com/v18.0/{post_id}"
            params = {
                'fields': 'insights.metric(post_video_views,post_engaged_users,post_clicks,post_reactions_by_type_total)',
                'access_token': self.facebook_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            metrics = {
                'views': 0,
                'likes': 0,
                'comments': 0,
                'shares': 0
            }
            
            if 'insights' in data:
                insights = data['insights']['data']
                
                for insight in insights:
                    metric_name = insight['name']
                    metric_values = insight['values'][0]['value'] if insight['values'] else 0
                    
                    if metric_name == 'post_video_views':
                        metrics['views'] = metric_values
                    elif metric_name == 'post_reactions_by_type_total':
                        if isinstance(metric_values, dict):
                            metrics['likes'] = sum(metric_values.values())
            
            return metrics
            
        except Exception as e:
            print(f"Erro ao coletar métricas Facebook: {str(e)}")
            return {}
    
    async def _get_youtube_metrics(self, video_id: str) -> Dict[str, Any]:
        """Coletar métricas do YouTube"""
        
        if not self.youtube_api_key:
            return {}
        
        try:
            # YouTube Analytics API
            from googleapiclient.discovery import build
            
            youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            
            # Estatísticas básicas
            response = youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()
            
            if response['items']:
                stats = response['items'][0]['statistics']
                
                return {
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'shares': 0  # YouTube não fornece shares diretamente
                }
            
            return {}
            
        except Exception as e:
            print(f"Erro ao coletar métricas YouTube: {str(e)}")
            return {}
    
    async def _get_tiktok_metrics(self, post_id: str) -> Dict[str, Any]:
        """Coletar métricas do TikTok (limitado - sem API pública)"""
        
        # TikTok não tem API pública para métricas orgânicas
        # Seria necessário usar scraping ou TikTok Business API (apenas para anúncios)
        
        try:
            # Placeholder - implementar scraping se necessário
            return {
                'views': 0,
                'likes': 0,
                'comments': 0,
                'shares': 0
            }
        except Exception as e:
            print(f"Erro ao coletar métricas TikTok: {str(e)}")
            return {}