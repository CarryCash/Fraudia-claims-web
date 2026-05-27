# scripts/generate_synthetic.py
"""Generate synthetic insurance claim datasets using Kaggle's insurance_claims.csv as a guide.

- Reads the raw Kaggle dataset.
- Translates and enriches it with Ecuadorian context (Loja, Cuenca, Machala, Zamora, Azogues).
- Automatically generates all required relational tables: Pólizas, Asegurados, Proveedores, Documentos.
- Injects specific patterns that trigger rules RF01 to RF07 and soft rules.
- Saves all datasets in data/raw/ and data/processed/.
"""

import os
import csv
import pandas as pd
import numpy as np
import random
from pathlib import Path
from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
from faker import Faker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Initialize Faker with Spanish locale
FAKE = Faker("es_ES")
random.seed(42)
np.random.seed(42)
Faker.seed(42)

# Ecuadorian cities and streets for the Southern region
EC_CITIES = ["Loja", "Cuenca", "Machala", "Zamora", "Azogues"]
EC_STREETS = {
    "Loja": ["Av. Orillas del Zamora", "Av. Manuel Agustín Aguirre", "Calle Bolívar", "Calle 18 de Noviembre", "Av. Salvador Bustamante Celi"],
    "Cuenca": ["Av. Remigio Crespo", "Av. de las Américas", "Calle Larga", "Av. Solano", "Av. 12 de Abril"],
    "Machala": ["Av. 25 de Junio", "Calle Rocafuerte", "Av. Las Palmeras", "Calle Bolívar", "Av. Madero Vargas"],
    "Zamora": ["Av. Héroes de Paquisha", "Calle Diego de Vaca", "Av. del Ejército", "Calle Sevilla de Oro"],
    "Azogues": ["Av. 24 de Mayo", "Calle 3 de Noviembre", "Av. Aurelio Jaramillo", "Calle Bolívar"]
}

# Providers (beneficiarios) in Ecuador
EC_PROVIDERS = {
    "Taller": ["Talleres del Austro", "Multiservicios Loja Car", "Tecnicentro El Oro", "Enderezada y Pintura Lojanita", "Autoservicio Cuenca"],
    "Clínica": ["Clínica Hospital Municipal Loja", "Hospital Santa Inés Cuenca", "Clínica La Cigüeña Machala", "Clínica San Agustín"],
    "Perito": ["Ing. Carlos Mendoza (Perito)", "Dr. Luis Silva (Perito)", "Ing. Juan Castro (Perito)", "Dra. María Cabrera (Perito)"],
    "Lista Restrictiva": ["Taller El Chueco", "Taller XYZ", "Clínica Trucha", "Perito Sospechoso"]
}

# ---------------------------------------------------------------------
# Helper generation functions
# ---------------------------------------------------------------------

def generate_ecuadorian_plate(city: str) -> str:
    """Generate a realistic Ecuadorian license plate.
    First letter represents province:
    L = Loja, A = Azuay (Cuenca), O = El Oro (Machala), U = Cañar (Azogues), V = Zamora Chinchipe
    """
    province_codes = {
        "Loja": "L",
        "Cuenca": "A",
        "Machala": "O",
        "Zamora": "V",
        "Azogues": "U"
    }
    prefix = province_codes.get(city, random.choice(["L", "A", "O", "V", "U"]))
    letters = prefix + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    numbers = "".join(random.choices("0123456789", k=4))
    return f"{letters}-{numbers}"

def generate_ecuadorian_id() -> str:
    """Generate a realistic 10-digit Ecuadorian ID (Cédula de Identidad)."""
    prov = random.randint(1, 24)
    prov_str = f"{prov:02d}"
    third_digit = random.randint(0, 5)
    sequence = "".join(random.choices("0123456789", k=6))
    digits = [int(d) for d in prov_str + str(third_digit) + sequence]
    
    # Verifier digit calculation (Luhn-like algorithm used in Ecuador)
    coefs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for d, c in zip(digits, coefs):
        val = d * c
        if val >= 10:
            val -= 9
        total += val
    verif = (10 - (total % 10)) % 10
    return "".join(map(str, digits)) + str(verif)

