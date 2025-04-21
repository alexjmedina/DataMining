import subprocess
import os
import re
from youtube_transcript_api import YoutubeTranscriptApi
from youtube_transcript_api.exceptions import NoTranscriptFound, TranscriptsDisabled, YouTubeRequestFailed, TooManyRequests

# --- Configuración ---
# URL de la sección Shorts del canal de Julian E. Alborna
channel_shorts_url = "https://www.youtube.com/@julianealborna/shorts"
# Directorio donde se guardarán las transcripciones
output_dir = "transcripciones_julian_alborna_shorts"
# Idiomas de transcripción preferidos (se intentará obtener el primero disponible)
# 'es' para español, 'es-419' para español latinoamericano, 'es-ES' para español de España
preferred_languages = ['es', 'es-419', 'es-ES']
# --- Fin Configuración ---

# Crear el directorio de salida si no existe
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Directorio '{output_dir}' creado para guardar las transcripciones.")

print(f"Obteniendo lista de Shorts del canal: {channel_shorts_url}...")

# --- Paso 1: Obtener lista de IDs de video usando yt-dlp ---
# Usamos yt-dlp para extraer las URLs de los videos de la página /shorts.
# --flat-playlist: lista los elementos de la "lista de reproducción" (página del canal) sin descargar.
# --print url: solo imprime la URL de cada elemento encontrado.
try:
    # Asegúrate de que yt-dlp está instalado y accesible en tu PATH.
    # Si estás en Windows, es posible que necesites shell=True.
    process = subprocess.run(
        ['yt-dlp', '--flat-playlist', '--print', 'url', channel_shorts_url],
        capture_output=True,
        text=True,
        check=True,  # Lanza un error si el comando falla
        shell=True # Keep shell=True for now, might help find it, but explicit path is better
    )
    video_urls = process.stdout.strip().split('\n')
    # Filtramos las URLs vacías que puedan aparecer
    video_urls = [url for url in video_urls if url.strip()]

    print(f"Encontradas {len(video_urls)} posibles URLs de videos/shorts.")

except FileNotFoundError:
    print("\nError: 'yt-dlp' command not found.")
    print("Por favor, instala yt-dlp (p. ej., `pip install yt-dlp`) y asegúrate de que está en el PATH de tu sistema.")
    print("Si ya lo tienes instalado pero sigue el error, intenta ejecutar el script desde un entorno donde 'yt-dlp' sea accesible.")
    exit()
except subprocess.CalledProcessError as e:
    print(f"\nError al ejecutar yt-dlp (código {e.returncode}): {e}")
    print(f"stderr: {e.stderr}")
    print("Hubo un problema al obtener la lista de videos. Revisa la URL del canal y tu conexión a internet.")
    exit()
except Exception as e:
    print(f"\nOcurrió un error inesperado al obtener la lista de videos: {e}")
    exit()

# Extraer los IDs de video de las URLs
video_ids = []
for url in video_urls:
    # Los IDs pueden estar en formato /shorts/ID o watch?v=ID (yt-dlp a veces devuelve watch?v=)
    match_shorts = re.search(r"/shorts/([a-zA-Z0-9_-]+)", url)
    match_watch = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if match_shorts:
        video_ids.append(match_shorts.group(1))
    elif match_watch:
        video_ids.append(match_watch.group(1))
    else:
        print(f"Saltando URL (no se pudo extraer ID): {url}")

# Eliminar IDs duplicados si los hubiera (aunque yt-dlp debería ser plano, por si acaso)
video_ids = list(dict.fromkeys(video_ids))

if not video_ids:
    print("No se pudieron extraer IDs de video válidos de las URLs obtenidas.")
    print("Verifica si la URL del canal de Shorts es correcta y si yt-dlp funciona.")
    exit()

print(f"Se procesarán {len(video_ids)} IDs de video únicos.")

# --- Paso 2: Obtener transcripciones para cada ID usando youtube-transcript-api ---
transcriptions_found_count = 0

