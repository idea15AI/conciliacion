# extractor_bajio_full.py
# -*- coding: utf-8 -*-

import re
import cv2
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import unicodedata
from pathlib import Path
from statistics import median
import easyocr

# Configuración
ZOOM = 2.6

TOP_CROP = 150
BOTTOM_CROP = 80

# RANGOS DE COLUMNAS (x_ini, x_fin) tras el recorte
COLS = {
    "FECHA":     (   0,  130),
    "NOREF":     ( 130,  220),
    "DESCRIP":   ( 220,  900),
    "DEPOSITOS": ( 900, 1150),
    "RETIROS":   (1150, 1350),
    "SALDO":     (1350, 1550),
}

# Tolerancias para la extracción
Y_MERGE_TOL     = 18   # fusionar anclas cercanas
Y_PICK_TOL      = 26   # elegir token más cercano al ancla
Y_DESC_ATTACH   = 60   # adjuntar detalle adicional
ROW_VALIDATE_NEED_SALDO = False

# Regex y normalizadores
MONTOS_RX = re.compile(r'^\s*\(?-?\s*\$?\s*\d{1,3}(?:[ \u00A0\.,]?\d{3})*(?:[\.,]\d{2})\)?\s*$')
EXTRACT_AMOUNT_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2}))(?!\d)')
RX_FECHA_NUM = re.compile(r'\b([0-3]?\d)[/.\-]([01]?\d)(?:[/.\-](\d{2,4}))?\b', re.I)
RX_FECHA_MES = re.compile(r'\b([0-3]?\d)[\-/\. ]?([A-ZÁ]{3,})[\-/\. ]?(\d{2,4})?\b', re.I)
RX_FECHA_DMY_IN_DESC = re.compile(r"\b([0-3]?\d)[-/](ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)[-/](\d{2,4})\b", re.I)
MESES = {"ENE":"ENE","FEB":"FEB","MAR":"MAR","ABR":"ABR","MAY":"MAY","JUN":"JUN",
         "JUL":"JUL","AGO":"AGO","SEP":"SEP","OCT":"OCT","NOV":"NOV","DIC":"DIC",
         "JAN":"ENE","APR":"ABR","AUG":"AGO","DEC":"DIC"}

KEYWORDS_PUENTE = re.compile(r"CONTINUA EN LA SIGUIENTE PAGINA|ESTADO DE CUENTA", re.I)

def normalize_text(s: str) -> str:
    if not isinstance(s, str): return ""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()

def normalize_text_upper(s: str) -> str:
    return normalize_text(s).upper()

def normalize_fecha(raw: str) -> str:
    s = normalize_text_upper(raw).replace(".", " ").replace("-", " ").replace("/", " ")
    s = re.sub(r'\s+', ' ', s).strip()
    m = RX_FECHA_MES.search(s) or RX_FECHA_NUM.search(s)
    if not m: return raw.strip()
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

# Core helpers sirven para todas las extracciones
def pdf_to_images_bgr(path: str, zoom: float = 2.0):
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

def x_center(bb): return (bb[0][0] + bb[2][0]) / 2.0
def y_center(bb): return int((bb[0][1] + bb[2][1]) / 2)
def in_xband(bb, xs, xe): return xs <= x_center(bb) < xe

def tokens_by_col(results, cols):
    out = {k: [] for k in cols.keys()}
    for (bb, txt, _p) in results:
        for col,(xs,xe) in cols.items():
            if in_xband(bb, xs, xe):
                out[col].append((bb, str(txt)))
                break
    return out

def cluster_ys(y_values, tol):
    if not y_values: return []
    y_values = sorted(y_values)
    clusters, cur = [], [y_values[0]]
    for y in y_values[1:]:
        if abs(y - cur[-1]) <= tol:
            cur.append(y)
        else:
            clusters.append(int(median(cur)))
            cur = [y]
    clusters.append(int(median(cur)))
    return clusters

def pick_nearest(token_list, y0, tol):
    if not token_list: return None
    best, bestd = None, 10**9
    for (bb, txt) in token_list:
        yc = y_center(bb)
        d = abs(yc - y0)
        if d <= tol and d < bestd:
            best = (bb, txt)
            bestd = d
    return best

# Corrección: mover NO.REF del inicio de la descripción (si está)
LEADING_REF_RX = re.compile(r'^\s*(\d{6,})\b[\s\-:]*', re.U)

def _norm_ref(s: str) -> str:
    s = re.sub(r'\D', '', str(s or ''))
    return s if (len(s) >= 5 and s.lstrip('0') != '') else ""

