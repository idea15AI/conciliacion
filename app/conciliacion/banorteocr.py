import cv2
import easyocr
import re
import numpy as np
import fitz  # PyMuPDF
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
from pathlib import Path
import unicodedata
from statistics import median
import pandas as pd
from typing import Optional

# =========================
# CONFIG
# =========================
ZOOM = 2.5

# Recorte vertical (quita encabezado/pie)
TOP_CROP = 150
BOTTOM_CROP = 80

# Modo: previsualizar (imshow) vs extraer
PREVIEW_ONLY = False            # <--- pon True para sólo ver overlays
PREVIEW_PAGES = []              # [] = todas | ej. [1,2]

# Coordenadas MANUALES (x_ini, x_fin) dentro del recorte
MANUAL_COL_RANGES = {
    "FECHA":     (   0,  210),
    "DESCRIP":   ( 210,  890),   # "DESCRIPCIÓN / ESTABLECIMIENTO"
    "DEPOSITO":  ( 890, 1080),   # "MONTO DEL DEPÓSITO"
    "RETIRO":    (1080, 1240),   # "MONTO DEL RETIRO"
    "SALDO":     (1240, 1500),
}

# Gate: exige TODAS las cabeceras (5/5) y en MAYÚSCULAS
REQUIRE_ALL_HEADERS = True

# Colores (BGR)
COLORS = {
    "FECHA":    (255,   0,   0),
    "DESCRIP":  (  0, 200,   0),
    "DEPOSITO": (  0,   0, 255),
    "RETIRO":   (  0, 165, 255),
    "SALDO":    (255,   0, 255),
    "HEADER":   (255, 255,   0),
    "OTROS":    (120, 120, 120),
    "LINE":     (50,  200,  50),
    "BAND":     (200, 200, 50),
}

ROW_Y_TOL = 16
MONTOS_RX = re.compile(r'^\s*-?\d{1,3}(?:[ ,]?\d{3})*(?:\.\d{2})\s*$')
EXTRACT_AMOUNT_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2}))(?!\d)')

# =========================
# Utilidades
# =========================
def pdf_to_images_bgr(path: str, zoom: float = 2.0) -> list:
    doc = fitz.open(path)
    imgs = []
    for page in doc:
        pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.h, pm.w, pm.n)
        if pm.n == 3:
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        elif pm.n == 1:
            bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        else:
            bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        imgs.append(bgr)
    doc.close()
    return imgs

def x_center(bb):
    return (bb[0][0] + bb[2][0]) / 2.0

def y_center(bb):
    return int((bb[0][1] + bb[2][1]) / 2)

def in_band_center(bb, xs, xe):
    xc = x_center(bb)
    return xs <= xc < xe

