# tests/test_rules.py
"""Unit tests for the business rules engine.

Tests all hard rules (RF01-RF07) and soft rule point calculations.
"""

import unittest
from src.rules.fraud_rules import (
    evaluate_record,
    hard_rule_rf01,
    hard_rule_rf02,
    hard_rule_rf03,
    hard_rule_rf04,
    hard_rule_rf05,
    hard_rule_rf06,
    hard_rule_rf07,
    compute_soft_score
)

class TestFraudRules(unittest.TestCase):

    def setUp(self):
        # Base record with normal values (no rules triggered)
        self.base_record = {
            "id_siniestro": 1,
            "id_poliza": "POL-12345",
            "id_asegurado": "ASEG-100",
            "ramo": "Vehículos",
            "cobertura": "Choque",
            "fecha_ocurrencia": "2025-01-15",
            "fecha_reporte": "2025-01-16",
            "monto_reclamado": 1500.0,
            "monto_estimado": 1300.0,
            "estado": "Liquidado",
            "sucursal": "Loja",
            "descripcion": "Un choque por alcance menor en semáforo.",
            "documentos_completos": "Sí",
            "beneficiario": "Taller Autorizado",
            "dias_desde_inicio_poliza": 50,
            "dias_desde_fin_poliza": 315,
            "dias_entre_ocurrencia_reporte": 1,
            "freq_asegurado_18m": 1,
            "freq_vehiculo_18m": 1,
            "freq_conductor_18m": 1,
            "freq_solo_rc_previos": 0,
            "proveedor_lista_restrictiva": 0,
            "proveedor_casos_observados_anio": 1,
            "documento_alterado": 0,
            "falta_documento_obligatorio": 0,
            "relato_ilogico": 0,
            "accidente_madrugada": 0,
            "tercero_huye_sin_camaras": 0,
            "narrativa_similitud_score": 0.1,
            "narrativa_clonada": 0,
            "monto_cercano_suma_asegurada": 0
        }

    def test_normal_claim(self):
        result = evaluate_record(self.base_record)
        self.assertFalse(result["hard_flag"])
        self.assertEqual(result["final_color"], "verde")
        self.assertEqual(result["final_score"], 0)

    def test_rf01_pt_robo(self):
        record = self.base_record.copy()
        record["cobertura"] = "Robo"
        record["descripcion"] = "Se reporta robo total del vehículo en la noche."
        record["estado"] = "Reserva"
        
        triggered, color = hard_rule_rf01(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "rojo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "rojo")

    def test_rf02_falsificacion_documentos(self):
        record = self.base_record.copy()
        record["documento_alterado"] = 1
        
        triggered, color = hard_rule_rf02(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "rojo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "rojo")

    def test_rf03_lista_restrictiva(self):
        record = self.base_record.copy()
        record["beneficiario"] = "Taller XYZ"
        
        triggered, color = hard_rule_rf03(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "rojo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "rojo")

    def test_rf04_dinamica_imposible(self):
        record = self.base_record.copy()
        record["relato_ilogico"] = 1
        
        triggered, color = hard_rule_rf04(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "rojo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "rojo")

    def test_rf05_borde_vigencia(self):
        record = self.base_record.copy()
        record["dias_desde_inicio_poliza"] = 1
        
        triggered, color = hard_rule_rf05(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "amarillo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "amarillo")

    def test_rf06_demora_robo(self):
        record = self.base_record.copy()
        record["cobertura"] = "Robo"
        record["dias_entre_ocurrencia_reporte"] = 5
        
        triggered, color = hard_rule_rf06(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "amarillo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "amarillo")

    def test_rf07_narrativa_clonada(self):
        record = self.base_record.copy()
        record["narrativa_clonada"] = 1
        
        triggered, color = hard_rule_rf07(record)
        self.assertTrue(triggered)
        self.assertEqual(color, "amarillo")
        
        result = evaluate_record(record)
        self.assertTrue(result["hard_flag"])
        self.assertEqual(result["final_color"], "amarillo")

    def test_soft_score_accumulation(self):
        record = self.base_record.copy()
        
        # 1. Close to policy start (<=10 days) -> 8 pts
        record["dias_desde_inicio_poliza"] = 8
        # 2. Report delay > 7 days -> 5 pts
        record["dias_entre_ocurrencia_reporte"] = 9
        # 3. High claim freq for insured (>=3 claims) -> 8 pts
        record["freq_asegurado_18m"] = 3
        # 4. Blacklist provider -> 10 pts
        record["proveedor_lista_restrictiva"] = 1
        
        score, alerts = compute_soft_score(record)
        self.assertEqual(score, 31) # 8 + 5 + 8 + 10 = 31
        self.assertEqual(len(alerts), 4)

if __name__ == "__main__":
    unittest.main()
