# Propuesta — Informe práctico: nodo sensor virtual

## Información general

| Campo | Descripción |
|--------|-------------|
| **Título provisional** | Nodo sensor virtual para captura periódica de variables ambientales con registro temporal |
| **Enfoque** | Hardware virtual (simulación) mediante CounterFit |
| **Lenguaje de adquisición** | Python |
| **Persistencia** | SQLite (una tabla: `lecturas`) |

---

## 1. Introducción (orientación para el informe PDF)

El trabajo consiste en implementar un **nodo de medición** que capture al menos una variable de interés, registre cada lectura con **marca de tiempo**, **muestre los datos en pantalla** y los **persista** en una **base de datos SQLite** (archivo `.db`). Al tratarse de un entorno **sin equipo físico**, el sensor y la cadena de medición se **simulan** mediante CounterFit, manteniendo la lógica propia de un sistema IoT: lectura periódica, marca temporal y almacenamiento estructurado.

---

## 2. Objetivos

### 2.1 Objetivo general

Implementar y documentar un nodo sensor virtual que registre variables ambientales seleccionadas con intervalo de muestreo de **30 segundos** durante **3 horas continuas**, generando **360 registros** en la base de datos (archivo `.db` SQLite entregable junto al informe).

### 2.2 Objetivos específicos

- Configurar en CounterFit el proyecto con sensores virtuales acordes a las variables elegidas.
- Desarrollar un programa en Python que inicialice la conexión al simulador, lea valores, genere timestamps y visualice cada muestra por consola.
- Persistir cada muestra en SQLite mediante la tabla **`lecturas`** (ver esquema en §5.3).
- Ejecutar la prueba de validación por **180 minutos** y conservar evidencias (capturas, fragmentos de código, consulta SQL o exportación opcional desde la BD si el docente pide tabla en Excel).

---

## 3. Alcance y variables

### 3.1 Variables propuestas

| Variable | Unidad | Justificación breve |
|----------|--------|---------------------|
| Temperatura ambiente simulada | °C | Indicador de condiciones térmicas habituales en monitoreo ambiental. |
| Humedad relativa simulada | % | Complemento frecuente de temperatura en aplicaciones de confort y conservación ambiental del espacio. |

*Nota: La lista debe ajustarse a los sensores disponibles en la versión de CounterFit utilizada.*

### 3.2 Marca de tiempo

Cada registro incluirá fecha y hora en formato ISO 8601 o equivalente unívoco (ej. `YYYY-MM-DD HH:MM:SS`), generado en el momento de la lectura dentro del programa Python.

---

## 4. Herramientas

| Componente | Función |
|------------|---------|
| **CounterFit** | Simulador con **interfaz web local** para crear y exponer sensores virtuales; no todo ocurre en segundo plano: la UI permite ver y configurar el entorno virtual. |
| **Python** | Adquisición, visualización en consola, control del intervalo de 30 s y persistencia mediante `sqlite3` (estándar). |
| **SQLite** | Motor embebido; un archivo `.db` concentra todas las lecturas. |
| **Editor / IDE** | Desarrollo y ejecución del script de prueba. |

Conexión típica desde código al simulador: host `127.0.0.1` y puerto configurado en CounterFit (frecuentemente `5000`), según documentación del proyecto CounterFit-IoT.

---

## 5. Metodología prevista (hardware y software virtual)

### 5.1 Hardware virtual

1. Instalación y ejecución de CounterFit.
2. Creación del proyecto o dispositivo virtual y asociación de pines/componentes virtuales correspondientes a temperatura y humedad (o variables disponibles equivalentes).
3. Verificación en la interfaz web de que los sensores responden y pueden modificarse conforme se requiera para las pruebas bajo distintas condiciones simuladas.

### 5.2 Software

1. Conectar SQLite: crear archivo (ej. `nodo_sensor.db`), ejecutar script `CREATE TABLE` si la tabla no existe.
2. Inicializar conexión desde Python al endpoint de CounterFit.
3. Bucle de lectura cada **30000 ms** (30 s): lectura → timestamp → imprimir en pantalla → **`INSERT` en tabla `lecturas`**.
4. Repetir **360** iteraciones (total **10800 s** = **3 h**).
5. Cerrar conexión a la base de datos al finalizar (`commit` implícito o explícito por iteración).

### 5.3 Persistencia SQLite: tabla `lecturas`

**Alcance de esta actividad:** el modelo de datos se limita deliberadamente a **una única tabla** (`lecturas`), suficiente para registrar la serie temporal de la prueba (360 muestras) y cumplir con la entrega. **No** se implementan otras tablas en el práctico; las extensiones propuestas quedaron descritas como **mejoras futuras** (§10).

Un solo conjunto físico de datos para la corrida de 3 horas.

#### Tabla única versus `CREATE INDEX` (aclaración para el informe)

En este bloque SQL **solo la sentencia `CREATE TABLE lecturas` define una tabla**. La sentencia siguiente, **`CREATE INDEX ... ON lecturas (ts)`**, **no crea una tabla nueva**: crea un **índice**, es decir una estructura auxiliar que SQLite usa para **acelerar** búsquedas y ordenamientos por la columna `ts`. Siguen existiendo **una sola tabla** de datos; el índice es metadatos internos. En herramientas como DB Browser for SQLite o DBeaver el índice suele aparecer aparte (“Indexes”) y **no** como segunda tabla de filas.

