# net-termux

Mira desde el teléfono cómo está tu red: la señal Wi-Fi, si hay Internet, qué equipos
están conectados y cómo va tu red de Tailscale. Corre en **Termux para Android, sin root**.

```text
$ net status

Red
● Wi-Fi · 5 GHz · señal excelente (-39 dBm) · 433 Mbps
  Este teléfono 192.168.1.108 · router .1 · 9 ms
● Internet · 31 ms · DNS 87 ms
  Mi Proveedor · Bogotá · 203.0.113.45
● Tailscale · 100.64.0.10

Equipos · 6 en 192.168.1.0/24
● router         .1    Router           9 ms  web https
● nas            .20   Linux            7 ms  ssh web smb
● portatil       .31   Windows         14 ms  ssh smb
● tele-sala      .42   TV/Chromecast   22 ms  cast
● sin nombre     .57   Linux/Android   69 ms
◆ este teléfono  .108  Android

Medido en 4,7 s
```

```text
$ tailscale status

Tailscale · ejemplo.ts.net
◆ Este teléfono · mi-telefono
  100.64.0.10 · fd7a:115c:a1e0::a

Equipos · 3 de 4 en línea
● nas         100.64.0.20   Linux    16 ms
● portatil    100.64.0.31   Windows   8 ms
◐ servidor    100.64.0.40   Linux    22 ms
  la clave vence en 12 días
○ tablet      100.64.0.55   Android  desconectado hace 2 meses

Lista: API de Tailscale (ahora) · estado medido desde aquí
```

## Instalar

En Termux, un solo comando:

```bash
curl -fsSL https://raw.githubusercontent.com/andresgarcia0313/net-termux/main/install.sh | bash
```

Instala lo que falte (`python`, `git`, `termux-api`), descarga el proyecto en
`~/.local/share/net-termux` y deja los comandos en `~/.local/bin`. Para ver la señal Wi-Fi
instala también la app **Termux:API** (F-Droid o Google Play), de la misma tienda que Termux.

Volver a correr el comando **actualiza**. Para **quitarlo**:

```bash
curl -fsSL https://raw.githubusercontent.com/andresgarcia0313/net-termux/main/install.sh | bash -s -- --uninstall
```

## Comandos

| Comando | Qué hace |
|---|---|
| `net status` | Wi-Fi, router, Internet (latencia, DNS, proveedor, IP pública), Tailscale y equipos de la red |
| `net status --json` | Lo mismo en JSON, para otros programas |
| `tailscale status` | Equipos de tu tailnet con su IP, en línea o no, latencia medida desde el teléfono |
| `tailscale status -v` | Además, la IPv6 y la versión de Tailscale de cada equipo |
| `tailscale status --json` | La lista normalizada en JSON |
| `tailscale ip` | La IP de Tailscale del teléfono |
| `net tailscale` | Igual que `tailscale status` |
| `net <otra cosa>` | Pasa al `net` de Samba si lo tienes instalado |

### Cómo leer los símbolos

El estado nunca va solo en color: cada símbolo tiene forma propia y va con una palabra.

| Símbolo | Significa |
|---|---|
| ● | Responde bien |
| ◐ | Responde, pero pide atención (lento o clave por vencer) |
| ✕ | Falla o clave vencida |
| ○ | Apagado, desconectado o sin respuesta al ping |
| ◆ | Este teléfono |

## Cómo obtiene `tailscale status` la lista

La app de Tailscale para Android no trae línea de comandos, y **no hace falta otro equipo**:

| Fuente | Qué aporta | Necesita |
|---|---|---|
| Medición en vivo | En línea o no y latencia de cada IP, medidas por el túnel desde el teléfono; nombre vigente de cada IP según MagicDNS (`100.100.100.100`) | Tailscale encendido en el teléfono |
| API de Tailscale | La lista completa y al día: equipos nuevos, desconectados, sistema, versión, vencimiento de claves | Una credencial de solo lectura (abajo) e Internet |
| Copia local | La última lista conocida, para trabajar sin Internet | Haber leído la lista una vez |
| SSH (opcional) | `tailscale status --json` de un equipo tuyo con el CLI | Acceso SSH sin contraseña |

