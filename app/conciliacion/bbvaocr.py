from __future__ import annotations
import cv2
import easyocr
import re
import pandas as pd
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path

# =========================
# CONFIG
# =========================
ZOOM = 2.5
SAVE_DEBUG = False                    # guardar PNGs de diagnóstico

# Rangos X (en píxeles) dentro del RECORTE VERTICAL (img_crop)
COLUMNAS = {"CARGOS": (880, 1000), "ABONOS": (1030, 1170), "LIQUIDACI": (1350, 1500)}
TEXT_COLS = {
    "OPER": (0, 115),        # FECHA (OPER)
    "COD_DESC": (210, 860),  # COD. DESCRIPCIÓN (CONCEPTO)
}
ROW_Y_TOL = 16  # tolerancia vertical

# Patrones
MONTOS = re.compile(r'^\d{1,3}(?:[ ,]?\d{3})*(?:\.\d{2})$')
EXTRACT_AMOUNT_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2}))(?!\d)')
# Acepta: ref / referencia; con ., :, -, espacios; máscaras; concatena dígitos
REF_BLOCK_RX = re.compile(r'(?i)\bref(?:erencia)?\b\.?\s*[:\-]?\s*(.+)$')
# Ruido a eliminar solo en CONCEPTO (fantasmas de fecha)
NOISE_CONCEPTO_RX = re.compile(r'\b(?:OSIMAY|O6IMAY)\b', re.I)

COLOR_BAND = {
    "CARGOS": (0, 0, 255), "ABONOS": (255, 255, 0), "LIQUIDACI": (255, 0, 255),
    "OPER": (255, 0, 0), "COD_DESC": (0, 200, 0)
}
COLOR_TOKEN = {
    "CARGOS": (0, 0, 255), "ABONOS": (0, 165, 255), "LIQUIDACI": (255, 0, 255),
    "OPER": (255, 0, 0), "COD_DESC": (0, 255, 255), "OTROS": (140, 140, 140)
}

# =========================
# UTILIDADES
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

reader = easyocr.Reader(['es'], gpu=False)

def parse_amount_to_float(s) -> float:
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

def y_center(bb): return int((bb[0][1] + bb[2][1]) / 2)
def x_left(bb):   return int(min(p[0] for p in bb))
def in_band_center(bb, xs, xe):
    xc = (bb[0][0] + bb[2][0]) / 2.0
    return xs <= xc < xe

def group_tokens_by_y(tokens, y_tol=ROW_Y_TOL):
    items = [(y_center(bb), x_left(bb), bb, txt) for bb, txt in tokens]
    items.sort(key=lambda z: z[0])
    lines, cur, last_y = [], [], None
    for yc, xl, bb, txt in items:
        if last_y is None or abs(yc - last_y) <= y_tol:
            cur.append((xl, txt, bb, yc))
        else:
            lines.append(cur); cur = [(xl, txt, bb, yc)]
        last_y = yc
    if cur: lines.append(cur)
    out = []
    for line in lines:
        line.sort(key=lambda z: z[0])
        yc = int(np.median([z[3] for z in line]))
        txt = " ".join(z[1] for z in line)
        out.append((yc, txt, [z[2] for z in line]))
    return out

def bbox_union(bboxes):
    xs = [p[0] for bb in bboxes for p in bb]
    ys = [p[1] for bb in bboxes for p in bb]
    return [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]

# ---------- Normalización de FECHA (OPER) ----------
MESES_ABBR = "ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC"
RX_DD_MES_SEP   = re.compile(rf'\b([0-3]?\d)[/Iil|\- ]+({MESES_ABBR})\b', re.I)
RX_DD_MES_NOSEP = re.compile(rf'\b([0-3]?\d)({MESES_ABBR})\b', re.I)
RX_DD_MM        = re.compile(r'\b([0-3]?\d)[/Iil|\- ]+([01]?\d)\b')

