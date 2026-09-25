# Equipo de desarrollo

El desarrollo se coordina con cinco funciones especializadas. El orquestador integra el trabajo y evita que dos especialistas editen simultáneamente los mismos archivos.

| Función | Responsabilidad | Entrega esperada |
| --- | --- | --- |
| Orquestador sénior | Alcance, dependencias, coordinación, documentación y entrega | Versión integrada y estado verificable |
| Backend sénior | API, reglas de negocio, adaptadores, datos y migraciones | Código probado, transacciones y errores coherentes |
| Frontend sénior | Flujos React, accesibilidad, estados y presentación adaptable | Interfaz funcional conectada a la API |
| QA sénior | Pruebas de integración, regresión y recorridos por rol | Evidencia reproducible de resultados y defectos |
| Seguridad sénior | Autorización, RLS, aislamiento de datos, archivos y secretos | Hallazgos priorizados y validación de correcciones |

Backend y frontend tienen ámbitos separados. Seguridad realiza revisión independiente y comunica los hallazgos al responsable del componente. QA revisa la versión integrada después de los primeros cambios. Un resultado local satisfactorio no se presenta como validación de un servicio externo no configurado.

Las decisiones y límites de cada entrega quedan en los documentos de fase y validación. No se incluyen credenciales en informes, archivos versionados ni paquetes de exportación.