def move_ref_from_desc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["NO.REF"] = df["NO.REF"].apply(_norm_ref)

    def fix_row(row):
        desc_up = normalize_text_upper(row.get("DESCRIPCION DE LA OPERACION", "") or "")
        # No tocar SALDO INICIAL
        if "SALDO INICIAL" in desc_up:
            return row

        desc = str(row.get("DESCRIPCION DE LA OPERACION", "") or "").strip()
        ref  = _norm_ref(row.get("NO.REF", ""))

        if not ref:
            m = LEADING_REF_RX.match(desc)  # sólo si está AL INICIO
            if m:
                ref = m.group(1)
                row["NO.REF"] = ref
                new_desc = desc[m.end():].lstrip()
                new_desc = re.sub(rf'\b{re.escape(ref)}\b', ' ', new_desc)  # borra repeticiones exactas
                new_desc = re.sub(r'\s{2,}', ' ', new_desc).strip(" ·-,:;")
                row["DESCRIPCION DE LA OPERACION"] = new_desc

        return row

    return df.apply(fix_row, axis=1)

# =========================
# Extraction
# =========================
def extract_page(img_bgr, page_idx, reader):
    crop = img_bgr[TOP_CROP: img_bgr.shape[0]-BOTTOM_CROP, :]
    results = reader.readtext(crop, detail=1, paragraph=False)

    # Organiza por columnas
    coltok = tokens_by_col(results, COLS)

    # Anclas: cualquier monto en DEPOSITOS/RETIROS/SALDO
    anchors_y = []
    for col in ("DEPOSITOS", "RETIROS", "SALDO"):
        for (bb, txt) in coltok[col]:
            s = txt.replace(" ", "")
            if MONTOS_RX.match(s):
                anchors_y.append(y_center(bb))

    if not anchors_y:
        return pd.DataFrame(columns=["FECHA","NO.REF","DESCRIPCION DE LA OPERACION","DEPOSITOS","RETIROS","SALDO"])

    row_ys = cluster_ys(anchors_y, Y_MERGE_TOL)

    rows = []
    used_descr_idxs = set()
    descr_tokens = list(enumerate(coltok["DESCRIP"]))

    last_fecha_seen = ""
    for y0 in row_ys:
        dep_t = pick_nearest(coltok["DEPOSITOS"], y0, Y_PICK_TOL)
        ret_t = pick_nearest(coltok["RETIROS"],   y0, Y_PICK_TOL)
        sal_t = pick_nearest(coltok["SALDO"],     y0, Y_PICK_TOL)

        dep = dep_t[1].strip() if dep_t else ""
        ret = ret_t[1].strip() if ret_t else ""
        sal = sal_t[1].strip() if sal_t else ""
        if not (dep or ret or sal): continue

        if sal_t: y_anchor = y_center(sal_t[0])
        elif dep_t and ret_t: y_anchor = int(median([y_center(dep_t[0]), y_center(ret_t[0])]))
        elif dep_t: y_anchor = y_center(dep_t[0])
        elif ret_t: y_anchor = y_center(ret_t[0])
        else: y_anchor = y0

        # FECHA
        fecha_pick = ""
        cand_fechas = []
        for (bb, txt) in coltok["FECHA"]:
            yc = y_center(bb)
            if abs(yc - y_anchor) <= max(Y_PICK_TOL, 28):
                n = normalize_text_upper(txt)
                if RX_FECHA_MES.search(n) or RX_FECHA_NUM.search(n) or re.search(r'\b(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\b', n):
                    cand_fechas.append((abs(yc - y_anchor), txt))
        if cand_fechas:
            cand_fechas.sort(key=lambda t: t[0])
            fecha_pick = normalize_fecha(cand_fechas[0][1])
            last_fecha_seen = fecha_pick
        else:
            fecha_pick = last_fecha_seen

        # NO.REF cercano
        noref_pick = ""
        cand_ref = []
        for (bb, txt) in coltok["NOREF"]:
            yc = y_center(bb)
            if abs(yc - y_anchor) <= max(Y_PICK_TOL, 28):
                cand_ref.append((abs(yc - y_anchor), txt))
        if cand_ref:
            cand_ref.sort(key=lambda t: t[0])
            raw = cand_ref[0][1]
            raw = raw.replace("O","0").replace("o","0")
            noref_pick = ''.join(ch for ch in raw if ch.isdigit())

        # DESCRIP principal + detalle cercano
        descr_pick = ""
        dists = []
        for idx,(bb, txt) in descr_tokens:
            yc = y_center(bb)
            d = abs(yc - y_anchor)
            if d <= Y_PICK_TOL:
                dists.append((d, idx, txt))
        if dists:
            dists.sort(key=lambda t: t[0])
            descr_pick = normalize_text(dists[0][2])
            used_descr_idxs.add(dists[0][1])

        more = []
        for idx,(bb, txt) in descr_tokens:
            if idx in used_descr_idxs: 
                continue
            yc = y_center(bb)
            d = abs(yc - y_anchor)
            if d <= Y_DESC_ATTACH:
                tnorm = normalize_text(txt)
                if KEYWORDS_PUENTE.search(tnorm):  # evita cabeceras
                    continue
                if re.fullmatch(r'[\s\-\.,0-9]+', tnorm or ""):
                    continue
                if tnorm and tnorm != descr_pick:
                    more.append(tnorm)
                    used_descr_idxs.add(idx)
        if more:
            descr_pick = (descr_pick + " · " + " · ".join(more)).strip(" ·")

        rows.append({
            "FECHA": fecha_pick,
            "NO.REF": noref_pick,
            "DESCRIPCION DE LA OPERACION": descr_pick,
            "DEPOSITOS": dep,
            "RETIROS": ret,
            "SALDO": sal,
        })

    # ---- DataFrame y limpiezas ----
    if not rows:
        return pd.DataFrame(columns=["FECHA","NO.REF","DESCRIPCION DE LA OPERACION","DEPOSITOS","RETIROS","SALDO"])

    df = pd.DataFrame(rows, columns=["FECHA","NO.REF","DESCRIPCION DE LA OPERACION","DEPOSITOS","RETIROS","SALDO"])

    # Normaliza importes
    for c in ["DEPOSITOS","RETIROS","SALDO"]:
        df[c] = df[c].apply(parse_amount_to_float)

    # Mueve fechas incrustadas en descripción
    def pull_date_from_desc(row):
        desc = row.get("DESCRIPCION DE LA OPERACION", "")
        if isinstance(desc, str) and desc:
            m = RX_FECHA_DMY_IN_DESC.search(desc)
            if m and not row.get("FECHA"):
                try:
                    row["FECHA"] = normalize_fecha(m.group(0))
                except Exception:
                    pass
                desc = RX_FECHA_DMY_IN_DESC.sub(" ", desc)
                row["DESCRIPCION DE LA OPERACION"] = re.sub(r"\s+", " ", desc).strip(" -,:;")
        return row
    df = df.apply(pull_date_from_desc, axis=1)

    # Forward-fill de FECHA cuando haya importes
    mask_amt = df[["DEPOSITOS","RETIROS","SALDO"]].notna().any(axis=1)
    df.loc[mask_amt, "FECHA"] = (
        df.loc[mask_amt, "FECHA"].replace(r'^\s*$', np.nan, regex=True).ffill()
    )

    # Exclusividad DEP vs RET
    def enforce_one_amount(row):
        dep, ret = row["DEPOSITOS"], row["RETIROS"]
        if pd.notna(dep) and pd.notna(ret):
            desc = normalize_text_upper(row.get("DESCRIPCION DE LA OPERACION", ""))
            if any(w in desc for w in ("CARGO","RETIRO","COMISION","COMISIÓN","IVA","ENVIO","ENVÍO","PAGO","TRANSFERENCIA")):
                row["DEPOSITOS"] = np.nan
            elif any(w in desc for w in ("ABONO","DEPOSITO","DEPÓSITO","RECIBIDO","TRASPASO","DEVOLUCION","DEVOLUCIÓN","SPEI RECIBIDO")):
                row["RETIROS"] = np.nan
            else:
                try:
                    if float(dep) >= float(ret): row["RETIROS"] = np.nan
                    else:                         row["DEPOSITOS"] = np.nan
                except Exception:
                    row["DEPOSITOS"] = np.nan
        return row
    df = df.apply(enforce_one_amount, axis=1)

    # === NUEVO: mover NO.REF del inicio de la descripción ===
    df = move_ref_from_desc(df)

    # Limpiar NO.REF final
    def clean_ref(s):
        if not s: return ""
        s = str(s).replace("O","0").replace("o","0")
        return ''.join(ch for ch in s if ch.isdigit())
    df["NO.REF"] = df["NO.REF"].apply(clean_ref)

    # (Opcional) ffill prudente de NO.REF dentro del mismo día
    df["NO.REF"] = df["NO.REF"].replace("", np.nan)
    df["NO.REF"] = df.groupby(df["FECHA"].ffill())["NO.REF"].ffill()
    df["NO.REF"] = df["NO.REF"].fillna("")

    # Quita puentes/cabeceras
    df = df[~df["DESCRIPCION DE LA OPERACION"].astype(str).str.contains(KEYWORDS_PUENTE)].reset_index(drop=True)

    # Validación mínima
    valid = []
    for _, r in df.iterrows():
        desc = normalize_text_upper(r.get("DESCRIPCION DE LA OPERACION",""))
        is_saldo_inicial = "SALDO INICIAL" in desc
        fecha_ok  = isinstance(r["FECHA"], str) and r["FECHA"].strip() != ""
        one_amt   = (pd.notna(r["DEPOSITOS"]) ^ pd.notna(r["RETIROS"]))
        saldo_ok  = pd.notna(r["SALDO"]) or (not ROW_VALIDATE_NEED_SALDO)

        if is_saldo_inicial:
            if pd.notna(r["SALDO"]): valid.append(r)
        else:
            if fecha_ok and (one_amt or pd.notna(r["SALDO"])) and saldo_ok:
                valid.append(r)
    df = pd.DataFrame(valid, columns=df.columns)

    # Inferencia de saldo por continuidad
    def infer_saldos(df_in):
        df_in = df_in.copy()
        prev = np.nan
        for i, r in df_in.iterrows():
            sal, dep, ret = r["SALDO"], r["DEPOSITOS"], r["RETIROS"]
            if pd.notna(sal):
                prev = sal; continue
            if pd.notna(prev):
                try:
                    if pd.notna(dep): sal = prev + float(dep)
                    elif pd.notna(ret): sal = prev - float(ret)
                    else: sal = prev
                    df_in.at[i, "SALDO"] = sal
                    prev = sal
                except Exception:
                    pass
        return df_in
    df = infer_saldos(df)

    return df.reset_index(drop=True)

