import whisper
import openai
from typing import Optional, Dict, Any
import os
import tempfile

class SubtitleGenerator:
    """Gerador de legendas usando Whisper"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.use_api = config.get('use_openai_api', False)
        self.api_key = config.get('openai_api_key')
        
        if not self.use_api:
            # Carregar modelo Whisper local
            model_size = config.get('whisper_model', 'base')  # tiny, base, small, medium, large
            self.model = whisper.load_model(model_size)
        elif self.api_key:
            openai.api_key = self.api_key
    
    async def generate_subtitles(self, video_path: str) -> Optional[str]:
        """Gerar legendas a partir do áudio do vídeo"""
        
        if not os.path.exists(video_path):
            return None
        
        try:
            # Extrair áudio do vídeo
            audio_path = await self._extract_audio(video_path)
            
            if not audio_path:
                return None
            
            # Transcrever áudio
            if self.use_api and self.api_key:
                transcript = await self._transcribe_with_api(audio_path)
            else:
                transcript = await self._transcribe_local(audio_path)
            
            # Limpar arquivo temporário
            if audio_path != video_path:
                os.remove(audio_path)
            
            return transcript
            
        except Exception as e:
            print(f"Erro ao gerar legendas: {str(e)}")
            return None
    
    async def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extrair áudio do vídeo"""
        try:
            import ffmpeg
            
            # Criar arquivo temporário para o áudio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                audio_path = temp_file.name
            
            # Extrair áudio usando FFmpeg
            stream = ffmpeg.input(video_path)
            audio = stream.audio
            out = ffmpeg.output(audio, audio_path, acodec='pcm_s16le', ar=16000, ac=1)
            ffmpeg.run(out, overwrite_output=True, quiet=True)
            
            return audio_path
            
        except Exception as e:
            print(f"Erro ao extrair áudio: {str(e)}")
            return None
    
    async def _transcribe_local(self, audio_path: str) -> Optional[str]:
        """Transcrever usando modelo Whisper local"""
        try:
            result = self.model.transcribe(audio_path, language='pt')  # Português
            return result.get('text', '').strip()
        except Exception as e:
            print(f"Erro na transcrição local: {str(e)}")
            return None
    
    async def _transcribe_with_api(self, audio_path: str) -> Optional[str]:
        """Transcrever usando API da OpenAI"""
        try:
            with open(audio_path, 'rb') as audio_file:
                transcript = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language='pt'
                )
            return transcript.get('text', '').strip()
        except Exception as e:
            print(f"Erro na transcrição via API: {str(e)}")
            return None
    
    def clean_transcript(self, text: str, max_length: int = 100) -> str:
        """Limpar e otimizar texto da transcrição para overlay"""
        if not text:
            return ""
        
        # Remover caracteres especiais e normalizar
        import re
        text = re.sub(r'[^\w\s\.,!?]', '', text)
        text = ' '.join(text.split())  # Normalizar espaços
        
        # Truncar se muito longo
        if len(text) > max_length:
            words = text.split()
            truncated = []
            length = 0
            
            for word in words:
                if length + len(word) + 1 > max_length:
                    break
                truncated.append(word)
                length += len(word) + 1
            
            text = ' '.join(truncated) + '...'
        
        return text