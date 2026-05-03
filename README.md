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
git clone https://github.com/<usuario>/nodo-sensor-virtual.git
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

## Estructura del repositorio

```
nodo-sensor-virtual/
├── nodo_sensor.py                   # Script principal de captura
├── init_db.py                       # Creación inicial de la BD
├── export_lecturas_csv.py           # Exportación a CSV
├── requirements.txt                 # Dependencias Python
├── Graficos_Resultados.ipynb        # Notebook de análisis y visualización
├── Guia_Actividad_3_horas.ipynb     # Guía paso a paso de la actividad
├── Informe_Practica_Nodo_Sensor.md  # Borrador del informe
├── Propuesta_Nodo_Sensor_Virtual.md # Propuesta y planificación
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
