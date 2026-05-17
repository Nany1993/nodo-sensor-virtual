# Nodo Sensor Virtual — Registro de Temperatura y Humedad con SQLite

Implementación de un **nodo de medición IoT virtual** que captura temperatura y humedad relativa mediante el simulador **CounterFit**, almacena cada lectura con marca de tiempo en una base de datos **SQLite** y genera visualizaciones para análisis de resultados.

Desarrollado como práctica de laboratorio para la asignatura de **Internet de las Cosas (IoT)**.

---

## Descripción general

| Parámetro | Valor de la prueba oficial |
|---|---|
| Intervalo entre lecturas | 30 segundos |
| Número de muestras | 360 |
| Duración total | ~3 horas |
| Sensor simulado | DHT11 virtual (temperatura + humedad) |
| Almacenamiento | SQLite (`nodo_sensor.db`) |

El sistema está compuesto por tres componentes principales:

- **`nodo_sensor.py`** — script de adquisición: lee los sensores virtuales, genera la marca de tiempo en formato ISO 8601 y persiste cada muestra en la tabla `lecturas`.
- **`Graficos_Resultados.ipynb`** — notebook de análisis: carga los datos desde la base de datos y genera series temporales, gráfico de dispersión e histogramas de distribución.
- **`Guia_Actividad_3_horas.ipynb`** — guía paso a paso para ejecutar la actividad completa.

---

## Requisitos previos

- **Python 3.11 o 3.12** (CounterFit no es compatible con Python 3.13 debido a conflictos con `eventlet` y `ssl.wrap_socket`)
- **Git**
- Navegador web (para la interfaz de CounterFit)

---

## Instalación

```powershell
# 1. Clonar el repositorio
git clone https://github.com/Nany1993/nodo-sensor-virtual.git
cd nodo-sensor-virtual

# 2. Crear entorno virtual con Python 3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt
```

> `requirements.txt` fija `werkzeug>=2.3,<3` para resolver la incompatibilidad de CounterFit con Werkzeug 3.

---

## Configuración de CounterFit

1. En una terminal con el entorno activo, ejecutar el simulador:

    ```powershell
    counterfit
    ```

2. Abrir `http://127.0.0.1:5000` en el navegador.
3. Crear dos sensores en la pestaña **Sensors**:

    | Sensor      | Tipo        | Unidades   | Pin GPIO virtual |
    |-------------|-------------|------------|-----------------|
    | Humedad     | Humidity    | Percentage | **5**           |
    | Temperatura | Temperature | Celsius    | **6**           |

4. Ajustar los valores manualmente (**Set**) o activar el modo **Random** con límites definidos (p. ej. Min: 15, Max: 35 para temperatura).

> **No es necesario configurar actuadores.** El alcance del nodo es exclusivamente lectura y registro.

---

## Uso

### Crear la base de datos (primer uso)

```powershell
python init_db.py
```

Crea `nodo_sensor.db` con la tabla `lecturas` vacía. El script de captura también la crea automáticamente si no existe.

### Prueba corta sin CounterFit (modo simulado)

Útil para verificar el flujo de captura y escritura en SQLite sin depender del simulador:

```powershell
python nodo_sensor.py --simulate --interval-sec 5 --samples 6 --db prueba.db
```

### Prueba oficial (3 horas)

Con CounterFit en ejecución en otra terminal:

```powershell
python nodo_sensor.py --interval-sec 30 --samples 360 --db nodo_sensor.db
```

La consola muestra cada lectura junto con una **barra de progreso** (`tqdm`). Para desactivarla:

```powershell
python nodo_sensor.py --interval-sec 30 --samples 360 --db nodo_sensor.db --no-progress
```

### Opciones del script

| Argumento | Descripción | Por defecto |
|---|---|---|
| `--host` | Host de CounterFit | `127.0.0.1` |
| `--port` | Puerto de CounterFit | `5000` |
| `--dht-pin` | Pin GPIO del sensor DHT11 | `5` |
| `--interval-sec` | Segundos entre lecturas | `30` |
| `--samples` | Número total de muestras | `360` |
| `--db` | Ruta del archivo SQLite | `nodo_sensor.db` |
| `--init-db` | Solo crear la BD y salir | — |
| `--simulate` | Generar datos sintéticos (sin CounterFit) | — |
| `--no-progress` | Desactivar barra de progreso | — |

---

## Esquema de la base de datos

```sql
CREATE TABLE IF NOT EXISTS lecturas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,        -- Marca de tiempo ISO 8601
    temperatura_c REAL NOT NULL,
    humedad_pct   REAL NOT NULL
);
```

---

## Exportar datos a CSV

```powershell
python export_lecturas_csv.py --db nodo_sensor.db -o lecturas.csv
```

---

## Análisis y gráficos

