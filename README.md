# ORION CORPORATIVO

Plataforma Indicadores de Recuperación de Mercancía  
PRICE SHOES | OPERACIONES ROPA

## Archivos
- `app.py`
- `requirements.txt`

## Deploy en Streamlit Cloud
1. Sube `app.py` y `requirements.txt` a GitHub.
2. En Streamlit Cloud crea una app nueva.
3. Repository: tu repositorio.
4. Branch: `main`.
5. Main file path: `app.py`.
6. Deploy.

## Acceso administrador
Clave por defecto:
`orion_admin`

Para cambiarla en Streamlit Cloud:
Settings > Secrets

```toml
ADMIN_PASSWORD = "tu_clave"
```

## Uso
1. Entra como Administrador.
2. Carga el Excel.
3. ORION guarda los datos en SQLite/Parquet.
4. Usuarios Consulta ya pueden ver dashboards sin cargar Excel.
