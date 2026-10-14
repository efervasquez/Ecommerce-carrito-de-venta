### AGENTS.md

### 1. Project Overview

* **Sistema:** E-commerce escalable con carrito de compras, catálogo agrupado por categorías, gestión de inventario (stock), control de listas de precios, pasarela de pagos integrada y un módulo centralizado de generación de usuarios con control de permisos y roles (RBAC).
* **Problema que resuelve:** Automatiza la venta digital masiva mediante una experiencia web altamente adaptable a dispositivos móviles (PWA/Responsive), garantizando transacciones seguras, control de accesos estricto y actualizaciones reactivas en tiempo real.
* **Arquitectura general:** Sistema desacoplado basado en una Arquitectura Orientada a Eventos (EDA). El backend se expone mediante APIs asíncronas y microservicios locales protegidos dentro de la red corporativa privada, comunicados a través de un bus de eventos / broker de mensajería central que reacciona a los cambios de estado de manera reactiva hacia un frontend en React.

### 2. Repository Structure

```text
├── .agents/                # Configuraciones internas del agente
├── docs/                   # Documentación global del proyecto (Formatos Markdown y Wireframes)
│   ├── pm/                 # Resultados de Product Manager (Roadmaps, Epics)
│   ├── ba/                 # Resultados de Business Analyst (User Stories, Reglas de negocio)
│   ├── ux/                 # Resultados de Diseñador UX (Design System, Figma links, Wireframes)
│   ├── qa/                 # Resultados de Quality Assurance (Test Cases, Reportes de bugs)
│   └── aq/                 # Resultados de Architect Agent (Diagramas de arquitectura, Event Storming)
├── backend/                # Código fuente de Python (Servicios IIS / FastAPI)
│   ├── src/                # Lógica de negocio, controladores de endpoints e identidades
│   └── tests/              # Pruebas unitarias e integración de backend
├── frontend/               # Código fuente de React (Web & Adaptabilidad App)
│   ├── src/                # Componentes, Contextos y Hooks
│   └── tests/              # Pruebas de componentes y E2E
├── infra/                  # Scripts de configuración de infraestructura (PowerShell / Docker Compose local)
├── Agents.md               # Este archivo de reglas del proyecto
└── README.md               # Instrucciones generales de inicialización
```

* **Carpetas importantes:** Las subcarpetas dentro de `docs/` (`pm`, `ba`, `ux`, `qa`, `aq`) son estructurales; contienen los entregables de cada agente y deben actualizarse antes de escribir código utilizando archivos Markdown (`.md`) y enlaces a Wireframes.
* **Qué NO debe tocar:** No modificar estructuras de carpetas raíz ni alterar configuraciones globales de red local, firewall del servidor o empaquetado sin aprobación cruzada entre el Agente Arquitecto (Aq) y el Product Manager (PM).

### 3. Tech Stack

* **Runtime:** Python 3.12+ (Backend) / Node.js 20+ (Frontend).
* **Framework:** FastAPI con soporte para WSGI/ASGI en entornos Windows (Backend) y React 18+ con Vite (Frontend).
* **Servidor Web:** Internet Information Services (IIS 10) en Windows 11 Pro, utilizando el módulo **HttpPlatformHandler** o **FastCGI** para el enrutamiento hacia la aplicación Python.
* **Database:** MySQL Server (Instancia unificada u optimizada localmente para el catálogo, carritos, sesiones, datos transaccionales de compras, usuarios y permisos).
* **Infrastructure:** Servidor físico / On-Premise dentro de red LAN interna protegida: Windows 11 Pro con IIS 10, Firewall de Windows avanzado, un Broker de mensajería local (ej. RabbitMQ o Mosquitto) para el bus de eventos de la arquitectura reactiva, y orquestación de tareas en segundo plano mediante hilos asíncronos o Celery sobre Windows.
* **Testing:** Pytest (Backend) / Jest, React Testing Library y Cypress (Frontend).
* **Package manager:** poetry (Python) / pnpm o npm (JavaScript).

