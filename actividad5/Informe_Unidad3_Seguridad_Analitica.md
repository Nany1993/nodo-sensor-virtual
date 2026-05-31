# Informe — Unidad 3
## Seguridad en IoT y analisis de datos

---

**Estudiante:** Ana María García Arias  
**Programa:** Maestría en Inteligencia Artificial  
**Asignatura:** Internet de las Cosas  
**Docente:** Cristian Duney Bermúdez Quintero  
**Fecha:** Mayo 2026  
**Repositorio:** https://github.com/Nany1993/nodo-sensor-virtual

---

## 1. Introduccion

En esta fase se completa el proyecto de monitoreo ambiental con un panel web que muestra, casi en tiempo real, la temperatura y la humedad capturadas por un sensor virtual. El sistema guarda los datos en la nube y permite consultarlos con graficos, tablas y filtros por fecha.

Este informe responde las tres preguntas de la Unidad 3 y explica, con lenguaje sencillo, como se protege la informacion y como el panel ayuda a entender lo que mide el sensor.

**Como funciona el sistema (resumen):**

```
Sensor virtual (CounterFit)
        |
        v
Programa de captura (nodo_timescale.py)
        |
        v
Base de datos en la nube (TimescaleDB)
        |
        v
Panel web (dashboard_iot.py) — http://localhost:8501
```

---

## 2. Pregunta 1: Riesgos de seguridad en IoT y como reducirlos

### 2.1 Principales riesgos en nuestro proyecto

| Riesgo | Que puede pasar | Que hicimos (o se puede mejorar) |
|---|---|---|
| Claves y contraseñas expuestas | Alguien accede a la base de datos o al panel | Las claves van en un archivo `.env` que no se sube a GitHub |
| Panel abierto a cualquiera | Cualquier persona ve los datos | El panel pide usuario y contraseña antes de entrar |
| Datos alterados o falsos | Se guardan lecturas incorrectas | El programa descarta valores fuera de rango y marca las lecturas validas |
| Comunicacion interceptada hacia la nube | Terceros leen lo que envia el sensor | La conexion a TimescaleDB va cifrada (conexion segura tipo HTTPS) |
| Contraseñas debiles | Entrada facil con `admin` / `admin` | Se pueden cambiar en `.env`; en produccion usar contraseñas largas |
| Sensor solo en la PC local | Si CounterFit no corre, no hay datos nuevos | Es un entorno de practica; en un proyecto real el sensor estaria en red protegida |
| Envio MQTT sin cifrado (Actividad 2/3) | En Adafruit IO el envio iba por canal no cifrado | En esta fase se usa la base en la nube con conexion segura |

### 2.2 Medidas que ya aplicamos

1. **Separar secretos del codigo:** usuario, contraseña del panel y de la base de datos estan en `.env`.
2. **Acceso al panel con login:** solo quien tenga credenciales ve los datos.
3. **Conexion segura a la nube:** al guardar en TimescaleDB se exige conexion cifrada.
4. **Revisar datos antes de guardar:** temperatura y humedad fuera de limites razonables no se insertan.
5. **Comparacion segura de contraseñas:** el panel no compara la clave de forma naive; usa un metodo que dificulta ataques por tiempo.

### 2.3 Que se podria mejorar en un despliegue real

- Usar contraseñas fuertes y distintas para panel y base de datos.
- Publicar el panel solo en HTTPS (por ejemplo Streamlit Cloud con HTTPS).
- Limitar quien puede entrar a la base de datos por IP o red privada.
- Registrar quien entra al panel y cuando (bitacora de accesos).
- Cifrar tambien el envio MQTT si se vuelve a usar Adafruit IO (puerto seguro).

---

## 3. Pregunta 2: Proteccion de datos, privacidad y normativa

### 3.1 Que datos manejamos

El sensor registra **temperatura**, **humedad**, **fecha y hora** y una etiqueta de origen (`counterfit`, pruebas, etc.). En la practica son datos ambientales simulados, no nombres ni documentos de personas.

Aun asi, en un escenario real (oficina, bodega, vivienda) esos datos podrian **revelar habitos** (horarios, presencia, condiciones del lugar). Por eso conviene tratarlos con cuidado.

### 3.2 Ley 1581 de 2012 (Colombia) — ideas clave

La Ley de Proteccion de Datos Personales (Habeas Data) aplica cuando se tratan datos que identifican o pueden identificar a una persona. Para un proyecto IoT serio conviene tener presente:

| Principio | Significado sencillo | Aplicacion en nuestro caso |
|---|---|---|
| Finalidad | Solo usar los datos para lo que se dijo | Medir ambiente para monitoreo, no para otro fin |
| Libertad | Informar y, si aplica, pedir autorizacion | En un despliegue real: aviso de que hay sensores |
| Veracidad | Datos correctos y actualizados | Validacion de rangos y marca de lecturas validas |
| Seguridad | Proteger la informacion | Login, `.env`, conexion cifrada a la nube |
| Confidencialidad | No compartir con quien no debe ver | Panel con acceso restringido |
| Minimizacion | Solo recolectar lo necesario | Solo temperatura y humedad, no datos extra |

### 3.3 Buenas practicas que seguimos

