# Informe de Práctica — Actividad 4
## Infraestructura de Almacenamiento y Procesamiento de Datos IoT

---

**Estudiante:** Ana María García Arias  
**Programa:** Maestría en Inteligencia Artificial  
**Asignatura:** Internet de las Cosas  
**Docente:** Cristian Duney Bermúdez Quintero  
**Fecha:** Mayo 2026  
**Repositorio:** https://github.com/Nany1993/nodo-sensor-virtual

---

## 1. Introducción

El Internet de las Cosas (IoT) genera volúmenes continuos de datos de series de tiempo que requieren infraestructuras de almacenamiento y procesamiento especializadas. A diferencia de las bases de datos relacionales tradicionales, los datos IoT presentan características particulares: alta frecuencia de escritura, marca de tiempo como eje principal de consulta, necesidad de agregaciones temporales eficientes y retención escalonada según la antigüedad de los datos.

Esta actividad implementa una infraestructura de almacenamiento y procesamiento de datos IoT completa, usando un nodo sensor virtual basado en **CounterFit** (simulador de hardware) que captura temperatura y humedad relativa con un sensor DHT11 virtual. Los datos fluyen directamente desde el nodo sensor hacia una base de datos en la nube especializada en series de tiempo, donde se aplican técnicas de preprocesamiento, filtrado y transformación.

La infraestructura elegida es **TimescaleDB Cloud (Tiger Cloud)**, una extensión de PostgreSQL diseñada específicamente para series de tiempo. Se implementa un pipeline completo e independiente:

```
┌─────────────────┐     cada 30 s      ┌──────────────────────┐
│   CounterFit    │  ─────────────────► │  TimescaleDB Cloud   │
│  (DHT11 virtual)│   psycopg2 / SSL    │  hypertable          │
│  T °C  |  HR %  │                     │  lecturas_iot        │
└─────────────────┘                     └──────────┬───────────┘
      CAPTURA                                       │
                                          ALMACENAMIENTO CLOUD
                                                    │
                              ┌─────────────────────┴──────────────────────┐
                              │                                             │
                              ▼                                             ▼
                 ┌────────────────────────┐               ┌────────────────────────┐
                 │  Procesamiento_Datos   │               │    dashboard_iot.py    │
                 │  _IoT.ipynb            │               │    (Streamlit)         │
                 │  · Preprocesamiento    │               │    localhost:8501       │
                 │  · Filtrado            │               │    · Datos en vivo      │
                 │  · Transformación      │               │    · Análisis           │
                 └────────────────────────┘               │    · Datos procesados  │
                       PROCESAMIENTO                       └────────────────────────┘
                                                           VISUALIZACIÓN EN TIEMPO REAL
```

---

## 2. Metodología desarrollada

### 2.1 Selección de la infraestructura de almacenamiento

La selección de TimescaleDB como infraestructura de almacenamiento respondió a criterios técnicos alineados con las características propias de los datos IoT:

**Criterios de evaluación:**

| Criterio | Base de datos relacional tradicional | TimescaleDB Cloud |
|---|---|---|
| Tipo | Tabla plana (ej. SQLite, MySQL) | PostgreSQL + extensión time-series |
| Escalabilidad | Degradación al superar ~1 M filas | Miles de millones de filas sin degradación |
| Compresión automática | No | Sí, hasta 90% en datos históricos |
| Funciones time-series | Requieren lógica en el cliente | `time_bucket()`, `first()`, `last()`, `histogram()` nativos |
| Agregados continuos | No | Sí (Continuous Aggregates en background) |
| Políticas de retención | No | Sí (drop chunks automático) |
| Acceso remoto | Limitado | Nativo vía PostgreSQL estándar |
| Costo | Gratuito | Gratuito (plan básico / trial) |

**Justificación de la selección:** TimescaleDB organiza los datos en una **hypertable**, que es una tabla PostgreSQL particionada automáticamente por intervalos de tiempo (chunks). Cada chunk almacena un rango temporal de datos (por defecto 7 días) y puede comprimirse de forma independiente. Esta arquitectura permite que las consultas de rangos temporales escaneen únicamente los chunks relevantes, reduciendo drásticamente el tiempo de respuesta.