### 4. Development Workflow

* **Cómo levantar el proyecto:** 
  * Backend: Ejecución del servidor de desarrollo local de FastAPI (`uvicorn src.main:app --reload`) o mediante el sitio configurado localmente en IIS 10.
  * Frontend: `cd frontend && pnpm dev`.
* **Cómo ejecutar tests:** 
  * Python: `pytest`
  * React: `pnpm test`
* **Cómo hacer lint:** 
  * Python: `black . && flake8`
  * React: `pnpm lint`
* **Cómo buildar:** 
  * Backend: Preparación del empaquetado para distribución en el directorio raíz de IIS o scripts de despliegue automatizados en PowerShell.
  * Frontend: `pnpm build`.
* **Cómo ejecutar migraciones:** Las configuraciones de bases de datos relacionales (MySQL), tablas, índices, usuarios y permisos se gestionan y ejecutan localmente mediante herramientas de migración tradicionales (Alembic para Python), integradas en los scripts de despliegue del servidor.

### 5. Architecture Rules

* **Principios que deben respetarse:** Arquitectura dirigida por eventos (Event-Driven), Principios SOLID, Desacoplamiento estricto, Privacidad por diseño (Zero Trust) e Inmutabilidad de eventos.
* **Dependencias permitidas:** Librerías estándar de Python, conectores oficiales de MySQL (`mysql-connector-python` o `aiomysql`), frameworks de validación oficiales (`Pydantic` para Python, `Zod` para TypeScript/React).
* **Patrones obligatorios:** Control de Accesos Basado en Roles (RBAC) para el módulo de usuarios, CQRS para separar lecturas de escrituras en el catálogo, y Patrón Saga o transacciones MySQL nativas para flujos que involucren pasarela de pagos y liberación de stock.
* **Patrones prohibidos:** Exponer puertos de la base de datos MySQL directamente a internet público, comunicación directa HTTP síncrona bloqueante entre microservicios cuando deba ser asíncrona (todo flujo desacoplado debe ir por el broker de eventos local) e inyección de secretos o credenciales en texto plano en el código fuente.

### 6. Coding Conventions

* **Naming:** 
  * Python: `snake_case` para variables/funciones, `PascalCase` para clases.
  * React: `camelCase` para variables/funciones, `PascalCase` para componentes.
* **Organización de archivos:** Estructura limpia por capas dentro del proyecto backend (`Handler/Route -> Controller -> Service -> Repository`).
* **Error handling:** Bloques try-except explícitos. Mapear excepciones de seguridad a códigos HTTP estándar (401 Unauthorized, 403 Forbidden). Cualquier error imprevisto debe registrarse en logs locales bloqueando fugas de información.
* **Logging:** Uso obligatorio de un Logger estructurado en formato JSON (como Python `logging` configurado para JSON) con inyección de un `correlation_id` para trazabilidad de eventos. Prohibido hacer log de datos sensibles (contraseñas, tarjetas de crédito, datos personales).
* **Async patterns:** Uso de `async/await` nativo en Python para optimizar la concurrencia y reducir los tiempos de respuesta del servidor IIS ante solicitudes masivas.
* **DTOs / types / interfaces:** Todo payload de evento o petición de usuario debe estar estrictamente tipado y validado usando modelos de `Pydantic` en el backend.

### 7. Testing

* **Qué debe testearse:** Lógica de negocio, validadores de permisos (RBAC), flujos de transacciones de pago, concurrencia en stock y validadores de esquemas de eventos.
* **Dónde están los tests:** En las carpetas `/tests` adyacentes al código fuente.
* **Cómo ejecutar los tests:** Automatizado en el pipeline de Integración Continua (CI/CD) local o antes de copiar los archivos al directorio de producción de IIS.
* **Qué cobertura/reglas aplican:** Cobertura mínima del 85% en el backend de seguridad, usuarios y pasarela de pagos.

