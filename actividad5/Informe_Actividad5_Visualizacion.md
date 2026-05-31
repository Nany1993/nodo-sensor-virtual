# Informe — Actividad 5
## Visualizacion en tiempo real y analitica basica IoT

---

**Estudiante:** Ana María García Arias  
**Programa:** Maestría en Inteligencia Artificial  
**Asignatura:** Internet de las Cosas  
**Docente:** Cristian Duney Bermúdez Quintero  
**Fecha:** Mayo 2026  
**Repositorio:** https://github.com/Nany1993/nodo-sensor-virtual

---

## 1. Objetivo

Diseñar e implementar una solución de visualización en tiempo real para los datos transmitidos por el nodo sensor IoT, integrando la fuente de datos en la nube (TimescaleDB) con un dashboard interactivo y analitica basica (estadisticas, correlacion y dispersion).

---

## 2. Seleccion de herramienta de visualizacion

| Herramienta evaluada | Ventaja | Limitacion |
|---|---|---|
| Grafana | Paneles profesionales para series de tiempo | Configuracion mas compleja; menos flexible para filtros custom |
| Power BI | Reportes empresariales | Licencia; menos integracion directa con Python IoT |
| **Streamlit + Plotly** | Desarrollo rapido en Python, graficos interactivos, conexion directa a PostgreSQL/TimescaleDB | Requiere servidor propio o Streamlit Cloud |

**Decision:** Streamlit con Plotly, porque el proyecto ya esta en Python, la conexion a TimescaleDB es directa con SQLAlchemy/pandas, y permite login, filtros dinamicos y actualizacion periodica sin codigo frontend adicional.

---

## 3. Integracion con la fuente de datos

```
CounterFit (DHT11 virtual, :5050)
        │ cada 5 s
        ▼
nodo_timescale.py  ──SSL/TLS──►  TimescaleDB Cloud (lecturas_iot)
                                        │
                                        ▼
                              dashboard_iot.py (Streamlit :8501)
```

- **Captura:** `actividad4/nodo_timescale.py` inserta temperatura y humedad con preprocesamiento en linea.
- **Almacenamiento:** hypertable `lecturas_iot` en TimescaleDB Cloud.
- **Visualizacion:** `actividad4/dashboard_iot.py` consulta la BD con filtros temporales y refresco automatico cada 30 s.

---

## 4. Diseno del dashboard

### 4.1 Componentes

| Componente | Implementacion |
|---|---|
| Indicadores | Metricas de temperatura, humedad, timestamp y conteo de lecturas |
| Graficos temporales | Series duales (T °C y HR %) con Plotly |
| Tablas | Lecturas filtradas ordenadas por fecha; tabla `describe()` |
| Analitica basica | Histogramas, Pearson, Spearman, grafico de dispersion |
| Filtros | Ano, meses multiples, dias multiples, hora |
| Seguridad | Login con credenciales en `.env`; conexion TLS a TimescaleDB |
| Tiempo real | Captura cada 5 s; panel se actualiza cada 30 s (+ boton manual) |

### 4.2 Pestanas

| Pestana | Contenido |
|---|---|
| **En vivo (ultimas)** | Ultimas 120 lecturas sin filtros del sidebar |
| **Datos filtrados** | Serie temporal + tabla segun segmentacion temporal |
| **Estadisticas** | Correlacion (Pearson/Spearman), dispersion T vs HR, histogramas, resumen estadistico |

---

## 5. Analitica basica

La pestana **Estadisticas** expone:

1. **Coeficiente de Pearson** y **Spearman** entre temperatura y humedad.
2. **Grafico de dispersion** (temperatura en eje X, humedad en eje Y).
3. **Histogramas** de distribucion por variable.
4. **Estadisticas descriptivas** (media, desviacion, min, max, cuartiles).

La interpretacion de los resultados queda a cargo del analista que revisa los graficos.

---

## 6. Ejecucion

```powershell
# Desde la raiz del proyecto
.\actividad5\activar_flujo.ps1
```

O manualmente en tres terminales:

```powershell
.venv\Scripts\counterfit --port 5050
.venv\Scripts\python actividad4/nodo_timescale.py --port 5050 --interval-sec 5 --samples 1440
.venv\Scripts\streamlit run actividad4/dashboard_iot.py
```

Login del dashboard: credenciales en `.env` (`DASHBOARD_USER`, `DASHBOARD_PASSWORD`).

---

## 7. Consideraciones de visualizacion y analisis

- **Escala dual:** temperatura y humedad comparten el tiempo pero tienen unidades distintas; se usan dos ejes Y.
- **Zona horaria:** timestamps se muestran en `America/Bogota`.
- **Refresco vs captura:** el sensor captura cada 5 s; el panel refresca cada 30 s para equilibrar tiempo real e interactividad.
- **Correlacion:** Pearson mide relacion lineal; Spearman es robusta a relaciones no lineales.
- **Filtros:** la analitica respeta la segmentacion temporal del sidebar.

---

## 8. Conclusiones

1. Streamlit integrado con TimescaleDB permite un dashboard IoT funcional con bajo esfuerzo de desarrollo.
2. La segmentacion temporal (meses y dias multiples) facilita explorar periodos concretos sin consultas SQL manuales.
3. Correlacion y dispersion completan el analisis basico junto a las estadisticas descriptivas ya existentes.
4. El flujo CounterFit → TimescaleDB → Streamlit demuestra visualizacion casi en tiempo real apta para monitoreo ambiental.
