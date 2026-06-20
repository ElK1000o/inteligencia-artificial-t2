# MatEnergy-ML — Guía Completa de la Plataforma

> **Propósito de este documento:** Explicar qué problema real de almacenamiento de energía ataca esta plataforma, cómo el aprendizaje automático va más allá de un simple cálculo para ayudar a diseñar mejores materiales de batería y almacenamiento, cómo usar cada funcionalidad, y cómo interpretar cada resultado en términos de impacto energético real.

---

## Índice

1. [El problema real: las baterías actuales no son suficientes](#1-el-problema-real)
2. [Qué propiedades determinan si un material sirve para almacenamiento](#2-propiedades-clave)
3. [Por qué ML es necesario — y por qué no es trivial](#3-por-que-ml)
4. [Tutorial de la plataforma — página por página](#4-tutorial)
5. [Cómo interpretar cada resultado en términos energéticos](#5-interpretacion)
6. [El ciclo completo: de dato a decisión de síntesis](#6-ciclo-completo)
7. [Limitaciones honestas del sistema](#7-limitaciones)
8. [Glosario rápido](#8-glosario)

---

## 1. El Problema Real

### Las tecnologías de almacenamiento de energía tienen cuellos de botella materiales

La transición a energías renovables (solar, eólica) no depende solo de instalar paneles o turbinas — depende de **poder guardar esa energía** cuando se produce y usarla cuando se necesita. El cuello de botella no es la generación, es el almacenamiento.

Las baterías de litio dominan hoy: teléfonos, autos eléctricos, grid storage. Pero tienen limitaciones que frenan la transición energética:

| Limitación | Consecuencia real |
|---|---|
| Densidad de energía del cátodo ~200 mAh/g (NMC811) | Un auto eléctrico requiere 400–800 kg de baterías |
| Degradación en ~500–1000 ciclos | Una batería de auto dura 8–10 años, luego residuo tóxico |
| Cobalto en cátodos (~20% del costo) | Escaso, costoso, geopolíticamente concentrado (Congo) |
| Electrolito líquido inflamable | Riesgo de fuego térmica en accidentes |
| Temperatura de operación estrecha | Pérdida de 30–40% de capacidad a −20 °C |

Estas limitaciones no son de ingeniería de proceso — son de **física y química del material mismo**. No se pueden resolver rediseñando la celda. Requieren materiales fundamentalmente mejores.

### El problema de diseñar esos materiales

Para un cátodo de batería de litio se necesita un material que cumpla simultáneamente:

- **Alta capacidad específica** → muchos iones Li⁺ que puede insertar/extraer
- **Alto voltaje de operación** → depende de la diferencia de potencial redox
- **Estabilidad termodinámica** → no se descompone durante el ciclado
- **Estabilidad del ciclo** → la estructura cristalina no colapsa al extraer/insertar Li repetidamente
- **Compatibilidad con electrolito** → no reacciona con el electrolito formando capas pasivantes
- **Bajo costo y abundancia** → idealmente sin Co, sin Ni de alta pureza, sin Li en exceso

Encontrar un material que optimice todos estos factores simultáneamente es un **problema de diseño multivariable** en un espacio enorme.

### El espacio de candidatos

Considerando solo óxidos de metales de transición con litio (el espacio de cátodos más explorado): hay más de **500,000 composiciones posibles** en el espacio Li-Me-O donde Me puede ser cualquier combinación de Fe, Co, Ni, Mn, Ti, V, Cr, Al y sus mezclas. De esos, se han caracterizado experimentalmente miles. Se han calculado con DFT decenas de miles. El resto — cientos de miles — es territorio desconocido.

El experimento de síntesis + caracterización completa de un material tarda 2–5 años y cuesta decenas de miles de euros. No es factible explorar ese espacio experimentalmente de forma sistemática.

**Ahí es exactamente donde entra esta plataforma.**

---

## 2. Propiedades Clave del Material de Almacenamiento

Antes de entender cómo ML ayuda, hay que entender qué predice y por qué eso importa para el almacenamiento.

### 2.1 Energía sobre el casco convexo (EAH) — ¿el material aguanta?

Esta es la métrica de **estabilidad termodinámica**. Responde: ¿este material existe, o se descompone espontáneamente en otros compuestos más estables?

Un cátodo con EAH alto (inestable) se descompone durante el ciclado de la batería, especialmente cuando está parcialmente delitiado (cargado). Eso significa:

- Pérdida irreversible de capacidad
- Formación de fases nuevas que bloquean la difusión de Li⁺
- Liberación de gases (O₂) en cátodos de óxido → riesgo de fuego

**Para almacenamiento:** un buen cátodo tiene EAH ≤ 0.05 eV/átomo tanto en estado litiado como delitiado. La plataforma predice el EAH del estado litiado y lo usa como proxy de estabilidad operacional.

### 2.2 Energía de formación (ΔHf) — ¿qué tan fuertemente ligado está?

La energía de formación mide cuánta energía se necesita para descomponer el material en sus elementos. Para baterías:

- **ΔHf muy negativa** (< −3 eV/átomo): estructura muy estable → bueno para vida útil, malo para cinética de extracción de Li (voltaje alto pero dificultad de ciclado rápido)
- **ΔHf moderadamente negativa** (−1.5 a −3 eV/átomo): balance ideal para la mayoría de cátodos
- **ΔHf positiva**: el material es metaestable cinéticamente — puede existir pero se desintegrará bajo condiciones de operación

### 2.3 Band gap — ¿conductor, semiconductor o aislante?

El band gap determina si el material puede conducir electrones dentro del electrodo:

| Band gap | Comportamiento | Rol en batería |
|---|---|---|
| 0 eV | Conductor metálico | No funciona como electrodo activo (cortocircuito) |
| 0.5–3 eV | Semiconductor | Electrodo ideal (LiCoO₂: 2.1 eV, LiFePO₄: 3.8 eV) |
| 3–6 eV | Aislante parcial | Electrolito sólido (ej: LLZO ~5.5 eV) |
| > 6 eV | Aislante | No conduce ni iones ni electrones → inutilizable |

Un cátodo semiconductor conduce electrones hacia el colector de corriente mientras deja pasar solo Li⁺ hacia el electrolito — exactamente lo que se necesita. Un material con band gap demasiado alto necesita aditivos conductores (carbono negro), que reducen la densidad de energía.

### 2.4 Estabilidad electroquímica — ¿aguanta el voltaje?

Durante la carga, el potencial del cátodo puede superar 4 V vs. Li/Li⁺. Si el electrolito se oxida a ese voltaje, se forma una capa de interface (CEI — Cathode Electrolyte Interphase) que degrada la batería. La estabilidad del material frente a alta oxidación está relacionada con su EAH en estado delitiado — propiedad que la plataforma puede aproximar.

---

## 3. Por Qué ML Es Necesario — y Por Qué No Es Trivial

### 3.1 El rol del cálculo DFT

La Teoría del Funcional de la Densidad (DFT) calcula desde primeros principios —usando mecánica cuántica— el EAH, la energía de formación, el band gap y otras propiedades. Es el método más confiable disponible sin síntesis experimental. El problema:

- Un cálculo DFT de un material tarda entre 1 hora y varios días en un clúster de cómputo
- Evaluar 100,000 candidatos = años de cómputo exclusivo

Bases de datos como Materials Project han acumulado ~150,000 materiales calculados con DFT. Eso representa décadas de cómputo distribuido global. Y aun así cubre menos del 0.2% del espacio de composiciones posibles.

### 3.2 Qué hace ML que DFT no puede a escala

El ML aprende la función implícita que relaciona la composición química de un material con sus propiedades:

```
f(descriptores de LiCoO₂) → EAH = 0.0 eV/átomo ✓
f(descriptores de Li₂MnO₃) → EAH = 0.0 eV/átomo ✓
f(descriptores de Li(Co₀.₃₃Mn₀.₃₃Ni₀.₃₃)O₂) → EAH ≈ 0.02 eV/átomo (candidato no calculado)
```

Una vez entrenado, evaluar f tarda **microsegundos** — 6 órdenes de magnitud más rápido que DFT. Eso permite:

- Evaluar 500,000 composiciones en horas, no décadas
- Identificar los top-100 candidatos prometedores
- Enviar solo esos 100 a DFT de verificación
- Resultado: 5,000× menos cómputo para el mismo resultado de screening

### 3.3 Por qué no es solo una calculadora

Un modelo de ML en este dominio hace cosas que ninguna fórmula simple puede hacer:

**1. Captura interacciones no-lineales entre propiedades elementales**

La estabilidad de LiNiO₂ no es simplemente "media de estabilidad de Li, Ni y O". Depende de cómo el Ni³⁺ en sitio octaédrico interactúa con el campo de ligandos del oxígeno, lo cual a su vez depende del radio iónico relativo y la diferencia de electronegatividad. Un modelo Random Forest con 300 árboles y 150 descriptores captura estas interacciones en alta dimensionalidad. Una regla heurística no puede.

**2. Predice tendencias de sustitución**

Si se entrenan modelos sobre datos de la familia NMC (Li-Ni-Mn-Co-O), el modelo aprende cómo varía el EAH al cambiar la proporción Ni:Mn:Co. Puede predecir que NMC 811 (Ni₀.₈Mn₀.₁Co₀.₁) tiene mayor inestabilidad que NMC 622 — lo que DFT ya confirmó — y extrapolar hacia composiciones sin datos como NMC 91 o sustituciones con Mg.

**3. Explica por qué un material falla o funciona**

Mediante análisis SHAP (ver sección 5.4), el modelo no solo dice "este candidato tiene EAH = 0.08 eV/átomo" sino "este candidato tiene EAH = 0.08 principalmente porque su mismatch de radio iónico es 55% — mayor que el umbral crítico de ~40% que correlaciona con inestabilidad estructural". Eso dirige la estrategia: reducir el tamaño del dopante.

**4. Cuantifica incertidumbre**

Un modelo Gaussian Process no da un número — da una distribución de probabilidad. Para un candidato muy parecido a los del training set: EAH = 0.03 ± 0.01 eV/átomo (alta confianza, proceder). Para un candidato en territorio desconocido: EAH = 0.04 ± 0.12 eV/átomo (baja confianza, necesita DFT antes de síntesis). Esta información cambia las decisiones de priorización.

**5. Detecta candidatos fuera del dominio de aplicación**

El sistema de detección OOD (Out-of-Domain) identifica materiales cuyas propiedades elementales están fuera del rango estadístico del conjunto de entrenamiento. Predecir un sulfuro de calcio con un modelo entrenado en óxidos de litio da un número, pero ese número no tiene base estadística. La plataforma lo advierte explícitamente.

---

## 4. Tutorial de la Plataforma

### 4.1 Dashboard — Estado global del proyecto de optimización

**Ruta:** `/`

El dashboard muestra el estado del ciclo de screening completo:

| Métrica | Qué dice sobre el proyecto |
|---|---|
| Total / Valid Materials | Cuántos candidatos entraron al pipeline y cuántos pasaron control de calidad |
| DFT-Stable Materials | Cuántos tienen EAH ≤ 0.05 eV/átomo según datos DFT — base real de candidatos prometedores |
| Active Models | Cuántos modelos entrenados están listos para predicción |
| Best MAE | Error típico de predicción de EAH en eV/átomo. < 0.1 eV/átomo es competitivo con literatura |
| Best F1 | Qué tan bien clasifica el modelo estable vs. inestable. > 0.7 es útil para screening |

**Los gráficos:**
- **Pie chart:** proporción stable/metastable/unstable del dataset. En un espacio de óxidos de metales de transición, típicamente ~30–40% son estables — esto confirma que el espacio no está saturado de buenos candidatos y el screening tiene valor.
- **Bar chart:** materiales válidos vs. rechazados. Un rechazo alto (> 10%) indica problemas de calidad en los datos fuente.

---

### 4.2 Datasets — Los datos de referencia

**Ruta:** `/datasets`

El dataset es el conjunto de materiales con propiedades DFT conocidas que sirve como base de entrenamiento y referencia. En el contexto de almacenamiento de energía, un buen dataset incluye:

- Materiales de catodo conocidos: LiCoO₂, LiFePO₄, LiMn₂O₄, NMC, NCA, Li-rich layered oxides
- Sus propiedades DFT: EAH, formación energy, band gap
- Variantes de dopaje ya calculadas: Fe-doped LiFePO₄, Al-doped NMC, etc.

**El reporte de validación** (botón "View") es crítico: muestra qué filas fueron rechazadas y por qué. Una fórmula mal escrita ("LiCO2" en lugar de "LiCoO2") genera un descriptor incorrecto que envenena el modelo. Revisar el reporte antes de entrenar es esencial.

---

### 4.3 Materials — Explorar el espacio de estabilidad

**Ruta:** `/materials`

#### Vista Convex Hull

Esta visualización responde directamente: **¿cuáles de los materiales en mi dataset son termodinámicamente candidatos viables para almacenamiento?**

Cada punto es un material:
- **Eje X:** energía de formación por átomo — cuán exotérmica es su formación
- **Eje Y:** energía sobre el casco convexo — cuán lejos está de la estabilidad absoluta

```
EAH  ↑
0.3  |    •  •  •  •
     |  •        •   ← Inestables: se descomponen en operación
0.1  |___•__•________  ← Umbral metaestable
0.05 |___•____•______  ← Umbral de screening convencional
0.0  |•  •  •         ← Estables: candidatos reales
     +----------------→ Formation Energy (eV/átomo)
```

Hacer clic en cualquier punto abre el detalle completo: propiedades, análisis composicional, estructura 3D desde MP, y vía de descomposición.

**Para baterías:** los candidatos en zona verde (EAH ≤ 0.05) son los que tienen mayor probabilidad de sobrevivir el ciclado. Los amarillos (metaestables) pueden funcionar bajo condiciones específicas o con dopaje estabilizador.

#### Vista Cards con Stability Gauge

Muestra cada material como tarjeta con un semáforo visual de estabilidad — útil para revisión rápida de candidatos específicos.

---

### 4.4 Material — Análisis profundo de un candidato

**Ruta:** `/materials/:id`

Al seleccionar un material, tres tabs organizan el análisis de profundidad creciente:

#### Tab Properties

Tabla completa de propiedades DFT. Para un cátodo de batería, los valores críticos a buscar:

| Propiedad | Valor ideal (cátodo) | Interpretación |
|---|---|---|
| energy_above_hull | ≤ 0.05 eV/átomo | Estable durante ciclado |
| formation_energy_per_atom | −1.5 a −3.5 eV/átomo | Balance estabilidad/reactividad |
| band_gap | 0.5–3.5 eV | Semiconductor útil como electrodo |

#### Tab Chemical Analysis

Análisis composicional sin necesitar la estructura cristalina. Directamente relevante para diseño de materiales:

**Stability Verdict:** Veredicto directo con EAH del dataset. Si dice "Thermodynamically unstable" con EAH = 0.18 eV/átomo, este material no sobrevivirá el ciclado sin modificación.

**Atomic Profile (diagrama SVG):** Los círculos representan los elementos, escalados por radio atómico y coloreados por electronegatividad. Para un buen cátodo, se busca:
- Diferencia de electronegatividad moderada (carácter iónico suficiente para conducción, sin ser tan alta que haga la estructura rígida)
- Iones de tamaño compatible (bajo size mismatch para que la red no colapse al insertar/extraer Li)

**Composition Statistics:**
- **Electronegativity spread > 2.4:** indica carácter muy iónico — puede significar que el material es buen conductor iónico pero mal conductor electrónico (necesitará más aditivo de carbono)
- **Size mismatch > 40%:** el cátodo puede sufrir distorsión de Jahn-Teller (ej: Mn³⁺ en LiMnO₂) que colapsa la estructura durante ciclado
- **Sin balance de carga:** el material no puede tener estados de oxidación consistentes — señal de alerta de inestabilidad electrónica

**Instability Factors:** Lista de por qué este material puede fallar en operación. Cada factor es clickeable para ver la explicación física y el umbral cuantitativo.

**Decomposition Pathway:** Ver sección 5.5 — es la funcionalidad más directamente relevante para entender qué pasa cuando el material falla.

#### Tab Structure 3D

La estructura cristalina desde Materials Project. Para baterías, la estructura cristalina determina:
- **Canales de difusión de Li⁺** — la velocidad de carga/descarga depende de qué tan fácil viaja el ión litio dentro de la red. Estructuras en capas (layered, R3̄m) tienen canales 2D; olivina (Pnma) tiene canales 1D; espinela (Fd3̄m) tiene canales 3D.
- **Número de coordinación del Li:** CN=6 (octaédrico) es típico en óxidos en capas. CN distinto indica ambiente inusual que puede afectar la facilidad de extracción.
- **Parámetros de red:** el volumen de la celda unitaria cambia al extraer Li. Si el cambio es > 5%, la red sufre fatiga mecánica y el material se pulveriza en ciclos repetidos.

---

### 4.5 Descriptors — La representación numérica de la composición

**Ruta:** `/descriptors`

Para que el ML pueda trabajar, "LiCoO₂" debe convertirse en un vector de números. Los descriptores Magpie derivan estadísticas sobre las propiedades de los elementos presentes ponderadas por su fracción atómica:

| Descriptor | Para LiCoO₂ | Significado físico |
|---|---|---|
| mean Electronegativity | (1×0.98 + 1×1.88 + 2×3.44)/4 = 2.44 | Electronegatividad promedio |
| range AtomicRadius | 1.52 − 0.60 = 0.92 Å | Mismatch de tamaño iónico |
| mean NValance | (1+3+2×6)/4 = 4.0 | Electrones de valencia promedio |
| max MeltingT | 2927°C (Co) | Temperatura máxima de fusión |

La plataforma genera ~150 de estos descriptores por material. El modelo ML aprende qué combinaciones de estos valores correlacionan con alta/baja EAH, alta/baja ΔHf, etc.

#### Chemical Space Map (t-SNE)

Reduce los 150 descriptores a 2 dimensiones para visualizar cómo se agrupan los materiales. En el contexto de baterías:

- Los materiales de la familia NMC aparecen agrupados juntos
- LiFePO₄ y variantes olivina forman otro cluster separado
- Un candidato nuevo que aparece lejos de todos los clusters → alta probabilidad de estar fuera del dominio del modelo → necesita DFT antes de confiar en la predicción ML

---

### 4.6 Models — Entrenar los modelos de predicción

**Ruta:** `/models`

#### Qué modelos entrenar y para qué

Para un proyecto de optimización de materiales de batería, la estrategia típica es:

1. **Ridge Regression** → línea base. Si falla aquí, hay problema de datos.
2. **Random Forest** → robusto, da Feature Importance (saber qué propiedades elementales importan)
3. **Gradient Boosting** → mayor precisión si los datos son suficientes (> 500 materiales)
4. **Gaussian Process** → cuando se quiere incertidumbre calibrada para guiar adquisición de datos

#### Métricas y su significado para el proyecto

**MAE (Mean Absolute Error) en EAH:**
- MAE = 0.05 eV/átomo: el modelo acierta dentro del umbral de estabilidad convencional — usable para screening grueso
- MAE = 0.10 eV/átomo: el modelo puede confundir materiales metaestables con estables — usar solo para filtrado previo
- MAE = 0.20 eV/átomo: incertidumbre demasiado alta, el screening no es fiable

**R² en EAH:**
- R² > 0.90: el modelo captura más del 90% de la variación de estabilidad — excelente
- R² > 0.75: útil para screening, con revisión de los candidatos marginales
- R² < 0.60: el modelo no está aprendiendo la física — revisar calidad del dataset y descriptores

**F1-macro (clasificación estable/inestable):**
- F1 > 0.80: screening confiable — los candidatos marcados como estables probablemente lo son
- F1 = 0.60–0.80: útil pero con tasa de falsos positivos notable — siempre verificar con DFT los top candidatos
- F1 < 0.60: el modelo no distingue estables de inestables — no usar para decisiones

#### Tab Feature Importance

**Esta es una de las contribuciones científicas más directas de la plataforma.**

Si el modelo aprende que el descriptor más importante para predecir EAH es "range of AtomicRadius" (mismatch de tamaño iónico), eso es una hipótesis física verificable: materiales con iones de tamaño muy diferente tienden a ser inestables. Un investigador puede usar eso para:

- Priorizar sustituciones isovalentes con radios similares
- Descartar composiciones con gran mismatch sin necesitar DFT

Si "mean Electronegativity" domina la Feature Importance para band gap, el modelo ha aprendido la ley de Pauling implícitamente desde datos — sin que nadie se la programara.

#### Tab Parity Plot

Gráfico predicho vs. real para el conjunto de test. Lo que buscar:

- **Scatter uniforme alrededor de la diagonal:** error aleatorio, bueno
- **Cluster de puntos con gran error arriba del 0.10 eV/átomo:** materiales con EAH alto que el modelo subestima — son los más "seguros" de ignorar para síntesis, pero el modelo los señala mal
- **Puntos muy alejados de la diagonal cerca de EAH=0:** materiales estables clasificados como inestables (falsos negativos) — los más críticos, porque son buenos candidatos perdidos

---

### 4.7 Predictions — Aplicar el modelo al dataset completo

**Ruta:** `/predictions`

Aquí se cierra el loop: el modelo entrenado se aplica a todos los materiales del dataset para identificar cuáles son los más prometedores.

#### Flujo de screening

1. Seleccionar `energy_above_hull` como propiedad objetivo
2. Seleccionar el dataset completo
3. Ejecutar → el sistema predice EAH para cada material
4. El histograma muestra la distribución — materiales a la izquierda de la línea 0.05 eV/átomo son candidatos

#### OOD Badge — señal de alerta crítica

Un material marcado OOD (Out-of-Domain) tiene descriptores fuera del rango estadístico del training set. Para un proyecto de cátodos:

- Si el training set es todo óxidos de Li-Co y aparece un fluoruro de Mg, marcará OOD
- La predicción de EAH = 0.02 para ese fluoruro puede ser totalmente incorrecta
- El badge OOD es la plataforma diciendo: "tengo una predicción pero no tengo base estadística para ella"

En screening real: candidatos OOD con predicción prometedora van a una cola separada para DFT de verificación, no directamente a síntesis.

#### SHAP — el "Why?" por material

El botón **Why?** en cada fila abre el waterfall chart de SHAP para ese material específico. Para un candidato con EAH predicho = 0.03 eV/átomo, SHAP explica:

```
Predicción base del modelo: 0.12 eV/átomo (EAH promedio del dataset)

+ MagpieData range Electronegativity = −0.05   → bajo mismatch EN → estabiliza
+ MagpieData mean MeltingT           = −0.03   → alta Tm → estructura robusta  
+ MagpieData mean NValance           = −0.02   → valencia adecuada
+ MagpieData range AtomicRadius      = +0.01   → leve mismatch de radio
───────────────────────────────────────────────
= Predicción final: 0.03 eV/átomo
```

Esto no es solo un número — es una **hipótesis de diseño**: si queremos mejorar otro candidato, reducir el mismatch de electronegatividad es la palanca más efectiva según el modelo.

**Narrativa automática (sesión 7):** Debajo del waterfall chart aparece una narrativa en texto plano generada de forma determinista a partir de los mismos valores SHAP. Incluye:

- Un **badge de veredicto** con el valor predicho y su clasificación (ej. "stable thermodynamic candidate — EAH ≤ 0.05 eV/atom")
- Dos columnas: factores que aumentan la EAH (en rojo, desfavorables) vs factores que la reducen (en verde, favorables)
- Nombre legible de cada descriptor (ej. "Mean electronegativity" en vez de `avg_electronegativity`), su valor para el material, y la contribución SHAP
- Contexto científico al pie explicando qué significa la propiedad para aplicaciones de batería

La narrativa es completamente rule-based y reproducible — no usa IA generativa.

---

### 4.8 Explorer — Diseñar composiciones nuevas

**Ruta:** `/explore`

**Esta es la funcionalidad de diseño, no solo de screening.**

El Explorer permite introducir cualquier fórmula química — incluyendo materiales que no existen en ninguna base de datos — y predecir sus propiedades instantáneamente.

#### Caso de uso real: optimizar NMC

Los cátodos NMC (Li-Ni-Mn-Co-O) son los más usados en autos eléctricos. NMC 811 (Li(Ni₀.₈Mn₀.₁Co₀.₁)O₂) tiene alta capacidad pero baja estabilidad. ¿Cómo optimizarlo?

Sin la plataforma: contratar síntesis de 10 variantes, esperar meses, caracterizar cada una.

Con la plataforma:
```
Li(Ni₀.₈Mn₀.₁Co₀.₁)O₂        → EAH = 0.08 eV/átomo (inestable)
Li(Ni₀.₇Mn₀.₂Co₀.₁)O₂        → EAH = 0.04 eV/átomo ✓
Li(Ni₀.₇Mn₀.₁Co₀.₁Al₀.₁)O₂  → EAH = 0.02 eV/átomo ✓✓ (candidato destacado)
Li(Ni₀.₆Mn₀.₂Co₀.₂)O₂        → EAH = 0.01 eV/átomo ✓✓ (pero menos capacidad)
```

En minutos se identifican que el dopaje con Al y reducir Ni mejoran estabilidad. Solo los candidatos más prometedores van a síntesis.

**Si el material es "Known in dataset"** → botón "View" navega directamente al análisis completo con las 3 tabs.

---

### 4.9 Ranking — Priorizar para síntesis

**Ruta:** `/ranking`

Cuando hay 100 candidatos con predicciones ML prometedoras, ¿cuáles se sintetizan primero? El ranking usa un **score compuesto** que integra:

- **Stability score:** EAH predicho — el más importante para operación de batería
- **Uncertainty penalty:** candidatos con alta incertidumbre del modelo bajan en el ranking
- **OOD penalty:** candidatos fuera del dominio de aplicación se descuentan

Los candidatos "High priority" son aquellos donde el modelo tiene alta confianza de que son estables. Estos son los que justifican la inversión en síntesis experimental.

La exportación CSV genera la lista completa para compartir con el equipo experimental o para justificar solicitudes de cómputo DFT adicional.

---

### 4.10 DFT Jobs — Verificación atomística de candidatos

**Ruta:** `/dft-jobs`

Una vez identificados los candidatos top por el ranking, esta página permite lanzar cálculos DFT de verificación y rastrear su estado — cerrando el loop entre screening ML y confirmación desde primeros principios.

#### ¿Qué es un cálculo DFT local (ASE/EMT)?

La plataforma implementa dos modos de cálculo:

| Modo | Cuándo usarlo | Qué calcula |
|---|---|---|
| **Local ASE/EMT** | Sistemas metálicos simples (Al, Cu, Ag, Au, Ni, Pd, Pt, Zn, Cd, Hg) | Energía real de relajación geométrica con el potencial EMT de la Atomic Simulation Environment |
| **Aproximación determinista** | Cualquier otra fórmula | Valores reproducibles seeded por `md5(formula)` — marcados explícitamente como aproximaciones |
| **SLURM (stub)** | Para preparar envío a cluster HPC real | Genera POSCAR, INCAR, KPOINTS (via pymatgen) y script `#SBATCH` listo para copiar al cluster |

El cálculo ASE/EMT es una simulación **real** con la estructura del material (relajación BFGS hasta convergencia). Para la mayoría de materiales de batería (óxidos, fosfatos, sulfuros), se usa la aproximación determinista — útil para validar el flujo y como placeholder mientras se conecta un cluster real.

#### Flujo de trabajo típico

**1. Enviar un trabajo:**
- Ingresa la fórmula del candidato (ej. `LiNi0.8Mn0.1Co0.1O2`)
- Selecciona `calculation_type`: `ENERGY` (energía estática) o `RELAX` (optimización geométrica — más preciso, más lento)
- Selecciona `adapter`: `local` o `slurm`
- Clic en "Submit Job" → el servidor responde 202 (aceptado) inmediatamente, el cálculo corre en background

**2. Monitorear el progreso:**
La tabla de trabajos se actualiza automáticamente cada 5 segundos mientras haya trabajos pendientes o en ejecución. Estados posibles:
- `pending` → en cola, hilo no iniciado aún
- `running` → cálculo en curso
- `completed` → resultados disponibles (clic en la fila para verlos)
- `failed` → error en el cálculo (mensaje de error visible al expandir)
- `cancelled` → cancelado por el usuario antes de completarse

**3. Ver resultados:**
Al expandir una fila completada, aparece el panel de resultados:
- `formation_energy_eV_per_atom` — energía de formación calculada
- `total_energy_eV` — energía total del sistema
- `n_atoms` — átomos en la celda calculada
- `n_steps` — pasos de relajación (solo para RELAX)
- `converged` — si la geometría convergió
- `method` — `ASE-EMT` para cálculo real, `deterministic-approx` para la aproximación

**Advertencia de aproximación:** Si el resultado usa la aproximación determinista, aparece un aviso naranja indicando que los valores no provienen de un cálculo cuántico real y deben tratarse solo como placeholder.

**4. Ingresar resultados a la base de datos:**
Una vez completado, el botón "Ingest" almacena los resultados DFT como `MaterialProperty` del material seleccionado — disponibles en la página de materiales, en el Convex Hull, y como datos adicionales para reentrenamiento futuro. `data_source` queda marcado como `"dft_local"` o `"dft_slurm"`.

**5. Descargar inputs SLURM:**
Para el adaptador SLURM, el botón "Download Inputs" descarga el script de SLURM y los archivos VASP (POSCAR, INCAR, KPOINTS) listos para copiar al cluster HPC y ejecutar `sbatch`.

#### Por qué esto cierra el ciclo científico

```
ML screening → top 20 candidatos
    → DFT Jobs: calcular EAH real para esos 20
    → Ingest: añadir resultados DFT al dataset
    → Reentrenar modelo con datos DFT propios
    → Screening más preciso en la siguiente iteración
```

Cada ciclo de verificación DFT hace al modelo más preciso en el espacio de composiciones de interés, reduciendo progresivamente la tasa de falsos positivos y optimizando el uso de tiempo computacional de HPC.

---

## 5. Cómo Interpretar Cada Resultado en Términos Energéticos

### 5.1 EAH predicho y operabilidad de la batería

La conexión directa:

| EAH predicho | Diagnóstico operacional | Acción |
|---|---|---|
| 0.0–0.05 eV/átomo | Cátodo termodinámicamente apto | Priorizar para DFT + síntesis |
| 0.05–0.10 eV/átomo | Metaestable — puede funcionar | Verificar DFT del estado delitiado |
| 0.10–0.20 eV/átomo | Alto riesgo de degradación | Solo si tiene otro factor compensador |
| > 0.20 eV/átomo | Se descompondrá en operación | Descartar o rediseñar la composición |

### 5.2 El parity plot como diagnóstico del modelo

Un parity plot con alta dispersión en la zona EAH = 0–0.10 eV/átomo es el más preocupante para un proyecto de baterías: es exactamente la zona donde necesitamos mayor precisión (distinguir buenos de malos candidatos está en esos 0.10 eV/átomo de diferencia).

Si el parity plot muestra buena predicción para EAH alto (inestables obvios) pero alta dispersión en EAH bajo (los candidatos de interés), el modelo necesita más datos de materiales estables en el training set.

### 5.3 Feature importance y estrategia de dopaje

Si el Feature Importance del modelo de EAH dice que "MagpieData range AtomicRadius" es el descriptor más predictivo, la estrategia de dopaje se vuelve clara:

**Para estabilizar un material inestable:** buscar sustituyentes isovalentes con radio atómico más similar al que sustituyen. Si Co³⁺ (0.545 Å) se sustituye por Al³⁺ (0.535 Å) en lugar de Ti⁴⁺ (0.605 Å), el mismatch es menor y el modelo predice mayor estabilidad — y eso es verificable experimentalmente.

El ML no solo predice — **guía la estrategia de diseño**.

### 5.4 SHAP waterfall y narrativa automática como justificación científica

Cuando se presenta un candidato a un comité de síntesis, "el modelo predijo EAH = 0.03 eV/átomo" no es suficiente justificación. Pero "el modelo predijo EAH = 0.03, principalmente porque este material tiene bajo mismatch de radio iónico (contribución −0.05 eV/átomo) y alta temperatura de fusión media (contribución −0.03 eV/átomo), ambos factores correlacionados con estabilidad estructural en la literatura" — eso es un argumento científico. SHAP provee esa narrativa de forma automática.

A partir de la sesión 7, el modal de explicación SHAP incluye una **narrativa automática** generada directamente de los valores SHAP, sin IA generativa. La narrativa:

- Muestra un **veredicto** de estabilidad con código de color (verde/amarillo/rojo/gris) según el valor predicho y el umbral de la propiedad objetivo.
- Lista los **factores que aumentan la propiedad** (e.g. aumentan la EAH → menos estable) y los **factores que la reducen** (e.g. reducen la EAH → más estable), cada uno con su nombre de descriptor legible, valor numérico del descriptor para ese material, y contribución SHAP.
- Incluye una **nota de baseline** que explica que la suma de todas las contribuciones SHAP desde el valor base del modelo produce el valor predicho.
- Cierra con un **contexto científico** de la propiedad para que el lector no experto entienda qué significa físicamente cada dirección de predicción.

La narrativa es completamente **rule-based y reproducible** — mismos datos de entrada producen siempre la misma narrativa. No depende de modelos de lenguaje ni genera texto especulativo.

### 5.5 La vía de descomposición y la seguridad de la batería

**Esta funcionalidad es directamente relevante para la seguridad operacional.**

Cuando se carga una batería Li-ion al máximo, el cátodo está delitiado — en estado de alta energía. Si el cátodo es metaestable en ese estado, la pregunta crítica es: **¿en qué se descompone?**

La plataforma lo calcula usando el diagrama de fases de Materials Project:

**Ejemplo LiCoO₂:**
```
LiCoO₂ → 0.333 Li₂O + 0.667 Co₃O₄
```
Los productos son estables, no reactivos con electrolito común — relativamente seguro.

**Ejemplo LiNiO₂ (problemático):**
```
LiNiO₂ → 0.5 NiO + 0.25 Li₂O + 0.25 O₂ ↑
```
Se libera O₂ gaseoso a alta temperatura — eso es exactamente el mecanismo de los incendios térmicos en baterías de Ni-rico.

**Implicaciones para diseño:**
- Un candidato cuya vía de descomposición libera O₂ → riesgo de seguridad inaceptable
- Un candidato que descompone en fases inertes → mucho más seguro
- Esto orienta la estrategia: dopar con Al, Ti o Mg en NMC estabiliza la superficie y cambia la vía de descomposición hacia productos menos reactivos

Sin esta herramienta, verificar la vía de descomposición requeriría DFT del diagrama de fases completo del sistema — costoso y tardío en el pipeline.

---

## 6. El Ciclo Completo: de Dato a Decisión de Síntesis

El workflow que implementa la plataforma no es lineal — es iterativo:

```
┌─────────────────────────────────────────────────────────────────────┐
│  CICLO DE OPTIMIZACIÓN DE MATERIALES DE ALMACENAMIENTO              │
│                                                                     │
│  ① Importar datos DFT de materiales conocidos (MP, OQMD)           │
│     → Dataset de referencia con EAH, ΔHf, band gap                 │
│                         ↓                                           │
│  ② Validar y caracterizar el espacio de datos                      │
│     → ¿Qué familias de materiales están representadas?              │
│     → ¿Qué tan denso es el muestreo en zona de interés?             │
│                         ↓                                           │
│  ③ Generar descriptores composicionales                             │
│     → Convertir fórmulas en vectores numéricos (Magpie)             │
│     → Visualizar el espacio de materiales con t-SNE                 │
│                         ↓                                           │
│  ④ Entrenar modelos ML                                              │
│     → Random Forest + GBM para predicción de EAH                   │
│     → Clasificador para screening binario estable/inestable         │
│     → Evaluar con parity plot, MAE, F1                              │
│                         ↓                                           │
│  ⑤ Analizar qué aprendió el modelo                                 │
│     → Feature Importance: ¿qué propiedades elementales importan?   │
│     → SHAP: ¿por qué cada predicción individual es lo que es?       │
│     → Extraer hipótesis de diseño verificables                      │
│                         ↓                                           │
│  ⑥ Screening de candidatos existentes                              │
│     → Predecir EAH para todo el dataset                             │
│     → Identificar top candidatos con OOD check                      │
│     → Ranquear por score compuesto                                  │
│                         ↓                                           │
│  ⑦ Explorar composiciones nuevas                                   │
│     → Introducir variantes hipotéticas en el Explorer               │
│     → Comparar sistemáticamente sustituciones                       │
│     → Identificar tendencias de dopaje                              │
│                         ↓                                           │
│  ⑧ Análisis profundo de candidatos prometedores                    │
│     → Chemical Analysis: factores de inestabilidad                  │
│     → Structure 3D: canales de difusión, coordinación               │
│     → Decomposition Pathway: ¿qué pasa si falla? ¿es seguro?       │
│                         ↓                                           │
│  ⑨ Lista final priorizada → DFT Jobs: verificación atomística       │
│     → Enviar top candidatos a /dft-jobs (adapter local o SLURM)    │
│     → Esperar resultados (ASE/EMT real o aproximación)              │
│     → Ingest: persistir EAH/ΔHf/band_gap DFT en MaterialProperty   │
│                         ↓                                           │
│  ⑩ Síntesis y retroalimentación                                    │
│     → Candidatos verificados van a síntesis experimental            │
│     → Nuevos datos DFT → reentrenar modelos → mayor precisión      │
│     → El sistema mejora con cada ciclo                              │
└─────────────────────────────────────────────────────────────────────┘
```

**El resultado final no es un número — es una lista priorizada de candidatos con justificación científica para cada uno**, lista para presentar a un grupo de síntesis o para solicitar tiempo en una supercomputadora para DFT de verificación.

---

## 7. Limitaciones Honestas del Sistema

Una plataforma científica seria requiere transparencia sobre qué no puede hacer:

### 7.1 Los descriptores no saben de estructura

Los descriptores Magpie derivan de propiedades elementales de la composición. No saben si LiCoO₂ es cúbico o hexagonal. Dos polimorfos de la misma fórmula con propiedades completamente distintas tienen el mismo descriptor — el modelo los trata igual. Para discriminar polimorfos, se necesitan descriptores estructurales (CGCNN, ALIGNN), que requieren la estructura cristalina como input — que para candidatos hipotéticos no existe.

### 7.2 EAH a 0 K, 0 Pa

Los cálculos DFT de referencia son a temperatura y presión cero. Un material estable a 0 K puede desestabilizarse a 300 K (temperatura operacional de una batería) por efectos de entropía vibracional. Las correcciones de temperatura están fuera del alcance de los modelos actuales en esta plataforma.

### 7.3 El modelo predice lo que los datos contienen

Si el dataset está sesgado hacia ciertos sistemas químicos (por ejemplo, óxidos de Co y Ni), el modelo será mejor en esos sistemas y más incierto en otros. La detección OOD alerta, pero el sesgo puede ser sutil. Los top-candidatos siempre deben interpretarse en el contexto de qué datos se usaron para entrenar.

### 7.4 La predicción de EAH no predice rendimiento electroquímico directamente

EAH predice estabilidad termodinámica. No predice directamente:
- Capacidad específica (mAh/g) — requiere conteo de Li extraíbles con voltaje adecuado
- Velocidad de carga (C-rate) — depende de la difusividad del Li⁺ en la estructura
- Retención de ciclos — depende de la cinética de la interfase y de la fatiga mecánica

Estos requerirían modelos separados entrenados en datos electroquímicos experimentales — una extensión natural de esta plataforma.

### 7.5 La vía de descomposición es termodinámica, no cinética

El diagrama de fases dice "este material podría descomponerse en A + B". Si esa descomposición requiere superar una barrera energética de 2 eV, en práctica puede no ocurrir en escala de tiempo operacional. La cinética de descomposición requiere métodos adicionales (NEB, MD) no implementados aquí.

---

## 8. Glosario Rápido

| Término | Definición en contexto de almacenamiento de energía |
|---|---|
| **EAH** | Energy Above Hull. 0 = termodinámicamente estable. > 0.10 = probablemente no sintetizable o inestable en operación. |
| **ΔHf** | Energía de formación. Negativa = el material quiere formarse. Positiva = requiere fuerza externa para existir. |
| **Band gap** | Brecha electrónica. 0.5–3.5 eV es ideal para electrodo activo de batería. |
| **Cátodo** | Electrodo positivo de la batería. Li se inserta durante descarga. Aquí se alojan los materiales estudiados. |
| **Intercalación** | Inserción/extracción reversible de Li⁺ en la red cristalina durante carga/descarga. |
| **Delitiado** | Estado del cátodo durante carga — Li⁺ extraído. El estado más reactivo y de mayor riesgo de descomposición. |
| **NMC** | Li(NiₓMnᵧCoᵤ)O₂. Familia de cátodos con balance capacidad/estabilidad. NMC 811: alta capacidad pero menos estable. |
| **LFP** | LiFePO₄. Cátodo estable, abundante, seguro. Menor densidad energética que NMC. |
| **Polimorfo** | Misma fórmula, distinta estructura cristalina. Pueden tener EAH muy diferente. |
| **Diagrama de fases** | Mapa de qué compuestos son estables en un sistema de elementos dado. Base del cálculo de descomposición. |
| **OOD** | Out-of-Domain. Material cuya composición está fuera del rango estadístico del training set. Predicción de alta incertidumbre. |
| **Descriptor Magpie** | Característica numérica derivada de propiedades elementales. ~150 por material. Input del modelo ML. |
| **Surrogate model** | Modelo ML que reemplaza DFT costoso con predicción rápida aprendida de datos existentes. |
| **SHAP** | SHapley Additive exPlanations. Explica por qué el modelo predijo ese valor para ese material específico. |
| **Parity plot** | Gráfico predicho vs. real. Diagonal = modelo perfecto. Dispersión = error del modelo. |
| **Feature Importance** | Qué descriptores contribuyen más a la predicción. Genera hipótesis de diseño verificables. |
| **t-SNE** | Reducción de dimensionalidad. Muestra cómo se agrupan los materiales en el espacio de descriptores. |
| **DFT** | Teoría del Funcional de la Densidad. Cálculo cuántico de propiedades. Días por material. El "oráculo". |
| **ASE** | Atomic Simulation Environment. Librería Python para simulación atomística. EMT (Effective Medium Theory): potencial empírico de alta velocidad para metales. |
| **EMT** | Effective Medium Theory. Calculador rápido de ASE para metales (Al, Cu, Ag, Au, Ni, Pd, Pt, Zn, Cd, Hg). No DFT, pero suficiente para relajación geométrica de metales simples. |
| **VASP** | Vienna Ab Initio Simulation Package. Software DFT de referencia industrial. Requiere licencia comercial. Los archivos POSCAR/INCAR/KPOINTS son sus inputs. |
| **SLURM** | Simple Linux Utility for Resource Management. Gestor de trabajos en clusters HPC. La plataforma genera scripts SLURM listos para `sbatch`. |
| **POSCAR** | Formato de estructura cristalina de VASP. Describe la celda unitaria, posiciones atómicas y parámetros de red. |
| **HPC** | High Performance Computing. Clúster de cómputo paralelo. Los cálculos DFT reales requieren HPC — la plataforma genera los inputs, el usuario hace el envío manual. |
| **CEI** | Cathode Electrolyte Interphase. Capa que se forma en la superficie del cátodo. Afecta vida útil. |
| **Olivina** | Estructura cristalina de LiFePO₄. Canales 1D para Li⁺. Alta estabilidad, baja velocidad. |
| **Layered** | Estructura en capas (LiCoO₂, NMC). Canales 2D para Li⁺. Alta capacidad. |
| **Spinel** | Estructura espinela (LiMn₂O₄). Canales 3D para Li⁺. Alta velocidad de carga. |
| **MAE** | Mean Absolute Error. Error medio de predicción en eV/átomo. |
| **F1-macro** | Métrica de clasificación balanceada entre precisión y recall para todas las clases. |

---

*Documento de referencia para MatEnergy-ML — "Diseño computacional de materiales energéticos para tecnologías de almacenamiento avanzado mediante inteligencia artificial y simulación atomística."*