- No publicar contraseñas en GitHub.
- Mostrar fechas en hora de Colombia (`America/Bogota`) para que el analisis sea claro.
- Permitir filtrar periodos sin exportar toda la base a archivos sueltos.
- La interpretacion de los graficos la hace la persona que analiza; el sistema solo muestra numeros y figuras.

### 3.4 Responsabilidades en un proyecto real

- Definir **quien es responsable** de los datos (titular del tratamiento).
- Establecer **cuanto tiempo** se guardan las lecturas.
- Tener un plan si hay **fuga de credenciales** (cambiar claves, revisar accesos).

---

## 4. Pregunta 3: Analisis de datos y panel para tomar decisiones

### 4.1 Que herramientas usamos

Elegimos **Streamlit** para el panel y **Plotly** para los graficos interactivos. Permiten conectar directamente con la base en la nube, filtrar por fechas y actualizar la pantalla cada 30 segundos (o al pulsar **Actualizar ahora**).

### 4.2 Que muestra el panel

| Pestana | Para que sirve |
|---|---|
| **En vivo (ultimas)** | Ver lo mas reciente del sensor: ultimos valores y grafica de las ultimas 120 lecturas |
| **Datos filtrados** | Ver un periodo concreto (ano, meses, dias, hora) con tabla y grafica |
| **Estadisticas** | Resumen numerico, histogramas, correlacion entre temperatura y humedad, grafico de dispersion |

**Filtros del menu lateral:** ano, uno o varios meses, uno o varios dias, hora. Asi se puede comparar, por ejemplo, varios dias de mayo sin escribir consultas a mano.

### 4.3 Analisis basico incluido

1. **Numeros resumen:** promedio, minimo, maximo, desviacion (tabla descriptiva).
2. **Histogramas:** como se distribuyen temperatura y humedad.
3. **Correlacion de Pearson y Spearman:** indica si las dos variables suben o bajan juntas (sin texto interpretativo automatico).
4. **Grafico de dispersion:** cada punto es una lectura; el analista ve patrones visualmente.

El procesamiento al guardar (promedio movil, normalizacion) ocurre en `nodo_timescale.py`; el panel se centra en datos claros para consulta y analisis visual.

### 4.4 Como apoya la toma de decisiones

| Situacion | Que mira el usuario | Decision posible |
|---|---|---|
| Monitoreo del momento | Pestana En vivo | Saber si hace calor o hay mucha humedad ahora |
| Revision de un dia o mes | Filtros + Datos filtrados | Comparar un periodo concreto (ej. mayo) |
| Detectar patrones | Estadisticas + dispersion | Ver si al subir la temperatura baja la humedad |
| Muchas lecturas | Tabla filtrada | Revisar valores puntuales o exportar mentalmente tendencias |
| Datos desactualizados | Boton Actualizar ahora | Refrescar sin esperar el ciclo automatico |

El panel **no decide solo**: muestra la informacion ordenada para que la persona responsable interprete y actue (ventilar, revisar equipo, ajustar umbral interno, etc.).

---

## 5. Procesamiento de datos (antes de verlos en el panel)

Antes de guardar cada lectura, el programa:

1. **Comprueba** que temperatura y humedad esten en rangos validos.
2. **Evita duplicados** muy seguidos en el tiempo.
3. **Calcula** promedio movil y valores normalizados (util para analisis futuro).

Solo las lecturas marcadas como validas alimentan las consultas del panel. Eso reduce errores por lecturas absurdas del simulador.

---

## 6. Como ejecutar esta fase

```powershell
# Desde la raiz del proyecto
.\actividad5\activar_flujo.ps1
```

Abre CounterFit, la captura hacia la nube y el panel en `http://localhost:8501`.

Credenciales del panel en `.env`:

```
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=admin
```

(Recomendado cambiarlas antes de un uso fuera del aula.)

---

## 7. Conclusiones

1. **Seguridad:** el proyecto aplica medidas basicas utiles (login, secretos fuera del codigo, conexion cifrada a la nube, validacion de datos). Quedan mejoras tipicas de un entorno real (contraseñas fuertes, HTTPS publico, auditoria).

2. **Privacidad y Ley 1581:** aunque los datos de la practica son simulados, el marco colombiano exige finalidad clara, seguridad y no recolectar de mas; el diseno del sistema va en esa direccion.

3. **Analitica y panel:** Streamlit con filtros, graficos, tablas y correlacion permite ver el estado actual, revisar periodos pasados y explorar relaciones entre variables para apoyar decisiones informadas.

4. **Unidad 3 cumplida en conjunto:** captura en la nube, panel en tiempo casi real, analisis basico y reflexion sobre riesgos y proteccion de datos aplicados a este nodo sensor IoT.

---

## 8. Referencias del proyecto

| Recurso | Ubicacion |
|---|---|
| Panel web | `actividad4/dashboard_iot.py` |
| Captura y guardado | `actividad4/nodo_timescale.py` |
| Informe de visualizacion | `actividad5/Informe_Actividad5_Visualizacion.md` |
| Arranque rapido | `actividad5/activar_flujo.ps1` |
| Repositorio | https://github.com/Nany1993/nodo-sensor-virtual |