for i, video_id in enumerate(video_ids):
    print(f"\n--- Procesando video {i+1}/{len(video_ids)}: {video_id} ---")
    transcript_text = None
    video_title = video_id  # Título predeterminado si no se puede obtener

    try:
        # Obtener la lista de transcripciones disponibles para este video (incluye título)
        transcript_list = YoutubeTranscriptApi.list_transcripts(video_id)
        video_title = transcript_list.video_info.get('title', video_id) # Obtener título

        # Intentar encontrar la transcripción en los idiomas preferidos o la primera disponible
        try:
             transcript = transcript_list.find_transcript(preferred_languages)
             print(f"Transcipción encontrada ({transcript.language} - {'manual' if transcript.is_manual else 'automática'}) para: '{video_title}'")
        except NoTranscriptFound:
             # Si no se encuentra en los preferidos, intentar obtener CUALQUIER transcripción disponible (manual o automática)
             # Esto maneja casos donde solo hay, por ejemplo, inglés o subtítulos no identificados.
             available_transcripts = transcript_list._fetch_from_api()['transcripts']
             if available_transcripts:
                 # Tomar la primera disponible
                 transcript = transcript_list.find_transcript([list(available_transcripts.keys())[0]])
                 print(f"Transcipción encontrada ({transcript.language} - {'manual' if transcript.is_manual else 'automática'}) en idioma alternativo para: '{video_title}'")
             else:
                 raise NoTranscriptFound # Si no hay ninguna, lanzar la excepción original

        # Obtener los datos de la transcripción
        transcript_data = transcript.fetch()

        # Concatenar el texto de la transcripción
        # Unimos los textos de cada segmento con un espacio para formar un párrafo continuo.
        transcript_text = " ".join([item['text'] for item in transcript_data])


    except NoTranscriptFound:
        print(f"No se encontró transcripción (manual ni automática en idiomas preferidos o alternativos) para el video '{video_title}' ({video_id}).")
    except TranscriptsDisabled:
        print(f"Las transcripciones están deshabilitadas por el creador para el video '{video_title}' ({video_id}).")
    except YouTubeRequestFailed as e:
         print(f"Error de solicitud a YouTube para {video_id}: {e}")
    except TooManyRequests:
         print(f"Demasiadas solicitudes a la API de YouTube. Espera un poco antes de volver a intentarlo.")
         # Puedes agregar una pausa aquí si quieres reintentar automáticamente
         # import time
         # time.sleep(60) # Esperar 60 segundos antes de continuar (o salir)
         # continue # o exit()
    except Exception as e:
        # Capturar cualquier otro error inesperado durante el proceso de transcripción
        print(f"Ocurrió un error inesperado al procesar la transcripción de {video_id}: {e}")


    # Guardar la transcripción si se encontró
    if transcript_text:
        transcriptions_found_count += 1
        # Limpiar el título para usarlo en el nombre del archivo
        # Reemplazar caracteres no seguros con guiones bajos o eliminarlos
        safe_title = re.sub(r'[^\w\s-]', '', video_title).strip() # Eliminar caracteres no alfanuméricos, espacios o guiones
        safe_title = re.sub(r'\s+', '_', safe_title) # Reemplazar secuencias de espacios con un guion bajo
        safe_title = safe_title[:50] # Limitar la longitud del título en el nombre del archivo para evitar problemas

        if not safe_title: # Si el título sanitizado queda vacío
             safe_title = "video" # Usar un nombre genérico + ID

        filename = os.path.join(output_dir, f"{safe_title}_{video_id}.txt")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Título del Video: {video_title}\n")
                f.write(f"ID del Video: {video_id}\n\n")
                f.write(transcript_text)
            print(f"Transcipción guardada en: {filename}")
        except IOError as e:
            print(f"Error al guardar el archivo {filename}: {e}")

print("\n--- Resumen del Proceso ---")
print(f"Total de IDs de video encontrados: {len(video_ids)}")
print(f"Transcripciones obtenidas y guardadas: {transcriptions_found_count}")
print(f"Archivos guardados en el directorio: {output_dir}")
print("Proceso completado.")