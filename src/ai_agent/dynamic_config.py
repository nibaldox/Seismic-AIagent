"""Utilidades para manejo dinámico de configuración de agentes basado en selección de modelo."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def create_dynamic_agents_config(selected_model: str, base_config_path: str = "config/agents_config.yaml") -> Dict[str, Any]:
    """
    Crea una configuración de agentes dinámicamente basada en el modelo seleccionado.
    
    Args:
        selected_model: ID del modelo seleccionado (ej: "moonshotai/kimi-k2:free")
        base_config_path: Ruta al archivo de configuración base
        
    Returns:
        Diccionario con la configuración actualizada
    """
    # Cargar configuración base
    with open(base_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Actualizar todos los agentes con el modelo seleccionado
    if 'agents' in config:
        for agent_key, agent_config in config['agents'].items():
            if 'model' in agent_config:
                # Mantener el proveedor como openrouter para todos los modelos listados
                agent_config['model']['id'] = selected_model
                # Todos los modelos listados son de OpenRouter
                agent_config['model']['provider'] = "openrouter"
    
    return config

def save_dynamic_config(config: Dict[str, Any], output_path: str = "config/agents_config_dynamic.yaml") -> None:
    """
    Guarda la configuración dinámica en un archivo temporal.
    
    Args:
        config: Configuración de agentes
        output_path: Ruta donde guardar el archivo
    """
    Path(output_path).parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def get_dynamic_config_path(selected_model: str) -> str:
    """
    Crea y retorna la ruta a un archivo de configuración dinámico para el modelo seleccionado.
    
    Args:
        selected_model: ID del modelo seleccionado
        
    Returns:
        Ruta al archivo de configuración dinámico
    """
    # Crear configuración dinámica
    config = create_dynamic_agents_config(selected_model)
    
    # Guardar en archivo temporal
    output_path = "config/agents_config_dynamic.yaml"
    save_dynamic_config(config, output_path)
    
    return output_path