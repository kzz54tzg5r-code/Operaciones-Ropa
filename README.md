# ORION APP13 - Fix arranque GitHub

Corrección crítica:
- app.py con saltos de línea reales.
- requirements.txt con una dependencia por línea.

Motivo:
En GitHub el app.py estaba en una sola línea:
`import streamlit as st import traceback ...`
Eso genera SyntaxError antes de que Streamlit pueda mostrar el traceback, por eso aparecía "Oh no".