Cada vez que una fuente da la lista, se guarda en `~/.cache/net-termux/tailnet.json`. Sin
credencial ni SSH, `tailscale status` sigue funcionando con esa copia y la medición en vivo,
pero no verá equipos nuevos hasta la siguiente lectura completa.

### Credencial de la API (una vez, 1 minuto)

Recomendado: un **cliente OAuth de solo lectura**, que no vence.

1. Entra a <https://login.tailscale.com/admin/settings/oauth> y pulsa **Generate OAuth client**.
2. Marca solo **Devices › Core › Read** y genera. Copia el *Client ID* y el *Client secret*.
3. En Termux:

```bash
mkdir -p ~/.config/net-termux
printf '%s %s\n' 'CLIENT_ID' 'CLIENT_SECRET' > ~/.config/net-termux/tailscale-api
chmod 600 ~/.config/net-termux/tailscale-api
tailscale status
```

También sirve una llave de API (`tskey-api-...`, vence a los 90 días como máximo) sola en
ese fichero, o las variables `TS_OAUTH_CLIENT_ID` y `TS_OAUTH_CLIENT_SECRET`, o `TS_API_KEY`.
El token de acceso de 1 hora se guarda en `~/.cache/net-termux/` con permisos 600.

### SSH (opcional)

Si prefieres no crear credencial, escribe en `~/.config/net-termux/tailscale-hosts` el nombre
SSH de un equipo con el CLI de Tailscale (uno por línea) o usa `NET_TERMUX_TS_HOSTS`.

## Cómo funciona sin root

Android no deja leer la tabla ARP ni la de rutas, así que no hay MAC ni fabricante. En su lugar:

- **Equipos:** ping ICMP por socket de datagrama (Android lo permite sin root) leyendo el TTL,
  y conexión TCP a 7 puertos (22, 80, 443, 445, 554, 8009, 62078): un rechazo también prueba
  que el equipo existe. La latencia se vuelve a medir en calma para que sea real.
- **Nombres:** Tailscale, mDNS (Avahi, Bonjour), DNS del router y NetBIOS (Windows, Samba).
- **Tipo de equipo:** por Tailscale, por los puertos abiertos y por el TTL.
- **Router:** el `.1` o el `.254` que responde DNS.
- **Proveedor e IP pública:** una consulta a `ipinfo.io`. Con la API de Tailscale configurada,
  `tailscale status` consulta también `api.tailscale.com`. No hay más salidas a Internet.
- **Sin procesos en lote:** todo corre en hilos de un solo proceso; Android cierra Termux
  cuando una app crea demasiados procesos.

Solo barre la red `/24` del Wi-Fi: no escanea redes ajenas ni equipos fuera de tu LAN.
Úsalo en redes tuyas o donde tengas permiso.

## Diseño

Sigue las pautas de interfaz de Apple llevadas a la terminal: lo importante primero
(la red y luego los equipos), jerarquía por peso del texto y no por más columnas, estado
por forma, color y palabra, ancho que se adapta a la pantalla del teléfono, algo visible
mientras mide y sin color cuando la salida no es una terminal o existe `NO_COLOR`.

## Desarrollo

```bash
git clone https://github.com/andresgarcia0313/net-termux && cd net-termux
pkg install python-pip && pip install pytest
python3 -m pytest -q tests
```

Módulos en `lib/netkit/`: `probe` (ICMP y TCP), `mdns`, `names`, `link` (Wi-Fi, router,
Internet), `tsapi` (API de Tailscale), `tsdata` (fuentes y copia), `tslive` (medición por el
túnel), `tsstate`, `gather`, `netstatus`, `tsstatus`, `ui` y `fmt`.

Hermano para Linux: [net-status](https://github.com/andresgarcia0313/net-status).

## In English

`net status` and `tailscale status` for Termux on Android, no root required. Install with
the one-liner above, then run `net status`. Output is in Spanish.

## Control de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 2026-10-18 | Primera versión pública |
| 1.1.0 | 2026-10-18 | `tailscale status` sin depender de otro equipo (API, copia local y medición en vivo por el túnel); la IP se muestra en cualquier ancho |

## Licencia

MIT. Ver [LICENSE](LICENSE).
