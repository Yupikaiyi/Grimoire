# Guía de Contribución - Proyecto Grimoire 🧙‍♂️

¡Gracias por querer formar parte del Proyecto Grimoire! Ya sea arreglando un error, añadiendo una nueva funcionalidad o mejorando la documentación, tu ayuda es lo que hace que este proyecto sea mágico.

Este proyecto está diseñado para una **hackathon**, por lo que valoramos la **velocidad, la claridad y la colaboración**.

---

## 🚀 Inicio Rápido para Participantes (Hackathon)

Si eres parte del equipo o un colaborador invitado durante el evento:

1.  **Revisa los Issues:** Busca etiquetas como `good first issue` o `hackathon-priority`.
2.  **Reporta tu Tarea:** Comenta en el issue o avisa por el canal de comunicación para que otros sepan en qué estás trabajando.
3.  **Sincronización Constante:** Mantente en contacto para evitar conflictos de código (merge conflicts).

---

## 🛠️ Configuración del Entorno

Sigue estos pasos para preparar tu entorno de desarrollo:

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/GrimoireProject/Grimoire.git
    cd Grimoire
    ```
2.  **Crea un Entorno Virtual:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # En Windows
    # source venv/bin/activate # En Unix/macOS
    ```
3.  **Instala las Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Base de Datos y Servicios:**
    Asegúrate de tener Docker funcionando para Elasticsearch:
    ```bash
    docker-compose up -d
    ```

---

## 🌿 Política de Ramas (Branching)

Para que la rama `main` esté siempre lista para la demo final:

*   **Ramas de Función (Feature Branches):** Crea una rama para cada tarea: `feat/logica-busqueda`, `fix/boton-ui`, `docs/api-endpoints`.
*   **Pull Requests:** Siempre apunta a la rama `develop` (si existe) o a `main` mediante un Pull Request. **Nunca hagas push directo a main en las últimas horas de la hackathon.**

---

## 📝 Estándares y Estilo de Código

*   **Python:** Sigue PEP 8. Usa nombres de variables descriptivos.
*   **Commits:** Usa [Commits Convencionales](https://www.conventionalcommits.org/es/v1.0.0/):
    *   `feat: añade capacidad de búsqueda vectorial`
    *   `fix: resuelve timeout de conexión con elasticsearch`
*   **Documentación:** Si añades una funcionalidad, actualiza el `README.md`.

---

## 📋 Ejemplos de Issues y Reportes

Para mantener el orden durante la hackathon, usa estos formatos:

### 1. Reporte de Error (Bug Report)
> **Título:** `fix: [Descripción corta del error]`
>
> **Descripción:**
> - **¿Qué pasa?:** El botón de búsqueda no responde al hacer clic.
> - **¿Cómo lo repito?:** Abrir `index.html`, escribir "test", pulsar Enter.
> - **Entorno:** Chrome en Windows 11.

### 2. Sugerencia de Mejora (Feature Request)
> **Título:** `feat: [Descripción corta de la mejora]`
>
> **Descripción:**
> - **Objetivo:** Añadir un filtro por fecha de creación.
> - **Por qué:** Ayuda al usuario a encontrar hechizos más recientes rápidamente.
> - **Esfuerzo estimado:** 2 horas.

---

## 🤝 Código de Conducta

Estamos aquí para aprender y construir juntos. Sé respetuoso, inclusivo y apoya a tus compañeros. No se tolerará ningún tipo de acoso.

---

## 🏆 Checklist para la Entrega Final

Antes de la fecha límite de la hackathon, asegúrate de que tu contribución:
- [ ] Pasa las pruebas locales básicas.
- [ ] Incluye las variables de entorno necesarias en `.env.example`.
- [ ] Tiene una descripción clara en el Pull Request de lo que añade o arregla.

¡Feliz hacking! 🚀
