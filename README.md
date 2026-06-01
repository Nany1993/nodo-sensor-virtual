# Nodo Sensor Virtual IoT

**Estudiante:** Ana María García Arias  
**Programa:** Maestría en Inteligencia Artificial  
**Docente:** Cristian Duney Bermúdez Quintero  
**Asignatura:** Internet de las Cosas  

---

## Descripcion del proyecto

Proyecto de desarrollo progresivo de un sistema IoT completo. Partiendo de un nodo sensor virtual, cada actividad agrega una capa de complejidad: captura local, transmision a la nube, almacenamiento en serie de tiempo, visualizacion en tiempo real y analitica basica.

```
Actividad 1         Actividad 2 / 3              Actividad 4                 Actividad 5
-----------         ---------------              -----------                 -----------
CounterFit          CounterFit                   CounterFit                  CounterFit
    |                   |                            |                            |
nodo_sensor.py      nodo_mqtt.py              nodo_timescale.py           nodo_timescale.py
    |               /        \                       |                            |
SQLite         SQLite    Adafruit IO         TimescaleDB Cloud          TimescaleDB Cloud
                         (MQTT)                      |                            |
                                              dashboard_iot.py            dashboard_iot.py
                                              (Streamlit :8501)           + correlacion/dispersion
                                                                          (refresh 30 s)
```

---

## Estructura del repositorio

```
nodo-sensor-virtual/
|
|-- actividad1/              Actividad 1: Nodo sensor virtual + SQLite
|   |-- nodo_sensor.py       Script principal de captura
|   |-- init_db.py           Crea la base de datos vacia
|   |-- export_lecturas_csv.py  Exporta datos a CSV
|   |-- Graficos_Resultados.ipynb  Visualizacion de datos
|   |-- Guia_Actividad_3_horas.ipynb  Guia de la prueba de 3 horas
|   |-- Propuesta_Nodo_Sensor_Virtual.md  Planificacion inicial
|   └-- Informe_Practica_Nodo_Sensor.md  Informe de resultados
|
|-- actividad2_3/            Actividad 2/3: MQTT + Adafruit IO
|   |-- nodo_mqtt.py         Script de captura + transmision MQTT
|   |-- Propuesta_Actividad2_MQTT.md  Planificacion y arquitectura
|   └-- Resumen_Actividad3_MQTT.ipynb  Resumen para el docente
|
|-- actividad4/              Actividad 4: TimescaleDB Cloud + Streamlit
|   |-- nodo_timescale.py    Script de captura -> TimescaleDB
|   |-- dashboard_iot.py     Dashboard interactivo (Streamlit)
|   |-- activar_flujo.ps1    Arranque rapido del pipeline
|   |-- sembrar_datos_mayo.py  Datos de prueba para filtros
|   |-- Procesamiento_Datos_IoT.ipynb  Pipeline de procesamiento
|   |-- Informe_Actividad4.md  Informe de practica
|   └-- Resumen_Actividad4_TimescaleDB.ipynb  Resumen para el docente
|
|-- actividad5/              Actividad 5: Visualizacion tiempo real + analitica
|   |-- Informe_Unidad3_Seguridad_Analitica.ipynb  Entregable Unidad 3 (informe + video)
|   |-- Informe_Unidad3_Seguridad_Analitica.md  Fuente del informe
|   |-- Informe_Actividad5_Visualizacion.md  Informe del panel y graficos
|   └-- activar_flujo.ps1    Arranque del flujo completo (3 terminales)
|
|-- requirements.txt         Dependencias Python de todo el proyecto
|-- .env.example             Plantilla de credenciales
└-- README.md                Este archivo
```

---

## Requisitos

- Python 3.11 o 3.12 (CounterFit no es compatible con Python 3.13)
- Crear un entorno virtual:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
```

- Crear el archivo `.env` copiando `.env.example` y completando las credenciales.

---

## Actividad 1 — Nodo sensor virtual con SQLite

**Objetivo:** Capturar datos de temperatura y humedad de un sensor DHT11 virtual cada 30 segundos durante 3 horas y almacenarlos en una base de datos SQLite local.

**Tecnologias:** Python, CounterFit, SQLite, pandas, matplotlib

**Carpeta:** `actividad1/`

### Configuracion de CounterFit

1. Iniciar CounterFit:
   ```bash
   .venv\Scripts\counterfit --port 5050
   ```
2. Abrir `http://localhost:5050` y crear dos sensores:

   | Campo    | Sensor Humedad | Sensor Temperatura |
   |----------|---------------|-------------------|
   | Type     | Humidity      | Temperature        |
   | Units    | Percentage    | Celsius            |
   | Pin      | 5             | 6                  |
   | Value    | 60            | 25                 |
   | Random   | checked       | checked            |
   | Min      | 40            | 18                 |
   | Max      | 90            | 35                 |

   > **Importante:** Siempre escribe un numero en el campo Value antes de hacer clic en Set, incluso con Random activado.

### Ejecucion

```bash
# Prueba rapida (sin CounterFit)
.venv\Scripts\python actividad1/nodo_sensor.py --simulate --samples 10 --interval-sec 5

# Prueba oficial (3 horas, CounterFit activo en puerto 5050)
.venv\Scripts\python actividad1/nodo_sensor.py --port 5050 --interval-sec 30 --samples 360 --db actividad1/lecturas.db

# Ver graficas
jupyter notebook actividad1/Graficos_Resultados.ipynb
```

---

## Actividad 2 / 3 — Transmision MQTT hacia Adafruit IO

**Objetivo:** Extender el nodo sensor para transmitir los datos en tiempo real a la plataforma Adafruit IO usando el protocolo MQTT, manteniendo el respaldo local en SQLite.