def normalize_text(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.upper().strip()

def is_all_caps_raw(s: str) -> bool:
    no_acc = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    has_alpha = any(ch.isalpha() for ch in no_acc)
    if not has_alpha:
        return False
    return all((not ch.isalpha()) or ch == ch.upper() for ch in no_acc)

# -------- Detectar cabeceras (sólo mayúsculas) --------
HEADERS_PATTS = {
    "FECHA":    re.compile(r"^FECHA$"),
    "DESCRIP":  re.compile(r"^(DESCRIPCION|DESCRIPCIÓN|ESTABLECIMIENTO|DESCRIPCION\s*/\s*ESTABLECIMIENTO)$"),
    "DEPOSITO": re.compile(r"^(MONTO\s+DEL\s+DEP[ÓO]SITO|DEP[ÓO]SITO)$"),
    "RETIRO":   re.compile(r"^(MONTO\s+DEL\s+RETIRO|RETIRO)$"),
    "SALDO":    re.compile(r"^SALDO$"),
}
def detect_headers_uppercase(results):
    found = set(); matches = []
    for (bb, txt, _p) in results:
        if not is_all_caps_raw(txt):
            continue
        norm = normalize_text(txt)
        for tag, rx in HEADERS_PATTS.items():
            if rx.search(norm):
                found.add(tag)
                matches.append((bb, tag, txt))
    return found, matches

# -------- Fechas (amplias) --------
RX_FECHA_MES = re.compile(r'\b([0-3]?\d)[\-/\. ]?([A-ZÁ]{3,})[\-/\. ]?(\d{2,4})?\b', re.I)
RX_FECHA_NUM = re.compile(r'\b([0-3]?\d)[/.\-]([01]?\d)(?:[/.\-](\d{2,4}))?\b', re.I)
MESES = {"ENE":"ENE","FEB":"FEB","MAR":"MAR","ABR":"ABR","MAY":"MAY","JUN":"JUN",
         "JUL":"JUL","AGO":"AGO","SEP":"SEP","OCT":"OCT","NOV":"NOV","DIC":"DIC",
         "JAN":"ENE","APR":"ABR","AUG":"AGO","DEC":"DIC"}

# Fechas embebidas en descripción tipo "15-ENE-23" o "15/ENE/23"
RX_FECHA_DMY_IN_DESC = re.compile(r"\b([0-3]?\d)[-/](ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)[-/](\d{2,4})\b", re.I)

def normalize_fecha(raw: str) -> str:
    s = normalize_text(raw).replace(".", " ").replace("-", " ").replace("/", " ")
    s = re.sub(r'\s+', ' ', s).strip()
    m = RX_FECHA_MES.search(s) or RX_FECHA_NUM.search(s)
    if not m:
        return raw.strip()
    dd = int(m.group(1))
    mm = m.group(2)
    yy = m.group(3) or ""
    if mm and isinstance(mm, str) and mm.isalpha():
        mm = MESES.get(mm[:3], mm[:3])
        return f"{dd:02d}/{mm}/{yy[-2:]}" if yy else f"{dd:02d}/{mm}"
    else:
        mm_i = int(mm)
        meses = ["", "ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]
        mm_txt = meses[mm_i] if 0 < mm_i < len(meses) else str(mm_i)
        return f"{dd:02d}/{mm_txt}/{yy[-2:]}" if yy else f"{dd:02d}/{mm_txt}"

def parse_amount_to_float(s):
    if s is None: return np.nan
    m = EXTRACT_AMOUNT_RE.search(str(s))
    if not m:
        digits = ''.join(ch for ch in str(s) if ch.isdigit())
        return float(digits) if digits else np.nan
    token = m.group(1)
    last_dot, last_comma = token.rfind('.'), token.rfind(',')
    try:
        if last_dot != -1 and last_comma != -1:
            return float(token.replace(',', '')) if last_dot > last_comma else float(token.replace('.', '').replace(',', '.'))
        if last_dot != -1:  return float(token)
        if last_comma != -1: return float(token.replace('.', '').replace(',', '.'))
        return float(token)
    except Exception:
        return np.nan

def group_tokens_by_y(tokens, y_tol=ROW_Y_TOL):
    items = [(y_center(bb), min(p[0] for p in bb), bb, txt) for bb, txt in tokens]
    items.sort(key=lambda z: z[0])
    lines, cur, last_y = [], [], None
    for yc, xl, bb, txt in items:
        if last_y is None or abs(yc - last_y) <= y_tol:
            cur.append((xl, bb, txt, yc))
        else:
            lines.append(cur); cur = [(xl, bb, txt, yc)]
        last_y = yc
    if cur: lines.append(cur)
    out = []
    for line in lines:
        line.sort(key=lambda z: z[0])
        yc = int(median([z[3] for z in line]))
        txt = " ".join(z[2] for z in line)
        bbs = [z[1] for z in line]
        out.append((yc, txt, bbs))
    return out

def bbox_union(bboxes):
    xs = [p[0] for bb in bboxes for p in bb]
    ys = [p[1] for bb in bboxes for p in bb]
    return [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]

# -------- Detectar líneas horizontales y bandas de filas --------
def detect_row_bands(img_crop):
    """Devuelve (bands, mask, y_lines) usando líneas horizontales.
       Parámetros RELAJADOS para no perdernos filas."""
    gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
    # binarizar más sensible
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 31, 9)
    h, w = bw.shape
    # kernel horizontal (más corto que antes)
    klen = max(25, w // 10)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (klen, 1))
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=1)
    # consolidar
    horiz = cv2.dilate(horiz, np.ones((1,3), np.uint8), iterations=1)

    cnts, _ = cv2.findContours(horiz, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ys = []
    for c in cnts:
        x, y, ww, hh = cv2.boundingRect(c)
        # más permisivo en ancho, aún exige buena longitud
        if ww >= int(0.45 * w) and 1 <= hh <= 10:
            ys.append(int(y + hh/2))
    # fallback Hough si nada
    if not ys:
        lines = cv2.HoughLinesP(horiz, 1, np.pi/180, threshold=100,
                                minLineLength=int(0.45*w), maxLineGap=10)
        if lines is not None:
            for l in lines:
                x1,y1,x2,y2 = l[0]
                if abs(y1-y2) <= 3:
                    ys.append(int((y1+y2)//2))

    if not ys:
        return [], horiz, []

    ys = sorted(ys)
    # merge líneas cercanas
    merged = []
    cur = [ys[0], ys[0]]
    for v in ys[1:]:
        if v - cur[1] <= 8:
            cur[1] = v
        else:
            merged.append(int((cur[0]+cur[1])//2))
            cur = [v, v]
    merged.append(int((cur[0]+cur[1])//2))

    # construir bandas entre líneas
    bands = []
    # banda superior desde inicio del recorte hasta primera línea (para cabecera/primera fila)
    prev = 0
    for y in merged:
        if y - prev >= 14:
            bands.append((prev, y-1))
        prev = y+1
    # banda final
    if img_crop.shape[0]-prev >= 14:
        bands.append((prev, img_crop.shape[0]-1))

    # filtra bandas muy altas (encabezado) si no hay montos
    return bands, horiz, merged

# =========================
# PREVIEW
# =========================
def draw_preview(img_crop, results, col_ranges, page_num=1, text_limit=40, headers_info=None, lines_img=None, ylines=None, bands=None):
    if not MATPLOTLIB_AVAILABLE:
        print("⚠️ matplotlib no disponible, omitiendo preview visual")
        return
    vis = img_crop.copy()
    h, w = vis.shape[:2]
    # Bandas columnas
    for k,(xs,xe) in col_ranges.items():
        color = COLORS.get(k, COLORS["OTROS"])
        cv2.rectangle(vis, (int(xs),0), (int(xe),h), color, 2)
        cv2.putText(vis, f"{k} [{xs},{xe}]", (int(xs)+4, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    # Tokens
    for (bb, txt, prob) in results:
        tag = "OTROS"
        for k,(xs,xe) in col_ranges.items():
            if in_band_center(bb, xs, xe):
                tag = k
                break
        color = COLORS.get(tag, COLORS["OTROS"])
        pts = np.array([(int(x),int(y)) for x,y in bb], np.int32)
        cv2.polylines(vis, [pts], True, color, 2)
        txt_small = " ".join(str(txt).split())[:text_limit]
        cv2.putText(vis, txt_small, (int(bb[0][0]), max(int(bb[0][1])-5, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    # Cabeceras
    if headers_info:
        for bb, tag, txt in headers_info:
            pts = np.array([(int(x),int(y)) for x,y in bb], np.int32)
            cv2.polylines(vis, [pts], True, COLORS["HEADER"], 2)
            cv2.putText(vis, f"[{tag}]", (int(bb[0][0]), max(int(bb[0][1])-18, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["HEADER"], 2)
    # Líneas horizontales + bandas
    if lines_img is not None:
        mask_rgb = cv2.cvtColor(lines_img, cv2.COLOR_GRAY2BGR)
        mask_rgb = (mask_rgb>0).astype(np.uint8)*np.array(COLORS["LINE"],dtype=np.uint8)
        vis = cv2.addWeighted(vis, 1.0, mask_rgb, 0.35, 0)
    if ylines:
        for y in ylines:
            cv2.line(vis, (0,y), (w,y), COLORS["LINE"], 1)
    if bands:
        for (y0,y1) in bands:
            cv2.rectangle(vis, (0,y0), (w,y1), COLORS["BAND"], 1)

    try:
        plt.figure(figsize=(14, 10))
        plt.title(f"Banorte · Página {page_num} · PREVIEW (bandas tokens, headers, líneas)")
        plt.imshow(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        plt.axis("on")
        plt.show()
    except Exception as e:
        print(f"⚠️ Error en preview visual: {e}")

# =========================
# EXTRACCIÓN con líneas de fila + fallback
# =========================
def extract_page(img_bgr, page_num, col_ranges, reader, save_debug_dir=None):
    img_crop = img_bgr[TOP_CROP: img_bgr.shape[0]-BOTTOM_CROP, :]
    results = reader.readtext(img_crop, detail=1, paragraph=False)

    # Gate por cabeceras EN MAYÚSCULAS
    found, header_matches = detect_headers_uppercase(results)
    if REQUIRE_ALL_HEADERS and len(found) != 5:
        if save_debug_dir:
            save_debug_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(save_debug_dir / f"p{page_num:03d}_IGNORED_crop.png"), img_crop)
        return pd.DataFrame(columns=["FECHA","DESCRIPCION","DEPOSITO","RETIRO","SALDO"])

    # Detectar líneas horizontales -> bandas
    bands, lines_img, ylines = detect_row_bands(img_crop)
    # Si detectó muy pocas bandas, haremos fallback por proyección
    use_fallback = len(bands) <= 5

    # Tokens por columna
    tok = {k: [] for k in col_ranges.keys()}
    for (bb, txt, _p) in results:
        for col,(xs,xe) in col_ranges.items():
            if in_band_center(bb, xs, xe):
                tok[col].append((bb, txt))
                break

    # Helper: agrupar por Y (fallback)
    def amount_rows_by_projection():
        amount_tokens = []
        for col in ("DEPOSITO","RETIRO","SALDO"):
            for (bb, txt) in tok.get(col, []):
                if MONTOS_RX.match(str(txt).replace(" ", "")):
                    amount_tokens.append({"y": y_center(bb), "col": col, "text": txt.strip(), "bbox": bb})
        if not amount_tokens:
            return []

        row_groups, current, last_y = [], [], None
        for d in sorted(amount_tokens, key=lambda r: r["y"]):
            if last_y is None or abs(d["y"] - last_y) < 15:
                current.append(d)
            else:
                row_groups.append(current); current = [d]
            last_y = d["y"]
        if current: row_groups.append(current)

        bands_fallback = []
        for g in row_groups:
            ys = [it["y"] for it in g]
            yc = int(median(ys))
            y0 = yc - 12
            y1 = yc + 12
            bands_fallback.append((max(0,y0), min(img_crop.shape[0]-1,y1)))
        return bands_fallback

    if use_fallback:
        bands = amount_rows_by_projection()

    # Función para tokens dentro de una banda
    def tokens_in_band(pairs, y0, y1):
        return [(bb,txt) for (bb,txt) in pairs if y0 <= y_center(bb) <= y1]

    rows = []
    for (y0, y1) in bands:
        # FECHA (sólo “fecha-like”)
        f_tokens = tokens_in_band(tok.get("FECHA", []), y0, y1)
        f_lines = group_tokens_by_y(f_tokens, y_tol=ROW_Y_TOL)
        fecha_pick = ""
        if f_lines:
            # candidatas que parezcan fecha
            cand = []
            for (yc, t, bbs) in f_lines:
                norm = normalize_text(t)
                if RX_FECHA_MES.search(norm) or RX_FECHA_NUM.search(norm):
                    cand.append((yc, t.strip(), bbs))
            if cand:
                j = min(range(len(cand)), key=lambda i: abs(cand[i][0]-y0))
                fecha_pick = normalize_fecha(cand[j][1])

        # DESCRIP (primera línea en banda)
        d_tokens = tokens_in_band(tok.get("DESCRIP", []), y0, y1)
        d_lines = group_tokens_by_y(d_tokens, y_tol=ROW_Y_TOL)
        d_lines.sort(key=lambda t:t[0])
        descr_pick = d_lines[0][1].strip() if d_lines else ""

        # Montos
        def pick_amount(colname):
            a_tokens = tokens_in_band(tok.get(colname, []), y0, y1)
            a_tokens = [(bb,txt) for (bb,txt) in a_tokens if MONTOS_RX.match(str(txt).replace(" ",""))]
            if not a_tokens:
                return ""
            return max(a_tokens, key=lambda it: len(str(it[1])))[1].strip()

        dep = pick_amount("DEPOSITO")
        ret = pick_amount("RETIRO")
        sal = pick_amount("SALDO")

        if not any([fecha_pick, descr_pick, dep, ret, sal]):
            continue

        rows.append({"FECHA": fecha_pick, "DESCRIPCION": descr_pick,
                     "DEPOSITO": dep, "RETIRO": ret, "SALDO": sal})

    if not rows:
        return pd.DataFrame(columns=["FECHA","DESCRIPCION","DEPOSITO","RETIRO","SALDO"])

    df = pd.DataFrame(rows, columns=["FECHA","DESCRIPCION","DEPOSITO","RETIRO","SALDO"])
    for c in ["DEPOSITO","RETIRO","SALDO"]:
        df[c] = df[c].apply(parse_amount_to_float)

    # Forward-fill de FECHA/DESCRIP si hay montos (misma operación/concepto)
    mask_has_amount = df[["DEPOSITO","RETIRO","SALDO"]].notna().any(axis=1)
    df.loc[mask_has_amount, ["FECHA","DESCRIPCION"]] = (
        df.loc[mask_has_amount, ["FECHA","DESCRIPCION"]]
          .replace(r'^\s*$', np.nan, regex=True)
          .ffill()
    )

    # Limpieza puntual solicitada:
    # 1) Quitar fechas tipo "15-ENE-23" de DESCRIPCION y usarlas como FECHA si falta
    # 2) Asegurar que cada movimiento tenga solo DEPOSITO o RETIRO (no ambos)
    def _clean_row(row):
        desc = row.get("DESCRIPCION", "")
        if isinstance(desc, str) and desc:
            m = RX_FECHA_DMY_IN_DESC.search(desc)
            if m:
                # siempre usar la fecha detectada en la descripción
                try:
                    fecha_norm = normalize_fecha(m.group(0))
                    row["FECHA"] = fecha_norm
                except Exception:
                    pass
                # quitar TODAS las ocurrencias del token de fecha en la descripción
                desc = RX_FECHA_DMY_IN_DESC.sub(" ", desc)
                desc = re.sub(r"\s+", " ", desc).strip(" -,:;")
                row["DESCRIPCION"] = desc

        dep = row.get("DEPOSITO", np.nan)
        ret = row.get("RETIRO", np.nan)
        if pd.notna(dep) and pd.notna(ret):
            # Heurística simple por palabras clave en descripción
            descr_norm = normalize_text(row.get("DESCRIPCION", ""))
            retiro_words = ("CARGO","RETIRO","COMISION","COMISIÓN","IVA","ENVIO","ENVÍO","PAGO","TRANSFERENCIA")
            deposito_words = ("ABONO","DEPOSITO","DEPÓSITO","RECIBIDO","TRASPASO","DEVOLUCION","DEVOLUCIÓN","SPEI RECIBIDO")
            if any(w in descr_norm for w in retiro_words):
                row["DEPOSITO"] = np.nan
            elif any(w in descr_norm for w in deposito_words):
                row["RETIRO"] = np.nan
            else:
                # Si no hay pista, conservar solo el mayor
                try:
                    if float(dep) >= float(ret):
                        row["RETIRO"] = np.nan
                    else:
                        row["DEPOSITO"] = np.nan
                except Exception:
                    # fallback: preferir mantener un solo campo (retiro)
                    row["DEPOSITO"] = np.nan
        return row

    df = df.apply(_clean_row, axis=1)

    # Mantener solo movimientos con exactamente un monto en DEPOSITO o RETIRO
    # Excepción: "SALDO ANTERIOR" se mantiene aunque solo tenga SALDO
    mask_exactly_one = df["DEPOSITO"].notna() ^ df["RETIRO"].notna()
    mask_saldo_anterior = df["DESCRIPCION"].str.contains("SALDO ANTERIOR", case=False, na=False) & df["SALDO"].notna()
    df = df[mask_exactly_one | mask_saldo_anterior].reset_index(drop=True)

    # Guardar overlays si aplica
    if not PREVIEW_ONLY:
        base = Path.cwd()
        dbg_dir = base / "salidas" / "debug_banorte_lines"
        dbg_dir.mkdir(parents=True, exist_ok=True)
        ov = img_crop.copy()
        h, w = ov.shape[:2]
        for k,(xs,xe) in col_ranges.items():
            cv2.rectangle(ov, (int(xs),0), (int(xe),h), COLORS.get(k,(120,120,120)), 2)
        # si veníamos del detector de líneas
        if ylines:
            for y in ylines:
                cv2.line(ov, (0,y), (w,y), COLORS["LINE"], 1)
        for (y0,y1) in bands:
            cv2.rectangle(ov, (0,y0), (w,y1), COLORS["BAND"], 1)
        cv2.imwrite(str(dbg_dir / f"p{page_num:03d}_overlay.png"), ov)

    return df.reset_index(drop=True)

# =========================
# MAIN
# =========================
def process_banorte_pdf(pdf_path_in: str, save_debug: bool = True) -> dict:
    """Wrapper no invasivo: usa el OCR Banorte existente con PDF dinámico y devuelve lista de movimientos estándar.
    No modifica la lógica de extracción.
    """
    try:
        pages = pdf_to_images_bgr(pdf_path_in, zoom=ZOOM)
        reader = easyocr.Reader(['es'], gpu=False)

        base_dir = Path(__file__).parent
        pdf_stem = Path(pdf_path_in).stem
        out_dir = base_dir / "salidas" / f"banorte_{pdf_stem}"
        debug_dir = out_dir / "debug_banorte_lines"
        if save_debug:
            debug_dir.mkdir(parents=True, exist_ok=True)

        dfs = []
        for idx, img_bgr in enumerate(pages, start=1):
            dfp = extract_page(img_bgr, idx, MANUAL_COL_RANGES, reader,
                               save_debug_dir=(debug_dir if save_debug else None))
            if not dfp.empty:
                dfs.append(dfp)

        if dfs:
            df_final = pd.concat(dfs, ignore_index=True)
        else:
            df_final = pd.DataFrame(columns=["FECHA","DESCRIPCION","DEPOSITO","RETIRO","SALDO"])

        movimientos = []
        for _, row in df_final.iterrows():
            fecha = row.get('FECHA', '')
            concepto = row.get('DESCRIPCION', '')
            deposito = row.get('DEPOSITO')
            retiro = row.get('RETIRO')
            saldo = row.get('SALDO')

            cargos = float(retiro) if pd.notna(retiro) else None
            abonos = float(deposito) if pd.notna(deposito) else None
            saldo_out = float(saldo) if pd.notna(saldo) else None

            movimientos.append({
                'fecha': fecha,
                'concepto': concepto,
                'referencia': '',
                'cargos': cargos,
                'abonos': abonos,
                'saldo': saldo_out,
            })

        return {
            'exito': True,
            'mensaje': f"PDF BANORTE procesado: {len(movimientos)} movimientos",
            'total_movimientos': len(movimientos),
            'movimientos': movimientos,
            'archivo_procesado': pdf_path_in
        }
    except Exception as e:
        return {
            'exito': False,
            'mensaje': f'Error procesando PDF Banorte: {e}',
            'total_movimientos': 0,
            'movimientos': [],
            'archivo_procesado': pdf_path_in
        }