Abrir **`Graficos_Resultados.ipynb`** con el kernel del entorno virtual (requiere `pandas` y `matplotlib`, incluidos en `requirements.txt`).

El notebook genera:

- **Figura 1** — Series temporales de temperatura y humedad vs. tiempo
- **Figura 2** — Dispersión humedad vs. temperatura (color = orden de la muestra)
- **Figura 3** — Histogramas de distribución de ambas variables
- **Tabla estadística** — Mínimo, máximo, media y desviación estándar por variable

Las figuras pueden exportarse como PNG en `figuras_informe/` ejecutando la última celda del notebook.

---

## Actividad 2 — Transmisión MQTT a Adafruit IO

El script `nodo_mqtt.py` extiende el nodo sensor para enviar cada lectura a **Adafruit IO** en tiempo real mediante **MQTT**, además de seguir persistiendo en SQLite.

---

### Protocolo de comunicación: MQTT

**MQTT** (*Message Queuing Telemetry Transport*) es un protocolo de mensajería ligero diseñado específicamente para entornos IoT donde los dispositivos tienen recursos limitados y la red puede ser inestable o de baja velocidad.

#### ¿Cómo funciona?

MQTT opera bajo un modelo **publicar / suscribir** (*publish / subscribe*) que desacopla al emisor del receptor:

```
[Nodo sensor]  --publica-->  [Broker MQTT]  --distribuye-->  [Dashboard / App]
  (publisher)                (io.adafruit.com)                  (subscriber)
```

1. El **broker** actúa como intermediario central: recibe los mensajes y los reenvía a todos los suscriptores interesados.
2. El **publicador** (*publisher*) envía un valor a un **topic** (tema), que funciona como una dirección lógica. En este proyecto los topics son:
   - `NANY1993/feeds/temperatura`
   - `NANY1993/feeds/humedad`
3. El **suscriptor** (*subscriber*) —en este caso Adafruit IO— escucha esos topics y actualiza el dashboard en tiempo real.

#### Conceptos clave

| Concepto | Descripción |
|---|---|
| **Broker** | Servidor intermediario que enruta los mensajes. Aquí: `io.adafruit.com:1883` |
| **Topic** | Cadena jerárquica que identifica un canal de datos (ej. `usuario/feeds/temperatura`) |
| **QoS 0** | *At most once* — el mensaje se envía una vez sin confirmación. Suficiente para telemetría continua |
| **Keepalive** | Intervalo (60 s) en que el cliente confirma que sigue activo al broker |
| **Payload** | El valor transmitido; en este proyecto es un número flotante en formato texto |
| **`loop_start()`** | Hilo de fondo que mantiene la conexión MQTT activa mientras el script captura datos |

#### ¿Por qué MQTT y no HTTP o CoAP?

| Protocolo | Peso | Modelo | Ideal para |
|---|---|---|---|
| **MQTT** | Muy ligero | Pub/Sub — persistente | Telemetría IoT continua, sensores |
| HTTP | Medio | Request/Response | APIs REST, integración web |
| CoAP | Ligero | Request/Response | Redes con UDP, sensores muy restringidos |

MQTT es la elección estándar para sensores que envían datos de forma continua porque mantiene una sola conexión TCP abierta y el overhead por mensaje es mínimo (~2 bytes de cabecera fija).

---

### Configuración del sistema de transmisión

#### Rol del microcontrolador

La actividad requiere un microcontrolador (ESP32, ESP8266, u otro). En esta implementación el **PC actúa como nodo IoT**, simulando exactamente el rol que cumpliría un ESP32:

| Aspecto | ESP32 físico | Este proyecto (PC virtual) |
|---|---|---|
| Sensor | DHT11 conectado por GPIO | DHT11 virtual en CounterFit |
| Protocolo | MQTT vía `PubSubClient` (Arduino) | MQTT vía `paho-mqtt` (Python) |
| Red | Wi-Fi integrado | Wi-Fi del PC |
| Broker | `io.adafruit.com` | `io.adafruit.com` (idéntico) |
| Plataforma | Adafruit IO | Adafruit IO (idéntico) |

La lógica de comunicación, el protocolo y la integración con la plataforma son **exactamente iguales** a los de un dispositivo físico.

#### Tipo de red utilizada

**Wi-Fi (IEEE 802.11)** sobre TCP/IP. El PC se conecta a Internet a través de la red doméstica y establece una conexión TCP persistente con el broker `io.adafruit.com` en el puerto **1883**.

#### Plataforma de monitoreo: Adafruit IO

