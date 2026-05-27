# Modelo de Datos – Fraudia Claims

Este documento detalla la estructura, campos, tipos de datos y relaciones de la base de datos relacional del prototipo **Fraudia Claims**. Los datos son sintéticos y enriquecidos con contexto de Ecuador.

---

## 1. Diagrama de Relaciones

El modelo se estructura en torno al registro central de **Siniestros**, el cual se vincula mediante llaves foráneas a las tablas de **Pólizas**, **Asegurados**, **Proveedores** y **Documentos**.

```
  ┌───────────────┐          ┌───────────────┐
  │  Asegurados   │◄─────────┤    Pólizas    │
  └───────┬───────┘          └───────┬───────┘
          │ 1                        │ 1
          │                          │
          │ 1:N                      │ 1:N
          │        ┌───────────┐     │
          └───────►│Siniestros │◄────┘
                   └─────┬─────┘
                         │ 1
                         │
                         ├───────────────┐
                         │ 1:N           │ 1:N
                         ▼               ▼
                  ┌─────────────┐ ┌─────────────┐
                  │ Proveedores │ │ Documentos  │
                  └─────────────┘ └─────────────┘
```

---

## 2. Detalle de las Tablas

### 2.1. Tabla: Siniestros (`siniestros.csv`)
Registro principal de los incidentes de seguros reportados.

| Campo | Tipo | Descripción | Relación |
|---|---|---|---|
| `id_siniestro` | `Integer` | Identificador único secuencial del siniestro (PK). | |
| `id_poliza` | `String` | Identificador de la póliza asociada. | FK -> `polizas.id_poliza` |
| `id_asegurado` | `String` | Identificador anónimo del asegurado. | FK -> `asegurados.id_asegurado` |
| `ramo` | `String` | Ramo comercial: "Vehículos", "Salud", "Vida", "Hogar", "Generales". | |
| `cobertura` | `String` | Cobertura reclamada: "Choque", "Robo", "Atención médica", "Incendio", "Daño material". | |
| `fecha_ocurrencia` | `Date` | Fecha del evento (YYYY-MM-DD). | |
| `fecha_reporte` | `Date` | Fecha de notificación formal a la aseguradora (YYYY-MM-DD). | |
| `monto_reclamado` | `Float` | Valor solicitado en dólares (USD). | |
| `monto_estimado` | `Float` | Valor técnico estimado por el liquidador (USD). | |
| `monto_pagado` | `Float` | Monto pagado al beneficiario (USD). | |
| `estado` | `String` | Estado: "Reserva", "Pago Total", "Pago Parcial", "Negativa", "Cierre Sin Consecuencia", "Liquidado". | |
| `sucursal` | `String` | Ciudad de la sucursal (Loja, Cuenca, Machala, Zamora, Azogues). | |
| `descripcion` | `String` | Narrativa libre en español del reclamo. | |
| `documentos_completos` | `String` | Indicador si se entregó toda la documentación ("Sí", "No"). | |
| `beneficiario` | `String` | Nombre del taller, clínica o persona que recibe el pago. | |
| `dias_desde_inicio_poliza`| `Integer` | Días transcurridos entre el inicio de vigencia de la póliza y el siniestro. | |
| `dias_desde_fin_poliza` | `Integer` | Días transcurridos entre el siniestro y el fin de vigencia de la póliza. | |
| `dias_entre_ocurrencia_reporte`| `Integer`| Diferencia en días entre la ocurrencia y el reporte del siniestro. | |
| `historial_siniestros_asegurado`| `Integer`| Cantidad de reclamos previos del asegurado. | |
| `etiqueta_fraude_simulada`| `Integer`| Etiqueta binaria para entrenamiento (1 = Posible fraude, 0 = Normal). | |
| `placa_vehiculo` | `String` | Placa ecuatoriana del vehículo (`LBA-1234`). | |
| `id_proveedor` | `String` | Identificador del taller o clínica. | FK -> `proveedores.id_proveedor` |

---

### 2.2. Tabla: Pólizas (`polizas.csv`)
Contratos de seguros emitidos a los asegurados.

