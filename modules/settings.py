import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'config' / 'metas.json'

DEFAULT_METAS = {
    'meta_productividad_diaria': 784,
    'meta_recorridos_semanal': 47,
    'meta_conversion_pct': 80,
    'tiendas': ['Iztapalapa','Vallejo','Ecatepec','Toluca','Arco Norte','Ixtapaluca','Querétaro','Centro','Olivar','León','Puebla','Puebla Sur','Aguascalientes','Veracruz','Naucalpan','Miravalle','Atemajac']
}

def load_settings():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_METAS.copy()
