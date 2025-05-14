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
    Paso 1: Obtiene los IDs de los videos de un canal usando yt-dlp con extract_flat.
    Paso 2: Para cada ID, obtiene metadatos detallados (título, duración, vistas).
    """
    print(f"Obteniendo IDs de videos del canal: {channel_url}...")
    video_ids = []
    initial_ydl_opts = {
        'extract_flat': 'playlist', 
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'force_generic_extractor': False,
        # 'playlistend': 5, # Descomentar para probar solo con los primeros N videos
    }

    try:
        with yt_dlp.YoutubeDL(initial_ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            if 'entries' in result and result['entries'] is not None:
                for entry in result['entries']:
                    if entry and entry.get('id'):
                        video_ids.append(entry.get('id'))
            else:
                print("No se encontraron 'entries' (videos) en la respuesta inicial de yt-dlp. Verifica la URL del canal.")
                return []
    except yt_dlp.utils.DownloadError as e:
        print(f"\nError con yt-dlp al listar IDs del canal: {e}")
        return []
    except Exception as e:
        print(f"\nError inesperado al listar IDs con yt-dlp: {type(e).__name__} - {e}")
        return []

    if not video_ids:
        print("No se encontraron IDs de video. Verifica la URL del canal y si tiene contenido accesible.")
        return []

    print(f"Encontrados {len(video_ids)} IDs de video. Obteniendo metadatos para cada uno...")
    
    videos_data = []
    detailed_ydl_opts = { 
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'force_generic_extractor': False,
    }

    for i, video_id in enumerate(video_ids, 1):
        print(f"  Obteniendo metadatos para video {i}/{len(video_ids)} (ID: {video_id})...")
        video_url = f"https://www.youtube.com/watch?v={video_id}" 
        try:
            with yt_dlp.YoutubeDL(detailed_ydl_opts) as ydl_detail:
                video_info = ydl_detail.extract_info(video_url, download=False)
                title = video_info.get('title', 'N/A')
                duration = video_info.get('duration')  
                view_count = video_info.get('view_count')
                
                videos_data.append({
                    'id': video_id,
                    'title': title,
                    'duration': duration,
                    'view_count': view_count
                })
        except yt_dlp.utils.DownloadError as e:
            print(f"    Error con yt-dlp al obtener metadatos para {video_id} ({video_url}): {e}. Se usarán valores N/A.")
            videos_data.append({'id': video_id, 'title': f'Error al obtener título para {video_id}', 'duration': None, 'view_count': None})
        except Exception as e:
            print(f"    Error inesperado al obtener metadatos para {video_id} ({video_url}): {type(e).__name__} - {e}. Se usarán valores N/A.")
            videos_data.append({'id': video_id, 'title': f'Error al obtener título para {video_id}', 'duration': None, 'view_count': None})
        
        if i < len(video_ids): 
             time.sleep(random.uniform(3, 6)) # Delay corto entre peticiones de metadatos

    if videos_data:
        print(f"Metadatos obtenidos para {len(videos_data)} videos.")
    return videos_data


def get_transcript(video_id, preferred_langs):
    """
    Obtiene la transcripción de un video dado su ID.
    Devuelve el texto de la transcripción o None si no se puede obtener.
    También devuelve un booleano indicando si se sospecha un bloqueo de IP.
    """
    ip_block_suspected = False
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript_object = transcript_list.find_transcript(preferred_langs)
            print(f"  Transcripción encontrada en '{transcript_object.language}'.")
            return " ".join(item.text.strip() for item in transcript_object.fetch() if item.text and item.text.strip()), ip_block_suspected
        except NoTranscriptFound:
            print(f"  No se encontró transcripción en idiomas preferidos ({preferred_langs}). Buscando en otros idiomas...")
            available_transcripts = list(transcript_list)
            if available_transcripts:
                transcript_object = available_transcripts[0] 
                print(f"  Transcripción encontrada en idioma alternativo '{transcript_object.language}'.")
                return " ".join(item.text.strip() for item in transcript_object.fetch() if item.text and item.text.strip()), ip_block_suspected
            else:
                print(f"  No hay ninguna transcripción disponible para el video ID: {video_id}.")
                return None, ip_block_suspected
    except TranscriptsDisabled:
        print(f"  Transcripciones deshabilitadas para el video ID: {video_id}.")
    except VideoUnavailable:
        print(f"  Video ID: {video_id} no disponible.")
    except CouldNotRetrieveTranscript as e:
        print(f"  No se pudo recuperar la transcripción para el video ID: {video_id} (CouldNotRetrieveTranscript): {e}")
        # Esta excepción es un fuerte indicador de un bloqueo de IP
        if "YouTube is blocking requests from your IP" in str(e):
            ip_block_suspected = True
            print("  !!! SOSPECHA DE BLOQUEO DE IP DETECTADA !!!")
    except Exception as e: # Captura otras excepciones como ParseError
        print(f"  Error inesperado al obtener transcripción para {video_id}: {type(e).__name__} - {e}")
    
    return None, ip_block_suspected

def main():
    if "URL_CANAL_JULIAN_ALBORNA" in CHANNEL_URL and CHANNEL_URL == "https://www.youtube.com/@julianealborna/shorts": 
        print(f"Error: Por favor, reemplaza el placeholder en 'CHANNEL_URL' en el script con la URL real del canal de YouTube. URL actual: {CHANNEL_URL}")
        return

    videos_to_process = get_channel_video_ids_and_metadata(CHANNEL_URL)
    
    if not videos_to_process:
        print("No hay videos para procesar. Terminando script.")
        return

    with open(output_path_txt, 'w', encoding='utf-8') as f_txt, \
         open(output_path_md, 'w', encoding='utf-8') as f_md:

        f_md.write(f"# Transcripciones del Canal: {CHANNEL_URL}\n\n")

        total_videos = len(videos_to_process)
        transcriptions_obtained_count = 0

        for i, video_data in enumerate(videos_to_process, 1):
            video_id = video_data['id']
            title = video_data.get('title', f'Título no disponible para ID: {video_id}')
            duration_seconds_raw = video_data.get('duration') 
            view_count_raw = video_data.get('view_count') 

            duration_seconds = duration_seconds_raw if duration_seconds_raw is not None else 'N/A'
            view_count = view_count_raw if view_count_raw is not None else 'N/A'
            
            video_full_url = f"https://www.youtube.com/watch?v={video_id}"

            print(f"\n--- Procesando video {i}/{total_videos}: '{title}' (ID: {video_id}) ---")
            
            transcript_text, ip_block_detected = get_transcript(video_id, PREFERRED_LANGUAGES)

            if transcript_text:
                transcriptions_obtained_count += 1
                word_count = len(transcript_text.split())
                
                f_txt.write(f"Título del Video de YouTube: {title}\n")
                f_txt.write(f"URL del Video: {video_full_url}\n") 
                f_txt.write(f"Video ID: {video_id}\n")
                f_txt.write(f"Tiempo de duración del video: {duration_seconds} segundos\n")
                f_txt.write(f"Numero de reproducciones del video: {view_count}\n")
                f_txt.write(f"Conteo de palabras: {word_count}\n")
                f_txt.write("Transcripción:\n")
                f_txt.write(transcript_text)
                f_txt.write("\n\n---\n\n")

                f_md.write(f"## Título del Video de YouTube: {title}\n\n")
                f_md.write(f"**URL del Video:** [{video_full_url}]({video_full_url})\n\n") 
                f_md.write(f"**Video ID:** {video_id}\n\n")
                f_md.write(f"**Tiempo de duración del video:** {duration_seconds} segundos\n\n")
                f_md.write(f"**Numero de reproducciones del video:** {view_count}\n\n")
                f_md.write(f"**Conteo de palabras:** {word_count}\n\n")
                f_md.write(f"**Transcripción:**\n\n```text\n{transcript_text}\n```\n\n")
                f_md.write("---\n\n")
                
                print(f"  Información y transcripción guardadas para '{title}'.")
            else:
                f_txt.write(f"Título del Video de YouTube: {title}\n")
                f_txt.write(f"URL del Video: {video_full_url}\n") 
                f_txt.write(f"Video ID: {video_id}\n")
                f_txt.write(f"Tiempo de duración del video: {duration_seconds} segundos\n")
                f_txt.write(f"Numero de reproducciones del video: {view_count}\n")
                f_txt.write("Transcripción: No disponible o error al obtenerla.\n\n---\n\n")
                
                f_md.write(f"## Título del Video de YouTube: {title}\n\n")
                f_md.write(f"**URL del Video:** [{video_full_url}]({video_full_url})\n\n") 
                f_md.write(f"**Video ID:** {video_id}\n\n")
                f_md.write(f"**Tiempo de duración del video:** {duration_seconds} segundos\n\n")
                f_md.write(f"**Numero de reproducciones del video:** {view_count}\n\n")
                f_md.write(f"**Transcripción:** No disponible o error al obtenerla.\n\n---\n\n")
                print(f"  No se obtuvo transcripción para '{title}'. Información básica guardada.")

            # --- LÓGICA DE DELAY MODIFICADA ---
            if i < total_videos:
                if ip_block_detected:
                    # Enfriamiento largo si se detectó bloqueo de IP
                    cool_down_delay = 300 # 5 minutos
                    print(f"--- BLOQUEO DE IP DETECTADO. Enfriando por {cool_down_delay} segundos... ---")
                    time.sleep(cool_down_delay)
                else:
                    # Delay normal más largo
                    delay = random.randint(45, 90) 
                    print(f"--- Esperando {delay} segundos antes del próximo video (para transcripción)... ---")
                    time.sleep(delay)
            # --- FIN LÓGICA DE DELAY MODIFICADA ---

        print("\n--- Proceso Completado ---")
        print(f"Total de videos procesados: {total_videos}")
        print(f"Total de transcripciones obtenidas: {transcriptions_obtained_count}")
        print(f"Archivo de texto guardado en: {output_path_txt}")
        print(f"Archivo Markdown guardado en: {output_path_md}")

if __name__ == "__main__":
    main()
