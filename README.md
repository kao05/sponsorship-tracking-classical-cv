# Sponsorship Tracking 

Sistema que mide cuánto tiempo aparece la marca de un patrocinador en un video, usando únicamente técnicas clásicas de visión por computadora.

## Motivación del proyecto 

Cuando una marca patrocina a un equipo o a una persona, necesita saber cuánto vale esa exposición para decidir cuánto pagar. Ese valor depende de cuánto tiempo y con qué visibilidad aparece su logo en pantalla. Medirlo a mano es lento, costoso y subjetivo, y no siempre hay herramientas accesibles para hacerlo de forma automática. Este proyecto propone una forma objetiva y reproducible de obtener esas mediciones a partir del video.

## Vision Artificial Clasica

Este proyecto resuelve el problema de detectar y seguir logotipos en video **sin redes neuronales**: no se usa ``YOLO`` ni ningún modelo entrenado con aprendizaje profundo. Todo se construye con técnicas básicas que ya existen en la literatura de visión por computadora, como detección de **puntos característicos, validación geométrica, seguimiento por correlación y flujo óptico, y filtros de estimación como Kalman**.

### Hipótesis 

Los modelos convencionales de visión por computadora son más eficientes que las redes neuronales en cuanto a requerimientos de hardware y de entrenamiento: pueden funcionar en un equipo común, sin GPU y sin una fase de entrenamiento, y aun así medir la exposición de una marca con una precisión útil. Se evaluará midiendo la velocidad de procesamiento y el consumo de recursos del sistema, además del error en el tiempo de exposición frente a mediciones manuales.

## Metodología resumida

1. **Preparación:** se ajusta el video a una velocidad constante de fotogramas y se prepara la imagen del logo que se quiere buscar.
2. **Búsqueda del logo:** en cada fotograma se descartan las zonas que no se parecen al logo y se buscan coincidencias con él.
3. **Confirmación:** se comprueba que la coincidencia tenga sentido geométrico y se dibuja el contorno del logo en la escena.
4. **Seguimiento:** una vez encontrado, el logo se sigue de un fotograma al siguiente sin buscarlo desde cero, y se vuelve a buscar cada cierto tiempo.
5. **Estabilización e identidad:** se suaviza el recorrido del logo, se mantiene su posición durante pérdidas breves y se evita contarlo dos veces.
6. **Cálculo de la exposición:** se registran todas las apariciones, se descartan las falsas y se calcula el tiempo total en pantalla y el área que ocupa.
7. **Evaluación:** se comparan los resultados con mediciones hechas a mano y se visualizan en un video y en gráficas.

## Alcance

- **Marcas:** FC Barcelona (escudo), Spotify y Nike, en las variantes de color de las camisetas.
- **Video:** resumen de mejores momentos de ~17 min, 1920×1080 a 25 fps, sin recortar.
- **Exposición válida:** logo con área ≥ 40×40 px (a 1920 de ancho) durante ≥ 0.5 s
  (13 fotogramas); los huecos de hasta 0.3 s se unen. Lo más pequeño se reporta como
  "no medible".
- **Zonas ignoradas:** la franja superior de 170 px, donde la transmisión coloca el
  marcador y sus propios gráficos.

## 1. Arquitectura del proyecto

```text
sponsorship-tracking/
├── README.md
├── requirements.txt
├── .gitignore                  # ignora data/videos, data/processed, outputs, .venv, este plan
├── data/
│   ├── videos/                 # videos originales
│   ├── processed/              # videos normalizados a FPS constante
│   ├── logos/                  # una imagen de referencia por marca
│   └── annotations/            # intervalos.csv, segmentos.csv, cajas.csv
├── outputs/
│   ├── videos/                 # videos con contornos e IDs dibujados
│   ├── telemetry/              # CSV por video (frame, timestamp, track_id, sponsor, bbox, inliers)
│   └── figures/                # gráficas y tablas de resultados
├── notebooks/                  # exploración y pruebas por etapa
├── scripts/
│   ├── prepare_video.py        # Etapa 2: normaliza el video
│   ├── run_pipeline.py         # Etapas 3 a 6: corre el sistema
|   ├── annotate_boxes.py
│   └── evaluate.py             # Etapa 7: métricas y comparación
├── src/sponsortrack/
│   ├── config.py               # umbrales y parámetros en un solo lugar
│   ├── ingestion/              # PASO 1
│   │   ├── video_io.py         # FFmpeg + lectura de fotogramas
│   │   └── logo_loader.py      # carga del logo y precálculo offline (descriptores, histograma)
│   ├── detection/              # PASO 2
│   │   ├── features.py         # SIFT / ORB / AKAZE (misma interfaz)
│   │   ├── matcher.py          # emparejamiento + test de Lowe
│   │   ├── color_prefilter.py  # retroproyección de histograma
│   │   └── template_matching.py# respaldo multiescala + Canny
│   ├── geometry/               # PASO 3
│   │   └── homography.py       # RANSAC, validación del cuadrilátero, proyección del contorno
│   ├── tracking/               # PASOS 4 y 5
│   │   ├── trackers.py         # CSRT / KCF / MOSSE
│   │   ├── klt.py              # Harris + flujo óptico Lucas-Kanade
│   │   ├── kalman.py           # filtro de Kalman del bounding box
│   │   └── association.py      # asignación húngara (IoU)
│   ├── analytics/              # PASO 6
│   │   └── telemetry.py        # DataFrame, filtrado temporal, tiempo y área
│   ├── evaluation/             # PASO 7
│   │   ├── metrics.py          # precisión, recall, IoU, error de tiempo
│   │   └── benchmark.py        # FPS, CPU y memoria por método
│   └── pipeline.py             # bucle por fotograma: buscar <-> seguir
└── tests/                      # pruebas pequeñas de homografía, IoU, filtrado
```

## Modo de uso

Preparar el entorno (sin Docker)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -c "import cv2; print(cv2.__version__, hasattr(cv2, 'SIFT_create'))"
```