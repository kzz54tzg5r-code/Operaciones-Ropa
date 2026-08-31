# Operaciones Ropa V11

## Cambios y Muertos
- El Excel de Cambios y Muertos queda conectado directamente al módulo operativo.
- Se priorizan hojas mensuales y se evitan hojas de resumen para no duplicar información.
- La clasificación usa `Actividad Realizada + Motivo de ingreso`.
- Se calculan:
  - Cambios
  - Muertos
  - Cajas
  - Probador/Aduana
  - Piezas ingresadas
  - Acondicionado
  - Ubicado
  - Pendiente por ubicar
  - Productividad
  - Recorridos
- Al procesar el Excel, el sistema vuelve automáticamente a Cambios y Muertos.
- El periodo/semana filtra los registros operativos si el archivo tiene fechas válidas.

## Configuración de Metas
Disponible únicamente para Super Administrador y Administrador.

Metas iniciales heredadas del proyecto:
- Productividad diaria: 784
- Conversión: 80%
- Recuperación: 80%
- Acondicionado / Ingresos: 85%
- Ubicado / Ingresos: 80%
- Recorridos L/M/M: 5
- Recorridos J/V/S/D: 8
- Recorridos semanales: 47

Las modificaciones:
- se guardan en SQLite;
- conservan fecha/hora, usuario, valor anterior y valor nuevo;
- aplican sin reiniciar la aplicación.
