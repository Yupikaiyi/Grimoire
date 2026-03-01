# Política de Seguridad - Proyecto Grimoire 🛡️

La seguridad del Proyecto Grimoire es una prioridad. Queremos que el conocimiento mágico que almacenamos esté protegido de cualquier uso indebido.

## Versiones Compatibles

Actualmente, solo proporcionamos actualizaciones de seguridad para la versión activa durante esta hackathon.

| Versión | Soportada |
| ------- | --------- |
| 0.1.x   | ✅ Sí      |
| < 0.1.0 | ❌ No      |

---

## Reporte de Vulnerabilidades

**¡No abras un issue público para reportar un problema de seguridad!**

Si descubres una vulnerabilidad en este proyecto, por favor sigue estos pasos:

1.  Envía un mensaje privado a los mantenedores del proyecto (a través de nuestro canal de Discord/Telegram o al correo electrónico de contacto).
2.  Incluye una descripción detallada del problema y, si es posible, los pasos para reproducirlo.
3.  Danos un tiempo razonable para investigar y solucionar el problema antes de hacerlo público.

---

## Mejores Prácticas para Desarrolladores

Si estás contribuyendo al código, por favor ten en cuenta:

*   **No subas secretos:** Nunca incluyas claves de API (`ELASTIC_PASSWORD`, claves de OpenAI, etc.) directamente en el código. Usa archivos `.env`.
*   **Limpieza de datos:** Asegúrate de que las entradas del usuario se limpien antes de procesarlas (evita inyecciones SQL o ataques XSS).
*   **Dependencias:** Mantén las dependencias actualizadas para evitar vulnerabilidades conocidas en librerías de terceros (como Flask o Werkzeug).

---

## Divulgación Responsable

Agradecemos a todos aquellos que nos ayudan a mantener el proyecto seguro. Prometemos revisar todos los reportes de manera diligente y dar crédito a los investigadores que nos ayuden a mejorar nuestra seguridad.
