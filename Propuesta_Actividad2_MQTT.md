# Actividad 2 — Transmisión y Comunicación de Datos IoT

## Objetivo

Extender el nodo sensor virtual de la Actividad 1 para que, además de persistir las lecturas en SQLite, las transmita en tiempo real a una plataforma de monitoreo en la nube mediante el protocolo **MQTT**, permitiendo la visualización de los datos en un dashboard accesible desde cualquier dispositivo.

---

## Arquitectura del sistema

```
CounterFit (sensor virtual DHT11)
        │
        ▼
nodo_mqtt.py  (Python 3.11 — PC actúa como nodo IoT)
        │
        ├──► SQLite (nodo_mqtt.db)       ← persistencia local
        │
        └──► MQTT (paho-mqtt)
                │
                ▼
        Broker: io.adafruit.com:1883
                │
                ▼
        Adafruit IO Dashboard            ← visualización en la nube
          ├─ Feed: temperatura
          └─ Feed: humedad
```

---

## Decisiones de diseño

| Elemento | Decisión | Justificación |
|---|---|---|
| Protocolo de comunicación | **MQTT** | Ligero, diseñado para IoT, baja latencia, patrón publish/subscribe |
| Broker / Plataforma | **Adafruit IO** (gratuito) | Dashboard visual integrado, sin configurar servidor propio |
| Tipo de red | **Wi-Fi (TCP/IP local)** | El PC se conecta al broker por Internet vía la red doméstica |
| Biblioteca Python | **paho-mqtt** | Cliente MQTT estándar y multiplataforma |
| Credenciales | Archivo `.env` (excluido de git) | Separación de código y secretos (buena práctica de seguridad) |
| Base de datos | `nodo_mqtt.db` separada de Actividad 1 | Evitar mezcla de sesiones |
| Microcontrolador | PC simula rol del ESP32/ESP8266 | Mismo protocolo e integración que hardware físico |

---

## Protocolo MQTT — configuración

| Parámetro | Valor |
|---|---|
| Broker | `io.adafruit.com` |
| Puerto | `1883` (TCP sin TLS) |
| Autenticación | Usuario = AIO Username, Contraseña = AIO Key |
| Feed temperatura | `{usuario}/feeds/temperatura` |
| Feed humedad | `{usuario}/feeds/humedad` |
| QoS | 0 (fire-and-forget, suficiente para telemetría) |
| Keepalive | 60 s |

---

## Pasos de configuración

### 1. Cuenta Adafruit IO

1. Ir a [io.adafruit.com](https://io.adafruit.com) y crear cuenta gratuita.
2. Desde el menú lateral → **Feeds** → **New Feed**:
   - Crear feed con nombre exacto: `temperatura`
   - Crear feed con nombre exacto: `humedad`
3. Desde el menú → **Dashboards** → **New Dashboard** (nombre: `Nodo Sensor IoT`):
   - Agregar bloque **Line Chart** conectado al feed `temperatura`
   - Agregar bloque **Line Chart** conectado al feed `humedad`
   - Opcional: agregar bloques **Gauge** para ver el valor actual
4. Obtener credenciales: ícono de llave **(AIO Key)** → copiar **Username** y **Active Key**.

### 2. Credenciales locales

```powershell
# En la carpeta del proyecto:
copy .env.example .env
```

Editar `.env` con tus datos:

```
AIO_USERNAME=tu_usuario_adafruit
AIO_KEY=aio_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Instalar dependencias

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Ejecución

### Prueba rápida sin CounterFit (modo simulado)

```powershell
python nodo_mqtt.py --simulate --samples 6 --interval-sec 5
```

Esto envía 6 lecturas cada 5 segundos a Adafruit IO. Verificar en el dashboard que llegan los datos.

### Prueba local sin MQTT (solo SQLite)

```powershell
python nodo_mqtt.py --simulate --samples 6 --interval-sec 5 --no-mqtt
```

### Prueba con CounterFit activo (desarrollo)

```powershell
# Terminal 1:
counterfit

# Terminal 2:
python nodo_mqtt.py --interval-sec 10 --samples 12
```

### Corrida oficial (~3 horas)

```powershell
python nodo_mqtt.py --interval-sec 30 --samples 360 --db nodo_mqtt.db
```

---

## Archivos del proyecto (Actividad 2)

| Archivo | Descripción |
|---|---|
| `nodo_mqtt.py` | Script principal: captura → SQLite + MQTT |
| `.env` | Credenciales Adafruit IO (NO subir a GitHub) |
| `.env.example` | Plantilla de credenciales (sí se versiona) |
| `nodo_mqtt.db` | Base de datos SQLite de esta actividad |
| `requirements.txt` | Dependencias actualizadas con `paho-mqtt` |

---

## Guion sugerido para el video (6 minutos)

| Tiempo | Contenido |
|---|---|
| 0:00 – 0:45 | Presentación: equipo, objetivo, arquitectura del sistema |
| 0:45 – 1:30 | Mostrar dashboard de Adafruit IO (feeds, dashboard preparado) |
| 1:30 – 2:30 | Mostrar CounterFit con sensores configurados y el `.env` (ocultar la key) |
| 2:30 – 4:00 | Ejecutar `nodo_mqtt.py` en vivo: mostrar consola con lecturas y MQTT OK |
| 4:00 – 5:00 | Mostrar dashboard de Adafruit IO actualizándose en tiempo real |
| 5:00 – 5:30 | Mostrar `nodo_mqtt.db` en DB Browser con los registros almacenados |
| 5:30 – 6:00 | Conclusiones: protocolo usado, red, plataforma, aspectos clave |
