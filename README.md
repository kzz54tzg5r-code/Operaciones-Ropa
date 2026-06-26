# ORION APP13 - Conversión Semanal Dev → Venta Final

Cambios:
- Indicador Conversión Semanal Dev → Venta.
- Regla: devolución sólo cuenta si la venta ocurrió en la misma Semana ISO.
- Cálculo amarrado a Tienda + ID/Modelo + Color + Talla + Semana ISO.
- Si se consultan varias semanas, calcula semana por semana y luego suma.
- KPIs:
  Dev Pzs Semana
  Conversión Dev → Venta Pzs
  Conversión Dev → Venta $
  % Conversión Semanal Dev → Venta
  Pendiente por Convertir Pzs
- Recuperación Económica usa la misma lógica semanal.
- Corrección de formato: Conv. Pzs y Conv. $ ya no se muestran como porcentaje.
