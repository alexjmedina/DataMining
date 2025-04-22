import subprocess
import os
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.exceptions import (NoTranscriptFound, TranscriptsDisabled, YouTubeRequestFailed, TooManyRequests) # type: ignore

def main():
    # --- Configuración ---
    channel_shorts_url = "https://www.youtube.com/@julianealborna/shorts"
    output_dir = "transcripciones_julian_alborna_shorts"
    preferred_languages = ['es', 'es-419', 'es-ES']
    # --- Fin Configuración ---

    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    print(f"Directorio '{output_dir}' listo para guardar transcripciones.")

    print(f"Obteniendo lista de Shorts del canal: {channel_shorts_url}...")

    # Paso 1: Obtener lista de IDs de video
    video_ids = get_video_ids(channel_shorts_url)
    if not video_ids:
        print("No se encontraron IDs de video válidos.")
        return

    print(f"Se procesarán {len(video_ids)} IDs de video únicos.")

    # Paso 2: Obtener y guardar transcripciones
    transcriptions_found_count = process_transcriptions(video_ids, preferred_languages, output_dir)

    # Resumen final
    print("\n--- Resumen del Proceso ---")
    print(f"Total de IDs de video encontrados: {len(video_ids)}")
    print(f"Transcripciones obtenidas y guardadas: {transcriptions_found_count}")
    print(f"Archivos guardados en el directorio: {output_dir}")
    print("Proceso completado.")

def get_video_ids(channel_url):
    """Obtiene los IDs de video de la URL del canal."""
    try:
        process = subprocess.run(
            [r'C:\Users\alexj\AppData\Local\Programs\Python\Python310\Scripts\yt-dlp', '--flat-playlist', '--print', 'url', channel_url],
            capture_output=True,
            text=True,
            check=True
        )
        video_urls = [url.strip() for url in process.stdout.split('\n') if url.strip()]
        print(f"Encontradas {len(video_urls)} posibles URLs de videos/shorts.")

        # Extraer IDs de video
        video_ids = []
        for url in video_urls:
            match = re.search(r"(?:/shorts/|v=)([a-zA-Z0-9_-]+)", url)
            if match:
                video_ids.append(match.group(1))

        return list(dict.fromkeys(video_ids))  # Eliminar duplicados

    except FileNotFoundError:
        print("\nError: 'yt-dlp' no encontrado. Instálalo con 'pip install yt-dlp'")
    except subprocess.CalledProcessError as e:
        print(f"\nError al ejecutar yt-dlp (código {e.returncode}): {e}")
        print(f"stderr: {e.stderr}")
    except Exception as e:
        print(f"\nError inesperado al obtener lista de videos: {e}")
    
    return None

def process_transcriptions(video_ids, preferred_languages, output_dir):
    """Procesa las transcripciones para cada ID de video."""
    transcriptions_found = 0

    for i, video_id in enumerate(video_ids, 1):
        print(f"\n--- Procesando video {i}/{len(video_ids)}: {video_id} ---")
        transcript_text = None
        video_title = video_id  # Valor por defecto

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            video_title = transcript_list.video_info.get('title', video_id)

            # Intentar obtener transcripción en idiomas preferidos
            try:
                transcript = transcript_list.find_transcript(preferred_languages)
                print(f"Transcripción encontrada ({transcript.language}) para: '{video_title}'")
            except NoTranscriptFound:
                # Intentar con cualquier idioma disponible
                available = list(transcript_list._fetch_from_api()['transcripts'].keys())
                if available:
                    transcript = transcript_list.find_transcript([available[0]])
                    print(f"Transcripción encontrada ({transcript.language}) en idioma alternativo para: '{video_title}'")
                else:
                    raise NoTranscriptFound

            # Obtener texto de la transcripción
            transcript_text = " ".join(item['text'] for item in transcript.fetch())

        except NoTranscriptFound:
            print(f"No se encontró transcripción para '{video_title}' ({video_id}).")
        except TranscriptsDisabled:
            print(f"Transcripciones deshabilitadas para '{video_title}' ({video_id}).")
        except YouTubeRequestFailed as e:
            print(f"Error de solicitud a YouTube: {e}")
        except TooManyRequests:
            print("Demasiadas solicitudes. Espera antes de reintentar.")
            return transcriptions_found
        except Exception as e:
            print(f"Error inesperado al procesar {video_id}: {e}")

        # Guardar transcripción si se encontró
        if transcript_text:
            if save_transcription(video_title, video_id, transcript_text, output_dir):
                transcriptions_found += 1

    return transcriptions_found

def save_transcription(title, video_id, text, output_dir):
    """Guarda la transcripción en un archivo."""
    # Limpiar título para nombre de archivo
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()
    safe_title = re.sub(r'\s+', '_', safe_title)[:50] or "video"
    
    filename = os.path.join(output_dir, f"{safe_title}_{video_id}.txt")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Título del Video: {title}\n")
            f.write(f"ID del Video: {video_id}\n\n")
            f.write(text)
        print(f"Transcripción guardada en: {filename}")
        return True
    except IOError as e:
        print(f"Error al guardar {filename}: {e}")
        return False

if __name__ == "__main__":
    main()