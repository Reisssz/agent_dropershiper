from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import os
from typing import Optional, Tuple

class WatermarkManager:
    """Gerenciador de watermarks e logos"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logo_path = config.get('logo_path')
        self.brand_name = config.get('brand_name', 'Pet Shop')
        self.brand_color = config.get('brand_color', '#FF6B6B')
    
    def create_text_watermark(
        self, 
        text: str, 
        output_path: str,
        size: Tuple[int, int] = (300, 100),
        font_size: int = 24
    ) -> str:
        """Criar watermark de texto"""
        
        try:
            # Criar imagem transparente
            img = Image.new('RGBA', size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Tentar carregar fonte personalizada
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Calcular posição centralizada
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            # Desenhar texto com sombra
            shadow_offset = 2
            draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 128), font=font)
            draw.text((x, y), text, fill=self.brand_color + 'E6', font=font)  # 90% opacidade
            
            # Salvar
            img.save(output_path, 'PNG')
            return output_path
            
        except Exception as e:
            print(f"Erro ao criar watermark de texto: {str(e)}")
            return ""
    
    def create_logo_watermark(
        self, 
        logo_path: str, 
        output_path: str,
        max_size: Tuple[int, int] = (150, 150),
        opacity: float = 0.8
    ) -> str:
        """Processar logo para usar como watermark"""
        
        if not os.path.exists(logo_path):
            return ""
        
        try:
            # Abrir e redimensionar logo
            with Image.open(logo_path) as img:
                # Converter para RGBA se necessário
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Redimensionar mantendo proporção
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Ajustar opacidade
                if opacity < 1.0:
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(opacity)
                
                # Salvar
                img.save(output_path, 'PNG')
                return output_path
                
        except Exception as e:
            print(f"Erro ao processar logo: {str(e)}")
            return ""
    
    def get_watermark_path(self, campaign_id: str) -> str:
        """Obter caminho do watermark para uma campanha"""
        
        watermarks_dir = "assets/watermarks"
        os.makedirs(watermarks_dir, exist_ok=True)
        
        # Se existe logo personalizado, usar ele
        if self.logo_path and os.path.exists(self.logo_path):
            watermark_path = f"{watermarks_dir}/logo_{campaign_id}.png"
            return self.create_logo_watermark(self.logo_path, watermark_path)
        
        # Senão, criar watermark de texto
        watermark_path = f"{watermarks_dir}/text_{campaign_id}.png"
        return self.create_text_watermark(self.brand_name, watermark_path)