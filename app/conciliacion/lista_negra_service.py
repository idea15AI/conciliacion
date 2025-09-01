#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio para consultas de Lista Negra SAT
- Alineado 1:1 con el SQL base (CTEs, filtros sargables)
- Corrige MONITOREOS (RFCs únicos) y TOTAL REVISADO (RFCs únicos del periodo)
- Excluye cancelados (cf.fecha_cancelacion IS NULL)
- Parametriza rfc_empresa y rango de fechas
- Fija collation de sesión para evitar divergencias por acentos/espacios
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ListaNegraService:
    """Servicio para consultas de Lista Negra SAT con CTEs optimizados y conteos deduplicados por RFC."""

    def __init__(self, db: Session, enable_debug_sql: bool = False) -> None:
        self.db = db
        self.enable_debug_sql = enable_debug_sql

    # -------- Utilidades --------

    def _ensure_session_collation(self) -> None:
        """Asegura collation consistente en la sesión MySQL."""
        try:
            self.db.execute(text("SET NAMES utf8mb4 COLLATE utf8mb4_general_ci"))
            self.db.execute(text("SET collation_connection = 'utf8mb4_general_ci'"))
        except Exception as e:
            logger.warning(f"[ListaNegra] No se pudo fijar collation de sesión: {e}")

    def _params(self, rfc_empresa: str, fecha_inicio: Optional[str], fecha_fin: Optional[str]) -> Dict[str, str]:
        params: Dict[str, str] = {"rfc_empresa": rfc_empresa}
        if fecha_inicio:
            params["fecha_inicio"] = fecha_inicio
        if fecha_fin:
            params["fecha_fin"] = fecha_fin
        return params

    def _exec(self, query: str, params: Dict[str, object]) -> List[Dict]:
        """Ejecuta SQL con timing y logging; devuelve filas como dicts."""
        t0 = time.perf_counter()
        if self.enable_debug_sql:
            logger.debug(f"[ListaNegra SQL] Params={params}\n{query}")
        result = self.db.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        dt = (time.perf_counter() - t0) * 1000
        logger.info(f"[ListaNegra] Ejecutado en {dt:.1f} ms, filas={len(rows)}")
        return rows

    # -------- Bloque CTE base reusable --------

    def _get_base_cte_query(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> str:
        """
        Genera la consulta base con CTEs reutilizables.
        Filtros sargables + exclusión de cancelados.
        """
        # Filtros condicionales (sargables)
        fecha_ini_cf = "AND cf.fecha >= :fecha_inicio" if fecha_inicio else ""
        fecha_fin_cf = "AND cf.fecha < DATE_ADD(:fecha_fin, INTERVAL 1 DAY)" if fecha_fin else ""
        fecha_ini_cp = "AND cp.fecha_pago_pago >= :fecha_inicio" if fecha_inicio else ""
        fecha_fin_cp = "AND cp.fecha_pago_pago < DATE_ADD(:fecha_fin, INTERVAL 1 DAY)" if fecha_fin else ""

        return f"""
        WITH
        sat_scored AS (
          SELECT
            rfc,
            UPPER(REPLACE(tipo_lista,' ','')) AS tipo_lista_norm,
            UPPER(supuesto) AS supuesto,
            CASE
              WHEN (UPPER(REPLACE(tipo_lista,' ','')) IN ('69B','69') AND UPPER(supuesto) IN ('DEFINITIVO','PRESUNTO')) THEN 3
              WHEN (UPPER(supuesto) IN ('NO LOCALIZADOS','FIRMES','EXIGIBLES','RETORNO INVERSIONES','SENTENCIAS') OR INSTR(UPPER(supuesto),'CANCELADOS POR INSOLVENCIA')>0) THEN 2
              WHEN UPPER(supuesto) IN ('DESVIRTUADO','SENTENCIA FAVORABLE','CONDONACION','CONDONADOS','CONDONADOS ARTÍCULO 74','CANCELADOS','PUBLICADO') THEN 1
              ELSE 1
            END AS risk_score
          FROM lista_negra_sat_oficial
        ),
        sat_uniq AS (
        SELECT
            rfc,
            CASE
            WHEN MIN(risk_score) = 1 THEN 'BAJO'
            WHEN MIN(risk_score) = 2 THEN 'MEDIO'
            ELSE 'ALTO'
            END AS nivel_riesgo
        FROM sat_scored
        GROUP BY rfc
        ),
        datos_unificados AS (
          -- Clientes por I (ventas) PUE/NULL
          SELECT
            cf.rfc_receptor,
            cf.nombre_receptor,
            cf.codigo_postal_receptor,
            cf.id AS cfdi_id,
            cf.total AS monto_real,
            cf.fecha
          FROM comprobantes_fiscales cf
          WHERE cf.rfc_emisor = :rfc_empresa
            AND cf.tipo_comprobante = 'I'
            AND (cf.metodo_pago = 'PUE' OR cf.metodo_pago IS NULL)
            AND cf.estatus_sat = 1
            AND cf.fecha_cancelacion IS NULL
            AND cf.rfc_receptor <> :rfc_empresa
            {fecha_ini_cf}
            {fecha_fin_cf}
          UNION ALL
          -- Clientes por P (pagos cobrados)
          SELECT
            cf.rfc_receptor,
            cf.nombre_receptor,
            cf.codigo_postal_receptor,
            cf.id AS cfdi_id,
            cp.monto_pago AS monto_real,
            cp.fecha_pago_pago AS fecha
          FROM comprobantes_fiscales cf
          JOIN complementos_pago cp ON cp.cfdi_id = cf.id
          WHERE cf.rfc_emisor = :rfc_empresa
            AND cf.tipo_comprobante = 'P'
            AND cf.estatus_sat = 1
            AND cf.fecha_cancelacion IS NULL
            AND cf.rfc_receptor <> :rfc_empresa
            {fecha_ini_cp}
            {fecha_fin_cp}
        ),
        clientes AS (
          SELECT
            du.rfc_receptor AS rfc,
            COALESCE(du.nombre_receptor, 'Sin nombre') AS nombre,
            SUM(du.monto_real) AS monto_total,
            COUNT(DISTINCT du.cfdi_id) AS total_cfdis,
            MAX(du.fecha) AS ultima_operacion,
            MIN(du.fecha) AS primera_operacion,
            GREATEST(1, ROUND(DATEDIFF(MAX(du.fecha), MIN(du.fecha)) / 30.44, 1)) AS meses_activos,
            MAX(du.codigo_postal_receptor) AS codigo_postal,
            CASE
              WHEN LENGTH(du.rfc_receptor) < 13 THEN 'moral'
              WHEN LENGTH(du.rfc_receptor) = 13 THEN 'fisica'
              ELSE 'indefinido'
            END AS tipo_contribuyente
          FROM datos_unificados du
          GROUP BY du.rfc_receptor, COALESCE(du.nombre_receptor,'Sin nombre')
          HAVING SUM(du.monto_real) > 0
        ),
        clientes_ln AS (
          SELECT
            c.*,
            ROUND(c.total_cfdis / NULLIF(c.meses_activos,0), 2) AS frecuencia_mensual,
            (su.rfc IS NOT NULL) AS en_lista_negra,
            su.nivel_riesgo
          FROM clientes c
          LEFT JOIN sat_uniq su ON su.rfc = c.rfc
        ),
        proveedores AS (
          SELECT
            cf.rfc_emisor AS rfc,
            COALESCE(cf.nombre_emisor, 'Sin nombre') AS nombre,
            SUM(cf.total) AS monto_total,
            COUNT(DISTINCT cf.id) AS total_cfdis,
            MAX(cf.fecha) AS ultima_operacion,
            MIN(cf.fecha) AS primera_operacion,
            GREATEST(1, ROUND(DATEDIFF(MAX(cf.fecha), MIN(cf.fecha)) / 30.44, 1)) AS meses_activos,
            MAX(cf.codigo_postal_expedicion) AS codigo_postal,
            CASE
              WHEN LENGTH(cf.rfc_emisor) < 13 THEN 'moral'
              WHEN LENGTH(cf.rfc_emisor) = 13 THEN 'fisica'
              ELSE 'indefinido'
            END AS tipo_contribuyente
          FROM comprobantes_fiscales cf
          WHERE cf.rfc_receptor = :rfc_empresa
            AND cf.tipo_comprobante = 'I'
            AND cf.estatus_sat = 1
            AND cf.fecha_cancelacion IS NULL
            AND cf.rfc_emisor <> :rfc_empresa
            {fecha_ini_cf}
            {fecha_fin_cf}
          GROUP BY cf.rfc_emisor, COALESCE(cf.nombre_emisor,'Sin nombre')
          HAVING SUM(cf.total) > 0
        ),
        proveedores_ln AS (
          SELECT
            p.*,
            ROUND(p.total_cfdis / NULLIF(p.meses_activos,0), 2) AS frecuencia_mensual,
            (su.rfc IS NOT NULL) AS en_lista_negra,
            su.nivel_riesgo
          FROM proveedores p
          LEFT JOIN sat_uniq su ON su.rfc = p.rfc
        )
        """

    # -------- Consultas públicas --------

    def obtener_clientes_lista_negra(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> List[Dict]:
        """Clientes en lista negra (ordenados por monto_total DESC)."""
        try:
            self._ensure_session_collation()
            base_cte = self._get_base_cte_query(rfc_empresa, fecha_inicio, fecha_fin)
            query = f"""
            {base_cte}
            SELECT * FROM clientes_ln
            WHERE en_lista_negra = 1
            ORDER BY monto_total DESC
            """
            return self._exec(query, self._params(rfc_empresa, fecha_inicio, fecha_fin))
        except Exception as e:
            logger.error(f"[ListaNegra] Error obteniendo clientes LN: {e}")
            raise

    def obtener_proveedores_lista_negra(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> List[Dict]:
        """Proveedores en lista negra (ordenados por monto_total DESC)."""
        try:
            self._ensure_session_collation()
            base_cte = self._get_base_cte_query(rfc_empresa, fecha_inicio, fecha_fin)
            query = f"""
            {base_cte}
            SELECT * FROM proveedores_ln
            WHERE en_lista_negra = 1
            ORDER BY monto_total DESC
            """
            return self._exec(query, self._params(rfc_empresa, fecha_inicio, fecha_fin))
        except Exception as e:
            logger.error(f"[ListaNegra] Error obteniendo proveedores LN: {e}")
            raise

    def obtener_kpis_resumen(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> Dict:
        """
        KPIs resumen:
        - total_detectados: RFCs únicos en LN (cliente/proveedor deduplicado)
        - monto_total_en_riesgo: suma por RFC (si está en ambos lados no se duplica)
        - total_contribuyentes_revisados: RFCs únicos vistos en el periodo (I, P y E donde aplica)
        - total_clientes_revisados / total_proveedores_revisados: RFCs únicos por vista
        """
        try:
            self._ensure_session_collation()
            base_cte = self._get_base_cte_query(rfc_empresa, fecha_inicio, fecha_fin)

            fecha_ini_cf = "AND cf.fecha >= :fecha_inicio" if fecha_inicio else ""
            fecha_fin_cf = "AND cf.fecha < DATE_ADD(:fecha_fin, INTERVAL 1 DAY)" if fecha_fin else ""
            fecha_ini_cp = "AND cp.fecha_pago_pago >= :fecha_inicio" if fecha_inicio else ""
            fecha_fin_cp = "AND cp.fecha_pago_pago < DATE_ADD(:fecha_fin, INTERVAL 1 DAY)" if fecha_fin else ""

            query = f"""
            {base_cte},
            detectados AS (
              SELECT DISTINCT rfc FROM (
                SELECT rfc FROM clientes_ln    WHERE en_lista_negra=1
                UNION ALL
                SELECT rfc FROM proveedores_ln WHERE en_lista_negra=1
              ) z
            ),
                         revisados AS (
               SELECT DISTINCT rfc FROM (
                 -- CLIENTES: I emitidas
                 SELECT DISTINCT cf.rfc_receptor AS rfc
                 FROM comprobantes_fiscales cf
                 WHERE cf.rfc_emisor = :rfc_empresa
                   AND cf.estatus_sat = 1
                   AND cf.fecha_cancelacion IS NULL
                   AND cf.tipo_comprobante = 'I'
                   {fecha_ini_cf}
                   {fecha_fin_cf}
                 UNION
                 -- CLIENTES: P (pagos cobrados)
                 SELECT DISTINCT cf.rfc_receptor AS rfc
                 FROM comprobantes_fiscales cf
                 JOIN complementos_pago cp ON cp.cfdi_id = cf.id
                 WHERE cf.rfc_emisor = :rfc_empresa
                   AND cf.estatus_sat = 1
                   AND cf.fecha_cancelacion IS NULL
                   AND cf.tipo_comprobante = 'P'
                   {fecha_ini_cp}
                   {fecha_fin_cp}
               ) u
             ),
             proveedores_revisados AS (
               SELECT DISTINCT cf.rfc_emisor AS rfc
               FROM comprobantes_fiscales cf
               WHERE cf.rfc_receptor = :rfc_empresa
                 AND cf.estatus_sat = 1
                 AND cf.fecha_cancelacion IS NULL
                 AND cf.tipo_comprobante IN ('I','E')
                 {fecha_ini_cf}
                 {fecha_fin_cf}
             ),
            monto_en_riesgo_por_rfc AS (
              SELECT rfc, SUM(monto_total) AS monto_total
              FROM (
                SELECT rfc, monto_total FROM clientes_ln    WHERE en_lista_negra=1
                UNION ALL
                SELECT rfc, monto_total FROM proveedores_ln WHERE en_lista_negra=1
              ) m
              GROUP BY rfc
            )
                         SELECT
               (SELECT COUNT(*) FROM detectados)                                           AS total_detectados,
               (SELECT COALESCE(SUM(monto_total),0) FROM monto_en_riesgo_por_rfc)         AS monto_total_en_riesgo,
               (SELECT COUNT(DISTINCT rfc) FROM clientes_ln) + (SELECT COUNT(DISTINCT rfc) FROM proveedores_ln) AS total_contribuyentes_revisados,
               (SELECT COUNT(DISTINCT rfc) FROM clientes_ln)                              AS total_clientes_revisados,
               (SELECT COUNT(DISTINCT rfc) FROM proveedores_ln)                           AS total_proveedores_revisados
            """
            rows = self._exec(query, self._params(rfc_empresa, fecha_inicio, fecha_fin))
            return rows[0] if rows else {}
        except Exception as e:
            logger.error(f"[ListaNegra] Error obteniendo KPIs resumen: {e}")
            raise

    def obtener_distribucion_riesgo(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> Dict:
        """
        Distribución por nivel de riesgo (conteo), deduplicando por RFC:
        - Conteo: RFCs únicos en LN por nivel
        *Nota*: Los montos se calculan aparte en `obtener_montos_por_nivel_riesgo`.
        """
        try:
            self._ensure_session_collation()
            base_cte = self._get_base_cte_query(rfc_empresa, fecha_inicio, fecha_fin)

            query = f"""
            {base_cte}
            SELECT nivel_riesgo, COUNT(*) AS cantidad
            FROM (
            SELECT nivel_riesgo FROM clientes_ln    WHERE en_lista_negra = 1
            UNION ALL
            SELECT nivel_riesgo FROM proveedores_ln WHERE en_lista_negra = 1
            ) t
            GROUP BY nivel_riesgo
            ORDER BY FIELD(nivel_riesgo, 'ALTO','MEDIO','BAJO')
            """

            rows = self._exec(query, self._params(rfc_empresa, fecha_inicio, fecha_fin))
            conteo = { (r.get("nivel_riesgo") or "BAJO"): int(r.get("cantidad") or 0) for r in rows }

            # Log de depuración amigable
            logger.info(f"[ListaNegra] Distribución de riesgo (conteo): {conteo}")

            # Sólo devolvemos conteos aquí; los montos se obtienen con `obtener_montos_por_nivel_riesgo`
            return {"conteo": conteo}
        except Exception as e:
            logger.error(f"[ListaNegra] Error en distribución de riesgo: {e}")
            raise


    def obtener_montos_por_nivel_riesgo(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> Dict:
        """
        Obtiene montos por nivel de riesgo - versión simplificada
        """
        try:
            # Obtener clientes y proveedores en lista negra
            clientes_ln = self.obtener_clientes_lista_negra(rfc_empresa, fecha_inicio, fecha_fin)
            proveedores_ln = self.obtener_proveedores_lista_negra(rfc_empresa, fecha_inicio, fecha_fin)
            
            # Sumar montos por nivel de riesgo
            montos = {"ALTO": 0.0, "MEDIO": 0.0, "BAJO": 0.0}
            
            # Sumar montos de clientes
            for cliente in clientes_ln:
                nivel = cliente.get("nivel_riesgo", "BAJO")
                monto = float(cliente.get("monto_total", 0) or 0)
                montos[nivel] += monto
            
            # Sumar montos de proveedores
            for proveedor in proveedores_ln:
                nivel = proveedor.get("nivel_riesgo", "BAJO")
                monto = float(proveedor.get("monto_total", 0) or 0)
                montos[nivel] += monto
            
            logger.info(f"[ListaNegra] Montos por nivel: {montos}")
            return montos
            
        except Exception as e:
            logger.error(f"[ListaNegra] Error obteniendo montos por nivel: {e}")
            return {"ALTO": 0.0, "MEDIO": 0.0, "BAJO": 0.0}

    def debug_distribucion_riesgo(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> Dict:
        """
        Función de debug para ver exactamente qué está pasando con la distribución de riesgo
        """
        try:
            self._ensure_session_collation()
            base_cte = self._get_base_cte_query(rfc_empresa, fecha_inicio, fecha_fin)

            # Consulta simple para debug
            query_debug = f"""
            {base_cte}
            SELECT 
              'DEBUG' as tipo,
              su.nivel_riesgo,
              COUNT(*) as cantidad,
              COUNT(DISTINCT d.rfc) as rfc_unicos
            FROM (
              SELECT rfc FROM clientes_ln    WHERE en_lista_negra=1
              UNION ALL
              SELECT rfc FROM proveedores_ln WHERE en_lista_negra=1
            ) d
            LEFT JOIN sat_uniq su ON su.rfc = d.rfc
            WHERE su.rfc IS NOT NULL
            GROUP BY su.nivel_riesgo
            ORDER BY FIELD(su.nivel_riesgo, 'ALTO','MEDIO','BAJO')
            """
            
            rows_debug = self._exec(query_debug, self._params(rfc_empresa, fecha_inicio, fecha_fin))
            
            # También contar totales
            query_total = f"""
            {base_cte}
            SELECT 
              COUNT(*) as total_detectados,
              COUNT(DISTINCT rfc) as total_rfc_unicos
            FROM (
              SELECT rfc FROM clientes_ln    WHERE en_lista_negra=1
              UNION ALL
              SELECT rfc FROM proveedores_ln WHERE en_lista_negra=1
            ) d
            """
            
            row_total = self._exec(query_total, self._params(rfc_empresa, fecha_inicio, fecha_fin))
            
            return {
                "debug_distribucion": rows_debug,
                "totales": row_total[0] if row_total else {},
                "base_cte": base_cte[:200] + "..." if len(base_cte) > 200 else base_cte
            }
            
        except Exception as e:
            logger.error(f"[ListaNegra] Error en debug distribución: {e}")
            raise

    def obtener_agregados_riesgo_fiscal(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> List[Dict]:
        """
        Agregados de riesgo fiscal (IVA/ISR) por nivel ('ALTO','MEDIO','BAJO').
        Se basa en tu SQL original, con cancelados excluidos y parámetros.
        """
        try:
            self._ensure_session_collation()

            fecha_ini_cf = "AND cf.fecha >= :fecha_inicio" if fecha_inicio else ""
            fecha_fin_cf = "AND cf.fecha < DATE_ADD(:fecha_fin, INTERVAL 1 DAY)" if fecha_fin else ""
            fecha_ini_cp = "AND cp.fecha_pago_pago >= :fecha_inicio" if fecha_inicio else ""
            fecha_fin_cp = "AND cp.fecha_pago_pago < DATE_ADD(:fecha_fin, INTERVAL 1 DAY)" if fecha_fin else ""

            query = f"""
            WITH
            sat_scored AS (
              SELECT rfc, UPPER(REPLACE(tipo_lista,' ','')) AS tipo_lista_norm, UPPER(supuesto) AS supuesto,
                     CASE
                       WHEN (UPPER(REPLACE(tipo_lista,' ','')) IN ('69B','69') AND UPPER(supuesto) IN ('DEFINITIVO','PRESUNTO')) THEN 3
                       WHEN (UPPER(supuesto) IN ('NO LOCALIZADOS','FIRMES','EXIGIBLES','RETORNO INVERSIONES','SENTENCIAS') OR INSTR(UPPER(supuesto),'CANCELADOS POR INSOLVENCIA')>0) THEN 2
                       WHEN UPPER(supuesto) IN ('DESVIRTUADO','SENTENCIA FAVORABLE','CONDONACION','CONDONADOS','CONDONADOS ARTÍCULO 74','CANCELADOS','PUBLICADO') THEN 1
                       ELSE 1
                     END AS risk_score
              FROM lista_negra_sat_oficial
            ),
            sat_uniq AS (
              SELECT rfc, CASE WHEN MAX(risk_score)=3 THEN 'ALTO' WHEN MAX(risk_score)=2 THEN 'MEDIO' ELSE 'BAJO' END AS nivel_riesgo
              FROM sat_scored GROUP BY rfc
            ),
            cf_i AS (
              SELECT cf.id, cf.rfc_emisor, cf.tipo_comprobante, cf.subtotal, cf.metodo_pago, su.nivel_riesgo
              FROM comprobantes_fiscales cf
              JOIN sat_uniq su ON su.rfc = cf.rfc_emisor
              WHERE cf.rfc_receptor = :rfc_empresa
                AND cf.estatus_sat = 1
                AND cf.fecha_cancelacion IS NULL
                AND cf.tipo_comprobante = 'I'
                {fecha_ini_cf}
                {fecha_fin_cf}
            ),
            e_agg AS (
              SELECT su.nivel_riesgo, SUM(cf.subtotal) AS subtotal_e, SUM(COALESCE(ti.total_iva_trasladado,0)) AS iva_e
              FROM comprobantes_fiscales cf
              JOIN sat_uniq su ON su.rfc = cf.rfc_emisor
              LEFT JOIN totales_impuestos_comprobantes_fiscales ti ON ti.cfdi_id = cf.id
              WHERE cf.rfc_receptor = :rfc_empresa
                AND cf.estatus_sat = 1
                AND cf.fecha_cancelacion IS NULL
                AND cf.tipo_comprobante = 'E'
                {fecha_ini_cf}
                {fecha_fin_cf}
              GROUP BY su.nivel_riesgo
            ),
            p_base AS (
              SELECT p.id AS cfdi_id_p, p.rfc_emisor, su.nivel_riesgo, cp.monto_pago
              FROM comprobantes_fiscales p
              JOIN complementos_pago cp ON cp.cfdi_id = p.id
              JOIN sat_uniq su ON su.rfc = p.rfc_emisor
              WHERE p.rfc_receptor = :rfc_empresa
                AND p.estatus_sat = 1
                AND p.fecha_cancelacion IS NULL
                AND p.tipo_comprobante = 'P'
                {fecha_ini_cp}
                {fecha_fin_cp}
            ),
            iva_ie AS (
              SELECT c.nivel_riesgo,
                     SUM(CASE WHEN cf.tipo_comprobante='I' AND (cf.metodo_pago='PUE' OR cf.metodo_pago IS NULL)
                              THEN COALESCE(ti.total_iva_trasladado,0) ELSE 0 END) AS iva_ie
              FROM cf_i c
              JOIN comprobantes_fiscales cf ON cf.id = c.id
              LEFT JOIN totales_impuestos_comprobantes_fiscales ti ON ti.cfdi_id = cf.id
              GROUP BY c.nivel_riesgo
            ),
            iva_p AS (
              SELECT pb.nivel_riesgo,
                     SUM(COALESCE(cp.total_impuesto_iva_16_traslados_pago,0)
                       + COALESCE(cp.total_impuesto_iva_8_traslados_pago,0)
                       + COALESCE(cp.total_impuesto_iva_0_traslados_pago,0)) AS iva_p
              FROM p_base pb
              JOIN complementos_pago cp ON cp.cfdi_id = pb.cfdi_id_p
              GROUP BY pb.nivel_riesgo
            ),
            isr_ie AS (
              SELECT c.nivel_riesgo,
                     SUM(CASE WHEN cf.tipo_comprobante='I' AND (cf.metodo_pago='PUE' OR cf.metodo_pago IS NULL)
                              THEN cf.subtotal ELSE 0 END) AS isr_ie
              FROM cf_i c
              JOIN comprobantes_fiscales cf ON cf.id = c.id
              GROUP BY c.nivel_riesgo
            ),
            iva_p_por_nivel AS (SELECT nivel_riesgo, SUM(iva_p) AS iva_p FROM iva_p GROUP BY nivel_riesgo),
            pagos_p_por_nivel AS (SELECT nivel_riesgo, SUM(monto_pago) AS monto_pago FROM p_base GROUP BY nivel_riesgo),
            isr_p AS (
              SELECT COALESCE(pp.nivel_riesgo, ip.nivel_riesgo) AS nivel_riesgo,
                     COALESCE(pp.monto_pago,0) - COALESCE(ip.iva_p,0) AS isr_p
              FROM pagos_p_por_nivel pp
              LEFT JOIN iva_p_por_nivel ip ON ip.nivel_riesgo = pp.nivel_riesgo
              UNION ALL
              SELECT ip.nivel_riesgo, 0 - COALESCE(ip.iva_p,0)
              FROM iva_p_por_nivel ip
              LEFT JOIN pagos_p_por_nivel pp ON pp.nivel_riesgo = ip.nivel_riesgo
              WHERE pp.nivel_riesgo IS NULL
            )
            SELECT
              n.nivel_riesgo,
              COALESCE(ie.iva_ie,0) + COALESCE(p.iva_p,0)   AS iva_riesgo,
              COALESCE(ie2.isr_ie,0) + COALESCE(p2.isr_p,0) AS isr_riesgo,
              COALESCE(e.subtotal_e,0) AS notas_credito_subtotal,
              COALESCE(e.iva_e,0)      AS notas_credito_iva
            FROM (SELECT 'ALTO' AS nivel_riesgo UNION ALL SELECT 'MEDIO' UNION ALL SELECT 'BAJO') n
            LEFT JOIN iva_ie ie  ON ie.nivel_riesgo  = n.nivel_riesgo
            LEFT JOIN iva_p  p   ON p.nivel_riesgo   = n.nivel_riesgo
            LEFT JOIN isr_ie ie2 ON ie2.nivel_riesgo = n.nivel_riesgo
            LEFT JOIN isr_p  p2  ON p2.nivel_riesgo  = n.nivel_riesgo
            LEFT JOIN e_agg  e   ON e.nivel_riesgo   = n.nivel_riesgo
            ORDER BY FIELD(n.nivel_riesgo, 'ALTO','MEDIO','BAJO')
            """
            return self._exec(query, self._params(rfc_empresa, fecha_inicio, fecha_fin))
        except Exception as e:
            logger.error(f"[ListaNegra] Error obteniendo agregados fiscales: {e}")
            raise

    def generar_reporte_completo(
        self,
        rfc_empresa: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> Dict:
        """
        Genera el reporte completo con:
          - KPIs resumen (monitoreos/revisados dedupe)
          - Distribución de riesgo (conteo y montos)
          - Agregados fiscales (IVA/ISR por nivel)
          - Listados de clientes/proveedores en LN
        """
        try:
            logger.info(f"[ListaNegra] Generando reporte completo para {rfc_empresa}")
            clientes_ln = self.obtener_clientes_lista_negra(rfc_empresa, fecha_inicio, fecha_fin)
            proveedores_ln = self.obtener_proveedores_lista_negra(rfc_empresa, fecha_inicio, fecha_fin)
            kpis = self.obtener_kpis_resumen(rfc_empresa, fecha_inicio, fecha_fin)
            distribucion = self.obtener_distribucion_riesgo(rfc_empresa, fecha_inicio, fecha_fin)
            montos_por_nivel = self.obtener_montos_por_nivel_riesgo(rfc_empresa, fecha_inicio, fecha_fin)
            agregados_fiscal = self.obtener_agregados_riesgo_fiscal(rfc_empresa, fecha_inicio, fecha_fin)

            # Combinar conteo y montos
            distribucion_completa = {
                "conteo": distribucion.get("conteo", {}),
                "montos": montos_por_nivel
            }

            return {
                "empresa_rfc": rfc_empresa,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "fecha_generacion": datetime.now().isoformat(),
                "kpis": kpis,
                "distribucion_riesgo": distribucion_completa,
                "agregados_fiscal": agregados_fiscal,
                "clientes_lista_negra": clientes_ln,
                "proveedores_lista_negra": proveedores_ln,
                "resumen": {
                    "total_clientes_ln": len(clientes_ln),
                    "total_proveedores_ln": len(proveedores_ln),
                    "total_detectados": kpis.get("total_detectados", 0),
                    "monto_total_riesgo": kpis.get("monto_total_en_riesgo", 0),
                    "total_revisados": kpis.get("total_contribuyentes_revisados", 0),
                },
            }
        except Exception as e:
            logger.error(f"[ListaNegra] Error generando reporte completo: {e}")
            raise
