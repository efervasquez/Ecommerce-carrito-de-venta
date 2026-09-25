# AGENTS.md

---

# SECCIÓN 1: CONTEXTO

## 1.1 Marco Transversal de Proyectos Tecnológicos
- **Naturaleza del estándar:** Este documento establece el marco operativo y los estándares de calidad para equipos de agentes y desarrolladores de software.
- **Carácter transversal:** Aplica a cualquier proyecto tecnológico; no contiene reglas de negocio fijas ni decisiones acopladas a un dominio específico.
- **Alineación con el ciclo de vida:** Cubre de punta a punta: desde el descubrimiento y especificación funcional hasta la arquitectura, desarrollo y calidad.

## 1.2 Origen del Contexto Específico del Proyecto
- **Fuente de verdad:** El contexto funcional (problema, objetivos, actores, alcance) se obtiene **exclusivamente del insumo activo del proyecto** (PRD, brief o especificación de requerimientos).
- **Límites:** Los agentes deben respetar estrictamente el dominio y alcance fijado en dicho insumo.

<!-- PENDIENTE DE DEFINIR (Contexto):
  - [ ] Determinar si se creará un archivo específico de Arquitectura de Referencia por proyecto (ej. ARCHITECTURE.md).
-->

---

# SECCIÓN 2: REGLAS

## 2.1 Reglas Metodológicas de Análisis y Negocio
- **Cero asunciones:** Si el insumo funcional (PRD) no confirma un dato, regla o decisión, no se asume ni se elige "la opción más común". Se registra obligatoriamente como **`Punto Abierto`** con la pregunta exacta para el negocio.
- **Manejo de supuestos:** Solo se conservan supuestos si el insumo funcional los declara explícitamente. Prohibido inventar reglas, flujos, canales o datos.
- **Exclusiones estrictas:** No se redactan HUs ni se implementan funcionalidades marcadas en **No incluye** (fuera de alcance).

## 2.2 Reglas de Historias de Usuario (HUs)
- **Ubicación física:** Cada historia debe guardarse en un archivo Markdown independiente dentro de la carpeta `HUs/` en la raíz del proyecto.
- **Nomenclatura:** `HU-` + número correlativo de dos dígitos + descripción breve en minúsculas separada por guiones (ej. `HU-01-agendar-cita.md`).
- **Estructura obligatoria:**
  1. Título descriptivo.
  2. Historia en formato estándar: `Como [rol] quiero [acción] para [beneficio]`.
  3. Alcance específico de la HU.
  4. Criterios de aceptación funcionales.
  5. **Escenarios Gherkin (mínimo 2):** Al menos un camino feliz y un caso borde (`Given` / `When` / `Then`).
  6. Puntos Abiertos (pregunta exacta).
  7. Exclusiones ("No incluye").
- **Casos borde condicionales:** Todo caso borde dependiente de una decisión pendiente se marca explícitamente como "Pendiente" y no es implementable hasta resolverse.

<!-- PENDIENTE DE DEFINIR (Historias de Usuario):
  - [ ] Definir si se usará una plantilla / template Markdown oficial para la creación de las HUs.
  - [ ] Definir criterio de estimación de esfuerzo o complejidad (ej. Story Points, T-shirt size) si aplica.
-->

## 2.3 Reglas de Calidad y Definición de Terminado (DoD)
- **Definición de Terminado (DoD):** Una funcionalidad solo se considera terminada cuando:
  1. Cumple todos los criterios de aceptación y escenarios Gherkin.
  2. Posee pruebas asociadas que validan el comportamiento esperado.
  3. No introduce errores en el resto del sistema.
  4. La documentación técnica y de usuario asociada está actualizada.
- **Trazabilidad:** Toda tarea o cambio de código debe relacionarse directamente con su respectiva HU.