**Tecnologias:** Python, CounterFit, SQLite, paho-mqtt, Adafruit IO

**Carpeta:** `actividad2_3/`

**Video explicativo:** https://youtu.be/0L9Anxb1Pzk

### Credenciales necesarias en `.env`

```
AIO_USERNAME=tu_usuario_adafruit
AIO_KEY=tu_aio_key
```

### Ejecucion

```bash
# Prueba rapida (sin CounterFit)
.venv\Scripts\python actividad2_3/nodo_mqtt.py --simulate --samples 10 --interval-sec 5

# Con CounterFit activo en puerto 5050 (3 horas)
.venv\Scripts\python actividad2_3/nodo_mqtt.py --port 5050 --interval-sec 30 --samples 360
```

Los datos aparecen en tiempo real en el dashboard de Adafruit IO: https://io.adafruit.com

---

## Actividad 4 — Almacenamiento en TimescaleDB Cloud + Dashboard Streamlit

**Objetivo:** Implementar una infraestructura de almacenamiento cloud especializada para series de tiempo (TimescaleDB) y un dashboard web interactivo que muestre los datos en tiempo real con visualizaciones de datos crudos y procesados.

**Tecnologias:** Python, CounterFit, TimescaleDB Cloud (Tiger Cloud), Streamlit, Plotly, psycopg2, SQLAlchemy

**Carpeta:** `actividad4/`

### Credenciales necesarias en `.env`

```
TS_HOST=tu_servicio.region.tsdb.cloud.timescale.com
TS_PORT=33711
TS_DB=tsdb
TS_USER=tsdbadmin
TS_PASSWORD=tu_password
```

### Ejecucion

Abre tres terminales simultaneas:

```bash
# Terminal 1: iniciar CounterFit
.venv\Scripts\counterfit --port 5050

# Terminal 2: capturar datos hacia TimescaleDB (cada 5 s, 2 horas)
.venv\Scripts\python actividad4/nodo_timescale.py --port 5050 --interval-sec 5 --samples 1440

# Terminal 3: abrir el dashboard (pide usuario y contraseña)
.venv\Scripts\streamlit run actividad4/dashboard_iot.py
```

Credenciales del login en `.env`:

```
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=admin
```

El dashboard abre en `http://localhost:8501` y se refresca automaticamente cada 30 segundos.

### Pestanas del dashboard (Actividad 4 base)

Ver **Actividad 5** para la version actual con correlacion, dispersion y filtros avanzados.

### Procesamiento de datos

```bash
# Ejecutar el notebook de procesamiento
jupyter notebook actividad4/Procesamiento_Datos_IoT.ipynb
```

El notebook implementa el pipeline completo:
1. **Preprocesamiento:** deteccion de nulos, duplicados y anomalias de rango
2. **Filtrado:** ventana temporal, umbral de alerta, `time_bucket()` nativo de TimescaleDB
3. **Transformacion:** promedio movil, normalizacion min-max, agregados horarios y diarios

---

## Actividad 5 — Visualizacion en tiempo real y analitica basica

**Objetivo:** Dashboard interactivo con datos casi en tiempo real, filtros temporales, correlacion, dispersion y estadisticas descriptivas.

**Tecnologias:** Streamlit, Plotly, TimescaleDB Cloud, pandas

**Carpeta:** `actividad5/` (informe y arranque) · dashboard en `actividad4/dashboard_iot.py`

### Arranque rapido

```powershell
.\actividad5\activar_flujo.ps1
```

Abre CounterFit, captura cada **5 s** hacia TimescaleDB y el dashboard en `http://localhost:8501` (refresh automatico cada **30 s**).

### Pestanas del dashboard

| Pestana | Contenido |
|---------|-----------|
| En vivo (ultimas) | Metricas y serie temporal de las ultimas 120 lecturas |
| Datos filtrados | Serie temporal, metricas y tabla segun filtros del sidebar |
| Estadisticas | Pearson, Spearman, dispersion T vs HR, histogramas, `describe()` |

### Filtros del sidebar

- Ano (select)
- Mes (multiselect)
- Dia (multiselect)
- Hora (select)
- Botones: Limpiar filtros, Actualizar ahora

### Informe Unidad 3 (entregable)

Notebook con informe, video explicativo y enlace al repositorio:

`actividad5/Informe_Unidad3_Seguridad_Analitica.ipynb`

- Video: https://youtu.be/-VxEoZx7cU8
- Repositorio: https://github.com/Nany1993/nodo-sensor-virtual

Fuente en Markdown: `actividad5/Informe_Unidad3_Seguridad_Analitica.md`

---

## Dependencias

| Paquete | Version | Uso |
|---------|---------|-----|
| CounterFit | latest | Simulador de sensores IoT |
| counterfit-shims-seeed-python-dht | latest | Shim para sensor DHT11 virtual |
| paho-mqtt | >=1.6,<3 | Cliente MQTT (Actividad 2/3) |
| python-dotenv | >=1.0 | Gestion de credenciales |
| psycopg2-binary | >=2.9 | Conector PostgreSQL/TimescaleDB |
| sqlalchemy | >=2.0 | ORM para conexiones de pandas |
| streamlit | >=1.35 | Dashboard web interactivo |
| plotly | >=5.20 | Graficas interactivas |
| pandas | >=2.0 | Analisis y procesamiento de datos |
| matplotlib | >=3.7 | Visualizacion en notebooks |
| tqdm | >=4.66 | Barra de progreso en consola |

---

## Repositorio GitHub

https://github.com/Nany1993/nodo-sensor-virtual