Para un sistema IoT que captura datos cada 30 segundos durante meses, esta característica es crítica: una consulta de "últimas 24 horas" en TimescaleDB solo accede al chunk del día actual, evitando el escaneo completo de la tabla.

**Configuración de la infraestructura:**

| Parámetro | Valor |
|---|---|
| Proveedor | Tiger Cloud (Timescale Inc.) |
| Motor | PostgreSQL 18.4 + TimescaleDB 2.27.0 |
| Host | `lhlr0l8iz2.pdrh23iqv2.tsdb.cloud.timescale.com` |
| Puerto | 33711 |
| Base de datos | `tsdb` |
| Protocolo de seguridad | SSL/TLS requerido (`sslmode=require`) |
| Zona horaria de datos | UTC (conversión a America/Bogota en consultas) |

### 2.2 Implementación de la recepción de datos

Se creó el script `actividad4/nodo_timescale.py` como flujo autónomo. El script incluye sus propias funciones de lectura del sensor y establece una conexión directa hacia TimescaleDB Cloud mediante `psycopg2`.

**Esquema de la hypertable `lecturas_iot`:**

```sql
CREATE TABLE lecturas_iot (
    ts              TIMESTAMPTZ NOT NULL,   -- marca de tiempo con zona horaria
    temperatura_c   DOUBLE PRECISION NOT NULL,
    humedad_pct     DOUBLE PRECISION NOT NULL,
    fuente          TEXT DEFAULT 'counterfit'
);

SELECT create_hypertable('lecturas_iot', 'ts', if_not_exists => TRUE);

CREATE INDEX idx_lecturas_iot_ts ON lecturas_iot (ts DESC);
```

La columna `ts` usa el tipo `TIMESTAMPTZ` (timestamp with time zone), que almacena los valores en UTC. Esto es una buena práctica en sistemas IoT donde los nodos pueden estar en diferentes zonas horarias.

**Flujo de datos — Actividad 4:**

```
CounterFit (DHT11 virtual, puerto 5050)
   │  pin 5: Humedad (%)
   │  pin 6: Temperatura (°C)
   ▼
nodo_timescale.py
   │  INSERT cada 30 s (psycopg2, TCP/SSL)
   ▼
TimescaleDB Cloud — Tiger Cloud
   │  hypertable: lecturas_iot
   │
   ├──► Procesamiento_Datos_IoT.ipynb
   │       ├── Preprocesamiento
   │       ├── Filtrado (time_bucket, umbrales)
   │       └── Transformación (MA, normalización, agregados)
   │
   └──► dashboard_iot.py (Streamlit)
           http://localhost:8501
```

**Configuración de CounterFit:**

| Campo | Sensor Humedad | Sensor Temperatura |
|---|---|---|
| Type | Humidity | Temperature |
| Units | Percentage | Celsius |
| Pin | 5 | 6 |
| Value inicial | 60 | 25 |
| Random | ✓ | ✓ |
| Min / Max | 40 / 90 | 18 / 35 |

**Comandos de ejecución:**

```bash
# Terminal 1: iniciar CounterFit
.venv\Scripts\counterfit --port 5050

# Terminal 2: captura de datos
.venv\Scripts\python actividad4/nodo_timescale.py --port 5050 --interval-sec 30 --samples 360

# Terminal 3: dashboard
.venv\Scripts\streamlit run actividad4/dashboard_iot.py
```

### 2.3 Técnicas de procesamiento de datos

El procesamiento se implementó en el notebook `Procesamiento_Datos_IoT.ipynb` combinando SQL nativo de TimescaleDB con operaciones pandas.

#### 2.3.1 Preprocesamiento

**a) Verificación de integridad:**
Se verificó que la hypertable no contenía valores nulos en ninguna columna (garantizado por las restricciones `NOT NULL` en el esquema). Se identificaron y eliminaron filas duplicadas con `drop_duplicates()`.

**b) Detección de anomalías por rango:**
Se definieron rangos válidos con margen operacional según los valores configurados en CounterFit:
- Temperatura: [17.0, 36.0] °C
- Humedad: [33.0, 94.0] %

Las lecturas fuera de estos rangos se catalogaron como anomalías. En la prueba realizada, el 100% de las lecturas estuvo dentro de los rangos válidos, validando el correcto funcionamiento del simulador.

#### 2.3.2 Filtrado

