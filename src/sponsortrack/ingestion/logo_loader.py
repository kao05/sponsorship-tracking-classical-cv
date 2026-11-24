"""Carga de logos y limpieza del fondo de 'transparencia' horneado en los PNG."""
import cv2
import numpy as np


def clean_logo(img_bgr, solo_borde=False):
    """Devuelve una máscara uint8 (255 = logo).

    solo_borde=True: solo es fondo lo conectado al borde de la imagen
    (para logos con zonas blancas propias, como el escudo del FCB).
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    fondo = ((hsv[..., 1] < 40) & (hsv[..., 2] > 140)).astype(np.uint8)

    if solo_borde:
        _, lab = cv2.connectedComponents(fondo)
        borde = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        fondo = np.isin(lab, borde[borde != 0]).astype(np.uint8)

    mascara = (1 - fondo).astype(np.uint8) * 255
    k = np.ones((3, 3), np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, k)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, k)

    n, lab, stats, _ = cv2.connectedComponentsWithStats(mascara)
    if n > 1:  # conservar solo el componente más grande (el logo)
        mayor = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mascara = ((lab == mayor) * 255).astype(np.uint8)
    return mascara


def load_logo(path, solo_borde=False):
    """Devuelve (imagen BGR, máscara del logo)."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return img, clean_logo(img, solo_borde)