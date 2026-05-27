# src/rules/fraud_rules.py
"""Reglas de negocio para detección de posible fraude en siniestros.

Implementa:
- Hard Rules (RF01 - RF07): Generan alertas críticas (Rojo o Amarillo) de manera inmediata.
- Soft Rules: Asignan puntajes ponderados según la rúbrica, acumulando un score de 0 a 100.
"""

from typing import Dict, Tuple, List

# Lista Restrictiva de Proveedores
LISTA_RESTRICTIVA_PROVEEDORES = ["Taller El Chueco", "Taller XYZ", "Clínica Trucha", "Perito Sospechoso"]

def hard_rule_rf01(record) -> Tuple[bool, str]:
    """RF01: Cobertura Pérdida Total por Robo (PTxRB) -> Rojo.
    Dispara si la cobertura es Robo y el estado o la descripción indica pérdida total/robo total.
    """
    cobertura = str(record.get("cobertura", "")).lower()
    desc = str(record.get("descripcion", "")).lower()
    estado = str(record.get("estado", "")).lower()
    
    is_robo = "robo" in cobertura
    is_pt = "robo total" in desc or "pérdida total" in desc or "negativa" in estado or "cierre" in estado
    
    if is_robo and is_pt:
        return True, "rojo"
    return False, ""

def hard_rule_rf02(record) -> Tuple[bool, str]:
    """RF02: Evidencia de Falsificación o Adulteración Documental -> Rojo.
    Dispara si hay documentos marcados como alterados o inconsistentes.
    """
    doc_alterado = int(record.get("documento_alterado", 0))
    if doc_alterado == 1:
        return True, "rojo"
    return False, ""

def hard_rule_rf03(record) -> Tuple[bool, str]:
    """RF03: Coincidencia Exacta con 'Lista Restrictiva' -> Rojo.
    Dispara si el beneficiario o proveedor está en la lista restrictiva.
    """
    beneficiario = str(record.get("beneficiario", ""))
    in_blacklist = any(bad in beneficiario for bad in LISTA_RESTRICTIVA_PROVEEDORES) or int(record.get("proveedor_lista_restrictiva", 0)) == 1
    if in_blacklist:
        return True, "rojo"
    return False, ""

def hard_rule_rf04(record) -> Tuple[bool, str]:
    """RF04: Dinámica del Accidente Físicamente Imposible -> Rojo.
    Dispara si el relato es ilógico o físicamente imposible (ej. volcadura a 10 km/h).
    """
    relato_ilogico = int(record.get("relato_ilogico", 0))
    desc = str(record.get("descripcion", "")).lower()
    if relato_ilogico == 1 or "inconsistente con la velocidad" in desc or "dinámica imposible" in desc:
        return True, "rojo"
    return False, ""

def hard_rule_rf05(record) -> Tuple[bool, str]:
    """RF05: Siniestro Extremo al Borde de Vigencia (< 48 hrs) -> Amarillo.
    Siniestro ocurrido dentro de las primeras 48 horas de la póliza o antes de su vencimiento.
    """
    dias_inicio = float(record.get("dias_desde_inicio_poliza", 999))
    dias_fin = float(record.get("dias_desde_fin_poliza", 999))
    
    if (0 <= dias_inicio <= 2) or (0 <= dias_fin <= 2):
        return True, "amarillo"
    return False, ""

def hard_rule_rf06(record) -> Tuple[bool, str]:
    """RF06: Demora Atípica en Denuncia de Robo (> 4 días) -> Amarillo.
    Aplicable cuando la cobertura es Robo y pasaron más de 4 días en reportarse.
    """
    cobertura = str(record.get("cobertura", "")).lower()
    report_delay = float(record.get("dias_entre_ocurrencia_reporte", 0))
    
    if "robo" in cobertura and report_delay > 4:
        return True, "amarillo"
    return False, ""

def hard_rule_rf07(record) -> Tuple[bool, str]:
    """RF07: Narrativa Idéntica (Clonada) -> Amarillo.
    Dispara si hay una similitud textual exacta o muy alta (>85%) con otra narrativa.
    """
    narrativa_clonada = int(record.get("narrativa_clonada", 0))
    if narrativa_clonada == 1:
        return True, "amarillo"
    return False, ""

