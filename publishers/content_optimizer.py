from typing import Dict, Any, List, Optional
import re

class ContentOptimizer:
    """Otimizador de conteúdo para diferentes plataformas"""
    
    PLATFORM_LIMITS = {
        'instagram': {
            'caption_max': 2200,
            'hashtags_max': 30,
            'video_max_duration': 60
        },
        'tiktok': {
            'caption_max': 300,
            'hashtags_max': 20,
            'video_max_duration': 60
        },
        'youtube': {
            'title_max': 100,
            'description_max': 5000,
            'tags_max': 500,
            'video_max_duration': 60  # Para Shorts
        },
        'facebook': {
            'caption_max': 63206,
            'hashtags_max': 30,
            'video_max_duration': 60
        }
    }
    
    PLATFORM_HASHTAGS = {
        'instagram': ['#reels', '#petshop', '#pets', '#dogs', '#cats', '#animals'],
        'tiktok': ['#fyp', '#pets', '#dogs', '#cats', '#petshop', '#animals'],
        'youtube': ['#shorts', '#pets', '#animals', '#dogs', '#cats'],
        'facebook': ['#pets', '#animals', '#dogs', '#cats', '#petshop']
    }
    
    @classmethod
    def optimize_content(
        cls, 
        platform: str, 
        title: str, 
        caption: str, 
        hashtags: List[str]
    ) -> Dict[str, Any]:
        """Otimizar conteúdo para plataforma específica"""
        
        limits = cls.PLATFORM_LIMITS.get(platform, {})
        platform_hashtags = cls.PLATFORM_HASHTAGS.get(platform, [])
        
        # Otimizar título
        optimized_title = cls._optimize_title(title, limits.get('title_max', 100))
        
        # Otimizar caption
        optimized_caption = cls._optimize_caption(caption, limits.get('caption_max', 2200))
        
        # Otimizar hashtags
        all_hashtags = list(set(hashtags + platform_hashtags))
        optimized_hashtags = cls._optimize_hashtags(all_hashtags, limits.get('hashtags_max', 30))
        
        # Criar caption final com hashtags
        if platform == 'youtube':
            # YouTube usa hashtags na descrição
            final_caption = optimized_caption + '\n\n' + ' '.join(optimized_hashtags)
        else:
            # Outras plataformas integram hashtags na caption
            final_caption = optimized_caption + '\n\n' + ' '.join(optimized_hashtags)
        
        return {
            'title': optimized_title,
            'caption': final_caption,
            'hashtags': optimized_hashtags,
            'platform': platform
        }
    
    @classmethod
    def _optimize_title(cls, title: str, max_length: int) -> str:
        """Otimizar título respeitando limite de caracteres"""
        if len(title) <= max_length:
            return title
        
        # Truncar preservando palavras
        words = title.split()
        truncated = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_length - 3:  # -3 para "..."
                break
            truncated.append(word)
            current_length += len(word) + 1
        
        return ' '.join(truncated) + '...'
    
    @classmethod
    def _optimize_caption(cls, caption: str, max_length: int) -> str:
        """Otimizar caption respeitando limite de caracteres"""
        if len(caption) <= max_length:
            return caption
        
        # Truncar preservando parágrafos/frases
        sentences = re.split(r'[.!?]\s+', caption)
        truncated = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) + 4 > max_length:  # +4 para pontuação e "..."
                break
            truncated.append(sentence)
            current_length += len(sentence) + 2
        
        result = '. '.join(truncated)
        if len(result) < len(caption):
            result += '...'
        
        return result
    
    @classmethod
    def _optimize_hashtags(cls, hashtags: List[str], max_count: int) -> List[str]:
        """Otimizar lista de hashtags"""
        
        # Limpar e formatar hashtags
        clean_hashtags = []
        for tag in hashtags:
            if tag.strip():
                clean_tag = tag.strip().lower()
                if not clean_tag.startswith('#'):
                    clean_tag = '#' + clean_tag
                
                # Remover caracteres especiais
                clean_tag = re.sub(r'[^\w#]', '', clean_tag)
                
                if clean_tag not in clean_hashtags and len(clean_tag) > 1:
                    clean_hashtags.append(clean_tag)
        
        # Limitar quantidade
        return clean_hashtags[:max_count]
    
    @classmethod
    def get_best_posting_times(cls, platform: str) -> List[Dict[str, Any]]:
        """Obter melhores horários de postagem por plataforma"""
        
        times = {
            'instagram': [
                {'hour': 8, 'minute': 0, 'day_weight': 'weekday'},
                {'hour': 14, 'minute': 0, 'day_weight': 'any'},
                {'hour': 20, 'minute': 0, 'day_weight': 'any'}
            ],
            'tiktok': [
                {'hour': 9, 'minute': 0, 'day_weight': 'any'},
                {'hour': 16, 'minute': 0, 'day_weight': 'any'},
                {'hour': 21, 'minute': 0, 'day_weight': 'any'}
            ],
            'youtube': [
                {'hour': 10, 'minute': 0, 'day_weight': 'weekend'},
                {'hour': 15, 'minute': 0, 'day_weight': 'any'},
                {'hour': 19, 'minute': 0, 'day_weight': 'weekday'}
            ],
            'facebook': [
                {'hour': 7, 'minute': 0, 'day_weight': 'weekday'},
                {'hour': 13, 'minute': 0, 'day_weight': 'any'},
                {'hour': 18, 'minute': 0, 'day_weight': 'any'}
            ]
        }
        
        return times.get(platform, [])