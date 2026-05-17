# SmartSort EcoEnterprise IoT 2.0  
## Prototipo Inteligente de Clasificación de Residuos con Trazabilidad en Tiempo Real

**Nombre de los integrantes:**  
[Ana María García Arias]

---

## 1. Planteamiento del problema

En oficinas y entornos empresariales persisten errores en la segregación de residuos en la fuente, derivados de decisiones rápidas, falta de orientación en tiempo real y ausencia de mecanismos de validación durante el proceso de disposición. Esta situación genera contaminación cruzada entre residuos, disminuye el potencial de aprovechamiento de materiales reciclables y aumenta los costos asociados a la gestión ambiental.

A pesar de que en Colombia la Resolución 2184 de 2019 establece el Código de Colores obligatorio (blanco, verde y negro), su aplicación efectiva depende del comportamiento individual de los usuarios, sin contar con herramientas tecnológicas que guíen, verifiquen o corrijan dichas decisiones en el momento en que ocurren.

Adicionalmente, en la mayoría de las organizaciones no existe un sistema de información que permita registrar de manera estructurada cada evento de clasificación, lo que impide responder preguntas clave como: quién realizó la disposición, en qué contexto ocurrió, cuántos intentos fueron necesarios y si hubo mejora tras la retroalimentación. Esta ausencia de trazabilidad limita la generación de indicadores confiables y dificulta la toma de decisiones basada en datos.

Como consecuencia, los programas de cultura ambiental y gestión de residuos se implementan de forma generalizada y reactiva, sin evidencia objetiva sobre el comportamiento real de los usuarios ni sobre la efectividad de las estrategias adoptadas, lo que reduce su impacto y sostenibilidad en el tiempo.

---

## 2. Justificación

La correcta clasificación de residuos en la fuente representa un desafío recurrente en entornos organizacionales, debido a la falta de herramientas que permitan guiar, validar y medir el comportamiento real de los usuarios en el proceso de disposición. Esta problemática impacta directamente el cumplimiento de la normativa ambiental colombiana y la efectividad de los programas de gestión de residuos.

En Colombia, la Resolución 2184 de 2019 establece el Código de Colores obligatorio para la separación de residuos (blanco, verde y negro), lo cual exige a las organizaciones implementar mecanismos que garanticen su correcta aplicación. Sin embargo, en la práctica, la segregación depende en gran medida del conocimiento individual y no cuenta con sistemas de verificación o trazabilidad.

En este contexto, la solución propuesta introduce un enfoque basado en IoT, en el cual el smartphone actúa como dispositivo **(“The Thing”)**, permitiendo capturar información del entorno físico mediante la cámara, procesarla a través de un modelo de inteligencia artificial y generar retroalimentación inmediata al usuario. Este enfoque permite cerrar la brecha entre el conocimiento teórico y la ejecución práctica de la separación de residuos.

Adicionalmente, el sistema contribuye al cumplimiento del Decreto 1076 de 2015 y se alinea con la Política Nacional para la Gestión Integral de Residuos Sólidos, al promover la prevención, separación en la fuente y aprovechamiento de residuos. Asimismo, fortalece procesos organizacionales como los Sistemas de Gestión Ambiental (ISO 14001), al permitir la generación de datos, indicadores y trazabilidad.

Finalmente, la solución se articula con el Objetivo de Desarrollo Sostenible (ODS) 12 – Producción y Consumo Responsables, establecido en la Agenda 2030 de las Naciones Unidas, al fomentar prácticas sostenibles mediante el uso de tecnología accesible, escalable y de bajo costo, facilitando su implementación en entornos empresariales y educativos.
---

## 3. Objetivos

### 3.1 Objetivo general
Diseñar un prototipo IoT de clasificación de residuos en entorno empresarial, integrando smartphone, orquestación en n8n e inteligencia artificial en la nube para brindar recomendaciones en tiempo real y generar indicadores de desempeño ambiental.

### 3.2 Objetivos específicos
I1. mplementar la captura visual del residuo mediante smartphone, vinculada al escaneo de QR de la caneca para recuperar contexto operativo.