# =========================
# MAIN
# =========================
def process_bajio_pdf(pdf_path_in: str, save_debug: bool = False) -> dict:
    """
    Procesa un PDF BAJÍO usando el OCR local y devuelve movimientos en formato estándar.
    Retorna dict con claves: exito, mensaje, total_movimientos, movimientos, archivo_procesado.
    """
    try:
        # Preparar salida/debug opcional
        base_dir = Path(__file__).parent
        pdf_stem = Path(pdf_path_in).stem
        out_dir = base_dir / "salidas" / f"bajio_{pdf_stem}"
        if save_debug:
            out_dir.mkdir(parents=True, exist_ok=True)

        pages = pdf_to_images_bgr(pdf_path_in, zoom=ZOOM)
        reader = easyocr.Reader(['es'], gpu=False)

        all_rows = []
        for i, img in enumerate(pages, start=1):
            if save_debug:
                # Guardar overlay simple de columnas para inspección
                crop = img[TOP_CROP: img.shape[0]-BOTTOM_CROP, :]
                ov = crop.copy()
                h, _w = ov.shape[:2]
                colors = {
                    "FECHA": (255,0,0), "NOREF": (0,255,255), "DESCRIP": (0,200,0),
                    "DEPOSITOS": (0,0,255), "RETIROS": (0,165,255), "SALDO": (255,0,255)
                }
                for k,(xs,xe) in COLS.items():
                    cv2.line(ov, (int(xs),0), (int(xs),h), colors[k], 1)
                    cv2.line(ov, (int(xe),0), (int(xe),h), colors[k], 1)
                cv2.imwrite(str(out_dir / f"p{i:03d}_cols_overlay.png"), ov)

            dfp = extract_page(img, i, reader)
            if not dfp.empty:
                dfp["PAGINA"] = i
                all_rows.append(dfp)

        if all_rows:
            df = pd.concat(all_rows, ignore_index=True)
        else:
            df = pd.DataFrame(columns=["FECHA","NO.REF","DESCRIPCION DE LA OPERACION","DEPOSITOS","RETIROS","SALDO","PAGINA"])

        df = df.reset_index(drop=True)

        # Mapear DataFrame a formato estándar de movimientos
        movimientos = []
        for _, row in df.iterrows():
            fecha = row.get("FECHA", "")
            concepto = row.get("DESCRIPCION DE LA OPERACION", "")
            referencia = row.get("NO.REF", "")
            dep = row.get("DEPOSITOS")
            ret = row.get("RETIROS")
            sal = row.get("SALDO")
            try:
                cargos = float(ret) if pd.notna(ret) else None
            except Exception:
                cargos = None
            try:
                abonos = float(dep) if pd.notna(dep) else None
            except Exception:
                abonos = None
            try:
                saldo = float(sal) if pd.notna(sal) else None
            except Exception:
                saldo = None

            movimientos.append({
                'fecha': fecha,
                'concepto': concepto,
                'referencia': str(referencia) if referencia is not None else '',
                'cargos': cargos,
                'abonos': abonos,
                'saldo': saldo,
            })

        return {
            'exito': True,
            'mensaje': f"PDF BAJIO procesado: {len(movimientos)} movimientos",
            'total_movimientos': len(movimientos),
            'movimientos': movimientos,
            'archivo_procesado': pdf_path_in
        }
    except Exception as e:
        return {
            'exito': False,
            'mensaje': f'Error procesando PDF Bajío: {e}',
            'total_movimientos': 0,
            'movimientos': [],
            'archivo_procesado': pdf_path_in
        }

# (Sin bloque __main__ ni PDF_PATH estático; usar process_bajio_pdf en el flujo)