def normalize_oper_fecha(raw: str) -> str:
    s = raw.upper()
    s = s.replace('I','/').replace('L','/').replace('|','/')
    s = re.sub(r'(?<=\d)O','0', s)
    s = re.sub(r'O(?=\d)','0', s)
    s = re.sub(r'\s+','', s)
    m = RX_DD_MES_SEP.search(s)
    if m:
        d, mon = int(m.group(1)), m.group(2)[:3].upper()
        return f"{d:02d}/{mon}"
    m = RX_DD_MES_NOSEP.search(s)
    if m:
        d, mon = int(m.group(1)), m.group(2)[:3].upper()
        return f"{d:02d}/{mon}"
    m = RX_DD_MM.search(s)
    if m:
        d, mm = int(m.group(1)), int(m.group(2))
        if 1 <= mm <= 12:
            return f"{d:02d}/{mm:02d}"
    return raw.strip()

# ---------- Concepto/Referencia ----------
def extract_ref_from_text_after_ref_block(text: str) -> str:
    """
    Tras 'Ref' concatena TODOS los dígitos en la misma línea.
    'Ref. 0175015509 030' -> '0175015509030'
    'Ref. ******0932'    -> '0932'
    'ref.2039'           -> '2039'
    """
    s = " ".join(str(text).split())
    m = REF_BLOCK_RX.search(s)
    if not m:
        return ""
    tail = m.group(1)
    digits = "".join(ch for ch in tail if ch.isdigit())
    return digits if len(digits) >= 2 else ""

def split_concept_and_ref_from_line(text: str):
    s = " ".join(str(text).split())

    # 1) referencia (concatenada)
    m = REF_BLOCK_RX.search(s)
    ref = ""
    if m:
        tail = m.group(1)
        ref = "".join(ch for ch in tail if ch.isdigit())
        s = s[:m.start()].strip(" -,:;")

    # 2) normalizaciones puntuales del concepto
    s = re.sub(r'\bAAZ\b', 'AA7', s, flags=re.I)      # OCR común AAZ -> AA7
    s = NOISE_CONCEPTO_RX.sub('', s)                  # quita OSIMAY / O6IMAY solo en CONCEPTO
    s = re.sub(r'\s{2,}', ' ', s).strip(" -,:;")      # limpia espacios/puntuación sobrante

    return s, (ref if len(ref) >= 2 else "")

# ---------- Scoring de línea de concepto anclado al monto ----------
KEY_TOKENS = [
    "T20","T17","N06","AA7","AAZ","C02","WO2","SPEI","PAGO","TRANSFEREN","NOMINA",
    "EFECTIVO","PRACTIC","FOLIO","FOLIOS","BNET","BANAMEX","BANORTE","SANTANDER",
    "BAJIO","INBURSA","SCOTIA","SCOTIABANK","DEPOSITO","COBRO","ABONO","CARGO",
    "OSIMAY","O6IMAY"  # se usan para detectar la línea; luego se limpian del concepto
]
KEY_TOKENS_RX = re.compile("|".join(map(re.escape, KEY_TOKENS)), re.I)
MONEY_LIKE_RX = re.compile(r'\d{1,3}(?:[ ,]\d{3})*(?:[.,]\d{2})')

def _char_stats(s: str):
    s2 = "".join(s.split())
    letters = sum(ch.isalpha() for ch in s2)
    digits  = sum(ch.isdigit() for ch in s2)
    return letters, digits, len(s2)