2.Orquestar el procesamiento en n8n e integrar la inferencia con un modelo de inteligencia artificial en la nube.

3. Entregar respuesta al usuario con recomendación de caneca, nivel de confianza y explicación breve, registrando la traza completa de intentos y retroalimentaciones.

4. Definir, calcular y visualizar indicadores del piloto (éxito por caneca, área y colaborador; sesiones correctas en el primer intento; tasa de corrección e intentos promedio) para evaluar el nivel de conciencia ambiental y la mejora operativa.

---

## 4. Definición de arquitectura

### 4.1 Capas de la arquitectura

- **Capa física (IoT):** smartphone + canecas con códigos QR.
- **Capa de interacción:**  bot de Telegram para captura de imágenes y retroalimentación al colaborador.
- **Capa de orquestación:** n8n (piloto) para gestión de sesiones, reglas y flujo de integración.
- **Capa de inteligencia:** Modelo de IA Gemini (principal) y, opcionalmente, GPT como respaldo.
- **Capa de datos:** Google Sheets (piloto) y Supabase como alternativa de escalamiento.
- **Capa analítica:** Looker Studio para visualización de KPIs e indicadores de conciencia ambiental.

### 4.2 Componentes y roles

- **Smartphone**
  - Sensor: cámara.
  - Actuador: pantalla (respuesta visual de clasificación).
  - Canal: Telegram para envío de foto y recepción de feedback.

- **QR por caneca**
  - Contiene `id_caneca`.
  - Permite recuperar metadatos: `area`, `color_caneca`, `tipos_residuo_permitidos`.

- **n8n**
  - Crea y gestiona sesiones.
  - Llama a IA.
  - Aplica reglas de decisión y cierre.
  - Registra intentos en Google Sheets/Supabase.
  - Retorna mensajes al usuario.

---

## 5. Flujo operativo de extremo a extremo (inicio a fin)

1. El colaborador escanea el QR de la caneca.
2. Se abre Telegram con el parámetro `id_caneca`.
3. n8n crea `id_sesion` y solicita foto del residuo.
4. El colaborador envía la imagen.
5. n8n consulta en Google Sheets el catálogo de canecas por `id_caneca` y recupera `caneca_qr`, `area` y `tipos_residuo_permitidos`.
6. n8n invoca el modelo de IA para clasificación del residuo.
7. La IA responde con `prediccion_ia`, `nivel_confianza` y `explicacion_breve`.
8. n8n compara `prediccion_ia` contra `caneca_qr`.
9. Si coinciden, el intento se marca como `correcto`, se envía mensaje motivacional y se solicita confirmación de depósito.
10. Si no coinciden, el intento se marca como `incorrecto`, se envía mensaje correctivo y se solicita reintento escaneando la caneca recomendada.
11. Cada intento se registra en `registro_intentos` con `numero_intento` y trazabilidad completa del evento.
12. La sesión se cierra por éxito, por inactividad o por máximo de intentos.
13. Looker Studio consume los datos para tableros de seguimiento e indicadores de desempeño.

---

## 6. Diagrama de flujo propuesto

