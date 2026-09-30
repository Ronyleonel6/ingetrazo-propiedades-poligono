# SPDX-License-Identifier: MIT
# Copyright (c) 2026 <Rony Leonel Janampa Monago>
# ~/.local/share/ingetrazo/plugins/propiedades_poligono.py
"""
Propiedades del polígono — área, perímetro, centroide y momentos de
segundo orden del polígono (cara) seleccionado en el modelo.

Instalación: copia este archivo en la carpeta de plugins
(Extensions ▸ Abrir carpeta de plugins) y reinicia IngeTrazo.
Aparece como:
    Extensions ▸ Propiedades del polígono

Unidades: IngeTrazo trabaja internamente en metros. Todos los resultados
se expresan en el sistema internacional derivado de esa unidad base:
longitudes en m, áreas en m², momentos de segundo orden en m⁴.
"""

import math

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QPlainTextEdit, QDialogButtonBox,
    )
except ImportError:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QPlainTextEdit, QDialogButtonBox,
    )

from tools.base import Tool


# =========================================================================
# 0. Unidades base del informe.
#
#    IngeTrazo trabaja en metros. Si algún día quieres otro sistema,
#    cambia aquí los tres factores y las tres etiquetas; la matemática
#    no cambia (sigue calculando en metros internamente).
# =========================================================================

UNIT_LENGTH = ("m",   1.0)    # longitudes
UNIT_AREA   = ("m²",  1.0)    # áreas        (1 m²   = 1)
UNIT_MOMENT = ("m⁴",  1.0)    # inercia      (1 m⁴   = 1)

# Ejemplos alternativos (descomenta uno y comenta el bloque de arriba):
#   UNIT_LENGTH = ("cm", 1e2); UNIT_AREA = ("cm²", 1e4); UNIT_MOMENT = ("cm⁴", 1e8)
#   UNIT_LENGTH = ("mm", 1e3); UNIT_AREA = ("mm²", 1e6); UNIT_MOMENT = ("mm⁴", 1e12)


def _u(value, unit):
    """Formatea un valor escalar con su unidad, con 6 cifras significativas."""
    label, factor = unit
    return f"{value * factor:.6g} {label}"


# =========================================================================
# 1. La matemática — Python puro, sin documento, fácil de probar en consola.
#
#    Todo entra y sale en las unidades del polígono (que son metros,
#    porque provienen del modelo).
# =========================================================================

def polygon_properties(pts):
    """
    pts : secuencia de (x, y), los vértices del polígono simple en orden
          (el lazo se cierra implícitamente; no repitas el primer punto).
    Devuelve un dict con:
        área, perímetro, centroide,
        Ix, Iy, Ixy respecto al origen y respecto al centroide,
        momentos principales I1, I2 y su ángulo,
        radios de giro rx, ry, y la caja envolvente local.

    Unidades (coherentes con la entrada):
        longitudes → m        área → m²
        Ix, Iy, Ixy, I1, I2 → m⁴
        θ → radianes (el informe lo pasa a grados)
    """
    pts = [(float(x), float(y)) for (x, y) in pts]
    n = len(pts)
    if n < 3:
        raise ValueError("Un polígono necesita al menos 3 vértices.")

    # Fórmula del lazo (Gauss). Si el recorrido sale horario, lo invertimos
    # para que las fórmulas de momentos de abajo (que asumen antihorario)
    # devuelvan valores positivos.
    A2 = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        A2 += x0 * y1 - x1 * y0
    if A2 < 0.0:
        pts = pts[::-1]
        A2 = -A2
    A = 0.5 * A2
    if A < 1e-12:
        raise ValueError("El polígono es degenerado (área ≈ 0).")

    Sx = Sy = 0.0
    Ix_o = Iy_o = Ixy_o = 0.0
    perim = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0            # área con signo del triángulo de esta arista
        Sx += (x0 + x1) * cross
        Sy += (y0 + y1) * cross
        Ix_o  += (y0*y0 + y0*y1 + y1*y1) * cross
        Iy_o  += (x0*x0 + x0*x1 + x1*x1) * cross
        # Coeficientes 1, 2, 2, 1 — verificados contra un cuadrado unidad (Ixy = 1/4).
        Ixy_o += (x0*y1 + 2*x0*y0 + 2*x1*y1 + x1*y0) * cross
        perim += math.hypot(x1 - x0, y1 - y0)

    cx = Sx / (6.0 * A)
    cy = Sy / (6.0 * A)

    # Las sumas anteriores arrastran un factor 12 (Ix, Iy) / 24 (Ixy).
    Ix_o  /= 12.0
    Iy_o  /= 12.0
    Ixy_o /= 24.0

    # Teorema de los ejes paralelos: todo al centroide.
    Ixc  = Ix_o  - A * cy * cy
    Iyc  = Iy_o  - A * cx * cx
    Ixyc = Ixy_o - A * cx * cy

    # Momentos principales = autovalores de [[Ixc, Ixyc], [Ixyc, Iyc]].
    avg  = 0.5 * (Ixc + Iyc)
    diff = 0.5 * (Ixc - Iyc)
    R    = math.hypot(diff, Ixyc)
    I1   = avg + R
    I2   = avg - R
    # Ángulo del eje principal mayor, medido desde el eje u.
    theta = 0.5 * math.atan2(2.0 * Ixyc, Ixc - Iyc)

    # Radios de giro respecto al centroide.
    rx = math.sqrt(max(Ixc, 0.0) / A)
    ry = math.sqrt(max(Iyc, 0.0) / A)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    return {
        "n": n,
        "area": A,
        "perimeter": perim,
        "centroid": (cx, cy),
        "Ix_origin":   Ix_o,   "Iy_origin":   Iy_o,   "Ixy_origin":   Ixy_o,
        "Ix_centroid": Ixc,    "Iy_centroid": Iyc,    "Ixy_centroid": Ixyc,
        "I1_principal": I1, "I2_principal": I2,
        "theta_principal": theta,
        "rx_gyration": rx, "ry_gyration": ry,
        "bbox": (min(xs), min(ys), max(xs), max(ys)),
    }