def score_concept_line_for_anchor(y_anchor, line_h_est, txt, bbs, amount_y_tol, amount_hits, xs_band):
    letters, digits, nall = _char_stats(txt)
    has_letters = letters >= 1
    digit_ratio = 0 if nall == 0 else digits / nall
    starts_with_ref   = bool(re.match(r'(?i)^\s*ref', txt))
    starts_with_digit = bool(re.match(r'^\s*\d', txt))
    has_keyword       = bool(KEY_TOKENS_RX.search(txt))
    has_money_like    = bool(MONEY_LIKE_RX.search(txt))

    ub = bbox_union(bbs)
    x_l = ub[0][0]; width = ub[1][0] - ub[0][0]
    y_desc = int((ub[0][1] + ub[2][1]) / 2)

    has_amount_same_line = any(abs(d["y"] - y_desc) <= amount_y_tol for d in amount_hits)

    dy = abs(y_desc - y_anchor)
    score = 0.0
    # cercanía al anchor de monto
    score += max(0.0, 4.0 - dy / max(1.0, line_h_est/2.0))
    # contenido
    score += 2.4 if has_letters else -2.0
    score += -1.2 * max(0.0, digit_ratio - 0.78)  # permisivo
    # señales
    if starts_with_ref:   score -= 2.2
    if starts_with_digit: score -= 0.2
    if has_keyword:       score += 2.6
    if has_money_like:    score += 2.0
    # posición y tamaño
    score += 1.0 - min(max((x_l - xs_band)/140.0, 0.0), 1.0)
    if width < 70: score -= 0.6
    # monto en MISMA FILA
    if has_amount_same_line: score += 4.2
    # bonus si está encima o alineada (preferimos línea superior a la cantidad)
    if y_desc <= y_anchor + int(0.15*line_h_est):
        score += 0.8
    return score

