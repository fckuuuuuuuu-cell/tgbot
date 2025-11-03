import tidalapi
import csv
import time
from collections import defaultdict

# Paso 1: Autenticación en TIDAL
session = tidalapi.Session()
print("🔗 Abre este enlace en tu navegador e inicia sesión en TIDAL:")
device_code = session.login_oauth_simple()
print("⌛ Esperando autenticación...")

while not session.check_login():
    time.sleep(2)

print("✅ Sesión iniciada correctamente.")

# Paso 2: Agrupar canciones por playlist desde el CSV
playlists = defaultdict(list)  # Diccionario: {nombre_playlist: [lista de track_ids]}

with open("musica.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        playlist_name = row.get("Playlist name", "").strip()
        tidal_id = row.get("Tidal - id", "").strip()
        track_name = row.get("Track name", "").strip()
        artist_name = row.get("Artist name", "").strip()

        # Solo agregar si la playlist tiene nombre y el ID es un número válido
        if playlist_name and tidal_id.isdigit():
            playlists[playlist_name].append(int(tidal_id))
            print(f"Asignado a playlist '{playlist_name}': {track_name} - {artist_name} (ID: {tidal_id})")
        else:
            print(f"⏭️ Ignorado (falta playlist o ID válido): {track_name} - {artist_name}")

# Paso 3: Crear cada playlist en TIDAL y agregar las canciones
for pname, track_ids in playlists.items():
    print(f"\n🎵 Creando playlist: {pname} con {len(track_ids)} canciones")
    tidal_playlist = session.user.create_playlist(pname, f"Importada desde CSV: {pname}")

    # Añadir canciones en bloques de máximo 50 para evitar errores
    for i in range(0, len(track_ids), 50):
        chunk = track_ids[i:i+50]
        tidal_playlist.add(chunk)
        time.sleep(1)  # Pausa para no saturar la API

    print(f"✅ Playlist '{pname}' creada y completada.")

print("\n🎉 ¡Todas las playlists han sido importadas correctamente!")
