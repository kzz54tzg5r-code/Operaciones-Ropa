"""Entrada de producción para Render.

Las optimizaciones de memoria, los bloqueos de análisis y el procesamiento
aislado de Excel viven en ``web_app``. Mantener una sola implementación evita
que un parche de arranque reemplace las reglas funcionales del sistema.
"""
from web_app import app
