# Historial de Cambios (Changelog) - Proyecto Grimoire 🧙‍♂️

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [0.1.0] - 2026-02-28 (Lanzamiento Hackathon)

### Añadido
- **Estructura de Gobernanza:** Añadidos archivos de comunidad: `LICENSE` (Apache 2.0), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.
- **Integración de Búsqueda:** Configuración inicial de Elasticsearch mediante `docker-compose.yml`.
- **Lógica de IA:** Integración de `sentence-transformers` para capacidades de búsqueda semántica.
- **Herramientas de cumplimiento:** Instalación y configuración de `pip-licenses` para auditoría de dependencias.

### Cambiado
- **Requisitos del Sistema:** Actualizado `requirements.txt` para soportar **Python 3.13** en entornos Windows.
  - Actualizado `torch` a `>= 2.6.0`.
  - Actualizado `numpy` a `>= 2.1.0` para asegurar compatibilidad con wheels pre-construidos.

### Corregido
- **Entorno Virtual:** Resueltos problemas de instalación de dependencias pesadas en arquitecturas Windows modernas.
- **Configuración de ES:** Ajustada la seguridad de Elasticsearch en el entorno de desarrollo para facilitar el acceso inicial.

---
*Nota: Este proyecto comenzó como una entrada de hackathon. Las versiones anteriores a la 0.1.0 corresponden a fases de prototipado rápido.*
