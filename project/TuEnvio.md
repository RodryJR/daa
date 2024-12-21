## Descripción del problema
Durante la covid el país para evitar las inmensas colas optó por el comercio electrónico, el cual ha sufrido bastantes problemas a lo largo del tiempo y debido a las actuales circunstancias **TuEnvio** enfrenta el desafío de planificar y gestionar de manera eficiente su cadena de suministro, que abarca múltiples niveles y medios de transporte. Sus operaciones incluyen el movimiento de bienes desde proveedores internacionales hasta centros de distribución y, posteriormente, a los consumidores finales. La empresa debe coordinar una red compleja que utiliza distintos modos de transporte, incluyendo trenes, barcos, aviones y camiones, cada uno con sus propias capacidades y costos. Un problema crítico para TuEnvio es garantizar que los bienes sean transportados de manera eficiente mientras se minimizan los costos y se cumplen las restricciones de capacidad en cada medio de transporte.

## Representación del problema 
El problema se modela como un grafo dirigido *G* = ( *V*, *E* ), donde:

***Nodos (*V*):***

- **Proveedores**: Nodos que representan las ubicaciones de los proveedores.
- **Centros de distribución**: Nodos intermedios donde los productos pueden almacenarse y redistribuirse.
- **Consumidores**: Nodos finales que representan la demanda de los clientes.

***Aristas (E):***
Representan las rutas de transporte entre nodos (por ejemplo, de un proveedor a un centro de distribución, o de un centro de distribución a un consumidor). Cada arista tiene:
- **Capacidad (c_ij)**: Cantidad máxima de producto que puede transportarse a través de esa ruta.
- **Costo por unidad de flujo (cost_ij)**: Costo asociado al transporte por esa ruta.

## Objetivo
TuEnvio necesita una solución integral que optimice:

1. La asignación de productos y recursos a través de los diferentes modos de transporte.
2. Las rutas de transporte para minimizar costos operativos.
3. El uso de capacidades de transporte y almacenamiento para evitar congestiones o subutilización.

Con esta modelación y optimización, TuEnvio busca garantizar entregas eficientes, reducir costos y mantener la satisfacción del cliente mientras gestiona una red de suministro cada vez más compleja y globalizada.