| Campo | Tipo | Descripción | Relación |
|---|---|---|---|
| `id_poliza` | `String` | Identificador de la póliza (PK). | |
| `id_asegurado` | `String` | Identificador del asegurado dueño de la póliza. | FK -> `asegurados.id_asegurado` |
| `ramo` | `String` | Ramo comercial de cobertura. | |
| `fecha_inicio` | `Date` | Fecha de inicio de vigencia (YYYY-MM-DD). | |
| `fecha_fin` | `Date` | Fecha de fin de vigencia (YYYY-MM-DD). | |
| `prima` | `Float` | Prima anual pagada (USD). | |
| `suma_asegurada` | `Float` | Límite máximo de indemnización (USD). | |
| `deducible` | `Float` | Franquicia a cargo del asegurado (USD). | |
| `canal_venta` | `String` | Canal: "Agente Directo", "Broker", "Web", "Banca Seguros". | |
| `ciudad` | `String` | Ciudad de emisión del contrato. | |
| `estado_poliza` | `String` | Estado del contrato ("Activa", "Expirada"). | |

---

### 2.3. Tabla: Asegurados (`asegurados.csv`)
Información de clientes registrados.

| Campo | Tipo | Descripción | Relación |
|---|---|---|---|
| `id_asegurado` | `String` | Identificador único del cliente (PK). | |
| `nombre` | `String` | Nombre completo del asegurado. | |
| `cedula` | `String` | Documento de identidad ecuatoriano (10 dígitos). | |
| `segmento` | `String` | Segmento comercial: "Estándar", "Premium", "VIP", "Corporativo".| |
| `antigueedad` | `Integer` | Años de antigüedad como cliente en la aseguradora. | |
| `ciudad` | `String` | Ciudad de residencia del cliente. | |
| `numero_de_polizas` | `Integer` | Cantidad de pólizas activas simultáneas. | |
| `reclamos_ultimos_12_meses`| `Integer`| Siniestros reportados por el cliente en el último año. | |
| `mora_actual` | `String` | Estado de pago de sus cuotas ("Sí", "No"). | |
| `score_cliente_simulado` | `Integer` | Score interno de confiabilidad comercial (50 a 100). | |

---

### 2.4. Tabla: Proveedores (`proveedores.csv`)
Talleres mecánicos, clínicas médicas y peritos externos.

| Campo | Tipo | Descripción | Relación |
|---|---|---|---|
| `id_proveedor` | `String` | Identificador único del proveedor (PK). | |
| `nombre` | `String` | Nombre comercial del taller o clínica. | |
| `tipo` | `String` | Tipo: "Taller", "Clínica", "Perito", "Lista Restrictiva". | |
| `ciudad` | `String` | Ciudad del taller o clínica. | |
| `reclamos_asociados` | `Integer` | Historial total de reclamos tramitados. | |
| `monto_promedio_reclamado`| `Float`| Costo promedio de reparaciones o consultas (USD). | |
| `porcentaje_de_casos_observados`| `Float`| Porcentaje de alertas rojas/amarillas asociadas a este proveedor. | |
| `antigueedad_proveedor` | `Integer` | Años de vinculación como red de proveedores autorizados. | |

---

### 2.5. Tabla: Documentos (`documentos.csv`)
Documentación soporte presentada por cada siniestro.

| Campo | Tipo | Descripción | Relación |
|---|---|---|---|
| `id_documento` | `String` | Identificador único de archivo digital (PK). | |
| `id_siniestro` | `Integer` | ID del siniestro al que pertenece. | FK -> `siniestros.id_siniestro` |
| `tipo_documento` | `String` | Tipo: "Copia de Cédula", "Denuncia Fiscalía", "Informe Policial", "Factura de Taller/Clínica", "Formulario de Reclamo". | |
| `entregado` | `String` | Estado de entrega ("Sí", "No"). | |
| `legible` | `String` | Calidad del documento ("Sí", "No"). | |
| `fecha_emision` | `Date` | Fecha en la que fue emitido el documento físico (YYYY-MM-DD).| |
| `inconsistencia_detectada`| `String`| Alerta si se sospecha alteración o fechas inválidas ("Sí", "No").| |
| `observacion` | `String` | Notas del liquidador sobre el documento. | |
