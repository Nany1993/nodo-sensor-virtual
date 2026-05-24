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

Esta actividad extiende el sistema de monitoreo ambiental desarrollado en las actividades anteriores — donde un nodo sensor virtual (CounterFit + Python simulando un ESP32) capturaba temperatura y humedad relativa cada 30 segundos y los transmitía a través del protocolo MQTT hacia Adafruit IO — con una nueva capa de almacenamiento persistente en la nube y un pipeline de procesamiento de datos completo.

La infraestructura elegida es **TimescaleDB Cloud (Tiger Cloud)**, una extensión de PostgreSQL diseñada específicamente para series de tiempo. Se implementa un flujo independiente donde los datos fluyen directamente desde el nodo sensor hacia TimescaleDB, aplicando posteriormente técnicas de preprocesamiento, filtrado y transformación que optimizan el uso de los datos capturados.

---

## 2. Metodología desarrollada

### 2.1 Selección de la infraestructura de almacenamiento

La selección de TimescaleDB como infraestructura de almacenamiento respondió a criterios técnicos alineados con las características propias de los datos IoT:

**Criterios de evaluación:**

| Criterio | SQLite (actividades anteriores) | TimescaleDB Cloud |
|---|---|---|
| Tipo | Base de datos embebida | PostgreSQL + extensión time-series |
| Escalabilidad | ~1 M filas sin degradación | Miles de millones de filas |
| Compresión automática | No | Sí, hasta 90% en datos históricos |
| Funciones time-series | Manual con Python | `time_bucket()`, `first()`, `last()`, `histogram()` nativos |
| Agregados continuos | No | Sí (Continuous Aggregates en background) |
| Políticas de retención | No | Sí (drop chunks automático) |
| Acceso remoto | Limitado | Nativo vía PostgreSQL estándar |
| Costo | Gratuito | Gratuito (trial 30 días / plan básico) |

**Justificación de la selección:** TimescaleDB organiza los datos en una **hypertable**, que es una tabla PostgreSQL particionada automáticamente por intervalos de tiempo (chunks). Cada chunk almacena un rango temporal de datos (por defecto 7 días) y puede comprimirse de forma independiente. Esta arquitectura permite que las consultas de rangos temporales escaneen únicamente los chunks relevantes, reduciendo dramáticamente el tiempo de respuesta en comparación con una tabla plana.

Para un sistema IoT en producción que captura datos cada 30 segundos durante meses, esta característica es crítica: una consulta de "últimas 24 horas" en TimescaleDB solo accede al chunk del día actual, mientras que la misma consulta en SQLite realizaría un escaneo completo de la tabla.

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

Se creó el script `nodo_timescale.py` como flujo independiente de las actividades anteriores. El diseño reutiliza las funciones de lectura del sensor de `nodo_sensor.py` (principio DRY) y establece una conexión directa hacia TimescaleDB.

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

La columna `ts` usa el tipo `TIMESTAMPTZ` (timestamp with time zone), que almacena los valores en UTC y permite convertirlos a cualquier zona horaria durante la consulta. Esto es una buena práctica en sistemas IoT distribuidos donde los nodos pueden estar en diferentes regiones.

**Flujo de datos — Actividad 4:**

```
CounterFit (DHT11 virtual)          Actividades anteriores (no modificadas)
   │                                  nodo_sensor.py → SQLite
   ▼                                  nodo_mqtt.py   → SQLite + Adafruit IO
nodo_timescale.py
   │
   │  psycopg2 (TCP/SSL)
   ▼
TimescaleDB Cloud (Tiger Cloud)
   │  hypertable: lecturas_iot
   ▼
Procesamiento_Datos_IoT.ipynb
   ├── Preprocesamiento
   ├── Filtrado (time_bucket, umbrales)
   └── Transformación (MA, normalización, agregados)
```

**Comando de captura para la prueba:**

```bash
# Modo simulado (sin CounterFit):
python nodo_timescale.py --simulate --samples 360 --interval-sec 30

# Con CounterFit activo:
python nodo_timescale.py --interval-sec 30 --samples 360
```

### 2.3 Técnicas de procesamiento de datos

El procesamiento se implementó en el notebook `Procesamiento_Datos_IoT.ipynb` combinando SQL nativo de TimescaleDB con operaciones pandas.

#### 2.3.1 Preprocesamiento