<!-- PENDIENTE DE DEFINIR (Calidad):
  - [ ] Umbral mínimo de cobertura de pruebas unitarias (ej. 80%).
  - [ ] Herramienta/framework de pruebas a utilizar (ej. Jest, PyTest, JUnit, etc.).
  - [ ] Criterio de revisión de código (Pull Request con mínimo 1 aprobación humana o de agente reviewer).
-->

## 2.4 Reglas de Desarrollo y Código
- **Principios SOLID obligatorios:** Todo diseño e implementación orientada a objetos debe adherirse rigurosamente a los principios SOLID:
  - **S (Responsabilidad Única):** Cada clase, función o módulo debe tener una única responsabilidad y una sola razón para cambiar.
  - **O (Abierto/Cerrado):** El código debe estar abierto a la extensión pero cerrado a la modificación directa.
  - **L (Sustitución de Liskov):** Las clases derivadas deben poder sustituir a sus clases base sin alterar el correcto funcionamiento del sistema.
  - **I (Segregación de Interfaces):** Preferir múltiples interfaces específicas y reducidas en lugar de una interfaz genérica y sobrecargada.
  - **D (Inversión de Dependencias):** Los módulos de alto nivel deben depender de abstracciones (interfaces/contratos), nunca de implementaciones concretas.
- **Alcance acotado:** No alterar ni refactorizar archivos o componentes ajenos al objetivo específico de la tarea en curso.
- **Cero secretos en código:** Prohibido escribir contraseñas, tokens o API keys en el código fuente. Toda credencial debe inyectarse mediante variables de entorno (`.env`).
- **Código limpio y legible:** Seguir estándares de nomenclatura autoexplicativa, modularidad y separación de capas.

<!-- PENDIENTE DE DEFINIR (Desarrollo):
  - [ ] Stack tecnológico y versiones oficiales (lenguajes, frameworks, librerías base).
  - [ ] Herramientas de formateo y linters obligatorios (ej. Prettier, ESLint, Black, SonarLint).
  - [ ] Convención de commits (ej. Conventional Commits: `feat:`, `fix:`, `chore:`).
  - [ ] Estrategia de ramas Git (ej. Trunk-Based Development o GitFlow).
-->

## 2.5 Reglas de Arquitectura y Documentación
- **Diseño API-First:** Si el proyecto expone o consume servicios, estos deben documentarse con especificaciones abiertas (ej. OpenAPI / Swagger).
- **Documentación viva:** Mantener actualizados los diagramas de arquitectura y el archivo `README.md` con las instrucciones de ejecución y configuración.
- **Registro de decisiones (ADRs):** Toda decisión arquitectural relevante que altere la estructura del proyecto debe quedar registrada formalmente.

<!-- PENDIENTE DE DEFINIR (Arquitectura):
  - [ ] Ubicación de las Decisiones de Arquitectura (ej. carpeta `docs/adr/`).
  - [ ] Formato de diagramación estándar (ej. C4 Model con Mermaid.js).
-->

## 2.6 Reglas Técnicas y de Seguridad
- **Herramientas MCP:** Se configuran exclusivamente en `opencode.json`.
- **Protección de credenciales:** Si `opencode.json` u otro archivo contiene API keys o tokens embebidos, **está estrictamente prohibido compartirlos, exponerlos o commitearlos**.

<!-- PENDIENTE DE DEFINIR (Seguridad):
  - [ ] Escaneo automatizado de vulnerabilidades y secretos en CI/CD (ej. GitGuardian, SonarQube, Dependabot).
-->

## 2.7 Reglas de Idioma y Comunicación
- Toda la documentación, especificaciones, comentarios de código y comunicación entre agentes o con el usuario debe ser en **español neutro**.

## 2.8 Reglas de Coordinación entre Agentes
- La orquestación y comunicación entre agentes se realiza mediante el CLI `herdr`:
  - Enviar prompts: `herdr agent prompt <AGENTE> "<mensaje>"`
  - Monitoreo y lectura: `herdr agent list` / `herdr agent read`