[Adafruit IO](https://io.adafruit.com) es una plataforma IoT en la nube que ofrece:
- **Feeds**: canales de datos donde llegan los valores publicados vía MQTT.
- **Dashboards**: paneles visuales configurables con bloques *Line Chart*, *Gauge*, *Toggle*, etc.
- **Historial**: almacena automáticamente cada valor recibido con su timestamp.
- **API REST y MQTT**: accesibles con usuario y AIO Key.

#### Credenciales y seguridad

Las credenciales (usuario y AIO Key) se almacenan en un archivo **`.env`** local que **no se sube a GitHub** (incluido en `.gitignore`). El script las carga en tiempo de ejecución con `python-dotenv`.

```
# .env  (nunca versionar este archivo)
AIO_USERNAME=tu_usuario
AIO_KEY=aio_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Configuración rápida

1. Crear cuenta en [io.adafruit.com](https://io.adafruit.com) y dos feeds con nombres exactos: `temperatura` y `humedad`.
2. Copiar las credenciales al archivo `.env`:

```powershell
copy .env.example .env
# Editar .env con tu AIO_USERNAME y AIO_KEY
```

3. Probar con modo simulado (sin CounterFit):

```powershell
python nodo_mqtt.py --simulate --samples 6 --interval-sec 5
```

#### Opciones de `nodo_mqtt.py`

| Argumento | Descripción | Por defecto |
|---|---|---|
| `--simulate` | Valores sintéticos, sin CounterFit | — |
| `--interval-sec` | Segundos entre muestras | `30` |
| `--samples` | Total de lecturas | `360` |
| `--db` | Ruta del archivo SQLite | `nodo_mqtt.db` |
| `--no-mqtt` | Deshabilitar envío MQTT (solo SQLite) | — |
| `--no-progress` | Desactivar barra de progreso | — |

---

### Resultados obtenidos

#### Flujo de implementación

```
CounterFit (sensor DHT11 virtual)
        │  hum, temp
        ▼
nodo_mqtt.py  ──┬──► SQLite  (nodo_mqtt.db)       persistencia local
                │
                └──► paho-mqtt
                          │  TCP/Wi-Fi
                          ▼
                  Broker: io.adafruit.com:1883
                          │
                          ├──► feed: NANY1993/feeds/temperatura
                          └──► feed: NANY1993/feeds/humedad
                                        │
                                        ▼
                              Dashboard Adafruit IO
                          (visualización en tiempo real)
```

#### Comportamiento del sistema

Cada lectura genera en consola una línea de la forma:

```
[3/20] 2026-05-16T19:17:46  T=22.53C  HR=60.23%  -> MQTT OK
```

Indicando: número de muestra, timestamp ISO 8601, valores de temperatura y humedad, y confirmación de publicación MQTT exitosa.

#### Verificación en Adafruit IO

Al ejecutar el script, los feeds `temperatura` y `humedad` reciben los valores en tiempo real y los grafican automáticamente en el dashboard. Cada punto en la gráfica corresponde a una muestra capturada y transmitida por el nodo.

#### Prueba de conectividad realizada

```
Muestras enviadas : 20 lecturas × intervalo 10 s
Duración          : ~3.5 minutos
Protocolo         : MQTT sobre Wi-Fi (TCP puerto 1883)
Broker            : io.adafruit.com
Estado final      : 20/20 lecturas con "MQTT OK" — 0 errores
```

Ver `Propuesta_Actividad2_MQTT.md` para la guía completa y el guion del video de 6 minutos.

---

## Estructura del repositorio

```
nodo-sensor-virtual/
├── nodo_sensor.py                   # Actividad 1: captura → SQLite
├── nodo_mqtt.py                     # Actividad 2: captura → SQLite + MQTT
├── init_db.py                       # Creación inicial de la BD
├── export_lecturas_csv.py           # Exportación a CSV
├── requirements.txt                 # Dependencias Python
├── .env.example                     # Plantilla de credenciales MQTT
├── Graficos_Resultados.ipynb        # Notebook de análisis y visualización
├── Guia_Actividad_3_horas.ipynb     # Guía paso a paso de la actividad 1
├── Informe_Practica_Nodo_Sensor.md  # Borrador del informe (Actividad 1)
├── Propuesta_Nodo_Sensor_Virtual.md # Propuesta y planificación (Actividad 1)
├── Propuesta_Actividad2_MQTT.md     # Propuesta y planificación (Actividad 2)
└── .gitignore
```

---

## Dependencias principales

| Paquete | Versión | Uso |
|---|---|---|
| CounterFit | latest | Simulador de sensores IoT |
| counterfit-shims-seeed-python-dht | latest | Shim del sensor DHT11 virtual |
| werkzeug | >=2.3,<3 | Compatibilidad con Flask interno de CounterFit |
| tqdm | >=4.66 | Barra de progreso en consola |
| pandas | >=2.0 | Análisis de datos en el notebook |
| matplotlib | >=3.7 | Visualizaciones en el notebook |
| paho-mqtt | >=1.6,<3 | Cliente MQTT para Adafruit IO (Actividad 2) |
| python-dotenv | >=1.0 | Carga de credenciales desde `.env` (Actividad 2) |