Para un **esquema mínimo** alineado estrictamente con “solo tabla `lecturas`” en el código de entrega, basta ejecutar **`CREATE TABLE lecturas (...)`** y **omitir** por completo el `CREATE INDEX`. El práctico sigue siendo válido; el índice es una mejora opcional de rendimiento.

```sql
CREATE TABLE lecturas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,           -- marca de tiempo de la muestra (ISO 8601, ej. 2026-05-02T08:00:00)
    temperatura_c   REAL NOT NULL,
    humedad_pct     REAL NOT NULL
);

-- Opcional: índice sobre la misma tabla (no define otra tabla)
CREATE INDEX idx_lecturas_ts ON lecturas (ts);
```

- **`id`**: identificador secuencial de la fila.  
- **`ts`**: instante de la medición.  
- **`temperatura_c`** / **`humedad_pct`**: valores leídos del simulador (ajustar nombres si las variables difieren).  
- **Entrega:** adjuntar el archivo `.db`. Si se requiere hoja de cálculo, exportar con `SELECT * FROM lecturas ORDER BY id;` a CSV desde Python, DBeaver, DB Browser for SQLite u otra herramienta.

---

## 6. Visualización en pantalla

- **Primera evidencia:** consola donde se listen lecturas en tiempo casi real (timestamp + valores).
- **Segunda evidencia:** capturas de la **interfaz web de CounterFit** mostrando sensores virtuales durante la corrida.

Con ello se satisface el criterio de visualizar datos capturados en pantalla, combinando herramienta de simulación y salida del programa.

---

## 7. Prueba de tres horas y entregables

| Requisito | Criterio de cumplimiento |
|-----------|---------------------------|
| Duración | 3 horas continuas |
| Período entre muestras | 30 s |
| Cantidad de registros | **360** filas insertadas en `lecturas` |
| Entrega | Archivo **`nodo_sensor.db`** (SQLite) junto al informe; exportación opcional a CSV para gráficos o anexos según instructivo |

**Precauciones operativas:** equipo sin suspensión; CounterFit activo antes de iniciar el script; reloj de sistema correcto para timestamps coherentes.

---

## 8. Estructura del informe PDF (máximo 8 páginas)

1. Portada — título e integrantes.
2. Introducción.
3. Metodología — desarrollo hardware virtual y software (detalle de CounterFit, Python y esquema SQLite).
4. Resultados — distintas condiciones de las variables con evidencias (imágenes, código destacado).
5. Análisis de resultados y posibles mejoras.
6. Conclusiones.
7. Referencias (APA 7.ª edición).

---

## 9. Resultados esperados para la sección de pruebas

- Gráfico tiempo vs temperatura y tiempo vs humedad (consulta a `lecturas` o exportación puntual a CSV).
- Tabla resumen estadístico breve (mínimo, máximo, promedio) por variable.
- Evidencias visuales: interfaz CounterFit + consola + captura del **COUNT(\*)** o listado desde la BD (**360 filas**).
- Interpretación cualitativa al variar manualmente valores en la simulación en distintos tramos si la herramienta lo permite.

---

## 10. Mejoras posibles (para el análisis)

### 10.1 Mejoras técnicas y operativas

- Sensores físicos calibrados y comparación contra simulación.
- Precisión del reloj (RTC o sincronización NTP si en el futuro se usa hardware con red).
- Replicación a servidor central o envío MQTT para sistemas distribuidos (más allá del SQLite local).
- Manejo de reconexión si CounterFit se reinicia.

### 10.2 Líneas futuras del modelo de datos (no incluidas en esta entrega)

- **Sesiones de muestreo:** tabla de metadatos por cada corrida (intervalo, fechas planificadas, notas) y enlace mediante `sesion_id` desde `lecturas`, para diferenciar varias pruebas de 3 h en el mismo archivo `.db`.
- **Configuración del nodo:** tabla o registro con host/puerto de CounterFit y versión del script, para auditoría reproducible entre equipos.
- Otras extensiones solo si el producto crece (usuarios, dispositivos, calibraciones); fuera del alcance del informe práctico actual.

---

## 11. Referencias sugeridas (completar fechas de consulta y detalle APA)

- Repositorio CounterFit-IoT en GitHub: `https://github.com/CounterFit-IoT/CounterFit`
- Documentación o cursada oficial que utilicen (por ejemplo material de IoT para principiantes de Microsoft si aplica a su curso).

---

## 12. Cronograma sugerido (previo al informe)

| Actividad | Duración estimada |
|-----------|-------------------|
| Instalación CounterFit y prueba de lectura manual | 1 sesión |
| Código Python + SQLite (`lecturas`) + prueba corta (5-10 minutos) | 1 sesión |
| **Corrida completa 3 h** | 3 h (una ventana continua) |
| Gráficos, capturas y redacción del PDF | 1-2 sesiones |

---

*Documento de planeación. Ajustar nombres de integrantes, título final y bibliografía conforme instrucciones del docente.*
