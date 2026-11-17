# Metodología del proyecto 

El flujo del algoritmo es el siguiente:

1. Ingesta de datos y extracción de sponsors 
2. Prefiltrado y detección de características 
3. Validación geométrica y proyección de contorno 
4. Propagación temporal fotograma a fotograma
5. Estimación cinemática y asociación de identidades
6. Consolidación de telemetría y cálculo de tiempo en pantalla
7. Evaluación cuantitativa y visualización de resultados

- **Fase A, una sola vez:** 1. Ingesta y preparación.
- **Fase B, bucle por fotograma:**
  1. Prefiltrado y detección.
  2. Validación geométrica.
  3. Propagación temporal.
  4. Kalman y asociación húngara.
- **Fase C, al final:** 6. Consolidación de telemetría y 7. Evaluación.

Dentro del bucle hay dos modos. Si no hay logo siendo seguido, el algoritmo busca *(pasos 2 y 3)*. Si ya hay uno, sigue *(pasos 4 y 5)* y solo vuelve a buscar cada cierto intervalo o cuando el seguimiento falla. En el paso 5, el orden por fotograma es: Kalman predice, el húngaro asocia con las mediciones y Kalman actualiza

---

## Ingesta de datos y extracción de sponsors 

Mediante la herramienta de `FFmpeg` sse normaliza a una tasa de FPS constante para garantizar que cada fotograma tenga un tiempo justo, al mismo tiempo el **Logo(template)** a analizar se decodifica en un vector de NumPy y los descriptores (`SIFT`, `ORB` o `AKAZE`) para encontrar puntos geometricamente distintos y describir vecindades matemáticas se permiten encontrar el logotipo aunque aparezca más grande, más pequeño o inclinado en el video. 
Calculamos las esquinas mediante el método **Harris** y los contornos mediante **Canny** una pirámide de escalas y su histograma de color en espacio HSV o CIE Lab.

### FFmpeg

Motor de línea de comandos y librerías encargado de decodificar el video de entrada, extraer secuencias de fotogramas a una tasa constante (FPS fijos, indispensable para convertir conteo de fotogramas a segundos exactos), reescalar resoluciones para acelerar el procesamiento y renderizar el video final con los recuadros e identificadores superpuestos.

### Detectores de características 

| Algoritmo | Tipo de descriptor | Métrica de distancia | Ventaja en el proyecto | Limitación |
| :--- | :--- | :--- | :--- | :--- |
| **SIFT** | Vector flotante (128D) basado en gradientes DoG | Euclidiana ($L_2$) | Máxima precisión ante cambios de escala, rotación e iluminación. | Alto costo computacional (menor FPS). |
| **ORB** | Binario (256 bits) basado en FAST + rBRIEF | Hamming | Extremadamente rápido; viable para procesamiento en tiempo real. | Menor robustez ante deformaciones fuertes de perspectiva. |
| **AKAZE** | Binario (M-LDB) en espacio-escala no lineal | Hamming | Equilibrio entre velocidad y precisión; preserva bordes sin difuminarlos. | Más lento que ORB en resoluciones muy altas. |

---

## Prefiltrado cromático y detección por características

Mediante **retroproyección de histogramas de color** (algoritmo de segmentación probabilística que calcula qué tan probable es que cada píxel de una imagen pertenezca a un objeto de referencia basándose únicamente en su distribución cromática) descartamos regiones del fotograma esto para reducir espacio de búsqueda y si existe una region candidata se extraen los puntos con algún detector de caracteristicas.
Lo comparamos contra el **templeate** y filtramos con **Test de Ratio de Lowe** (método de filtrado estadístico diseñado para eliminar emparejamientos falsos (outliers) al comparar descriptores de características locales entre dos imágenes).
En caso que la imagen sea muy deficiente para comparar se activa como respaldo el **Template Matching multiescala** apoyado en **bordes Canny**

### Template Matching Multiescala 

Desliza la imagen exacta del logotipo sobre el fotograma calculando una métrica de correlación a través de una pirámide de escalas, siempre que el logotipo no sufra rotaciones pronunciadas.

### Bordes Canny

Aplica suavizado gaussiano, cálculo de gradientes Sobel, supresión no máxima y umbralización con histéresis para extraer contornos finos de 1 píxel. Sirve para aislar siluetas tipográficas del logotipo o detectar los bordes rectangulares

---

## Validación geométrica y proyección de contorno

Cuando hemos encotrado el posible frame de un sponsor `RANSAC` estima iterativamente la matriz de homografía $\mathbf{H}$ ($3 \times 3$).
Si el conteo de inliers supera el umbral establecido y la deformación proyectiva es válida, se proyectan las esquinas de la plantilla sobre el fotograma para delimitar el cuadro delimitador.

### RANSAC y Homografía

Una vez obtenidas las parejas de puntos coincidentes $(x, y) \leftrightarrow (x', y')$, se calcula una matriz de homografía $\mathbf{H}$ de dimensión $3 \times 3$ (8 grados de libertad) que modela la transformación proyectiva entre el plano 2D del logotipo original y su proyección inclinada en el fotograma.
Sirve para proyectar el contorno exacto del logotipo en la escena y validar si la detección es geométricamente válida.

---