def generate_narrative_local(row, city: str, street: str, is_fraud: bool, fraud_type: str = "") -> str:
    """Generate realistic claims narratives in Spanish based on row variables and fraud type."""
    make = row["auto_make"]
    model = row["auto_model"]
    year = row["auto_year"]
    severity = row["incident_severity"]
    collision = row["collision_type"] if pd.notna(row["collision_type"]) else "Choque"
    
    if is_fraud:
        if fraud_type == "RF01":
            return f"Se reporta el robo total del vehículo {make} {model} ({year}) mientras se encontraba estacionado en la calle {street} de la ciudad de {city}. El asegurado manifiesta que dejó el auto parqueado por la noche y al salir en la mañana ya no se encontraba. No hay testigos ni grabaciones de cámaras en el sector."
        elif fraud_type == "RF04":
            return f"El conductor declara haber perdido el control de su {make} {model} a una velocidad aproximada de 10 km/h al esquivar un perro en la calle {street} en {city}, resultando en una volcadura de campana y daños severos en el techo y laterales. El peritaje técnico preliminar indica que el daño es inconsistente con la velocidad reportada."
        elif fraud_type == "RF07":
            # Cloned narratives - must be exactly identical
            return "El asegurado reporta que mientras circulaba por la vía principal en condiciones de lluvia, otro vehículo no identificado invadió su carril rozándolo lateralmente y provocando que se saliera de la calzada e impactara contra un poste de alumbrado público. El tercero se dio a la fuga de inmediato."
        elif fraud_type == "RF06":
            return f"Se denuncia el robo de autopartes y accesorios del vehículo {make} {model} en la ciudad de {city}. El siniestro presuntamente ocurrió hace más de cinco días, pero el asegurado indica que no pudo asentar la denuncia antes por motivos de viaje personal de urgencia."
        elif fraud_type == "documentos_inconsistentes":
            return f"El cliente presenta reclamo por colisión frontal de su {make} {model} contra un muro en {city}. Adjunta facturas de reparación emitidas por repuestos del motor. Auditoría detecta inconsistencias en las fechas de las facturas del taller."
        else:
            return f"Se reporta choque frontal severo de {make} {model} contra un objeto fijo en la calle {street} de {city}. El conductor indica que se desvió para evitar colisión con otro carro que huyó. No hay registro policial del incidente."
    
    # Standard narratives
    narratives = [
        f"El asegurado reporta un choque por alcance en la calle {street} de la ciudad de {city}. Su {make} {model} ({year}) fue impactado en la parte posterior por otro vehículo que no guardó la distancia de seguridad. Daños leves en el parachoques trasero y cajuela.",
        f"Se reporta un choque lateral en la intersección de la calle {street} en {city}. El conductor de un {make} {model} indica que otro vehículo ignoró la señal de pare, impactando su puerta lateral izquierda. El choque provocó daños de consideración media.",
        f"El conductor reporta que al transitar por {street} en {city}, debido a trabajos en la vía y falta de señalización, cayó en un bache profundo provocando la rotura del neumático delantero derecho y daños en la suspensión del {make} {model}.",
        f"Se reporta la rotura del parabrisas delantero del {make} {model} ({year}) por impacto de una piedra lanzada por un camión de carga mientras circulaba por la vía de acceso a {city}. Sin terceras personas lesionadas.",
        f"El cliente reporta el robo parcial de los accesorios de su {make} {model} (retrovisores y radio) mientras se encontraba estacionado temporalmente frente a un local comercial en la calle {street} de {city}."
    ]
    return random.choice(narratives)

# ---------------------------------------------------------------------
# Main Generation Pipeline
# ---------------------------------------------------------------------