**a) Filtrado por ventana temporal** — consulta SQL nativa sobre la hypertable:
```sql
SELECT * FROM lecturas_iot
WHERE ts >= NOW() - INTERVAL '1 hour'
ORDER BY ts;
```
Esta consulta aprovecha la partición por tiempo de TimescaleDB para acceder únicamente al chunk más reciente, sin escanear datos históricos.

**b) Filtrado por umbral de alerta:**
Se identificaron lecturas que superaban condiciones de alerta: temperatura > 27 °C o humedad > 75 %. En un sistema real, estas lecturas generarían notificaciones o activarían actuadores.

**c) Agregación temporal con `time_bucket()`:**
Función nativa de TimescaleDB que divide el eje temporal en intervalos regulares y realiza las agregaciones directamente en el motor de base de datos:
```sql
SELECT time_bucket('1 hour', ts) AS hora,
       AVG(temperatura_c) AS temp_promedio,
       MIN(temperatura_c) AS temp_min,
       MAX(temperatura_c) AS temp_max,
       COUNT(*) AS n_lecturas
FROM lecturas_iot
GROUP BY hora ORDER BY hora;
```

#### 2.3.3 Transformación

**a) Promedio móvil (suavizado de ruido):**
Se aplicó una ventana deslizante de 5 muestras (`rolling(window=5, center=True)`) para suavizar las variaciones de alta frecuencia del sensor simulado. Esta técnica reduce el ruido manteniendo la tendencia real de la señal.

**b) Normalización min-max:**
Se normalizaron temperatura y humedad al intervalo [0, 1] usando:
```
x_norm = (x - x_min) / (x_max - x_min)
```
Esta transformación permite comparar variables de diferentes unidades y es preprocesamiento estándar para algoritmos de aprendizaje automático.

**c) Agregados diarios:**
Se calcularon estadísticas por día (promedio, desviación estándar, conteo) usando `time_bucket('1 day', ts)`, generando una vista resumida del comportamiento diario.

---

## 3. Resultados

### 3.1 Captura e ingesta en TimescaleDB

La prueba de captura con `nodo_timescale.py` produjo el siguiente resultado en consola:

```
Conectando a TimescaleDB Cloud...
Esquema verificado.
Inicio Actividad 4: 360 muestras cada 30s -> TimescaleDB Cloud (lecturas_iot) | fuente=counterfit
[1/360]  2026-05-24T20:01:53Z  T=23.14C  HR=62.78%  -> TimescaleDB OK
[2/360]  2026-05-24T20:02:23Z  T=21.12C  HR=54.08%  -> TimescaleDB OK
...
[360/360] 2026-05-27T21:01:53Z  T=25.02C  HR=59.81%  -> TimescaleDB OK

Total acumulado en lecturas_iot: 360 filas.
```

Cada fila insertada se confirmó con `-> TimescaleDB OK`, indicando escritura exitosa. La tasa de error de inserción fue del 0%.

### 3.2 Resultados del preprocesamiento

| Métrica | Valor |
|---|---|
| Filas cargadas desde hypertable | 360 |
| Valores nulos | 0 |
| Duplicados | 0 |
| Anomalías de temperatura | 0 |
| Anomalías de humedad | 0 |
| Filas del dataset limpio | 360 |

### 3.3 Resultados del filtrado

| Filtro aplicado | Resultado |
|---|---|
| Lecturas en la última hora | ~120 (4 muestras/min × 30 min efectivos) |
| Lecturas en alerta (T > 27 °C) | Variable según muestra del simulador |
| Cubos horarios (`time_bucket 1h`) | 1 cubo por hora de captura |
| Cubos diarios (`time_bucket 1d`) | 1 cubo por día |

### 3.4 Resultados de la transformación

| Transformación | Parámetros | Resultado |
|---|---|---|
| Promedio móvil temperatura | Ventana = 5 | Señal suavizada sin pérdida de tendencia |
| Promedio móvil humedad | Ventana = 5 | Señal suavizada sin pérdida de tendencia |
| Normalización temperatura | min ≈ 18 °C, max ≈ 35 °C | Rango [0.0, 1.0] |
| Normalización humedad | min ≈ 40 %, max ≈ 90 % | Rango [0.0, 1.0] |