### 8. Security (Anti-Hacker & Network Control)

* **Seguridad Perimetral:** El servidor IIS 10 debe configurarse detrás de una DMZ o un proxy inverso/firewall físico/lógico local que bloquee ataques comunes (SQL Injection, XSS, Bad Bots, OWASP Top 10) y mitigue denegación de servicio (DDoS). Se deben usar las reglas de restricción de IP y el módulo de seguridad de IIS.
* **Aislamiento de Red:** El servidor de base de datos MySQL debe residir exclusivamente en una red interna privada o escuchar únicamente en la interfaz de bucle invertido local (`127.0.0.1`), bloqueando cualquier acceso externo directo a nivel de Firewall de Windows. El acceso público queda restringido únicamente al puerto HTTPS de IIS.
* **Manejo de secretos:** Uso estricto de variables de entorno seguras del sistema Windows o archivos de configuración cifrados fuera de la raíz web de IIS. Queda terminantemente prohibido escribir credenciales en el código fuente.
* **Autenticación/autorización:** Implementado bajo un esquema seguro de tokens firmado y verificado con un módulo estricto de roles. Cada endpoint debe validar los alcances (*scopes*) antes de procesar una solicitud.
* **Acciones prohibidas:** Ejecutar el pool de aplicaciones de IIS con privilegios de Administrador del sistema (`Administrator`). Se debe aplicar estrictamente el principio de mínimo privilegio asignando identidades de servicio virtuales limitadas (`ApplicationPoolIdentity`).

### 9. Database & Resource Optimization

* **Optimización de Recursos Locales:** Dado que los recursos de hardware son fijos y limitados en el servidor local, se prohíbe el desperdicio de memoria. La base de datos MySQL debe contar con un pool de conexiones optimizado para evitar la saturación de sockets. Se deben implementar scripts programados (Tareas programadas de Windows) que actúen como políticas de ciclo de vida para purgar carritos abandonados antiguos directamente en las tablas correspondientes.
* **Schema:** Diseñado por el Agente Arquitecto (Aq) en `docs/aq/` usando formatos Markdown.
* **Migrations:** Automatizadas mediante scripts de Alembic en Python controlados durante las ventanas de mantenimiento del servidor.
* **Seed:** Scripts controlados para generar usuarios de prueba con diferentes niveles de permisos y catálogos iniciales agrupados.

### 10. Git & PR Rules

* **Naming de branches:** `feat/nombre-tarea`, `fix/descripcion-error`, `security/parche-seguridad`, `docs/agente-cambio`.
* **Commits:** Convención de *Conventional Commits* (ej. `feat(auth): implement RBAC middleware for admin permissions`).
* **PR expectations:** Los PR deben pasar los tests automatizados, análisis estáticos de seguridad (SAST) para evitar vulnerabilidades de código y requerir la firma del Agente QA y del Agente Arquitecto (Aq).

### 11. Agent Instructions

* **Dirección estratégica:** El Product Manager (PM) dirige el flujo y orquesta las tareas. Ningún agente actúa sin la asignación de su respectiva Epic/User Story.
* **Conectividad externa (MCP):** Los agentes se conectarán vía MCP a herramientas externas autorizadas para el diseño de wireframes, generación de código, empaquetado para IIS, testing de penetración local, compilación y auditorías de código.
* **Antes de modificar código:** El agente debe validar que los cambios mantengan la compatibilidad con el entorno Windows/IIS, asegurando la correcta gestión asíncrona de FastAPI bajo procesos FastCGI o HttpPlatformHandler, y comprobar que no se rompan las reglas de acceso del firewall local.
* **Después de modificar código:** Actualizar la documentación en su respectiva carpeta bajo `docs/` en formato Markdown, adjuntando wireframes o diagramas si corresponde.