## Propagación temporal fotograma a fotograma

Evitando un alto coste computacional al ejecutar el detector en cada imagen que generemos del video la validación inicia un **Tracker clásico** (`CSRT`, `KCF`, `MOSSE`) junto con puntos de anclaje (**esquinas de Harris**) rastreados mediante flujo óptico disperso Lucas-Kanade (`KLT`) en los fotogramas consecutivos, estos algoritmos estiman la traslación y cambio de escala del logotipo a alta velocidad hasta que cae la confianza de correlación o se alcanza el intervalo periódico de redetección.

Estos algoritmos estiman la traslación y cambio de escala del logotipo a alta velocidad hasta que cae la confianza de correlación o se alcanza el intervalo periódico de redetección.

### Tracker Clásico 

| Algoritmo | Fundamento y Características | Velocidad | Escala y Oclusión | Limitación Principal |
| :--- | :--- | :--- | :--- | :--- |
| **MOSSE** *(Bolme et al., 2010)* | Correlación adaptativa en el dominio de Fourier (FFT) minimizando la suma de errores cuadráticos sobre intensidad en escala de grises. | Muy alta (~450–600+ FPS) | Sin adaptación nativa de escala; tolerancia mínima a oclusiones breves. | Pierde precisión y deriva ante cambios rápidos de escala, rotación o iluminación. |
| **KCF** *(Henriques et al., 2015)* | Regresión Ridge con matrices circulantes (diagonalizadas vía DFT) y truco de kernel sobre características **HOG** multicanal. | Alta (~100–200+ FPS) | Mayor precisión que MOSSE en traslación; soporta oclusiones parciales leves. | No se recupera de oclusiones totales (el filtro aprende el oclusor) ni ajusta escala dinámicamente. |
| **CSRT** *(Lukežič et al., 2017)* | Filtros de correlación discriminativos (DCF) con ponderación por canal (HOG + color) y mapa espacial de fiabilidad que restringe el soporte al objeto y excluye el fondo dentro del recuadro. | Moderada/Baja (~25–45 FPS) | Alta estabilidad ante cambios de escala, relación de aspecto, deformaciones y oclusiones parciales. | Mayor costo computacional y menor tasa de FPS debido a la estimación del mapa espacial. |

### Detector de esquinas de Harris

Evalúa los eigenvalores de la matriz de autocorrelación de gradientes locales para localizar intersecciones donde la intensidad cambia en dos direcciones ortogonales. Sirve para seleccionar puntos de anclaje estables (inmunes al problema de la apertura) antes de rastrearlos con flujo óptico.

### KLT

Método diferencial disperso (sparse) que estima el vector de desplazamiento $(u, v)$ de un subconjunto de puntos clave (como esquinas de Harris o los inliers de RANSAC) entre el fotograma $t$ y $t+1$ resolviendo por mínimos cuadrados la ecuación de constancia de brillo en una vecindad local. Permite seguir la deformación y traslación del logotipo fotograma a fotograma sin recalcular descriptores completos.

---

## Estimación cinemática y asociación de identidades

El **Filtro de Kalman** predice la posición, escala y velocidad esperadas del bounding box en el fotograma actual y corrige su estado con las mediciones del detector o del tracker, suavizando trayectorias y manteniendo la continuidad durante oclusiones breves.
Cuando existen múltiples detecciones o instancias simultáneas, el **algoritmo de asociación húngara** asigna cada medición a su trayectoria activa correspondiente para conservar un track_id único sin fragmentar el conteo

### Filtro de Kalman

Estimador bayesiano recursivo que modela el estado cinemático del cuadro delimitador (bounding box) del patrocinador (posición, escala y sus velocidades: $[x, y, s, r, \dot{x}, \dot{y}, \dot{s}]$). Opera en dos pasos: predicción (estima dónde estará el logotipo en $t+1$ según su velocidad previa) y actualización (corrige la estimación cuando el detector produce una nueva medición). Suaviza trayectorias ruidosas y mantiene viva la posición durante oclusiones momentáneas.

### Algoritmo de asociación húngara

Resuelve en tiempo polinómico $O(n^3)$ el problema de asignación óptima bipartita entre $M$ detecciones nuevas y $N$ trayectorias activas del filtro de Kalman mediante una matriz de costos. Si hay múltiples instancias de logotipos simultáneos en pantalla, garantiza que cada instancia conserve su identificador único (track_id) para no duplicar ni fragmentar los tiempos de exposición.

## Consolidación de telemetría y cálculo de tiempo en pantalla

Cada instancia rastreada fotograma a fotograma se registra en un DataFrame de Pandas (frame_id, timestamp, track_id, sponsor, bbox, inliers).
Se aplica un filtrado temporal para eliminar detecciones espurias aisladas (ruido de 1 o 2 fotogramas), se agrupan los intervalos continuos de aparición y se calcula el tiempo total de exposición acumulada en segundos junto con el porcentaje de área ocupada en pantalla.


## Evaluación cuantitativa y visualización de resultados

Los intervalos temporales y coordenadas generados por el pipeline se contrastan contra las anotaciones manuales de referencia en la primera parte etiquetadas en CVAT o Label Studio para calcular Precisión, Recall, IoU promedio y el error absoluto de tiempo de exposición