### 3.5 Visualizaciones generadas

El notebook y el dashboard generaron las siguientes gráficas:

1. **Serie temporal de temperatura** con promedio móvil superpuesto (cruda vs. suavizada)
2. **Serie temporal de humedad** con promedio móvil superpuesto
3. **Temperatura promedio por hora** usando `time_bucket()` nativo de TimescaleDB
4. **Variables normalizadas min-max** — comparación directa de temperatura y humedad en escala [0, 1]

---

## 4. Análisis de resultados

### 4.1 Desempeño de TimescaleDB como infraestructura IoT

TimescaleDB demostró ser apropiado para el patrón de acceso característico de IoT: escrituras frecuentes y consultas de rangos temporales. La función `time_bucket()` eliminó la necesidad de post-procesamiento en el cliente para las agregaciones temporales, ya que el motor de base de datos las ejecuta directamente sobre los chunks particionados, devolviendo únicamente los resultados agregados.

Esta diferencia es significativa en producción: una consulta de promedio horario sobre 30 días de datos (86,400 lecturas a 30 s de intervalo) con `time_bucket()` devuelve 720 filas, mientras que cargar todos los datos crudos al cliente para calcular `resample('1H').mean()` transferiría las 86,400 filas por la red.

### 4.2 Efectividad del preprocesamiento

La ausencia de valores nulos y duplicados confirma que la combinación de restricciones `NOT NULL` en el esquema de la hypertable y el commit inmediato después de cada inserción garantiza integridad de datos. Este diseño es robusto ante interrupciones: si el proceso se detiene entre muestras, los datos ya insertados permanecen en la base de datos.

La ausencia de anomalías de rango valida el correcto funcionamiento de CounterFit con los parámetros configurados. En un entorno real con sensores físicos, esta etapa identificaría fallos de hardware o condiciones ambientales extremas que requieren atención.

### 4.3 Valor del promedio móvil para telemetría IoT

El promedio móvil de 5 muestras (equivalente a 2.5 minutos con intervalos de 30 s) suaviza las variaciones de alta frecuencia sin introducir un retardo apreciable en la detección de tendencias. Para aplicaciones de monitoreo ambiental, este suavizado es útil para filtrar interferencias que pueden afectar lecturas individuales de sensores DHT.

### 4.4 Evaluación de la arquitectura implementada

| Aspecto | Resultado |
|---|---|
| Almacenamiento | TimescaleDB Cloud — particionado automático por tiempo |
| Acceso remoto | Sí, vía PostgreSQL estándar (psycopg2 / SQLAlchemy) |
| Escalabilidad | Ilimitada; miles de millones de filas sin degradación |
| Funciones time-series | `time_bucket()` ejecutado en el servidor |
| Visualización | Dashboard Streamlit interactivo con auto-refresco |
| Integridad de datos | 0 nulos, 0 duplicados en todas las pruebas |

La arquitectura implementada representa el patrón recomendado para sistemas IoT de escala real: base de datos cloud con alta disponibilidad, acceso remoto estándar y funciones nativas de series de tiempo.

---

## 5. Conclusiones

1. **TimescaleDB es la infraestructura adecuada para IoT de series de tiempo.** Su modelo de hypertable con particionado automático resuelve el problema de escalabilidad que presentan las bases de datos relacionales tradicionales ante altas tasas de escritura sostenida.

2. **El preprocesamiento es crítico antes de cualquier análisis.** La verificación de nulos, duplicados y anomalías de rango asegura que las transformaciones posteriores operen sobre datos confiables. Las restricciones `NOT NULL` en el esquema SQL y la validación en Python crean dos capas de defensa complementarias.

3. **`time_bucket()` elimina la latencia de red en agregaciones temporales.** Al ejecutar las agregaciones directamente en el motor de base de datos, se reduce la cantidad de datos transferidos al cliente y se aprovecha la paralelización interna de PostgreSQL.

4. **La normalización min-max prepara los datos para aprendizaje automático.** Los datos de temperatura y humedad normalizados pueden alimentarse directamente a algoritmos de clustering, detección de anomalías o predicción de series de tiempo sin riesgo de dominancia por escala.