```text
[Escanear QR de caneca]
          |
          v
[Telegram abre con id_caneca]
          |
          v
[n8n crea id_sesion]
          |
          v
[Solicitar y recibir foto]
          |
          v
[Consultar catalogo_canecas en Sheets]
(derivar caneca_qr, area, tipos_residuo_permitidos)
          |
          v
[Clasificar imagen con IA]
(retorna prediccion_ia, nivel_confianza, explicacion_breve)
          |
          v
[Comparar prediccion_ia vs caneca_qr]
      /                         \
   Coinciden                 No coinciden
      |                            |
      v                            v
[Mensaje motivacional]   [Mensaje correctivo + reintento]
[Confirmar deposito]     [Escanear caneca recomendada]
      |                          |
      +------------+-------------+
                   |
                   v
      [Guardar intento en registro_intentos]
                   |
                   v
 [Cerrar sesion: exito / inactividad / maximo_intentos]
                   |
                   v
         [KPI y dashboard en Looker]

---
## 7. Gestión de sesión 

Para asegurar trazabilidad y evitar sesiones abiertas indefinidamente, el prototipo define estados de sesión, reglas de cierre y parámetros operativos unificados.

### 7.1 Estados de sesión

- `ABIERTA_ESPERANDO_FOTO`
- `ABIERTA_CLASIFICACION_INCORRECTA`
- `ABIERTA_CORRECTA_PENDIENTE_CONFIRMACION`
- `CERRADA_EXITOSA`
- `CERRADA_POR_INACTIVIDAD`
- `CERRADA_POR_MAXIMO_INTENTOS`
- `CERRADA_POR_ERROR_TECNICO` (opcional, cuando no se puede completar el procesamiento)

### 7.2 Reglas de cierre

- **Cierre exitoso:** ocurre cuando `caneca_qr` coincide con `prediccion_ia` y el usuario confirma depósito.
- **Cierre por inactividad:** ocurre cuando no hay nueva interacción dentro de `tiempo_reintento_seg`.
- **Cierre por máximo de intentos:** ocurre al alcanzar `maximo_intentos` sin lograr coincidencia entre `caneca_qr` y `prediccion_ia`.
- **Cierre por tiempo máximo de sesión:** ocurre al superar `tiempo_maximo_sesion_min`, aunque existan interacciones parciales.
- **Cierre por error técnico (opcional):** ocurre cuando falla la inferencia y no hay recuperación posible (por ejemplo, timeout del proveedor principal y secundario).

### 7.3 Parámetros recomendados (piloto)

- `maximo_intentos = 3`  
  Número máximo de intentos permitidos por sesión.

- `tiempo_reintento_seg = 300`  
  Tiempo máximo entre intentos antes de cerrar por inactividad.

- `tiempo_maximo_sesion_min = 10`  
  Duración máxima total de la sesión para evitar sesiones “zombie”.

- `sla_respuesta_seg = 2 a 5`  
  Objetivo de tiempo de respuesta del sistema por intento (rendimiento esperado, no regla de cierre).

### 7.4 Regla operativa de reintento

Si el intento es `incorrecto`, el sistema envía feedback correctivo indicando la `prediccion_ia` y solicita escanear la caneca recomendada para continuar con el siguiente `numero_intento` dentro de la misma `id_sesion`.
---

## 8. Variables del sistema (en español)

### 8.1 Variables de sesión e intento (explicación variable por variable)

- `id_sesion`: identificador único de la sesión iniciada por el usuario; agrupa todos los intentos hasta el cierre.
- `numero_intento`: número secuencial del intento dentro de la misma sesión (`1, 2, 3`).
- `estado_sesion`: estado actual de la sesión (`ABIERTA_ESPERANDO_FOTO`, `ABIERTA_CLASIFICACION_INCORRECTA`, `ABIERTA_CORRECTA_PENDIENTE_CONFIRMACION`, `CERRADA_EXITOSA`, `CERRADA_POR_INACTIVIDAD`, `CERRADA_POR_MAXIMO_INTENTOS`).
- `fecha_hora_evento`: fecha y hora exacta del intento registrado.
- `id_colaborador`: identificador del usuario que realiza la interacción.
- `id_caneca`: identificador de la caneca escaneada en ese intento.
- `caneca_qr`: tipo/color de caneca asociado al `id_caneca` en el catálogo (`blanca`, `verde`, `negra`).
- `area`: ubicación física de la caneca escaneada.
- `tipos_residuo_permitidos`: lista de residuos permitidos para la caneca escaneada, recuperada desde catálogo.
- `prediccion_ia`: caneca recomendada por la IA para el residuo observado en la foto.
- `nivel_confianza`: confianza numérica de la inferencia del modelo.
- `explicacion_breve`: justificación corta entregada por la IA para orientar al usuario.
- `resultado_intento`: resultado de comparar `caneca_qr` vs `prediccion_ia`:
  - `correcto` (si coinciden),
  - `incorrecto` (si no coinciden),
  - `error` (si no fue posible completar evaluación técnica).
- `mensaje_enviado`: tipo de mensaje entregado (`motivacional`, `correctivo`, `error_tecnico`).
- `confirmacion_deposito`: confirma si el usuario reportó que depositó el residuo.
- `tiempo_respuesta_ms`: latencia total del sistema para el intento.
- `proveedor_ia`: motor usado para inferencia (`gemini`, `gpt`, etc.).
- `respaldo_activado`: indica si se usó proveedor alterno por falla del principal.
- `codigo_error`: código técnico o funcional para trazabilidad (`IA_TIMEOUT`, `QR_NO_EXISTE`, `IMAGEN_INVALIDA`, `MISMATCH_QR_IA`, etc.).

### 8.2 Variables de configuración (explicación variable por variable)

- `maximo_intentos`: cantidad máxima de intentos permitidos por sesión.
- `tiempo_reintento_seg`: tiempo máximo entre intentos antes de cerrar por inactividad.
- `tiempo_maximo_sesion_min`: duración total máxima de una sesión.
- `nivel_confianza_minimo`: umbral mínimo para aceptar automáticamente la predicción de IA.
- `sla_respuesta_seg`: objetivo de tiempo de respuesta por intento (2 a 5 segundos).

### 8.3 Regla de decisión del prototipo (explícita)

1. El QR escaneado identifica la caneca real (`caneca_qr`) mediante `id_caneca`.
2. La foto del residuo se procesa con IA y retorna `prediccion_ia`.
3. Se compara `caneca_qr` vs `prediccion_ia`:
   - Si coinciden -> `resultado_intento = correcto`.
   - Si no coinciden -> `resultado_intento = incorrecto`.
4. En caso de `incorrecto`, el usuario recibe feedback correctivo y debe reintentar escaneando la caneca recomendada por IA.
5. El proceso continúa dentro de la misma `id_sesion` hasta cierre por éxito, inactividad o máximo de intentos.

---
## 9. Modelo de datos

### 9.1 Tabla: `catalogo_canecas` (estructura maestra de canecas)

- `id_caneca`: identificador único de la caneca (clave primaria).
- `area`: ubicación física de la caneca (piso, zona, dependencia).
- `color_caneca`: color normativo de la caneca (`blanca`, `verde`, `negra`).
- `tipos_residuo_permitidos`: lista de residuos aceptados en esa caneca.
- `estado_caneca`: estado operativo (`activa` / `inactiva`).
- `latitud`: coordenada geográfica opcional para evoluciones futuras de proximidad.
- `longitud`: coordenada geográfica opcional para evoluciones futuras de proximidad.

### 9.2 Tabla: `registro_intentos` (bitácora transaccional del flujo)

- `id_sesion`: identificador de la sesión.
- `numero_intento`: número secuencial de intento dentro de la sesión.
- `fecha_hora_evento`: timestamp del intento.
- `id_colaborador`: identificador del usuario.
- `id_caneca`: identificador de caneca escaneada.
- `caneca_qr`: caneca real derivada de `id_caneca`.
- `area`: ubicación física asociada al intento.
- `tipos_residuo_permitidos`: residuos permitidos para la caneca escaneada (valor de contexto).
- `prediccion_ia`: recomendación de caneca entregada por IA.
- `nivel_confianza`: confianza de la predicción.
- `explicacion_breve`: explicación corta asociada a la recomendación.
- `resultado_intento`: resultado final (`correcto`, `incorrecto`, `error`) según comparación `caneca_qr` vs `prediccion_ia`.
- `mensaje_enviado`: tipo de respuesta enviada (`motivacional`, `correctivo`, `error_tecnico`).
- `confirmacion_deposito`: confirmación reportada por el usuario.
- `tiempo_respuesta_ms`: latencia total por intento.
- `estado_sesion`: estado de la sesión al momento del registro.
- `proveedor_ia`: proveedor usado en la inferencia.
- `respaldo_activado`: indica si se activó proveedor secundario.
- `codigo_error`: código de error técnico/funcional si aplica.

### 9.3 Tabla: `reglas_residuos` (catálogo de apoyo educativo y consulta)

- `tipo_residuo`: categoría o nombre del residuo consultado.
- `caneca_recomendada`: caneca recomendada para ese tipo de residuo.
- `mensaje_educativo`: mensaje pedagógico asociado para retroalimentación al usuario.

### 9.4 Relación lógica entre tablas

- `registro_intentos.id_caneca` se relaciona con `catalogo_canecas.id_caneca` para obtener `caneca_qr`, `area` y `tipos_residuo_permitidos`.
- `reglas_residuos` apoya funcionalidades de consulta y mensajería educativa, sin reemplazar la clasificación por IA.
- La tabla principal para análisis de desempeño es `registro_intentos`.

### 9.5 Ejemplo de reintento (misma sesión)

- **Intento 1**
  - `id_sesion = SES-2026-001`
  - `numero_intento = 1`
  - `id_caneca = CAN-VERDE-02`
  - `caneca_qr = verde`
  - `prediccion_ia = negra`
  - `resultado_intento = incorrecto`
  - `mensaje_enviado = correctivo`
  - `estado_sesion = ABIERTA_CLASIFICACION_INCORRECTA`

- **Intento 2 (usuario escanea caneca recomendada)**
  - `id_sesion = SES-2026-001`
  - `numero_intento = 2`
  - `id_caneca = CAN-NEGRA-01`
  - `caneca_qr = negra`
  - `prediccion_ia = negra`
  - `resultado_intento = correcto`
  - `mensaje_enviado = motivacional`
  - `confirmacion_deposito = si`
  - `estado_sesion = CERRADA_EXITOSA`
---
## 10. Indicadores básicos (KPI)

Nota metodológica:
Los indicadores de desempeño del usuario se calculan con intentos correcto e incorrecto.
Los intentos con resultado_intento = error se reportan aparte como estabilidad técnica.

### 10.1 Éxito por tipo de caneca
Formula: tasa_exito_caneca = (intentos_correctos_caneca / (intentos_correctos_caneca + intentos_incorrectos_caneca)) * 100  
Interpretacion: porcentaje de aciertos por caneca_qr.

### 10.2 Éxito por área
Formula: tasa_exito_area = (intentos_correctos_area / (intentos_correctos_area + intentos_incorrectos_area)) * 100  
Interpretacion: porcentaje de aciertos por area.

### 10.3 Éxito por colaborador
Formula: tasa_exito_colaborador = (intentos_correctos_colaborador / (intentos_correctos_colaborador + intentos_incorrectos_colaborador)) * 100  
Interpretacion: porcentaje de aciertos por id_colaborador.

### 10.4 Sesiones correctas en primer intento (First Time Right)
Formula: first_time_right = (sesiones_cerradas_exitosas_en_primer_intento / sesiones_totales) * 100  
Interpretacion: porcentaje de sesiones resueltas bien al primer intento.

### 10.5 Intentos promedio hasta cierre exitoso
Formula: intentos_promedio_hasta_exito = suma_de_intentos_de_sesiones_cerradas_exitosas / total_sesiones_cerradas_exitosas  
Interpretacion: numero promedio de intentos necesarios para cerrar una sesion exitosamente.

### 10.6 Tasa de corrección tras feedback
Formula: tasa_correccion = (sesiones_con_primer_intento_incorrecto_y_cierre_exitoso / sesiones_con_primer_intento_incorrecto) * 100  
Interpretacion: porcentaje de sesiones que corrigen despues del primer error.

### 10.7 Tasa de cierre por inactividad
Formula: tasa_inactividad = (sesiones_cerradas_por_inactividad / sesiones_totales) * 100  
Interpretacion: porcentaje de sesiones abandonadas por falta de reintento.

### 10.8 Tasa de cierre por máximo de intentos
Formula: tasa_maximo_intentos = (sesiones_cerradas_por_maximo_intentos / sesiones_totales) * 100  
Interpretacion: porcentaje de sesiones que no lograron correccion antes del limite.

### 10.9 Tasa de error técnico
Formula: tasa_error_tecnico = (intentos_con_resultado_error / intentos_totales) * 100  
Interpretacion: porcentaje de intentos con falla tecnica del sistema.

### 10.10 Cumplimiento del SLA de respuesta
Formula: cumplimiento_sla = (intentos_con_tiempo_en_rango_objetivo / intentos_totales) * 100  
Interpretacion: porcentaje de intentos atendidos dentro del tiempo objetivo (2 a 5 segundos).
---

## 11. Mensajería al usuario (motivación y corrección)

### 11.1 Cuando el intento es correcto
Mensaje tipo:
> “Excelente. Este residuo corresponde a la caneca **{prediccion_ia}**. Tu acción ayuda a mejorar el reciclaje en **{area}** y reduce contaminación cruzada. ¡Gracias por clasificar correctamente!”

### 11.2 Cuando el intento es incorrecto
Mensaje tipo:
> “Este residuo no corresponde a la caneca escaneada. Debe ir en **{prediccion_ia}**. Segregar correctamente evita pérdidas de material reciclable y mejora el impacto ambiental de la oficina. Por favor, inténtalo de nuevo.”

### 11.3 Consulta de apoyo
Comando sugerido:
- “¿Dónde están las canecas para este tipo de residuo?”

Respuesta:
- Caneca recomendada.
- Áreas disponibles.
- Identificadores `id_caneca` para escaneo.

---

## 12. Requerimientos técnicos

- Python para utilidades de integración, validación y normalización de datos.
- n8n como orquestador de eventos, reglas de negocio y gestión de sesiones.
- Integración API con IA (Gemini como proveedor principal y GPT como respaldo opcional).
- Telegram Bot API como interfaz de interacción con el usuario.
- Google Sheets como persistencia del piloto y Supabase como alternativa de escalamiento.
- Looker Studio para visualización de indicadores y seguimiento de desempeño.
- Seguridad básica: HTTPS, token de webhook, control de acceso y seudonimización de identificadores.

---

## 13. Cronograma de actividades (4 semanas)

### Semana 1: Diseño y preparación
- Definición final del flujo operativo y reglas de decisión.
- Estructuración de hojas `catalogo_canecas`, `registro_intentos` y `reglas_residuos`.
- Generación y asociación de QR con `id_caneca`.
- Configuración inicial de Telegram Bot y n8n.

### Semana 2: Implementación del flujo base
- Desarrollo del flujo QR -> Telegram -> n8n -> IA.
- Integración de registro de intentos en Google Sheets.
- Implementación de respuesta al usuario con recomendación, nivel de confianza y explicación breve.
- Pruebas funcionales de punta a punta en entorno piloto.

### Semana 3: Reglas de sesión y calidad operativa
- Implementación de estados y reglas de cierre de sesión.
- Configuración de `maximo_intentos`, `tiempo_reintento_seg` y `tiempo_maximo_sesion_min`.
- Pruebas de casos de error técnico, reintentos e inactividad.
- Ajuste de mensajes motivacionales y correctivos.

### Semana 4: Indicadores y cierre del prototipo
- Construcción de dashboard en Looker Studio.
- Medición de KPIs por caneca, área y colaborador.
- Validación del cumplimiento del SLA de 2 a 5 segundos.
- Documentación final, análisis de resultados y socialización del piloto.

---

## 14. Línea futura de evolución

Como evolución del piloto, se propone incorporar ubicación del usuario (compartida por Telegram) para recomendar la caneca más cercana. Esta mejora requerirá coordenadas por caneca en `catalogo_canecas` y cálculo de distancia por proximidad.

---

## 15. Referencias (APA 7.ª edición)

Atzori, L., Iera, A., & Morabito, G. (2010). The Internet of Things: A survey. *Computer Networks, 54*(15), 2787-2805. https://doi.org/10.1016/j.comnet.2010.05.010

Borgia, E. (2014). The Internet of Things vision: Key features, applications and open issues. *Computer Communications, 54*, 1-31. https://doi.org/10.1016/j.comcom.2014.09.008

Gubbi, J., Buyya, R., Marusic, S., & Palaniswami, M. (2013). Internet of Things (IoT): A vision, architectural elements, and future directions. *Future Generation Computer Systems, 29*(7), 1645-1660. https://doi.org/10.1016/j.future.2013.01.010

Google Cloud. (n.d.). *Documentación de Gemini*. https://cloud.google.com/vertex-ai/generative-ai/docs

n8n. (n.d.). *n8n Documentation*. https://docs.n8n.io/