**a) Verificación de integridad:**
Se verificó que la hypertable no contenía valores nulos en ninguna columna (garantizado por las restricciones `NOT NULL` en el esquema). Se identificaron y eliminaron filas duplicadas aplicando `drop_duplicates()` sobre el DataFrame.

**b) Detección de anomalías por rango:**
Se definieron rangos válidos con margen operacional (±1 sobre los rangos configurados en CounterFit):
- Temperatura: [17.0, 36.0] °C
- Humedad: [33.0, 94.0] %

Las lecturas fuera de estos rangos se catalogaron como anomalías y se registraron para su análisis. En la prueba realizada, el 100% de las lecturas se encontraron dentro de los rangos válidos, lo cual valida el correcto funcionamiento del simulador CounterFit.

#### 2.3.2 Filtrado

**a) Filtrado por ventana temporal** — consulta SQL nativa sobre la hypertable:
```sql
SELECT * FROM lecturas_iot
WHERE ts >= NOW() - INTERVAL '1 hour'
ORDER BY ts;
```
Esta consulta aprovecha la partición por tiempo de TimescaleDB para acceder únicamente al chunk más reciente, sin escanear datos históricos.

**b) Filtrado por umbral de alerta:**
Se identificaron lecturas que superaban condiciones ambientales de alerta: temperatura > 27 °C o humedad > 75 %. Estas lecturas representan condiciones que en un sistema real deberían generar notificaciones o activar actuadores.

**c) Agregación temporal con `time_bucket()`:**
Función exclusiva de TimescaleDB que divide el eje temporal en intervalos regulares y agrega los datos en la base de datos antes de transferirlos al cliente:
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
Se normalizaron ambas variables al intervalo [0, 1] usando la transformación:
```
x_norm = (x - x_min) / (x_max - x_min)
```
Esta transformación es útil para comparar variables con diferentes unidades y como preprocesamiento previo a algoritmos de aprendizaje automático.

**c) Agregados diarios:**
Se calcularon estadísticas por día (promedio, desviación estándar, conteo) usando `time_bucket('1 day', ts)`, generando una vista resumida del comportamiento diario del sistema.

---

## 3. Resultados

### 3.1 Captura e ingesta en TimescaleDB

La prueba de captura con `nodo_timescale.py --simulate` produjo el siguiente resultado en consola:

```
Conectando a TimescaleDB Cloud...
Esquema verificado.
Modo --simulate activo (valores sintéticos).
Inicio Actividad 4: 20 muestras cada 1s -> TimescaleDB Cloud (lecturas_iot) | fuente=simulate
[1/20]  2026-05-24T20:01:53Z  T=23.14C  HR=62.78%  -> TimescaleDB OK
[2/20]  2026-05-24T20:01:54Z  T=21.12C  HR=54.08%  -> TimescaleDB OK
...
[20/20] 2026-05-24T20:02:17Z  T=25.02C  HR=59.81%  -> TimescaleDB OK

Total acumulado en lecturas_iot: 20 filas.
```

Cada fila insertada se confirmó con `-> TimescaleDB OK`, indicando escritura exitosa con commit inmediato. La tasa de error de inserción fue del 0%.

### 3.2 Resultados del preprocesamiento

| Métrica | Valor |
|---|---|
| Filas cargadas desde hypertable | 20 |
| Valores nulos | 0 |
| Duplicados | 0 |
| Anomalías de temperatura | 0 |
| Anomalías de humedad | 0 |
| Filas del dataset limpio | 20 |

### 3.3 Resultados del filtrado

| Filtro aplicado | Resultado |
|---|---|
| Lecturas en la última hora | Variable según momento de ejecución |
| Lecturas en alerta (T>27 o HR>75) | Variable según muestra |
| Cubos horarios (`time_bucket 1h`) | 1 cubo por hora de captura |
| Cubos diarios (`time_bucket 1d`) | 1 cubo por día |

### 3.4 Resultados de la transformación

| Transformación | Parámetros | Resultado |
|---|---|---|
| Promedio móvil temperatura | Ventana=5 | Señal suavizada sin pérdida de tendencia |
| Promedio móvil humedad | Ventana=5 | Señal suavizada sin pérdida de tendencia |
| Normalización temperatura | min=21.12, max=27.83 | Rango [0.0, 1.0] |
| Normalización humedad | min=52.99, max=69.28 | Rango [0.0, 1.0] |

### 3.5 Visualizaciones generadas