# ---------------------------------------------------------------------------
# Soft rules – Puntos de la rúbrica (Máximo 100 puntos en total de soft rules)
# ---------------------------------------------------------------------------

def compute_soft_score(record) -> Tuple[int, List[str]]:
    """Calcula el puntaje de reglas blandas según la rúbrica.
    Devuelve el puntaje acumulado (tope de 100) y la lista de alertas activadas.
    """
    score = 0
    alerts = []
    
    # 1. Reclamo cercano al borde de vigencia
    dias_inicio = float(record.get("dias_desde_inicio_poliza", 999))
    dias_fin = float(record.get("dias_desde_fin_poliza", 999))
    min_dias = min(dias_inicio, dias_fin)
    if min_dias <= 10:
        score += 8
        alerts.append("Vigencia extrema (<= 10 días): 8 pts")
    elif min_dias <= 30:
        score += 4
        alerts.append("Vigencia cercana (11-30 días): 4 pts")
        
    # 2. Demora denuncia por robo (específico de Robo)
    cobertura = str(record.get("cobertura", "")).lower()
    report_delay = float(record.get("dias_entre_ocurrencia_reporte", 0))
    if "robo" in cobertura:
        # Convertimos días a horas aproximadas (1 día = 24h)
        delay_hours = report_delay * 24
        if delay_hours > 48:
            score += 8
            alerts.append("Demora reporte robo > 48h: 8 pts")
        elif 24 <= delay_hours <= 48:
            score += 4
            alerts.append("Demora reporte robo 24-48h: 4 pts")
            
    # 3. Alta frecuencia de reclamos Asegurado (últimos 18 meses)
    freq_asegurado = int(record.get("freq_asegurado_18m", 1))
    if freq_asegurado >= 3:
        score += 8
        alerts.append(f"Alta frecuencia Asegurado (>=3 en 18m): 8 pts")
    elif freq_asegurado == 2:
        score += 4
        alerts.append("Frecuencia Asegurado (2 en 18m): 4 pts")
        
    # 4. Alta frecuencia de reclamos Vehículo (últimos 18 meses)
    freq_vehiculo = int(record.get("freq_vehiculo_18m", 1))
    if freq_vehiculo >= 3:
        score += 6
        alerts.append("Alta frecuencia Vehículo (>=3 en 18m): 6 pts")
    elif freq_vehiculo == 2:
        score += 3
        alerts.append("Frecuencia Vehículo (2 en 18m): 3 pts")
        
    # 5. Alta frecuencia de conductor (frecuencia del conductor del siniestro)
    freq_conductor = int(record.get("freq_conductor_18m", 1))
    if freq_conductor >= 3:
        score += 8
        alerts.append("Alta frecuencia Conductor (>=3 en 18m): 8 pts")
    elif freq_conductor == 2:
        score += 4
        alerts.append("Frecuencia Conductor (2 en 18m): 4 pts")
        
    # 6. Alta frecuencia reclamos solo Responsabilidad Civil (RC)
    freq_rc = int(record.get("freq_solo_rc_previos", 0))
    if freq_rc > 2:
        score += 6
        alerts.append("Frecuencia RC previa > 2 eventos: 6 pts")
    elif freq_rc == 1:
        score += 3
        alerts.append("Frecuencia RC previa: 1 evento: 3 pts")
        
    # 7. Beneficiario recurrente / Proveedor
    proveedor_restrictivo = int(record.get("proveedor_lista_restrictiva", 0))
    proveedor_casos_anio = int(record.get("proveedor_casos_observados_anio", 0))
    if proveedor_restrictivo == 1:
        score += 10
        alerts.append("Proveedor en Lista Restrictiva: 10 pts")
    elif proveedor_casos_anio >= 2:
        score += 5
        alerts.append("Proveedor con >=2 casos observados este año: 5 pts")
        
    # 8. Documentos incompletos
    doc_incompletos = record.get("documentos_completos", "Sí")
    if doc_incompletos == "No" or int(record.get("falta_documento_obligatorio", 0)) == 1:
        score += 4
        alerts.append("Falta de documento legal obligatorio: 4 pts")
        
    # 9. Dinámica sospechosa
    relato_ilogico = int(record.get("relato_ilogico", 0))
    madrugada = int(record.get("accidente_madrugada", 0))
    if relato_ilogico == 1:
        score += 6
        alerts.append("Relato ilógico vs Tipo de impacto: 6 pts")
    if madrugada == 1:
        score += 3
        alerts.append("Accidente múltiple o severo de madrugada: 3 pts")
        
    # 10. Eventos sin tercero identificado
    sin_tercero = int(record.get("tercero_huye_sin_camaras", 0))
    if sin_tercero == 1:
        score += 5
        alerts.append("Daño severo sin tercero ni cámaras: 5 pts")
        
    # 11. Documentos inconsistentes
    doc_alterado = int(record.get("documento_alterado", 0))
    if doc_alterado == 1:
        score += 10
        alerts.append("Alteración documental o facturas previas: 10 pts")
        
    # 12. Reporte tardío (general)
    report_delay_all = float(record.get("dias_entre_ocurrencia_reporte", 0))
    if report_delay_all > 7:
        score += 5
        alerts.append(f"Reporte muy tardío (>7 días): {report_delay_all} días: 5 pts")
    elif 4 <= report_delay_all <= 7:
        score += 3
        alerts.append(f"Reporte tardío (4-7 días): {report_delay_all} días: 3 pts")
        
    # 13. Narrativas similares
    similitud = float(record.get("narrativa_similitud_score", 0.0))
    if similitud >= 0.85:
        score += 8
        alerts.append(f"Similitud de narrativa >85% con otro caso: {similitud:.0%}: 8 pts")
    elif 0.70 <= similitud < 0.85:
        score += 4
        alerts.append(f"Similitud de narrativa 70%-84% con otro caso: {similitud:.0%}: 4 pts")
        
    # 14. Monto cercano o superior a suma asegurada
    monto_cercano = int(record.get("monto_cercano_suma_asegurada", 0))
    if monto_cercano == 1:
        score += 4
        alerts.append("Monto reclamado >=95% de suma asegurada o 50% de prom. reparación: 4 pts")
        
    return min(score, 100), alerts

