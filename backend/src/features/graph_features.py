import networkx as nx
import pandas as pd

def compute_graph_features(df_sin: pd.DataFrame) -> pd.DataFrame:
    """
    Construye un grafo de relaciones Asegurado ↔ Vehículo ↔ Proveedor
    y detecta componentes conectados anómalos (carruseles de fraude).
    """
    # Evitar modificar el original directamente si no se desea
    df = df_sin.copy()
    
    G = nx.Graph()
    
    # 1. Construir el Grafo
    for idx, row in df.iterrows():
        id_siniestro = row.get("id_siniestro")
        id_asegurado = f"ASEG_{row.get('id_asegurado')}" if pd.notna(row.get("id_asegurado")) else None
        placa = f"VEH_{row.get('placa_vehiculo')}" if pd.notna(row.get("placa_vehiculo")) else None
        beneficiario = f"PROV_{row.get('beneficiario')}" if pd.notna(row.get("beneficiario")) else None
        
        # Conectar nodos si existen, agregando el id_siniestro como atributo del edge
        if id_asegurado and beneficiario:
            G.add_edge(id_asegurado, beneficiario, siniestro=id_siniestro)
        if id_asegurado and placa:
            G.add_edge(id_asegurado, placa, siniestro=id_siniestro)
        if placa and beneficiario:
            G.add_edge(placa, beneficiario, siniestro=id_siniestro)
            
    # 2. Encontrar componentes conectados
    components = list(nx.connected_components(G))
    
    # 3. Detectar Redes Sospechosas (Carruseles)
    # Criterio: Una componente es sospechosa si tiene una densidad alta o una 
    # concentración inusual de siniestros cruzados. 
    # Extraemos todos los 'id_siniestro' de cada componente.
    siniestros_sospechosos = set()
    
    for comp in components:
        # Extraer el subgrafo
        sub_G = G.subgraph(comp)
        
        # Extraer siniestros en este subgrafo
        siniestros_in_comp = set()
        for u, v, data in sub_G.edges(data=True):
            if 'siniestro' in data:
                siniestros_in_comp.add(data['siniestro'])
                
        # Heurística: Si un grupo conectado (Asegurados + Vehículos + Proveedores) 
        # genera 3 o más siniestros diferentes entre ellos, es un carrusel o red cerrada.
        # Ajustamos el umbral a >= 3
        if len(siniestros_in_comp) >= 3:
            # También verificamos que involucre a más de 1 asegurado o más de 1 vehículo
            # para no penalizar a un asegurado legítimo que chocó 3 veces.
            asegurados = [n for n in comp if n.startswith("ASEG_")]
            vehiculos = [n for n in comp if n.startswith("VEH_")]
            if len(asegurados) > 1 or len(vehiculos) > 1:
                siniestros_sospechosos.update(siniestros_in_comp)
                
    # 4. Asignar variable al DataFrame
    df["alerta_red_fraude"] = df["id_siniestro"].apply(
        lambda x: 1 if x in siniestros_sospechosos else 0
    )
    
    return df