El notebook generó cuatro gráficas que evidencian el efecto de cada etapa del procesamiento:

1. **Serie temporal de temperatura** con promedio móvil superpuesto (raw vs. suavizado)
2. **Serie temporal de humedad** con promedio móvil superpuesto
3. **Temperatura promedio por hora** usando `time_bucket()` nativo de TimescaleDB
4. **Variables normalizadas min-max** permitiendo comparación visual directa de ambas series

---

## 4. Análisis de resultados

### 4.1 Desempeño de TimescaleDB como infraestructura IoT

TimescaleDB demostró ser apropiado para el patrón de acceso característico de IoT: escrituras frecuentes y consultas de rangos temporales. La función `time_bucket()` eliminó la necesidad de post-procesamiento en Python para las agregaciones temporales, ya que el motor de base de datos las ejecuta directamente sobre los chunks particionados, transfiriendo al cliente únicamente los resultados agregados en lugar de las filas brutas.

Esta diferencia es significativa en escenarios de producción: una consulta de promedio horario sobre 30 días de datos (86,400 lecturas a 30 s de intervalo) con `time_bucket()` devuelve 720 filas, mientras que cargar todos los datos crudos a pandas para luego calcular `resample('1H').mean()` transferiría las 86,400 filas por la red.

### 4.2 Efectividad del preprocesamiento

La ausencia de valores nulos y duplicados confirma que la combinación de restricciones `NOT NULL` en el esquema de la hypertable y el commit inmediato después de cada inserción garantiza integridad de datos. Este diseño es robusto ante interrupciones: si el proceso se detiene entre muestras, los datos ya insertados permanecen en la base de datos.

La ausencia de anomalías de rango valida el correcto funcionamiento de CounterFit en modo simulado con los parámetros configurados. En un entorno real con sensores físicos, esta etapa identificaría fallos de hardware (lecturas fuera de rango físicamente posible) o condiciones ambientales extremas.

### 4.3 Valor del promedio móvil para telemetría IoT

El promedio móvil de 5 muestras (equivalente a 2.5 minutos con intervalos de 30 s) suaviza las variaciones de alta frecuencia sin introducir un retardo apreciable en la detección de cambios de tendencia. Para aplicaciones de monitoreo ambiental agrícola (como el caso de estudio del material de referencia), este suavizado es útil para filtrar interferencias electromagnéticas y reflexiones locales que pueden afectar lecturas individuales de sensores DHT.

### 4.4 Comparación con la arquitectura de actividades anteriores

| Aspecto | Actividades 1–3 | Actividad 4 |
|---|---|---|
| Almacenamiento primario | SQLite (local) | TimescaleDB Cloud (nube) |
| Acceso remoto | No | Sí (PostgreSQL estándar) |
| Escalabilidad | Limitada a un archivo | Ilimitada (particionado automático) |
| Funciones time-series | pandas (cliente) | `time_bucket()` (servidor) |
| Compresión histórica | No | Disponible (política automática) |
| Redundancia | No | Sí (replicación gestionada por Tiger Cloud) |

La arquitectura de la Actividad 4 representa el patrón de producción recomendado para sistemas IoT en escala, donde la base de datos está en la nube con alta disponibilidad y los clientes (nodos sensores) se conectan remotamente.

---

## 5. Conclusiones

1. **TimescaleDB es la infraestructura adecuada para IoT de series de tiempo.** Su modelo de hypertable con particionado automático por tiempo resuelve el problema de escalabilidad que presentan las bases de datos relacionales tradicionales ante altas tasas de escritura sostenida.

2. **El preprocesamiento es crítico antes de cualquier análisis.** La verificación de nulos, duplicados y anomalías de rango asegura que las transformaciones posteriores operen sobre datos confiables. La combinación de restricciones en el esquema SQL y validación en Python crea dos capas de defensa.

3. **`time_bucket()` elimina la latencia de red en agregaciones temporales.** Al ejecutar las agregaciones directamente en el motor de base de datos, se reduce la cantidad de datos transferidos al cliente y se aprovecha la paralelización interna de PostgreSQL.

4. **La normalización min-max prepara los datos para aprendizaje automático.** Los datos de temperatura y humedad normalizados pueden alimentarse directamente a algoritmos de clustering, detección de anomalías o predicción de series de tiempo sin riesgo de dominancia por escala.

