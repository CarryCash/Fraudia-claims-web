import os
# pyrefly: ignore [missing-import]
from notion_client import Client

def create_notion_investigation_page(claim, eval_res, explanation, ml_prob):
    """
    Creates a new investigation page in Notion for a critical fraud claim.
    Requires NOTION_TOKEN and NOTION_PARENT_PAGE_ID (or NOTION_DATABASE_ID) in environment variables.
    """
    notion_token = os.getenv("NOTION_TOKEN")
    parent_id = os.getenv("NOTION_PARENT_PAGE_ID") or os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not parent_id:
        return {
            "success": False, 
            "error": "Faltan credenciales de Notion. Configura NOTION_TOKEN y NOTION_PARENT_PAGE_ID en el archivo .env"
        }

    notion = Client(auth=notion_token)

    title = f"🚨 Investigación Siniestro #{claim['id_siniestro']} - Fraude Crítico"
    
    # Preparamos los datos
    monto_reclamado = f"${claim['monto_reclamado']:,.2f}"
    monto_estimado = f"${claim['monto_estimado']:,.2f}"
    monto_pagado = f"${claim['monto_pagado']:,.2f}"
    
    # Creamos los bloques de la página
    blocks = [
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": "Resumen Ejecutivo (Generado por IA)"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": explanation}}]
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Ficha Técnica y Montos"}}]
            }
        },
        {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 2,
                "has_column_header": True,
                "has_row_header": False,
                "children": [
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Campo"}}],
                                [{"type": "text", "text": {"content": "Valor"}}]
                            ]
                        }
                    },
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Sucursal"}}],
                                [{"type": "text", "text": {"content": str(claim['sucursal'])}}]
                            ]
                        }
                    },
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Monto Reclamado"}}],
                                [{"type": "text", "text": {"content": monto_reclamado}}]
                            ]
                        }
                    },
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Monto Estimado"}}],
                                [{"type": "text", "text": {"content": monto_estimado}}]
                            ]
                        }
                    },
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Monto Pagado"}}],
                                [{"type": "text", "text": {"content": monto_pagado}}]
                            ]
                        }
                    },
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Score Riesgo (0-100)"}}],
                                [{"type": "text", "text": {"content": str(claim.get('final_score', 'N/A'))}}]
                            ]
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Grafo de Relaciones"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text", 
                        "text": {
                            "content": "Nota: La API de Notion no permite subir imágenes locales directamente sin una URL pública. Por favor, adjunta la captura del grafo interactivo de PyVis manualmente."
                        },
                        "annotations": {"italic": True, "color": "gray"}
                    }
                ]
            }
        }
    ]

    try:
        # Check if parent is a database or page
        # A typical Notion ID has 32 chars without hyphens
        parent_id_clean = parent_id.replace("-", "")
        
        # We will attempt to create it as a child page of the given parent page.
        # If the user provides a database ID, it should be passed as database_id.
        # We'll just try page_id first, if it fails, try database_id.
        parent_obj = {"page_id": parent_id}
        
        # If it looks like a database, one might need "database_id". 
        # But for simplicity, we'll assume it's a page ID. If the user wants to use a database,
        # they should use NOTION_DATABASE_ID.
        if os.getenv("NOTION_DATABASE_ID"):
            parent_obj = {"database_id": os.getenv("NOTION_DATABASE_ID")}

        new_page = notion.pages.create(
            parent=parent_obj,
            properties={
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            children=blocks
        )
        return {
            "success": True, 
            "url": new_page.get("url", "https://notion.so"),
            "id": new_page.get("id")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_dashboard_report(total_claims, red_claims, yellow_claims, amt_in_risk, potential_savings, top_10_df):
    """
    Creates a master Dashboard report in Notion.
    """
    notion_token = os.getenv("NOTION_TOKEN")
    parent_id = os.getenv("NOTION_PARENT_PAGE_ID") or os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not parent_id:
        return {
            "success": False, 
            "error": "Faltan credenciales de Notion. Configura NOTION_TOKEN y NOTION_PARENT_PAGE_ID en el archivo .env"
        }

    notion = Client(auth=notion_token)
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"📊 Dashboard de Fraude - {date_str}"
    
    blocks = [
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": "KPIs Principales"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Total de Siniestros Procesados: {total_claims:,}"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Alertas Rojas (Riesgo Alto): {red_claims}"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Alertas Amarillas (Riesgo Medio): {yellow_claims}"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Monto Total en Riesgo: ${amt_in_risk:,.2f}"}}]}
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"Ahorro Potencial Estimado (80%): ${potential_savings:,.2f}"}}]}
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🏆 Top 10 Siniestros Críticos"}}]}
        }
    ]
    
    # Build Top 10 table
    table_rows = [
        {
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"type": "text", "text": {"content": "Siniestro ID"}}],
                    [{"type": "text", "text": {"content": "Sucursal"}}],
                    [{"type": "text", "text": {"content": "Monto"}}],
                    [{"type": "text", "text": {"content": "Score"}}]
                ]
            }
        }
    ]
    
    for idx, r in top_10_df.iterrows():
        table_rows.append({
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"type": "text", "text": {"content": str(r['id_siniestro'])}}],
                    [{"type": "text", "text": {"content": str(r['sucursal'])}}],
                    [{"type": "text", "text": {"content": f"${r['monto_reclamado']:,.2f}"}}],
                    [{"type": "text", "text": {"content": str(r['final_score'])}}]
                ]
            }
        })
        
    blocks.append({
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 4,
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows
        }
    })

    try:
        parent_id_clean = parent_id.replace("-", "")
        parent_obj = {"page_id": parent_id}
        if os.getenv("NOTION_DATABASE_ID"):
            parent_obj = {"database_id": os.getenv("NOTION_DATABASE_ID")}

        new_page = notion.pages.create(
            parent=parent_obj,
            properties={
                "title": [{"text": {"content": title}}]
            },
            children=blocks
        )
        return {
            "success": True, 
            "url": new_page.get("url", "https://notion.so"),
            "id": new_page.get("id")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