# =========================================================================
# 2. Lectura del polígono desde el documento.
#
#    La API de plugins es 0.x y la forma exacta de "la selección actual"
#    aún no está congelada, así que este ayudante es defensivo: prueba
#    las formas documentadas y lanza un mensaje claro si no encuentra nada.
# =========================================================================

def _call_if_method(val):
    """Devuelve val() si val es invocable; si no, devuelve val.
    Sirve para tolerar tanto `vertex.x` como `vertex.x()` según la versión
    de IngeTrazo."""
    if callable(val):
        try:
            return val()
        except Exception:
            return None
    return val


def _as_point3(v, vertex_table):
    """
    Normaliza un vértice a (x, y, z) en flotantes.

    La API 0.x expone los vértices de varias formas; no adivinamos:
    probamos cada una y usamos la primera que funcione.

      • objeto con .x/.y/.z  (atributos O métodos)
      • objeto con .X/.Y/.Z
      • objeto con .position() / .co / .pos / .xyz / .location
      • un índice dentro de vertex_table (la lista de vértices de la malla)
      • una secuencia de 3 (tupla, lista, array, Vector)
    """
    # 1) Puede ser un índice dentro de la tabla de vértices.
    if isinstance(v, int) and vertex_table is not None:
        try:
            v = vertex_table[v]
        except Exception:
            pass

    # 2) Objeto con x / y / z — atributo o método.
    for names in (("x", "y", "z"), ("X", "Y", "Z")):
        vals = []
        for a in names:
            raw = getattr(v, a, None)
            if raw is None:
                break
            val = _call_if_method(raw)
            if val is None:
                break
            vals.append(val)
        if len(vals) == 3:
            try:
                return (float(vals[0]), float(vals[1]), float(vals[2]))
            except (TypeError, ValueError):
                pass

    # 3) Objeto con un único accesor a un vector de 3 componentes.
    for attr in ("position", "co", "pos", "xyz", "location", "coord"):
        raw = getattr(v, attr, None)
        if raw is None:
            continue
        val = _call_if_method(raw)
        if val is None:
            continue
        try:
            seq = list(val)
        except TypeError:
            continue
        if len(seq) >= 3:
            try:
                return (float(seq[0]), float(seq[1]), float(seq[2]))
            except (TypeError, ValueError):
                pass

    # 4) Secuencia simple (lista, tupla, array de numpy, Vector…).
    try:
        seq = list(v)
        if len(seq) >= 3:
            return (float(seq[0]), float(seq[1]), float(seq[2]))
    except (TypeError, ValueError):
        pass

    # 5) Nada funcionó: lanzamos un error que dice *qué* es el objeto,
    #    para que la próxima iteración sea un cambio de dos líneas.
    public = [a for a in dir(v) if not a.startswith("_")]
    raise RuntimeError(
        f"Vértice no reconocido {v!r} (tipo {type(v).__name__}; "
        f"atributos públicos: {public[:12]})."
    )