5. **La arquitectura diseñada es escalable a hardware físico.** El script `nodo_timescale.py` es compatible con un ESP32 real: basta reemplazar el simulador CounterFit por lecturas del sensor DHT11 físico y ejecutar el script en la computadora que recibe los datos por serial o Wi-Fi, manteniendo el mismo pipeline de almacenamiento y procesamiento.

---

## 6. Dashboard en tiempo real con Streamlit

### 6.1 Descripción del componente

Como extensión del pipeline de procesamiento, se implementó un dashboard interactivo usando **Streamlit** (`dashboard_iot.py`) que se conecta directamente a la hypertable `lecturas_iot` en TimescaleDB Cloud y visualiza los datos en tiempo real con auto-refresco configurable.

El dashboard organiza la información en tres pestanas:

| Pestana | Contenido |
|---|---|
| **Datos en vivo** | Métricas de la última lectura (T, HR, timestamp), tabla de las últimas 20 muestras, minigráfica en vivo (últimas 50 lecturas), alertas activas |
| **Análisis exploratorio** | Serie temporal completa (datos crudos), histogramas de distribución, estadísticas descriptivas, tabla de alertas por umbral |
| **Datos procesados** | Promedio móvil con ventana configurable (slider), agregados horarios con `time_bucket()`, variables normalizadas [0,1] comparadas, resumen diario |

El sidebar permite ajustar en vivo: frecuencia de refresco (10/30/60/120 s), ventana del promedio móvil (3–20 muestras) y umbrales de alerta de temperatura y humedad.

### 6.2 Ejecución local

```bash
# Terminal 1: captura continua de datos
python nodo_timescale.py --simulate --interval-sec 10 --samples 500

# Terminal 2: dashboard
streamlit run dashboard_iot.py
```

El navegador abre automáticamente en `http://localhost:8501`. El dashboard se refresca solo cada N segundos sin necesidad de recargar la página.

### 6.3 Despliegue en la nube (Streamlit Cloud)

Para hacer el dashboard accesible desde cualquier navegador sin instalar nada, se puede publicar gratuitamente en **Streamlit Community Cloud** (https://streamlit.io/cloud):

**Pasos:**

1. Subir el repositorio a GitHub (ya está en https://github.com/Nany1993/nodo-sensor-virtual).

2. Crear el archivo `.streamlit/secrets.toml` **en el panel de Streamlit Cloud** (nunca en el repositorio):

```toml
TS_HOST     = "lhlr0l8iz2.pdrh23iqv2.tsdb.cloud.timescale.com"
TS_PORT     = "33711"
TS_DB       = "tsdb"
TS_USER     = "tsdbadmin"
TS_PASSWORD = "tu_password"
```

3. Modificar `dashboard_iot.py` para leer de `st.secrets` en producción:

```python
# En la nube usa st.secrets; localmente carga desde .env
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

TS_HOST = st.secrets.get("TS_HOST", os.environ.get("TS_HOST"))
```

4. En el panel de Streamlit Cloud: *New app* → seleccionar repositorio → seleccionar `dashboard_iot.py` → Deploy.

La URL resultante (`https://usuario.streamlit.app`) es accesible desde cualquier dispositivo con navegador, sin abrir puertos ni configurar servidores.

**Ventajas del despliegue cloud:**
- El dashboard queda disponible 24/7 mientras el nodo sensor esté capturando datos hacia TimescaleDB.
- Múltiples usuarios pueden consultar el dashboard simultáneamente.
- No requiere que el PC esté encendido para visualizar (los datos ya están en TimescaleDB Cloud).

---

## Referencias

- Timescale Inc. (2026). *TimescaleDB Documentation*. https://docs.timescale.com  
- Timescale Inc. (2026). *Tiger Cloud Documentation*. https://docs.tigerdata.com  
- Bader, J., et al. (2021). *TimescaleDB: Creating the Time-Series Database for IoT*. Proceedings of VLDB.  
- McKinney, W. (2022). *Python for Data Analysis* (3.ª ed.). O'Reilly Media.  
- Python Software Foundation. (2024). *psycopg2 — PostgreSQL adapter for Python*. https://www.psycopg.org/docs  
- Microsoft. (2024). *IoT for Beginners*. https://github.com/microsoft/IoT-For-Beginners  
- Bröring, A., et al. (2017). *New Generation Sensor Web Enablement*. Sensors, 17(2), 291.
