"""Umbrales y parámetros del proyecto en un solo lugar.

Los valores marcados como INICIAL se calibran en la Etapa 3 con el ground truth.
"""
import math
from pathlib import Path

# --- Rutas ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
VIDEOS_DIR = DATA / "videos"
PROCESSED_DIR = DATA / "processed"
LOGOS_DIR = DATA / "logos"
ANNOTATIONS_DIR = DATA / "annotations"
OUTPUTS = ROOT / "outputs"
OUT_VIDEOS = OUTPUTS / "videos"
OUT_TELEMETRY = OUTPUTS / "telemetry"
OUT_FIGURES = OUTPUTS / "figures"

# --- Video (original: 1920x1080, 25 fps; no se recorta) ------------------
TARGET_FPS = 25
REF_WIDTH = 1920
REF_HEIGHT = 1080

# Franja superior con gráficos de transmisión (marcador, LaLiga, escudo fijo).
# Se ignora en la detección: medida en el original, 170 px de 1080.
EXCLUDE_TOP_PX = 170
EXCLUDE_TOP_FRAC = EXCLUDE_TOP_PX / REF_HEIGHT   # para otras resoluciones

# --- Marcas (una entrada por marca, varias variantes de color) -----------
# Los archivos viven planos en data/logos/ como marca_variante.png
# fondo_solo_borde=True: el logo tiene zonas blancas propias (ver logo_loader)
BRANDS = {
    "fcb": {
        "nombre": "FC Barcelona",
        "variantes": ["fcb_clasico.png", "fcb_naranja.png"],
        "fondo_solo_borde": True,
    },
    "spotify": {
        "nombre": "Spotify",
        "variantes": ["spotify_clasico.png", "spotify_alternativo.png"],
        "fondo_solo_borde": False,
    },
    "nike": {
        "nombre": "Nike",
        "variantes": ["nike_clasico.png", "nike_alternativo.png"],
        "fondo_solo_borde": False,
    },
    # Reserva, pendiente de confirmar que aparece en el video:
    # "kobe": {"nombre": "Kobe", "variantes": ["Kobe.png"], "fondo_solo_borde": False},
}

# --- Exposición válida (INICIAL) ------------------------------------------
MIN_LOGO_AREA_PX = 40 * 40    # a REF_WIDTH; se escala con (ancho_real / REF_WIDTH)**2
MIN_DURATION_S = 0.5          # duración mínima de una aparición válida
MAX_GAP_S = 0.3               # huecos menores se unen a la misma aparición

# Equivalentes en fotogramas (13 y 8 a 25 fps)
MIN_DURATION_FRAMES = math.ceil(MIN_DURATION_S * TARGET_FPS)
MAX_GAP_FRAMES = math.ceil(MAX_GAP_S * TARGET_FPS)

# --- Detector base: SIFT + Lowe + RANSAC (Etapa 3, INICIAL) ---------------
SIFT_LOGO_WIDTH = 160         # ancho al que se redimensiona el logo antes de SIFT
LOWE_RATIO = 0.75
MIN_GOOD_MATCHES = 8
RANSAC_REPROJ_THRESH = 5.0
MIN_INLIERS = 12              # en la captura, el escudo de ~100 px dio 29-32