def _polygon_normal(pts3):
    """Método de Newell — funciona con cualquier polígono plano, convexo o no."""
    nx = ny = nz = 0.0
    n = len(pts3)
    for i in range(n):
        x0, y0, z0 = pts3[i]
        x1, y1, z1 = pts3[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    L = math.sqrt(nx*nx + ny*ny + nz*nz)
    if L < 1e-12:
        raise RuntimeError("Los vértices del polígono son colineales o coincidentes.")
    return (nx / L, ny / L, nz / L)


def _project_to_plane(pts3, normal):
    """Devuelve (uv, origin, u_axis, v_axis): coordenadas 2D en el plano del
    polígono, con el origen en el primer vértice (así los resultados quedan
    referidos a un punto del polígono, no al origen del mundo)."""
    nx, ny, nz = normal
    ref = (0.0, 0.0, 1.0) if abs(nz) < 0.9 else (1.0, 0.0, 0.0)

    def cross(a, b):
        return (a[1]*b[2] - a[2]*b[1],
                a[2]*b[0] - a[0]*b[2],
                a[0]*b[1] - a[1]*b[0])

    def norm(a):
        L = math.sqrt(a[0]**2 + a[1]**2 + a[2]**2)
        return (a[0]/L, a[1]/L, a[2]/L)

    u = norm(cross(ref, normal))
    v = norm(cross(normal, u))
    ox, oy, oz = pts3[0]
    uv = []
    for (x, y, z) in pts3:
        dx, dy, dz = x - ox, y - oy, z - oz
        uv.append((dx*u[0] + dy*u[1] + dz*u[2],
                   dx*v[0] + dy*v[1] + dz*v[2]))
    return uv, (ox, oy, oz), u, v


def _iter_selection(viewport):
    """Recorre lo que el viewport exponga como "la selección actual",
    tolerando atributos y métodos. Nunca lanza; no devuelve nada cuando
    la versión de IngeTrazo no tiene una API de selección evidente."""
    for attr in ("selection", "selected", "selected_faces",
                 "selected_items", "get_selection"):
        raw = getattr(viewport, attr, None)
        if raw is None:
            continue
        if callable(raw):
            try:
                raw = raw()
            except Exception:
                continue
        if not raw:
            continue
        try:
            for item in raw:
                yield item
        except TypeError:
            yield raw
        return


def _get_selected_polygon(viewport):
    """Devuelve (pts3, normal, source_label). Lanza RuntimeError con un
    mensaje amable cuando no hay nada utilizable seleccionado."""
    scene = getattr(viewport, "scene", None)
    mesh  = getattr(scene, "loose_mesh", None) if scene else None
    vtable = list(getattr(mesh, "vertices", []) or []) if mesh else None

    # --- Primero, la selección actual ----------------------------------
    face = None
    for item in _iter_selection(viewport):
        face = (getattr(item, "face", None)
                or getattr(item, "polygon", None)
                or item)
        if face is not None:
            break

    # --- Si no hay selección, la malla suelta cuando tiene UNA sola cara --
    source = "selección"
    if face is None:
        faces = list(getattr(mesh, "faces", []) or []) if mesh else []
        if not faces:
            raise RuntimeError(
                "Seleccione un polígono (una cara) antes de ejecutar "
                "Propiedades del polígono."
            )
        if len(faces) > 1:
            raise RuntimeError(
                f"No hay nada seleccionado y la malla suelta tiene "
                f"{len(faces)} caras. Seleccione exactamente una."
            )
        face = faces[0]
        source = "malla suelta (única cara)"

    # --- Extraemos el lazo de vértices de la cara ----------------------
    verts = None
    for attr in ("vertices", "points", "loop", "indices", "verts", "vs"):
        raw = getattr(face, attr, None)
        if raw is None:
            continue
        if callable(raw):
            try:
                raw = raw()
            except Exception:
                continue
        try:
            raw = list(raw)
        except TypeError:
            continue
        if raw:
            verts = raw
            break

    if verts is None:
        public = [a for a in dir(face) if not a.startswith("_")]
        raise RuntimeError(
            f"No se pueden leer los vértices de la cara {face!r} "
            f"(tipo {type(face).__name__}; atributos públicos: {public[:12]})."
        )

    # Los vértices pueden ser índices dentro de la malla; los resolvemos.
    pts3 = [_as_point3(v, vtable) for v in verts]

    normal = _polygon_normal(pts3)
    return pts3, normal, source


# =========================================================================
# 3. El diálogo del informe.
# =========================================================================

def _format_report(props, note):
    L = []
    L.append("Propiedades del polígono")
    L.append("=" * 64)
    L.append(note)
    L.append("")
    L.append(f"Unidades: longitudes en {UNIT_LENGTH[0]}, "
             f"áreas en {UNIT_AREA[0]}, "
             f"momentos de segundo orden en {UNIT_MOMENT[0]}.")
    L.append("")
    L.append(f"Vértices              : {props['n']}")
    L.append(f"Área                  : {_u(props['area'],      UNIT_AREA)}")
    L.append(f"Perímetro             : {_u(props['perimeter'], UNIT_LENGTH)}")
    L.append("")
    L.append("Centroide (u, v) en el plano propio del polígono:")
    L.append(f"  u = {_u(props['centroid'][0], UNIT_LENGTH)}")
    L.append(f"  v = {_u(props['centroid'][1], UNIT_LENGTH)}")
    L.append("")
    L.append("Momentos de segundo orden respecto al centroide:")
    L.append(f"  Ix  = {_u(props['Ix_centroid'],  UNIT_MOMENT)}")
    L.append(f"  Iy  = {_u(props['Iy_centroid'],  UNIT_MOMENT)}")
    L.append(f"  Ixy = {_u(props['Ixy_centroid'], UNIT_MOMENT)}")
    L.append("")
    L.append("Momentos de segundo orden respecto al origen del plano:")
    L.append(f"  Ix  = {_u(props['Ix_origin'],  UNIT_MOMENT)}")
    L.append(f"  Iy  = {_u(props['Iy_origin'],  UNIT_MOMENT)}")
    L.append(f"  Ixy = {_u(props['Ixy_origin'], UNIT_MOMENT)}")
    L.append("")
    L.append("Momentos principales y ángulo:")
    L.append(f"  I1 = {_u(props['I1_principal'], UNIT_MOMENT)}")
    L.append(f"  I2 = {_u(props['I2_principal'], UNIT_MOMENT)}")
    L.append(f"  θ  = {math.degrees(props['theta_principal']):.4g}° "
             f"(medido desde el eje u, pasando por el centroide)")
    L.append("")
    L.append("Radios de giro respecto al centroide:")
    L.append(f"  rx = {_u(props['rx_gyration'], UNIT_LENGTH)}")
    L.append(f"  ry = {_u(props['ry_gyration'], UNIT_LENGTH)}")
    L.append("")
    x0, y0, x1, y1 = props["bbox"]
    L.append("Caja envolvente en el plano local:")
    L.append(f"  u ∈ [{_u(x0, UNIT_LENGTH)}, {_u(x1, UNIT_LENGTH)}]   "
             f"Δu = {_u(x1 - x0, UNIT_LENGTH)}")
    L.append(f"  v ∈ [{_u(y0, UNIT_LENGTH)}, {_u(y1, UNIT_LENGTH)}]   "
             f"Δv = {_u(y1 - y0, UNIT_LENGTH)}")
    return "\n".join(L)


class _ReportDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Propiedades del polígono")
        self.resize(600, 640)
        lay = QVBoxLayout(self)
        box = QPlainTextEdit(self)
        box.setReadOnly(True)
        box.setPlainText(text)
        box.setStyleSheet("font-family: monospace;")
        lay.addWidget(box)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)


