import subprocess
import os
import re
import time
import random
import json # Para un posible guardado estructurado si se prefiere
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable, CouldNotRetrieveTranscript

# --- Configuración ---
# URL del canal a procesar.
# Ejemplo de URL del canal de Julian Alborna que estabas usando: "https://www.youtube.com/@julianealborna/shorts"
CHANNEL_URL = "https://www.youtube.com/@julianealborna/shorts" 

OUTPUT_FILENAME_TXT = "transcripciones_julian_alborna.txt"
OUTPUT_FILENAME_MD = "transcripciones_julian_alborna.md" # Para formato Markdown
OUTPUT_DIR = "transcripciones_output" # Directorio para guardar los archivos
PREFERRED_LANGUAGES = ['es', 'es-419', 'es-ES']  # Prioridad de idiomas para la transcripción

# Crear directorio de salida si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)
output_path_txt = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME_TXT)
output_path_md = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME_MD)

def get_channel_video_ids_and_metadata(channel_url):
    """
    Obtiene los IDs, títulos, duraciones y conteo de vistas de los videos de un canal usando yt-dlp.
    Intenta filtrar por Shorts basándose en la URL o metadatos si es posible,
    aunque yt-dlp puede listar todos los videos si la URL es genérica del canal.
    """
    print(f"Obteniendo información de videos del canal: {channel_url}...")
    videos_data = []
    ydl_opts = {
        'extract_flat': 'in_playlist', # Obtener información de la playlist/canal de forma plana
        'quiet': True, # Suprimir salida de yt-dlp a la consola
        'no_warnings': True,
        'skip_download': True, # No descargar videos
        'force_generic_extractor': False,
        # 'playlistend': 5, # Descomentar para probar solo con los primeros N videos
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            if 'entries' in result and result['entries'] is not None: # Verificar que 'entries' no sea None
                for entry in result['entries']:
                    if entry and entry.get('id'): # Asegurarse que hay una entrada y tiene ID
                        video_id = entry.get('id')
                        title = entry.get('title', 'N/A')
                        duration = entry.get('duration') # Duración en segundos
                        view_count = entry.get('view_count')
                        
                        # Intento simple de filtrar Shorts por duración (ej. <= 70 segundos)
                        # YouTube Shorts son oficialmente <= 60s, pero puede haber variaciones.
                        # Si la URL ya apunta a la sección de Shorts, este filtro es menos crítico.
                        # if duration is not None and duration <= 70 : # Duración para shorts
                        # videos_data.append(...) 
                        # Si no se aplica filtro de duración, se procesarán todos los videos listados por yt-dlp para la URL dada.

                        videos_data.append({
                            'id': video_id,
                            'title': title,
                            'duration': duration,
                            'view_count': view_count
                        })
            else:
                print("No se encontraron 'entries' en la respuesta de yt-dlp. Verifica la URL del canal o si el canal está vacío/privado.")

    except yt_dlp.utils.DownloadError as e:
        print(f"\nError con yt-dlp al obtener información del canal (puede ser una URL incorrecta, restricciones del canal o problemas de red): {e}")
    except Exception as e:
        print(f"\nError inesperado al obtener lista de videos con yt-dlp: {type(e).__name__} - {e}")
    
    if videos_data:
        print(f"Encontrados {len(videos_data)} videos para procesar.")
    else:
        print("No se encontraron videos. Verifica la URL del canal y si tiene contenido accesible.")
    return videos_data


def get_transcript(video_id, preferred_langs):
    """
    Obtiene la transcripción de un video dado su ID.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Intentar encontrar en idiomas preferidos
        try:
            transcript_object = transcript_list.find_transcript(preferred_langs)
            print(f"  Transcripción encontrada en '{transcript_object.language}'.")
            # CORRECCIÓN: Usar item.text en lugar de item['text']
            return " ".join(item.text.strip() for item in transcript_object.fetch() if item.text and item.text.strip())
        except NoTranscriptFound:
            print(f"  No se encontró transcripción en idiomas preferidos ({preferred_langs}). Buscando en otros idiomas...")
            # Intentar con cualquier idioma disponible si no se encuentra en los preferidos
            available_transcripts = list(transcript_list)
            if available_transcripts:
                transcript_object = available_transcripts[0] # Tomar la primera disponible
                print(f"  Transcripción encontrada en idioma alternativo '{transcript_object.language}'.")
                # CORRECCIÓN: Usar item.text en lugar de item['text']
                return " ".join(item.text.strip() for item in transcript_object.fetch() if item.text and item.text.strip())
            else:
                print("  No hay ninguna transcripción disponible para este video.")
                return None
    except TranscriptsDisabled:
        print(f"  Transcripciones deshabilitadas para el video ID: {video_id}.")
        return None
    except VideoUnavailable:
        print(f"  Video ID: {video_id} no disponible.")
        return None
    except CouldNotRetrieveTranscript as e:
        # Este error puede ocurrir si el formato de la transcripción es inesperado (ej. XML vacío)
        print(f"  No se pudo recuperar la transcripción para el video ID: {video_id} (CouldNotRetrieveTranscript): {e}")
        return None
    except Exception as e:
        print(f"  Error inesperado al obtener transcripción para {video_id}: {type(e).__name__} - {e}")
        return None

def main():
    # Validación simple de la URL del canal para evitar que se ejecute con el placeholder.
    if "URL_CANAL_JULIAN_ALBORNA" in CHANNEL_URL : # Chequeo más genérico
        print(f"Error: Por favor, reemplaza el placeholder en 'CHANNEL_URL' en el script con la URL real del canal de YouTube. URL actual: {CHANNEL_URL}")
        return

    videos_to_process = get_channel_video_ids_and_metadata(CHANNEL_URL)
    
    if not videos_to_process:
        print("No hay videos para procesar. Terminando script.")
        return

    # Abrir archivos en modo 'write' para empezar de cero cada vez.
    with open(output_path_txt, 'w', encoding='utf-8') as f_txt, \
         open(output_path_md, 'w', encoding='utf-8') as f_md:

        # Escribir cabecera para el archivo Markdown
        f_md.write(f"# Transcripciones del Canal: {CHANNEL_URL}\n\n")

        total_videos = len(videos_to_process)
        transcriptions_obtained_count = 0

        for i, video_data in enumerate(videos_to_process, 1):
            video_id = video_data['id']
            title = video_data.get('title', 'Título no disponible')
            duration_seconds_raw = video_data.get('duration') # Puede ser None
            view_count_raw = video_data.get('view_count') # Puede ser None

            # Formatear duración y vistas para que sean más legibles o 'N/A'
            duration_seconds = duration_seconds_raw if duration_seconds_raw is not None else 'N/A'
            view_count = view_count_raw if view_count_raw is not None else 'N/A'


            print(f"\n--- Procesando video {i}/{total_videos}: '{title}' (ID: {video_id}) ---")
            
            transcript_text = get_transcript(video_id, PREFERRED_LANGUAGES)

            if transcript_text:
                transcriptions_obtained_count += 1
                word_count = len(transcript_text.split())
                
                # Formatear para TXT
                f_txt.write(f"Título del Video de YouTube: {title}\n")
                f_txt.write(f"Video ID: {video_id}\n")
                f_txt.write(f"Tiempo de duración del video: {duration_seconds} segundos\n")
                f_txt.write(f"Numero de reproducciones del video: {view_count}\n")
                f_txt.write(f"Conteo de palabras: {word_count}\n")
                f_txt.write("Transcripción:\n")
                f_txt.write(transcript_text)
                f_txt.write("\n\n---\n\n")

                # Formatear para Markdown
                f_md.write(f"## Título del Video de YouTube: {title}\n\n")
                f_md.write(f"**Video ID:** {video_id}\n\n")
                f_md.write(f"**Tiempo de duración del video:** {duration_seconds} segundos\n\n")
                f_md.write(f"**Numero de reproducciones del video:** {view_count}\n\n")
                f_md.write(f"**Conteo de palabras:** {word_count}\n\n")
                f_md.write(f"**Transcripción:**\n\n```text\n{transcript_text}\n```\n\n")
                f_md.write("---\n\n")
                
                print(f"  Información y transcripción guardadas para '{title}'.")
            else:
                # Incluso si no hay transcripción, registramos el video y sus metadatos
                f_txt.write(f"Título del Video de YouTube: {title}\n")
                f_txt.write(f"Video ID: {video_id}\n")
                f_txt.write(f"Tiempo de duración del video: {duration_seconds} segundos\n")
                f_txt.write(f"Numero de reproducciones del video: {view_count}\n")
                f_txt.write("Transcripción: No disponible o error al obtenerla.\n\n---\n\n")
                
                f_md.write(f"## Título del Video de YouTube: {title}\n\n")
                f_md.write(f"**Video ID:** {video_id}\n\n")
                f_md.write(f"**Tiempo de duración del video:** {duration_seconds} segundos\n\n")
                f_md.write(f"**Numero de reproducciones del video:** {view_count}\n\n")
                f_md.write(f"**Transcripción:** No disponible o error al obtenerla.\n\n---\n\n")
                print(f"  No se obtuvo transcripción para '{title}'. Información básica guardada.")


            # Retraso aleatorio entre 30 y 50 segundos, excepto para el último video
            if i < total_videos:
                # El rango de delay que tenías era random.randint(30, 50)
                # Lo mantendré así si lo prefieres, o puedes cambiarlo a 10-20
                delay = random.randint(30, 50) 
                print(f"--- Esperando {delay} segundos antes del próximo video... ---")
                time.sleep(delay)

        print("\n--- Proceso Completado ---")
        print(f"Total de videos procesados: {total_videos}")
        print(f"Total de transcripciones obtenidas: {transcriptions_obtained_count}")
        print(f"Archivo de texto guardado en: {output_path_txt}")
        print(f"Archivo Markdown guardado en: {output_path_md}")

if __name__ == "__main__":
    main()
