# Spotify Stream Deck Daemon

Daemon local para controlar Spotify desde los botones de tu Stream Deck,
sin depender del plugin oficial de Spotify.

## Arquitectura

```
Botón Stream Deck  →  script delgado (scripts/*.py)  →  daemon local (daemon.py)  →  Web API de Spotify
```

- El **daemon** corre siempre en segundo plano, mantiene la sesión de Spotify
  ya autenticada en memoria, y expone endpoints HTTP simples en tu propia
  máquina (`127.0.0.1:5111`).
- Los **scripts delgados** solo hacen una llamada HTTP al daemon — arrancan
  casi instantáneo porque no cargan `spotipy` ni manejan autenticación.
- Cada botón del Stream Deck se configura con la acción **System: Open**
  apuntando a uno de estos scripts.

## Seguridad

- El daemon **solo escucha en `127.0.0.1`** (nunca `0.0.0.0`) — nada fuera de
  tu máquina puede conectarse, ni siquiera otros dispositivos en tu misma
  red WiFi.
- Cada request debe incluir un **token compartido** (`X-Daemon-Token`) —
  evita que una pestaña de navegador random controle tu Spotify sin que te
  des cuenta (técnica conocida como "localhost drive-by").
- **Sin CORS habilitado** — ninguna página web puede pegarle al daemon desde
  JavaScript, tenga o no el token.
- No usa HTTPS a propósito: el tráfico nunca sale de tu máquina, así que
  cifrarlo no aporta protección real y solo añade complejidad.

## 1. Instalar dependencias

```bash
cd spotify-streamdeck-daemon
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Genera un token único para el daemon:

```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

Edita `.env` y llena:
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` — las mismas credenciales que
  usaste para el MCP (o crea una app nueva en el
  [dashboard de Spotify](https://developer.spotify.com/dashboard))
- `DAEMON_TOKEN` — el valor que acabas de generar

## 3. Configurar el token en los scripts

Edita `scripts/_config.py` y pega el mismo `DAEMON_TOKEN` en
`DAEMON_TOKEN_FALLBACK`:

```python
DAEMON_TOKEN_FALLBACK = "el_token_que_generaste"
```

(Alternativa más segura: en vez de dejarlo en el archivo, configúralo como
variable de entorno del sistema llamada `DAEMON_TOKEN` — en Windows esto lo
haces desde "Editar las variables de entorno del sistema"; el Stream Deck sí
respeta las variables de entorno de usuario al ejecutar procesos.)

## 4. Primera autenticación

Arranca el daemon una vez manualmente con `--login` para autorizar la app:

```bash
python run.py --login
```

Se abrirá el navegador pidiéndote autorizar el acceso a tu cuenta de
Spotify — acéptalo. Esto pasa **una sola vez**; el token queda guardado en
`.spotify_token_cache` y se refresca solo después.

El arranque normal (`python run.py`, sin `--login`) **nunca abre el
navegador**: si no encuentra un token válido, termina con un error que te
indica ejecutar `python run.py --login`. Así una tarea en segundo plano no se
quede colgada esperando un login.

Prueba que responde:

```bash
curl http://127.0.0.1:5111/health
```

Deberías ver `{"status":"ok"}`.

## 5. Configurar que el daemon arranque solo

Para que no tengas que abrir una terminal cada vez:

**Windows (Programador de tareas):**
1. Abre el Programador de tareas → Crear tarea básica
2. Desencadenador: "Al iniciar sesión"
3. Acción: iniciar un programa →
   `C:\ruta\a\spotify-streamdeck-daemon\venv\Scripts\python.exe`
   con argumentos: `C:\ruta\a\spotify-streamdeck-daemon\run.py`

**macOS (launchd):** crea un `.plist` en `~/Library/LaunchAgents/` que
ejecute el mismo `python run.py` con `RunAtLoad` en `true`.

**Linux (systemd, modo usuario):** crea un servicio en
`~/.config/systemd/user/spotify-daemon.service` con
`ExecStart=/ruta/venv/bin/python /ruta/run.py`, y actívalo con
`systemctl --user enable --now spotify-daemon`.

## 6. Configurar los botones del Stream Deck

Para cada botón:
1. Arrastra la acción **System → Open**
2. En "App / File", selecciona el Python del venv:
   `.../spotify-streamdeck-daemon/venv/bin/python` (o `python.exe` en Windows)
3. En los argumentos, apunta al script correspondiente, ej.:
   `.../spotify-streamdeck-daemon/scripts/next.py`

Repite para `play.py`, `pause.py`, `previous.py`, y duplica `volume_40.py`
si quieres botones de volumen a niveles específicos.

## Endpoints disponibles

| Endpoint | Método | Descripción |
|---|---|---|
| `/health` | GET | Health check, sin autenticación |
| `/play` | POST | Reanuda reproducción |
| `/pause` | POST | Pausa |
| `/next` | POST | Siguiente canción |
| `/previous` | POST | Canción anterior |
| `/volume?level=N` | POST | Cambia volumen (0-100) |
| `/now-playing` | GET | Info de lo que se reproduce actualmente |

Todos excepto `/health` requieren el header `X-Daemon-Token`.

## Notas

- Necesitas Spotify abierto y activo en algún dispositivo (ver conversación
  anterior sobre "dispositivo activo" de Spotify Connect) para que los
  comandos de reproducción funcionen.
- Este daemon comparte la misma cuenta y lógica de autenticación que el MCP
  de Spotify — si ya autorizaste uno, puedes copiar el
  `.spotify_token_cache` en vez de volver a autorizar, siempre que uses el
  mismo `SPOTIFY_CLIENT_ID`/`SECRET`.
- No subas `.env` ni `.spotify_token_cache` a ningún repositorio público.