# ---------------------------------------------------------------------------
# Public evaluation function
# ---------------------------------------------------------------------------
def evaluate_record(record) -> Dict:
    """Evalúa un siniestro aplicando tanto las reglas duras como las reglas blandas.
    Devuelve un diccionario estructurado con los flags de reglas activas y el color del semáforo.
    """
    # Convertir pandas Series a Dict si es necesario
    if hasattr(record, "to_dict"):
        rec_dict = record.to_dict()
    else:
        rec_dict = dict(record)
        
    # Check hard rules
    hard_triggered = []
    hard_color = ""
    
    rules = [
        ("RF01", hard_rule_rf01),
        ("RF02", hard_rule_rf02),
        ("RF03", hard_rule_rf03),
        ("RF04", hard_rule_rf04),
        ("RF05", hard_rule_rf05),
        ("RF06", hard_rule_rf06),
        ("RF07", hard_rule_rf07)
    ]
    
    for code, rule_fn in rules:
        triggered, color = rule_fn(rec_dict)
        if triggered:
            hard_triggered.append(code)
            # Rojo toma precedencia sobre Amarillo
            if color == "rojo" or not hard_color:
                hard_color = color
                
    # Compute soft score
    soft_score, soft_alerts = compute_soft_score(rec_dict)
    
    # Determinar color final
    # Si hay regla dura, esa dicta el color (RF01-RF04 -> Rojo, RF05-RF07 -> Amarillo)
    # Si no, se calcula por el puntaje acumulado
    if hard_triggered:
        final_color = hard_color
        # Damos un score representativo alto para reglas duras si es rojo/amarillo
        final_score = max(soft_score, 80 if final_color == "rojo" else 50)
    else:
        final_score = soft_score
        if final_score <= 40:
            final_color = "verde"
        elif final_score <= 75:
            final_color = "amarillo"
        else:
            final_color = "rojo"
            
    return {
        "id_siniestro": rec_dict.get("id_siniestro"),
        "hard_flag": len(hard_triggered) > 0,
        "hard_triggered": hard_triggered,
        "soft_score": soft_score,
        "soft_alerts": soft_alerts,
        "final_score": final_score,
        "final_color": final_color
    }
