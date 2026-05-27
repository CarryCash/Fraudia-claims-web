# Reglas de Negocio – Fraudia Claims

Este documento detalla las reglas de negocio, su lógica técnica de implementación y las alertas generadas por el sistema **Fraudia Claims** (Aseguradora del Sur).

---

## 1. Reglas Duras (Hard Rules - RF01 a RF07)

Las reglas duras representan banderas críticas de alerta inmediata. Cuando alguna de estas reglas se activa, el siniestro se clasifica automáticamente en el nivel de semáforo correspondiente (Rojo o Amarillo), independientemente de las puntuaciones de las reglas blandas.

| Código | Clasificación | Nombre de la Regla | Criterio de Activación Técnica | Semáforo |
|---|---|---|---|---|
| **RF01** | Crítica | Cobertura Pérdida Total por Robo (PTxRB) | Cobertura es "Robo" y el estado de la póliza o descripción indica robo/pérdida total del bien. | Rojo |
| **RF02** | Crítica | Falsificación o Adulteración Documental | Uno o más documentos requeridos son marcados con `inconsistencia_detectada = 'Sí'`. | Rojo |
| **RF03** | Crítica | Coincidencia con "Lista Restrictiva" | El beneficiario, taller o proveedor coincide con nombres de la Lista Restrictiva. | Rojo |
| **RF04** | Crítica | Dinámica de Accidente Imposible | El relato en `descripcion` describe un evento físicamente imposible (ej. volcadura a 10 km/h). | Rojo |
| **RF05** | Alerta | Siniestro al Borde de la Vigencia | El siniestro ocurrió dentro de las 48 horas posteriores al inicio o previas al vencimiento del contrato. | Amarillo |
| **RF06** | Alerta | Demora Atípica en Denuncia de Robo | Siniestro de tipo "Robo" reportado con un retardo mayor a 4 días tras la ocurrencia. | Amarillo |
| **RF07** | Alerta | Narrativa Clonada (Idéntica) | Similitud de texto calculada mayor o igual a 85% en comparación con otro siniestro. | Amarillo |

---

## 2. Reglas Blandas (Soft Rules) – Rúbrica de Puntos

Las reglas blandas acumulan puntos de riesgo (de 0 a 100). La sumatoria de estos puntos define el semáforo si no hay reglas duras activadas:
- **0 - 40**: Verde (Riesgo Bajo)
- **41 - 75**: Amarillo (Riesgo Medio)
- **76 - 100**: Rojo (Riesgo Alto)

### 2.1. Criterios de Puntuación Detallados:

1. **Cercanía al Borde de Vigencia (Póliza)**
   - Ocurrido en primeros 10 días o últimos 10 días de vigencia: **8 pts**
   - Ocurrido entre los días 11 y 30 de vigencia: **4 pts**
   
2. **Demora en Reporte de Robo**
   - Retardo de reporte superior a 48 horas en casos de robo: **8 pts**
   - Retardo entre 24 y 48 horas en casos de robo: **4 pts**
   
3. **Frecuencia de Siniestros (Asegurado)**
   - Asegurado con 3 o más reclamos en los últimos 18 meses: **8 pts**
   - Asegurado con 2 reclamos en los últimos 18 meses: **4 pts**
   
4. **Frecuencia de Siniestros (Vehículo)**
   - Vehículo con 3 o más reclamos en los últimos 18 meses: **6 pts**
   - Vehículo con 2 reclamos en los últimos 18 meses: **3 pts**
   
5. **Frecuencia de Siniestros (Conductor)**
   - Conductor con 3 o más reclamos en los últimos 18 meses: **8 pts**
   - Conductor con 2 reclamos en los últimos 18 meses: **4 pts**
   
6. **Frecuencia en Responsabilidad Civil (RC) previa**
   - Más de 2 reclamos previos de solo cobertura RC: **6 pts**
   - Exactamente 1 reclamo previo de solo cobertura RC: **3 pts**
   
7. **Beneficiario Recurrente / Proveedor**
   - Proveedor en Lista Restrictiva: **10 pts**
   - Proveedor con 2 o más siniestros observados en el año: **5 pts**
   
8. **Documentación Incompleta**
   - Reclamo con documentos_completos = "No" (falta copia cédula, denuncia o factura obligatoria): **4 pts**
   
9. **Dinámica de Accidente Sospechosa**
   - Relato ilógico versus daños periciados en el tipo de impacto: **6 pts**
   - Accidente reportado de madrugada (00:00 - 06:00): **3 pts**
   
10. **Siniestro Sin Tercero Identificado**
    - Daño severo donde el tercero involucrado huye o no hay registros de cámaras: **5 pts**
    
11. **Documentación Inconsistente**
    - Fechas de facturación previas al evento o facturas con adulteración confirmada: **10 pts**
    
12. **Reporte Tardío General**
    - Siniestro reportado después de 7 días: **5 pts**
    - Siniestro reportado entre 4 y 7 días: **3 pts**
    
13. **Narrativas Similares (NLP)**
    - Similitud mayor o igual a 85% con otra descripción de siniestro: **8 pts**
    - Similitud entre 70% y 84% con otra descripción de siniestro: **4 pts**
    
14. **Proporción de Suma Asegurada**
    - Monto reclamado es mayor o igual a 95% de la suma asegurada total contratada: **4 pts**