# =========================
# OCR por página (mantenemos montos intactos)
# =========================
def ocr_pagina_unico(img_bgr: np.ndarray, page_num: int, debug_dir: Path | None) -> pd.DataFrame:
    img_crop = img_bgr[90:img_bgr.shape[0]-60, :]
    results = reader.readtext(img_crop, detail=1, paragraph=False)

    # ---------- Montos (intacto) ----------
    amount_hits = []
    for box, txt, _ in results:
        x_min = min(p[0] for p in box)
        for col, (xs, xe) in COLUMNAS.items():
            if xs <= x_min < xe and MONTOS.match(re.sub(r"\s", "", txt)):
                amount_hits.append({"y": min(p[1] for p in box), "col": col, "text": re.sub(r"\s", "", txt), "bbox": box})
                break

    # Agrupo montos por filas y guardo anclas de Y
    row_groups, current, last_y = [], [], None
    for d in sorted(amount_hits, key=lambda r: r["y"]):
        if last_y is None or abs(d["y"] - last_y) < 15:
            current.append(d)
        else:
            row_groups.append(current); current = [d]
        last_y = d["y"]
    if current: row_groups.append(current)

    rows = []
    anchors_y = []
    for g in row_groups:
        row = {}
        for it in g:
            row[it["col"]] = it["text"]
        rows.append(row)
        ys = [int((it["bbox"][0][1] + it["bbox"][2][1]) / 2) for it in g]
        anchors_y.append(int(np.median(ys)) if ys else None)

    df_montos = (pd.DataFrame(rows)
        .rename(columns={"LIQUIDACI": "SALDO"})
        .reindex(columns=["CARGOS","ABONOS","SALDO"])
        .fillna(""))

    # Puerta vertical por montos
    has_any_monto = len(amount_hits) > 0
    if amount_hits:
        y_min_tab = min(min(pt[1] for pt in d["bbox"]) for d in amount_hits)
        y_max_tab = max(max(pt[1] for pt in d["bbox"]) for d in amount_hits)
        y_low_gate = max(0, y_min_tab - 30)
        y_high_gate = y_max_tab + 30
    else:
        y_low_gate, y_high_gate = 0, img_crop.shape[0]

    oper_tokens = [(bb, txt) for (bb, txt, _) in results
                   if in_band_center(bb, *TEXT_COLS["OPER"]) and y_low_gate <= y_center(bb) <= y_high_gate]
    desc_tokens = [(bb, txt) for (bb, txt, _) in results
                   if in_band_center(bb, *TEXT_COLS["COD_DESC"]) and y_low_gate <= y_center(bb) <= y_high_gate]

    oper_lines_all = group_tokens_by_y(oper_tokens, y_tol=ROW_Y_TOL)
    # FECHA: cualquier línea con dígitos; luego normalizo
    oper_lines = [(y, t.strip(), bbs) for (y, t, bbs) in oper_lines_all if re.search(r"\d", t)]
    desc_lines_full = group_tokens_by_y(desc_tokens, y_tol=ROW_Y_TOL)

    if not has_any_monto or not desc_lines_full:
        return pd.DataFrame(columns=["FECHA","CONCEPTO","REFERENCIA","TIPO","MONTO","SALDO"])

    oper_lines.sort(key=lambda z: z[0])
    desc_lines_full.sort(key=lambda z: z[0])

    # Altura de línea y tolerancias
    if len(desc_lines_full) > 1:
        gaps = np.diff([y for (y,_,_) in desc_lines_full])
        line_h = int(np.median(gaps)) if len(gaps) else 22
    else:
        line_h = 22
    AMOUNT_Y_TOL = max(ROW_Y_TOL, int(0.6*line_h))

    # Filtrado de filas inválidas (solo para alinear con anchors; NO afecta montos en salida)
    invalid = ((df_montos["SALDO"].astype(str).str.strip()!="") &
               (df_montos["CARGOS"].astype(str).str.strip()=="") &
               (df_montos["ABONOS"].astype(str).str.strip()==""))
    valid_idx = [i for i in range(len(df_montos)) if not (invalid.iloc[i] if i < len(invalid) else False)]
    anchors_y_valid = [anchors_y[i] for i in valid_idx] if valid_idx else []

    # Prepara ayuda para fecha por ancla: buscamos la última oper <= y_anchor
    oper_y = [y for (y,_,_) in oper_lines]
    def fecha_for_anchor(y_anchor):
        # último oper por encima (o muy cerca)
        prev = [ (y,t) for (y,t,_) in oper_lines if y <= y_anchor + int(0.25*line_h) ]
        if prev:
            y,t = prev[-1]
            return normalize_oper_fecha(t)
        # si no hay por arriba, toma el más cercano
        if oper_lines:
            y,t,_ = min(oper_lines, key=lambda it: abs(it[0]-y_anchor))
            return normalize_oper_fecha(t)
        return ""

    # Índices de desc_lines por Y para cortes rápidos
    desc_Ys = [y for (y,_,_) in desc_lines_full]

    conceptos = []
    for k, y_anchor in enumerate(anchors_y_valid):
        # Ventana alrededor del anchor para buscar 1ª línea de concepto
        win_up    = max(ROW_Y_TOL, int(0.9*line_h))
        win_down  = int(0.35*line_h)
        y0 = y_anchor - win_up
        y1 = y_anchor + win_down

        cand = [ (j,desc_lines_full[j]) for j in range(len(desc_lines_full))
                 if y0 <= desc_lines_full[j][0] <= y1 ]

        # si no hay, ampliamos
        if not cand:
            y0 = y_anchor - 2*line_h
            y1 = y_anchor + int(0.6*line_h)
            cand = [ (j,desc_lines_full[j]) for j in range(len(desc_lines_full))
                     if y0 <= desc_lines_full[j][0] <= y1 ]

        # Scoring por anchor
        best_j, best_score = None, None
        for j,(y_desc, txt, bbs) in cand:
            s = score_concept_line_for_anchor(
                    y_anchor=y_anchor,
                    line_h_est=line_h,
                    txt=txt,
                    bbs=bbs,
                    amount_y_tol=AMOUNT_Y_TOL,
                    amount_hits=amount_hits,
                    xs_band=TEXT_COLS["COD_DESC"][0]
                )
            if (best_score is None) or (s > best_score):
                best_score, best_j = s, j

        if best_j is None:
            # Fallback: coge la línea desc más cercana hacia arriba
            upper = [ (j,desc_lines_full[j]) for j in range(len(desc_lines_full)) if desc_lines_full[j][0] <= y_anchor ]
            if upper:
                best_j = upper[-1][0]
            else:
                # o la 1a por debajo
                best_j = 0

        # Concepto de la línea elegida (limpieza + posible ref en esa línea)
        _, line1, _bbs1 = desc_lines_full[best_j]
        concept_text, ref_inline = split_concept_and_ref_from_line(line1)

        # Busca REF en las siguientes hasta topar con el siguiente anchor
        referencia = ref_inline
        next_anchor = anchors_y_valid[k+1] if (k+1) < len(anchors_y_valid) else None

        MAX_FOLLOW = 3
        follow = 0
        j2 = best_j + 1
        while j2 < len(desc_lines_full) and follow < MAX_FOLLOW:
            y2, txt2, _ = desc_lines_full[j2]
            if next_anchor is not None and y2 >= next_anchor - max(ROW_Y_TOL, int(0.4*line_h)):
                break
            # prioriza línea con 'ref'
            if re.search(r'(?i)\bref', txt2):
                r2 = extract_ref_from_text_after_ref_block(txt2)
                if r2:
                    referencia = r2
            else:
                # fallback: por si partieron la referencia sin 'ref'
                digits = "".join(ch for ch in txt2 if ch.isdigit())
                if len(digits) >= 4 and (len(digits) > len(referencia or "")):
                    referencia = digits
            j2 += 1
            follow += 1

        # FECHA mapeada por anchor
        fecha = fecha_for_anchor(y_anchor)

        conceptos.append((fecha, concept_text, referencia))

    # ---------- TIPO/MONTO/SALDO (NO se toca la lógica) ----------
    if invalid.any():
        df_montos = df_montos[~invalid].reset_index(drop=True)

    cargos = df_montos["CARGOS"].apply(parse_amount_to_float) if "CARGOS" in df_montos else pd.Series([])
    abonos = df_montos["ABONOS"].apply(parse_amount_to_float) if "ABONOS" in df_montos else pd.Series([])
    saldos = df_montos["SALDO"].apply(parse_amount_to_float) if "SALDO" in df_montos else pd.Series([])
    n_rows = max(len(cargos), len(abonos), len(saldos))
    cargos, abonos, saldos = [s.reindex(range(n_rows)) for s in (cargos,abonos,saldos)]

    # Ahora conceptos está alineado 1 a 1 con anchors válidos = n_rows
    df_fc = pd.DataFrame(conceptos, columns=["FECHA","CONCEPTO","REFERENCIA"])
    if len(df_fc) != n_rows:
        # si por algún borde quedaron menos, reindex sin ffill (prefiero vacío a arrastrar)
        df_fc = df_fc.reindex(range(n_rows)).fillna({"FECHA":"", "CONCEPTO":"", "REFERENCIA":""})

    tipos, montos = [], []
    for c, a in zip(cargos.tolist(), abonos.tolist()):
        c_ok, a_ok = not pd.isna(c), not pd.isna(a)
        if c_ok and a_ok: tipos.append("CARGO" if c>=a else "ABONO"); montos.append(max(c,a))
        elif c_ok:        tipos.append("CARGO"); montos.append(c)
        elif a_ok:        tipos.append("ABONO"); montos.append(a)
        else:             tipos.append(""); montos.append(np.nan)
    df_tms = pd.DataFrame({"TIPO": tipos, "MONTO": montos, "SALDO": saldos}).round(2)

    out = pd.concat([df_fc, df_tms], axis=1)

    # Dedup de referencias: vacía duplicadas (no borra filas)
    mask_ref_valid = out["REFERENCIA"].astype(str).str.fullmatch(r"\d{2,}")
    dupe_mask = mask_ref_valid & out.duplicated(subset=["REFERENCIA"], keep="first")
    out.loc[dupe_mask, "REFERENCIA"] = ""

    # Debug (opcional): bandas
    if SAVE_DEBUG and debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
        h, w = img_crop.shape[:2]
        vis = img_crop.copy()
        for k,(xs,xe) in COLUMNAS.items():
            cv2.rectangle(vis, (xs,0), (xe,h), COLOR_BAND[k], 2); cv2.putText(vis, k, (xs+4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_BAND[k], 2)
        for k,(xs,xe) in TEXT_COLS.items():
            cv2.rectangle(vis, (xs,0), (xe,h), COLOR_BAND[k], 2); cv2.putText(vis, k, (xs+4, 40 if k=="COD_DESC" else 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_BAND[k], 2)
        cv2.imwrite(str(debug_dir / f"p{page_num:03d}_anchors_by_row.png"), vis)

    return out.reset_index(drop=True)

# =========================
# WRAPPER PARA INTEGRACIÓN EN FLUJO (NO MODIFICA LÓGICA DE DETECCIÓN)
# =========================
def process_bbva_pdf(pdf_path_in: str, debug_dir: Path | None = None) -> dict:
    """
    Ejecuta el OCR BBVA con el mismo pipeline actual pero aceptando ruta dinámica
    y regresando movimientos en el formato estándar del flujo.
    No modifica la lógica de detección.
    """
    try:
        # Directorios de salida/debug automáticos si no se proporcionan
        base_dir = Path(__file__).parent
        pdf_stem = Path(pdf_path_in).stem
        out_dir = base_dir / "salidas" / pdf_stem
        pages_dir = out_dir / "pages"
        auto_debug_dir = out_dir / "debug"

        # Crear carpetas si SAVE_DEBUG está activo (o si el usuario pasó un debug_dir)
        debug_dir_to_use = debug_dir
        if SAVE_DEBUG:
            pages_dir.mkdir(parents=True, exist_ok=True)
            if debug_dir_to_use is None:
                auto_debug_dir.mkdir(parents=True, exist_ok=True)
                debug_dir_to_use = auto_debug_dir
            else:
                Path(debug_dir_to_use).mkdir(parents=True, exist_ok=True)

        pages = pdf_to_images_bgr(pdf_path_in, zoom=ZOOM)
        dfs = []
        for i, img in enumerate(pages, start=1):
            # Guardar PNG de la página completa si está habilitado el debug
            if SAVE_DEBUG:
                cv2.imwrite(str(pages_dir / f"p{i:03d}.png"), img)

            dfp = ocr_pagina_unico(img, page_num=i, debug_dir=debug_dir_to_use if SAVE_DEBUG else None)
            if not dfp.empty:
                dfs.append(dfp)

        if not dfs:
            return {
                'exito': True,
                'mensaje': 'PDF BBVA procesado: 0 movimientos',
                'total_movimientos': 0,
                'movimientos': [],
                'archivo_procesado': pdf_path_in
            }

        df_final = pd.concat(dfs, ignore_index=True)

        movimientos = []
        for _, row in df_final.iterrows():
            tipo = str(row.get('TIPO', '')).upper() if 'TIPO' in row else ''
            monto = row.get('MONTO') if 'MONTO' in row else None
            cargos = float(monto) if (tipo == 'CARGO' and pd.notna(monto)) else None
            abonos = float(monto) if (tipo == 'ABONO' and pd.notna(monto)) else None
            saldo_val = row.get('SALDO') if 'SALDO' in row else None
            try:
                saldo = float(saldo_val) if pd.notna(saldo_val) else None
            except Exception:
                saldo = None

            movimientos.append({
                'fecha': row.get('FECHA', '') if 'FECHA' in row else '',
                'concepto': row.get('CONCEPTO', '') if 'CONCEPTO' in row else '',
                'referencia': row.get('REFERENCIA', '') if 'REFERENCIA' in row else '',
                'cargos': cargos,
                'abonos': abonos,
                'saldo': saldo,
            })

        return {
            'exito': True,
            'mensaje': f"PDF BBVA procesado: {len(movimientos)} movimientos",
            'total_movimientos': len(movimientos),
            'movimientos': movimientos,
            'archivo_procesado': pdf_path_in
        }
    except Exception as e:
        return {
            'exito': False,
            'mensaje': f'Error procesando PDF BBVA: {e}',
            'total_movimientos': 0,
            'movimientos': [],
            'archivo_procesado': pdf_path_in
        }

# (Sin bloque __main__ para evitar PDF estático; se usa process_bbva_pdf en el flujo)