def process_and_generate():
    csv_input_path = DATA_RAW / "insurance_claims.csv"
    if not csv_input_path.exists():
        csv_input_path = PROJECT_ROOT / "insurance_claims.csv"
    if not csv_input_path.exists():
        raise FileNotFoundError(f"Base Kaggle CSV not found. Place it at: {DATA_RAW / 'insurance_claims.csv'}")
    
    print(f"Reading base dataset from: {csv_input_path}")
    base_df = pd.read_csv(csv_input_path)
    base_df = base_df.replace('?', np.nan)
    
    total_records = len(base_df)
    print(f"Loaded {total_records} records from base dataset.")
    
    # Lists to store relational tables
    siniestros_rows = []
    polizas_rows = []
    asegurados_rows = []
    proveedores_rows = []
    documentos_rows = []
    
    # Pre-generate unique Asegurados & Proveedores to ensure referential integrity
    unique_insured_ids = [f"ASEG-{100000 + i}" for i in range(total_records // 2)]
    insured_pool = []
    for iid in unique_insured_ids:
        city = random.choice(EC_CITIES)
        insured_pool.append({
            "id_asegurado": iid,
            "nombre": FAKE.name(),
            "cedula": generate_ecuadorian_id(),
            "segmento": random.choice(["Eándar", "Premium", "VIP", "Corporativo"]),
            "antigueedad": random.randint(1, 15),
            "ciudad": city,
            "numero_de_polizas": random.randint(1, 4),
            "reclamos_ultimos_12_meses": random.randint(0, 3),
            "mora_actual": random.choice(["Sí", "No"]),
            "score_cliente_simulado": random.randint(50, 95)
        })
    asegurados_df = pd.DataFrame(insured_pool)
    
    # Pre-generate Proveedores (Talleres, Clínicas, Peritos)
    prov_pool = []
    prov_counter = 1
    for p_type, names in EC_PROVIDERS.items():
        for name in names:
            prov_id = f"PROV-{100 + prov_counter}"
            prov_pool.append({
                "id_proveedor": prov_id,
                "nombre": name,
                "tipo": p_type,
                "ciudad": random.choice(EC_CITIES),
                "reclamos_asociados": random.randint(5, 50),
                "monto_promedio_reclamado": round(random.uniform(1000, 8000), 2),
                "porcentaje_de_casos_observados": round(random.uniform(0.0, 0.15) * 100, 2) if name not in EC_PROVIDERS["Lista Restrictiva"] else round(random.uniform(0.60, 0.95) * 100, 2),
                "antigueedad_proveedor": random.randint(2, 20)
            })
            prov_counter += 1
    proveedores_df = pd.DataFrame(prov_pool)
    
    # Process Siniestros and Pólizas
    # We will iterate and map each row in Kaggle to Ecuadorian context
    for idx, row in base_df.iterrows():
        id_siniestro = int(idx + 1)
        
        # Select client and provider
        insured_record = random.choice(insured_pool)
        id_asegurado = insured_record["id_asegurado"]
        city = insured_record["ciudad"]
        street = random.choice(EC_STREETS[city])
        
        # Decide if this claim is simulated fraud
        # Kaggle fraud reported is Y or N. We'll match that but also inject specific patterns.
        base_fraud = 1 if row["fraud_reported"] == "Y" else 0
        is_fraud = base_fraud == 1
        
        # Assign provider
        if is_fraud and random.random() < 0.3:
            # Inject RF03: blacklist provider
            provider_record = random.choice([p for p in prov_pool if p["nombre"] in EC_PROVIDERS["Lista Restrictiva"]])
        else:
            provider_record = random.choice([p for p in prov_pool if p["nombre"] not in EC_PROVIDERS["Lista Restrictiva"]])
        
        id_proveedor = provider_record["id_proveedor"]
        beneficiario = provider_record["nombre"]
        
        # Ramo and Cobertura
        ramo = "Vehículos" # Default auto
        # Introduce a few health and home claims for variety
        if idx % 12 == 0:
            ramo = "Salud"
            cobertura = "Atención médica"
            beneficiario = random.choice([p["nombre"] for p in prov_pool if p["tipo"] == "Clínica"])
        elif idx % 20 == 0:
            ramo = "Hogar"
            cobertura = "Incendio"
            beneficiario = "Otro"
        else:
            incident_type = row["incident_type"]
            if incident_type == "Vehicle Theft":
                cobertura = "Robo"
            elif incident_type == "Parked Car":
                cobertura = "Daño material"
            else:
                cobertura = "Choque"
        
        # Dates
        # Incident date in Kaggle is 2015-01-01 to 2015-03-01. Let's shift it to recent years (2024-2025)
        base_date = datetime.strptime(row["incident_date"], "%Y-%m-%d")
        # Shift 10 years forward
        fecha_ocurrencia = base_date + timedelta(days=365*10)
        
        # Report delay
        if is_fraud and cobertura == "Robo" and random.random() < 0.4:
            # Inject RF06: delay in theft claim reporting (> 4 days)
            report_delay = random.randint(5, 15)
        else:
            report_delay = random.randint(0, 3)
        fecha_reporte = fecha_ocurrencia + timedelta(days=report_delay)
        
        # Póliza duration: let's generate policy dates around the occurrence
        # Póliza starts some days before occurrence
        # RF05: Siniestro al borde de la vigencia (< 48 hrs / <= 2 días)
        if is_fraud and random.random() < 0.3:
            # 2 days from policy start or end
            if random.random() < 0.5:
                dias_desde_inicio_poliza = random.randint(0, 2)
                policy_start_date = fecha_ocurrencia - timedelta(days=dias_desde_inicio_poliza)
                policy_end_date = policy_start_date + timedelta(days=365)
                dias_desde_fin_poliza = (policy_end_date - fecha_ocurrencia).days
            else:
                dias_desde_fin_poliza = random.randint(0, 2)
                policy_end_date = fecha_ocurrencia + timedelta(days=dias_desde_fin_poliza)
                policy_start_date = policy_end_date - timedelta(days=365)
                dias_desde_inicio_poliza = (fecha_ocurrencia - policy_start_date).days
        else:
            dias_desde_inicio_poliza = random.randint(15, 300)
            policy_start_date = fecha_ocurrencia - timedelta(days=dias_desde_inicio_poliza)
            policy_end_date = policy_start_date + timedelta(days=365)
            dias_desde_fin_poliza = (policy_end_date - fecha_ocurrencia).days
            
        id_poliza = f"POL-{row['policy_number']}"
        
        # Amounts
        monto_reclamado = float(row["total_claim_amount"])
        
        # Modify amounts if Hogar/Salud to make sense
        if ramo == "Salud":
            monto_reclamado = round(random.uniform(100, 3000), 2)
        elif ramo == "Hogar":
            monto_reclamado = round(random.uniform(2000, 35000), 2)
            
        monto_estimado = round(monto_reclamado * random.uniform(0.75, 0.95), 2)
        
        # Pagos
        if is_fraud:
            # Under review/Negativa/Reserva
            estado = random.choice(["Negativa", "Reserva", "Cierre Sin Consecuencia"])
            monto_pagado = 0.0
        else:
            estado = random.choice(["Pago Total", "Pago Parcial", "Liquidado"])
            monto_pagado = monto_estimado if estado in ["Pago Total", "Liquidado"] else round(monto_estimado * random.uniform(0.4, 0.8), 2)

        # Documentos completos
        # RF02: Falsificación / Documentos incompletos
        if is_fraud and random.random() < 0.3:
            documentos_completos = "No"
        else:
            documentos_completos = "Sí"
            
        # Determine specific fraud type for narrative generation
        fraud_type = ""
        if is_fraud:
            if cobertura == "Robo" and row["incident_severity"] == "Total Loss":
                fraud_type = "RF01"
            elif random.random() < 0.2:
                fraud_type = "RF04" # Dinámica imposible
            elif idx % 15 == 0:
                fraud_type = "RF07" # Cloned narrative
            elif report_delay > 4 and cobertura == "Robo":
                fraud_type = "RF06"
            elif random.random() < 0.2:
                fraud_type = "documentos_inconsistentes"
                
        # Generate Spanish narrative
        descripcion = generate_narrative_local(row, city, street, is_fraud, fraud_type)
        
        # Historial de reclamos
        historial_siniestros_asegurado = insured_record["reclamos_ultimos_12_meses"]
        
        # Add Siniestro row
        siniestros_rows.append({
            "id_siniestro": id_siniestro,
            "id_poliza": id_poliza,
            "id_asegurado": id_asegurado,
            "ramo": ramo,
            "cobertura": cobertura,
            "fecha_ocurrencia": fecha_ocurrencia.strftime("%Y-%m-%d"),
            "fecha_reporte": fecha_reporte.strftime("%Y-%m-%d"),
            "monto_reclamado": monto_reclamado,
            "monto_estimado": monto_estimado,
            "monto_pagado": monto_pagado,
            "estado": estado,
            "sucursal": city,
            "descripcion": descripcion,
            "documentos_completos": documentos_completos,
            "beneficiario": beneficiario,
            "dias_desde_inicio_poliza": dias_desde_inicio_poliza,
            "dias_desde_fin_poliza": dias_desde_fin_poliza,
            "dias_entre_ocurrencia_reporte": report_delay,
            "historial_siniestros_asegurado": historial_siniestros_asegurado,
            "etiqueta_fraude_simulada": base_fraud,
            "placa_vehiculo": generate_ecuadorian_plate(city) if ramo == "Vehículos" else np.nan,
            "id_proveedor": id_proveedor
        })
        
        # Add Póliza row (if not already added)
        if id_poliza not in [p["id_poliza"] for p in polizas_rows]:
            polizas_rows.append({
                "id_poliza": id_poliza,
                "id_asegurado": id_asegurado,
                "ramo": ramo,
                "fecha_inicio": policy_start_date.strftime("%Y-%m-%d"),
                "fecha_fin": policy_end_date.strftime("%Y-%m-%d"),
                "prima": round(float(row["policy_annual_premium"]), 2),
                "suma_asegurada": round(float(row["policy_deductable"]) * random.uniform(20, 50), 2) if ramo == "Vehículos" else round(monto_reclamado * random.uniform(1.2, 2.0), 2),
                "deducible": float(row["policy_deductable"]),
                "canal_venta": random.choice(["Agente Directo", "Broker", "Web Aseguradora", "Banca Seguros"]),
                "ciudad": city,
                "estado_poliza": "Activa" if policy_end_date > datetime.now() else "Expirada"
            })
            
        # Add Documentos for each claim
        # Generate 3-4 documents per claim
        doc_types = ["Copia de Cédula", "Denuncia Fiscalía", "Informe Policial", "Factura de Taller/Clínica", "Formulario de Reclamo"]
        for j, dtype in enumerate(doc_types):
            doc_id = f"DOC-{id_siniestro:04d}-{j+1}"
            
            # Simulate whether document was delivered and legible
            delivered = "Sí"
            legible = "Sí"
            inconsistencia = "No"
            observacion = ""
            
            # If documents are not complete, randomly miss a critical document
            if documentos_completos == "No" and dtype in ["Denuncia Fiscalía", "Informe Policial", "Factura de Taller/Clínica"]:
                if random.random() < 0.5:
                    delivered = "No"
                    legible = "No"
                    
            # If it is a fraud type of documents inconsistency, make a document inconsistent
            if is_fraud and fraud_type == "documentos_inconsistentes" and dtype == "Factura de Taller/Clínica":
                inconsistencia = "Sí"
                observacion = "Fecha de factura es previa a la ocurrencia del siniestro."
            elif is_fraud and random.random() < 0.05:
                inconsistencia = "Sí"
                observacion = "Firma del taller no coincide con la registrada."
                
            documentos_rows.append({
                "id_documento": doc_id,
                "id_siniestro": id_siniestro,
                "tipo_documento": dtype,
                "entregado": delivered,
                "legible": legible,
                "fecha_emision": (fecha_ocurrencia + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d") if delivered == "Sí" else np.nan,
                "inconsistencia_detectada": inconsistencia,
                "observacion": observacion
            })
            
    # Convert to DataFrames
    siniestros_df = pd.DataFrame(siniestros_rows)
    polizas_df = pd.DataFrame(polizas_rows)
    documentos_df = pd.DataFrame(documentos_rows)
    
    # Save Raw Tables
    siniestros_df.to_csv(DATA_RAW / "siniestros.csv", index=False)
    polizas_df.to_csv(DATA_RAW / "polizas.csv", index=False)
    asegurados_df.to_csv(DATA_RAW / "asegurados.csv", index=False)
    proveedores_df.to_csv(DATA_RAW / "proveedores.csv", index=False)
    documentos_df.to_csv(DATA_RAW / "documentos.csv", index=False)
    
    # Save copy to Processed for training pipeline
    siniestros_df.to_csv(DATA_PROCESSED / "siniestros.csv", index=False)
    polizas_df.to_csv(DATA_PROCESSED / "polizas.csv", index=False)
    asegurados_df.to_csv(DATA_PROCESSED / "asegurados.csv", index=False)
    proveedores_df.to_csv(DATA_PROCESSED / "proveedores.csv", index=False)
    documentos_df.to_csv(DATA_PROCESSED / "documentos.csv", index=False)
    
    print("Synthetic and augmented data generation finished successfully!")
    print(f"Generated {len(siniestros_df)} Claims")
    print(f"Generated {len(polizas_df)} Policies")
    print(f"Generated {len(asegurados_df)} Insureds")
    print(f"Generated {len(proveedores_df)} Providers")
    print(f"Generated {len(documentos_df)} Documents")
    print("Files saved in data/raw/ and data/processed/")

if __name__ == "__main__":
    process_and_generate()