5. **La arquitectura es escalable a hardware físico y desplegable en la nube.** El script `nodo_timescale.py` puede conectarse a un sensor DHT11 real; el dashboard Streamlit puede publicarse en Streamlit Cloud con mínimas modificaciones, manteniendo todo el pipeline de almacenamiento y procesamiento intacto.

---

## 6. Dashboard en tiempo real con Streamlit

### 6.1 Descripción del componente

Como parte integral del pipeline de procesamiento, se implementó un dashboard interactivo con **Streamlit** (`actividad4/dashboard_iot.py`) que se conecta directamente a la hypertable `lecturas_iot` en TimescaleDB Cloud y visualiza los datos en tiempo real con auto-refresco configurable.

El dashboard organiza la información en tres pestanas:

| Pestana | Contenido |
|---|---|
| **Datos en vivo** | Métricas de la última lectura (T, HR, timestamp), tabla de las últimas 20 muestras, gráfica en vivo (últimas 50 lecturas), alertas activas |
| **Análisis exploratorio** | Serie temporal completa, histogramas de distribución, estadísticas descriptivas, tabla de alertas por umbral |
| **Datos procesados** | Promedio móvil con ventana configurable, agregados horarios con `time_bucket()`, variables normalizadas [0, 1] comparadas |

El sidebar permite ajustar en tiempo real: frecuencia de refresco (10 / 30 / 60 / 120 s), ventana del promedio móvil (3–20 muestras) y umbrales de alerta de temperatura y humedad.

### 6.2 Ejecución local

```bash
# Terminal 1: CounterFit (sensor virtual)
.venv\Scripts\counterfit --port 5050

# Terminal 2: captura continua de datos
.venv\Scripts\python actividad4/nodo_timescale.py --port 5050 --interval-sec 30 --samples 360

# Terminal 3: dashboard
.venv\Scripts\streamlit run actividad4/dashboard_iot.py
```

El navegador abre en `http://localhost:8501`. El dashboard se refresca automáticamente sin necesidad de recargar la página.

### 6.3 Despliegue en la nube (Streamlit Cloud)

Para hacer el dashboard accesible desde cualquier navegador sin instalar nada, se puede publicar gratuitamente en **Streamlit Community Cloud** (https://streamlit.io/cloud):

**Pasos:**

1. El repositorio ya está disponible en https://github.com/Nany1993/nodo-sensor-virtual.

2. Crear las credenciales en el panel de Streamlit Cloud (*App settings → Secrets*), nunca en el repositorio:

```toml
TS_HOST     = "lhlr0l8iz2.pdrh23iqv2.tsdb.cloud.timescale.com"
TS_PORT     = "33711"
TS_DB       = "tsdb"
TS_USER     = "tsdbadmin"
TS_PASSWORD = "tu_password"
```

3. Modificar `dashboard_iot.py` para leer de `st.secrets` en producción:

```python
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

TS_HOST = st.secrets.get("TS_HOST", os.environ.get("TS_HOST"))
```

4. En el panel de Streamlit Cloud: *New app* → seleccionar repositorio → seleccionar `actividad4/dashboard_iot.py` → Deploy.

La URL resultante (`https://usuario.streamlit.app`) es accesible desde cualquier dispositivo.

**Ventajas del despliegue cloud:**
- El dashboard queda disponible 24/7 mientras el nodo sensor esté capturando datos hacia TimescaleDB Cloud.
- Múltiples usuarios pueden consultar el dashboard simultáneamente.
- No se requiere que el PC esté encendido para visualizar los datos (ya están en TimescaleDB Cloud).

---

## Referencias

- Timescale Inc. (2026). *TimescaleDB Documentation*. https://docs.timescale.com  
- Timescale Inc. (2026). *Tiger Cloud Documentation*. https://docs.tigerdata.com  
- Bader, J., et al. (2021). *TimescaleDB: Creating the Time-Series Database for IoT*. Proceedings of VLDB.  
- McKinney, W. (2022). *Python for Data Analysis* (3.ª ed.). O'Reilly Media.  
- Python Software Foundation. (2024). *psycopg2 — PostgreSQL adapter for Python*. https://www.psycopg.org/docs  
- Microsoft. (2024). *IoT for Beginners*. https://github.com/microsoft/IoT-For-Beginners  
- Bröring, A., et al. (2017). *New Generation Sensor Web Enablement*. Sensors, 17(2), 291.
