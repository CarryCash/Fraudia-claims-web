import os
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def get_notion_headers() -> Dict[str, str]:
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise ValueError("NOTION_API_KEY no está configurado en las variables de entorno.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

def create_report_page(parent_page_id: str, title: str, stats: Dict[str, Any], claims: List[Dict[str, Any]]) -> str:
    """
    Creates a new Notion Page inside a given parent page.
    The page will contain an executive summary (KPIs) and a table of the high priority claims.
    """
    headers = get_notion_headers()
    
    # 1. Blocks for the KPIs
    kpi_blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📊 Resumen Ejecutivo (KPIs)"}}]
            }
        },
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {
                        "type": "text", 
                        "text": {"content": f"Ahorro Potencial (Capital en Riesgo): "},
                        "annotations": {"bold": True}
                    },
                    {
                        "type": "text", 
                        "text": {"content": f"${stats.get('ahorro_potencial', 0):,.2f}"}
                    }
                ],
                "icon": {"type": "emoji", "emoji": "💰"},
                "color": "red_background"
            }
        },
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {
                        "type": "text", 
                        "text": {"content": f"Monto Total Reclamado: "},
                        "annotations": {"bold": True}
                    },
                    {
                        "type": "text", 
                        "text": {"content": f"${stats.get('monto_total', 0):,.2f}"}
                    }
                ],
                "icon": {"type": "emoji", "emoji": "🏦"},
                "color": "gray_background"
            }
        },
        {
            "object": "block",
            "type": "divider",
            "divider": {}
        }
    ]

    # 2. Block for the Table Heading
    table_heading = {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🚨 Casos Críticos (Triaje IA)"}}]
        }
    }

    # 3. Block for the Table (Columns: ID, Beneficiario, Ramo, Monto, Riesgo)
    table_rows = []
    
    # Header row
    table_rows.append({
        "type": "table_row",
        "table_row": {
            "cells": [
                [{"type": "text", "text": {"content": "ID"}}],
                [{"type": "text", "text": {"content": "Beneficiario"}}],
                [{"type": "text", "text": {"content": "Ramo"}}],
                [{"type": "text", "text": {"content": "Monto"}}],
                [{"type": "text", "text": {"content": "Riesgo"}}]
            ]
        }
    })

    # Data rows (limit to 50 so we don't hit payload limits for the demo)
    for c in claims[:50]:
        table_rows.append({
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"type": "text", "text": {"content": str(c.get('id_siniestro', ''))}}],
                    [{"type": "text", "text": {"content": str(c.get('beneficiario', '—'))}}],
                    [{"type": "text", "text": {"content": str(c.get('ramo', ''))}}],
                    [{"type": "text", "text": {"content": f"${c.get('monto_reclamado', 0):,.2f}"}}],
                    [{"type": "text", "text": {"content": str(c.get('final_color', '')).upper()}}]
                ]
            }
        })

    table_block = {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 5,
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows
        }
    }

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "properties": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ]
        },
        "children": kpi_blocks + [table_heading, table_block]
    }

    req = urllib.request.Request(
        f"{NOTION_API_URL}/pages",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            return res_data.get("url")
    except urllib.error.HTTPError as e:
        error_info = e.read().decode()
        raise Exception(f"Notion API error: {e.code} - {error_info}")
