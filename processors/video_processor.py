import os
import subprocess
import tempfile
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import ffmpeg
from pathlib import Path

class VideoProcessor:
    """Processador principal de vídeos"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target_resolution = config.get('target_resolution', '1080x1920')  # 9:16
        self.max_duration = config.get('max_duration', 60)
        self.output_format = 'mp4'
    
    async def process_video(
        self, 
        input_path: str, 
        output_path: str,
        subtitle_text: Optional[str] = None,
        cta_text: Optional[str] = None,
        watermark_path: Optional[str] = None
    ) -> str:
        """Processar vídeo completo: redimensionar, legendas, CTA, watermark"""
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
        
        try:
            # Obter informações do vídeo
            video_info = self._get_video_info(input_path)
            
            # Criar pipeline FFmpeg
            input_stream = ffmpeg.input(input_path)
            
            # 1. Redimensionar e ajustar aspect ratio
            processed_stream = self._resize_video(input_stream, video_info)
            
            # 2. Cortar duração se necessário
            processed_stream = self._trim_duration(processed_stream)
            
            # 3. Adicionar filtros de melhoria
            processed_stream = self._enhance_video(processed_stream)
            
            # 4. Adicionar watermark se fornecido
            if watermark_path and os.path.exists(watermark_path):
                processed_stream = self._add_watermark(processed_stream, watermark_path)
            
            # 5. Configurar output
            output_stream = processed_stream.output(
                output_path,
                vcodec='libx264',
                acodec='aac',
                preset='medium',
                crf=23,  # Qualidade
                movflags='faststart',  # Otimizar para streaming
                format=self.output_format
            )
            
            # Executar processamento
            ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
            
            # 6. Adicionar legendas e CTA como overlay se fornecidos
            if subtitle_text or cta_text:
                temp_output = output_path + '.temp'
                os.rename(output_path, temp_output)
                await self._add_text_overlays(temp_output, output_path, subtitle_text, cta_text)
                os.remove(temp_output)
            
            return output_path
            
        except Exception as e:
            print(f"Erro ao processar vídeo: {str(e)}")
            raise
    
    def _get_video_info(self, input_path: str) -> Dict[str, Any]:
        """Obter informações do vídeo"""
        try:
            probe = ffmpeg.probe(input_path)
            video_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
            
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'duration': float(video_stream.get('duration', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '30/1')),
                'aspect_ratio': video_stream['width'] / video_stream['height']
            }
        except Exception as e:
            print(f"Erro ao obter info do vídeo: {str(e)}")
            return {'width': 720, 'height': 1280, 'duration': 30, 'fps': 30, 'aspect_ratio': 0.5625}
    
    def _resize_video(self, input_stream, video_info: Dict[str, Any]):
        """Redimensionar vídeo para 9:16 (Stories/Reels)"""
        target_width, target_height = map(int, self.target_resolution.split('x'))
        target_aspect = target_width / target_height  # 0.5625 para 9:16
        
        current_aspect = video_info.get('aspect_ratio', 1.0)
        
        if abs(current_aspect - target_aspect) < 0.01:
            # Já está no aspect ratio correto, apenas redimensionar
            return input_stream.filter('scale', target_width, target_height)
        
        elif current_aspect > target_aspect:
            # Vídeo é mais largo, fazer crop horizontal e scale
            crop_width = int(video_info['height'] * target_aspect)
            crop_x = (video_info['width'] - crop_width) // 2
            
            return input_stream.filter('crop', crop_width, video_info['height'], crop_x, 0).filter('scale', target_width, target_height)
        
        else:
            # Vídeo é mais alto, fazer crop vertical e scale
            crop_height = int(video_info['width'] / target_aspect)
            crop_y = (video_info['height'] - crop_height) // 2
            
            return input_stream.filter('crop', video_info['width'], crop_height, 0, crop_y).filter('scale', target_width, target_height)
    
    def _trim_duration(self, stream):
        """Cortar vídeo se exceder duração máxima"""
        return stream.filter('trim', duration=self.max_duration)
    
    def _enhance_video(self, stream):
        """Aplicar filtros de melhoria da imagem"""
        # Ajustar contraste, saturação e nitidez levemente
        enhanced = stream.filter('eq', contrast=1.1, saturation=1.2)
        enhanced = enhanced.filter('unsharp', luma_msize_x=5, luma_msize_y=5, luma_amount=0.8)
        return enhanced
    
    def _add_watermark(self, video_stream, watermark_path: str):
        """Adicionar watermark/logo no canto inferior direito"""
        watermark = ffmpeg.input(watermark_path)
        
        # Redimensionar watermark para 15% da largura do vídeo
        watermark_resized = watermark.filter('scale', 'iw*0.15', -1)
        
        # Posicionar no canto inferior direito com margem de 20px
        return ffmpeg.overlay(
            video_stream,
            watermark_resized,
            x='main_w-overlay_w-20',
            y='main_h-overlay_h-20'
        )
    
    async def _add_text_overlays(
        self, 
        input_path: str, 
        output_path: str, 
        subtitle_text: Optional[str] = None,
        cta_text: Optional[str] = None
    ):
        """Adicionar legendas e CTA como overlay de texto"""
        
        input_stream = ffmpeg.input(input_path)
        
        # Configurações de texto
        font_file = self._get_system_font()
        
        filters = []
        
        # Adicionar legendas (centro-inferior)
        if subtitle_text:
            subtitle_filter = f"drawtext=text='{subtitle_text}':fontfile='{font_file}':fontsize=36:fontcolor=white:bordercolor=black:borderw=2:x=(w-text_w)/2:y=h-150"
            filters.append(subtitle_filter)
        
        # Adicionar CTA (centro-superior)
        if cta_text:
            cta_filter = f"drawtext=text='{cta_text}':fontfile='{font_file}':fontsize=32:fontcolor=yellow:bordercolor=black:borderw=2:x=(w-text_w)/2:y=50"
            filters.append(cta_filter)
        
        # Aplicar todos os filtros
        if filters:
            output_stream = input_stream.filter('drawtext', **{
                'text': subtitle_text or cta_text,
                'fontfile': font_file,
                'fontsize': 36,
                'fontcolor': 'white',
                'bordercolor': 'black',
                'borderw': 2,
                'x': '(w-text_w)/2',
                'y': 'h-150' if subtitle_text else '50'
            })
        else:
            output_stream = input_stream
        
        # Se tiver ambos, aplicar o segundo filtro
        if subtitle_text and cta_text:
            output_stream = output_stream.filter('drawtext', **{
                'text': cta_text,
                'fontfile': font_file,
                'fontsize': 32,
                'fontcolor': 'yellow',
                'bordercolor': 'black',
                'borderw': 2,
                'x': '(w-text_w)/2',
                'y': '50'
            })
        
        output_stream = output_stream.output(output_path, vcodec='libx264', acodec='aac')
        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
    
    def _get_system_font(self) -> str:
        """Encontrar fonte do sistema para texto"""
        fonts = [
            '/System/Library/Fonts/Arial.ttf',  # macOS
            '/Windows/Fonts/arial.ttf',  # Windows
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
            '/usr/share/fonts/TTF/arial.ttf',  # Linux alternativo
        ]
        
        for font in fonts:
            if os.path.exists(font):
                return font
        
        return 'arial'  # Fallback