# =========================================================================
# 4. La herramienta.
# =========================================================================

class PolygonPropertiesTool(Tool):
    name = "Propiedades del polígono"
    shortcut = None                 # p. ej. "Ctrl+Shift+G" si está libre
    description = ("Área, perímetro, centroide y momentos de segundo orden "
                   "del polígono seleccionado (longitudes en m, área en m², "
                   "momentos en m⁴).")

    def on_activate(self, viewport):
        try:
            pts3, normal, source = _get_selected_polygon(viewport)
            uv, origin, _u_axis, _v_axis = _project_to_plane(pts3, normal)
            props = polygon_properties(uv)
        except Exception as exc:
            viewport.flash_status(f"Propiedades del polígono: {exc}", 6000)
            return

        note = (f"Origen: {source}.  "
                f"Plano local: origen en el primer vértice "
                f"({origin[0]:.4g}, {origin[1]:.4g}, {origin[2]:.4g}) m;  "
                f"normal ({normal[0]:.3f}, {normal[1]:.3f}, {normal[2]:.3f}).  "
                f"Ix respecto al eje u, Iy respecto al eje v.")
        text = _format_report(props, note)

        parent = None
        try:
            parent = viewport.window()
        except Exception:
            parent = None

        _ReportDialog(text, parent).exec()

        viewport.flash_status(
            f"Propiedades del polígono: "
            f"área = {_u(props['area'],      UNIT_AREA)},  "
            f"perímetro = {_u(props['perimeter'], UNIT_LENGTH)}.", 5000)

    def on_deactivate(self, viewport):
        pass
