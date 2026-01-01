---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/research/technical-soni-vs-rasa-calm-research-2026-01-01.md'
  - 'docs/architecture.md'
  - 'docs/project-overview.md'
  - 'docs/source-tree-analysis.md'
workflowType: 'prd'
lastStep: 4
project_name: 'soni'
user_name: 'Jorge'
date: '2026-01-01'
documentCounts:
  briefs: 0
  research: 1
  brainstorming: 0
  projectDocs: 10
---

# Product Requirements Document - {{project_name}}

**Author:** {{user_name}}
**Date:** {{date}}

## Executive Summary

**TL;DR**: Soni Framework v0.5.0 is a foundational architectural redesign that makes the framework production-ready by solving critical conversation flow reliability issues. It introduces a centralized interrupt architecture via the `human_input_gate` node and implements all 6 Rasa CALM conversational patterns (start flow, cancel flow, clarify flows, set slot, correct slot, chitchat) at full implementation level, enabling bot builders to create complex, reliable multi-turn conversations for the first time.

---

**Soni Framework v0.5.0** represents a fundamental architectural redesign to establish stability and maintainability after identifying critical flaws in v0.4.0. This release focuses on "Fresh Start & Core Architecture" - eliminating technical debt and establishing patterns that enable bot builders to create reliable, complex conversational AI systems.

### The Problem

The v0.4.0 codebase suffered from three critical architectural issues that made production deployment unreliable:

1. **Fragmented Interrupt Architecture**: LangGraph interrupts occurred at multiple nodes (\`confirm\`, \`collect\`, and other user-input nodes), creating a combinatorial explosion of resume logic. Each interrupt point had to independently handle:
   - Conversation resumption from the correct state
   - Digression detection and recovery (user changing context mid-flow)
   - All possible conversational patterns at that specific point

   **Impact**: Spent hours debugging state corruption issues. Attempting to fix digression handling in one node would create bugs in others. **E2E tests could not pass** - the fundamental architecture made reliable conversation flow impossible.

2. **Mixed Responsibilities**: Business logic, infrastructure concerns, and orchestration were intermingled across modules, violating separation of concerns and making changes unpredictable

3. **Documentation Obsolescence**: The architectural redesign rendered all existing documentation misleading and unusable

### The Solution

Version 0.5.0 introduces a **centralized interrupt architecture** anchored by the \`human_input_gate\` node, implementing all 6 core conversational patterns from Rasa CALM:

**Technical Architecture:**

\`\`\`
Graph Flow: human_input_gate → nlu → orchestrator → (loop back if pending_task)
             ↑_______interrupt point (LangGraph's interrupt() mechanism)_______|
\`\`\`

**Before (v0.4.0):**
- Multiple interrupt points scattered across \`confirm\`, \`collect\`, and custom input nodes
- Each node implemented its own resumption + digression handling logic
- Conversational patterns duplicated across the codebase
- Complex conversations were unreliable

**After (v0.5.0):**
- **Single interrupt point**: \`human_input_gate.py\` node (all LangGraph interrupts occur here)
- **Predictable flow**: Entry point → NLU → Orchestrator → Loop back to gate if task pending
- **Centralized pattern handling**: All 6 Rasa CALM conversational patterns implemented at Level 3 (detect + handle + graceful recovery with context preservation):

| Pattern | Rasa CALM Definition | Implementation Level |
|---------|---------------------|---------------------|
| \`start flow\` | User wants to complete a specific flow | Level 3: Full context-aware routing |
| \`cancel flow\` | User doesn't want to continue current flow | Level 3: Graceful flow termination + cleanup |
| \`clarify flows\` | **System asks for clarification** when multiple flows could apply to user input | Level 3: Smart disambiguation with context |
| \`set slot\` | User provides a value for required slot | Level 3: Validation + context preservation |
| \`correct slot\` | User updates previously provided slot value | Level 3: Retroactive correction with flow continuity |
| \`chitchat\` | User makes small-talk (digression from flow) | Level 3: Handle digression + seamless return to flow |

**Note**: RAG/knowledge retrieval patterns explicitly deferred to v0.7.5

### Core Deliverables (Sequential Execution Order)

**Solo developer workflow - items executed in sequence:**

1. **Documentation Cleanup** (#18): Complete rewrite of all documentation to match new \`src/soni\` architecture, removing obsolete references (ADR-001, ADR-002, archive/* links)

2. **Core Refinement** (#19): Formalize interfaces through \`INLUProvider\` and \`IDialogueManager\` protocols for clean separation of concerns

3. **Zero-Leakage Audit** (#20): Systematic validation pass ensuring business logic remains pure with no infrastructure concerns leaking into domain code

4. **Conversational Pattern Library**: Full implementation (Level 3) of all 6 Rasa CALM patterns at the \`human_input_gate\`, with context preservation and smart recovery

5. **E2E Test Suite**: 3-4 comprehensive E2E tests covering different complex conversation scenarios in banking domain (e.g., transfer with mid-conversation chitchat, slot correction, flow cancellation, multi-flow clarification)

**Explicitly Out of Scope for v0.5.0:**
- ❌ Event Architecture (#21) - Deferred to v0.6.0 (prerequisite for TUI decoupling)
- ❌ RAG/Knowledge patterns - Deferred to v0.7.5
- ❌ TUI implementation - Deferred to v0.6.0

### What Makes This Special

**For Bot Builders (Primary Audience):**

1. **Complete Conversational Toolkit**: All 6 fundamental Rasa CALM patterns implemented from day one - bot builders can create sophisticated conversations without worrying about edge cases. The system handles flow switching (\`start flow\`), user changes of mind (\`cancel flow\`), ambiguity (\`clarify flows\`), data input (\`set slot\`), corrections (\`correct slot\`), and digressions (\`chitchat\`).

2. **Debuggable by Design**: When conversations behave unexpectedly, there's exactly one place to investigate - \`human_input_gate.py\` - with clear visibility into interrupt/resume mechanics. This reduces debugging time from hours to minutes.

3. **Production-Ready Stability**: By solving the fundamental interrupt architecture problem, v0.5.0 makes Soni deployable in production scenarios for the first time. The architecture won't fight you anymore.

4. **Extensible Foundation**: All 6 patterns localized at the gate. Clean protocol-based interfaces (\`INLUProvider\`, \`IDialogueManager\`) make the system maintainable as complexity grows.

### Success Criteria (Non-Negotiable)

**v0.5.0 Release Requirements:**

✅ **All four workstreams completed:**
- Documentation cleanup (all docs reviewed and updated to match \`src/soni\`)
- Core Refinement (protocols implemented)
- Zero-Leakage Audit (validation pass completed)
- Conversational Patterns (all 6 patterns at Level 3)

✅ **All 6 conversational patterns working at Level 3:**
- \`start flow\`, \`cancel flow\`, \`clarify flows\`, \`set slot\`, \`correct slot\`, \`chitchat\`
- Each pattern handles edge cases gracefully with context preservation

✅ **Test Coverage:**
- **Manual testing**: Banking domain scenarios verified manually
- **Automated E2E tests**: 3-4 comprehensive tests covering different complex conversation use cases
- All E2E tests pass reliably and consistently

✅ **Documentation accuracy**:
- \`src/soni\` is single source of truth
- All docs reflect actual implementation
- No broken references to non-existent files

✅ **No deadline** - quality over speed. Release when all criteria are met.

**Example Success Scenarios:**

1. **Multi-turn transfer with chitchat + correction**:
   - User initiates transfer (\`start flow\`)
   - Mid-flow, user makes small-talk about weather (\`chitchat\`)
   - System handles digression, returns to transfer
   - User corrects transfer amount (\`correct slot\`)
   - Transfer completes successfully

2. **Ambiguous intent with clarification**:
   - User says "I want to check something"
   - System detects multiple possible flows (\`clarify flows\`)
   - System asks: "Would you like to check your balance or transaction history?"
   - User clarifies, flow continues

3. **Flow cancellation + new flow**:
   - User starts bill payment (\`start flow\`)
   - Mid-flow, user changes mind (\`cancel flow\`)
   - User initiates transfer instead (\`start flow\`)
   - System gracefully switches flows

## Project Classification

**Technical Type:** Python Library/Framework (Conversational AI)
**Domain:** Conversational AI / NLU / Dialogue Management
**Complexity:** High - Combines DSPy prompt optimization, LangGraph state management, hexagonal architecture
**Project Context:** Brownfield - Major architectural refactoring of existing v0.4.0 system
**Primary Audience:** Bot builders (developers creating conversational AI applications)
**Development Model:** Solo developer, sequential workstream execution
**Inspiration Source:** Rasa CALM conversational patterns (all 6 core patterns adapted to Soni architecture)

**Strategic Position:** Developer-first conversational AI framework with modern architecture patterns (async-first, centralized state management via \`human_input_gate\`, protocol-based interfaces) that prioritizes **reliability and debuggability** over feature quantity. Establishes stable foundation for advanced features (RAG, TUI, optimization) in subsequent releases (v0.6.0+).


## Success Criteria

### User Success

**For Bot Builders (Primary Users):**

1. **Build Reliable Complex Conversations**: Bot builders can implement sophisticated multi-turn dialogues with all 6 Rasa CALM patterns (start flow, cancel flow, clarify flows, set slot, correct slot, chitchat) working reliably

2. **Debug Efficiently**: When issues occur, developers can identify and fix conversation problems in minutes instead of hours by investigating a single location (\`human_input_gate.py\`)

3. **Extend Confidently**: Adding new conversational patterns is straightforward and localized - developers aren't afraid to extend the framework

4. **Deploy to Production**: Framework is stable enough that bot builders feel confident deploying their conversational AI applications to production environments

**Success Moment**: "Finally, I can build the complex banking bot I envisioned without fighting the framework"

### Business Success

**Project Success Indicators:**

1. **Technical Foundation Solid**: All E2E tests pass consistently - no more hours lost debugging state corruption

2. **Documentation Complete**: Fresh, accurate documentation enables future development and potential contributors

3. **Architecture Validated**: Clean separation of concerns (protocols, zero-leakage) proven through implementation

4. **Roadmap Unblocked**: v0.5.0 establishes foundation for RAG (v0.7.5), TUI (v0.6.0), and optimization (v0.8.0) features

**Since you're the solo developer, business success = technical foundation that enables future growth**

### Technical Success

**Non-Negotiable Technical Requirements:**

1. **Centralized Interrupt Architecture**: \`human_input_gate.py\` is the single point of interrupt/resume - no exceptions

2. **All 6 Patterns Implemented**: Every Rasa CALM pattern working at Level 3 (detect + handle + graceful recovery with context preservation)

3. **Protocol Interfaces**: \`INLUProvider\` and \`IDialogueManager\` protocols formalized and implemented

4. **Zero-Leakage Validated**: Business logic completely separated from infrastructure - audit pass completed

5. **Test Coverage**: 3-4 comprehensive E2E tests covering complex conversations in banking domain - all passing reliably

### Measurable Outcomes

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| **E2E Test Pass Rate** | 100% consistent | Automated test suite |
| **Conversational Patterns** | All 6 at Level 3 | Manual + automated testing |
| **Interrupt Points** | Exactly 1 (\`human_input_gate\`) | Code inspection |
| **Documentation Coverage** | 100% of implemented features | Manual review against \`src/soni\` |
| **Protocol Implementation** | \`INLUProvider\`, \`IDialogueManager\` complete | Code review |
| **Debugging Time** | Reduced from hours to minutes | Real-world usage validation |

## Product Scope

### MVP - Minimum Viable Product (v0.5.0)

**Must Have - All items are non-negotiable:**

1. **Documentation Cleanup** (#18)
   - All docs rewritten to match \`src/soni\` architecture
   - No broken references (ADR-001, ADR-002, archive/*)
   - English only throughout

2. **Core Refinement** (#19)
   - \`INLUProvider\` protocol defined and implemented
   - \`IDialogueManager\` protocol defined and implemented
   - Clean separation of concerns validated

3. **Zero-Leakage Audit** (#20)
   - Systematic review of all nodes
   - Business logic separated from infrastructure
   - Validation pass documented

4. **Conversational Patterns** (All 6)
   - \`start flow\` - Full context-aware routing
   - \`cancel flow\` - Graceful termination + cleanup
   - \`clarify flows\` - Smart disambiguation
   - \`set slot\` - Validation + context preservation
   - \`correct slot\` - Retroactive correction
   - \`chitchat\` - Digression handling + seamless return

5. **E2E Test Suite**
   - 3-4 comprehensive tests in banking domain
   - Coverage of complex multi-turn scenarios
   - All tests passing reliably

**MVP Success Definition**: All 5 workstreams complete, all tests passing, documentation accurate. No deadline - release when ready.

### Growth Features (Post-MVP)

**v0.6.0 - Developer Experience:**
- Event Architecture (deferred from v0.5.0)
- TUI implementation for visual debugging
- CLI evolution (streaming, slash commands)

**v0.7.5 - Knowledge & RAG:**
- RAG Integration with \`IKnowledgeProvider\` protocol
- Document ingestion pipeline
- Knowledge retrieval patterns

**v0.8.0 - Performance & Persistence:**
- PostgreSQL support (beyond SQLite)
- NLU Optimization Pipeline enhancements
- Redis caching

### Vision (Future - v1.0+)

**Long-term Vision: Developer-First Rasa Alternative**

- **Complete Pattern Library**: Beyond 6 core patterns - advanced conversation repair
- **Production Tooling**: Analytics, monitoring, deployment automation
- **Multi-modal Support**: Voice integration, rich media
- **Enterprise Features**: Multi-tenancy, RBAC, compliance (SOC 2, HIPAA)
- **Ecosystem Growth**: Community connectors, plugins, extensions

**Strategic Positioning**: Position Soni as the modern, developer-first alternative to Rasa - emphasizing automatic optimization (DSPy), clean architecture, and debuggability

## User Journeys

### Journey 1: Alex Chen - From Frustration to Flow Confidence

Alex Chen es un desarrollador full-stack que trabaja para un banco digital. Durante 3 meses ha estado intentando construir un bot bancario usando Soni v0.4.0 que permita a los clientes hacer transferencias, consultar saldos y gestionar cuentas. El proyecto está atrasado porque cada vez que implementa manejo de digressions (cuando el usuario se desvía del flujo principal), el bot se corrompe y pierde contexto. Ha pasado incontables horas debuggeando por qué las conversaciones se interrumpen en lugares inesperados. Su manager le está preguntando cuándo estará listo para producción, pero Alex no puede dar una fecha - no confía en la estabilidad del sistema.

Una tarde, después de perder 4 horas rastreando un bug de resumption de flow, Alex decide actualizar a Soni v0.5.0 que acaba de salir. Lee en el changelog sobre la "centralized interrupt architecture" y el soporte completo de los 6 patrones de Rasa CALM. Actualiza su proyecto y empieza a refactorizar su código de transferencias.

Lo primero que nota es que ya no tiene que manejar interrupts en cada nodo \`confirm\` y \`collect\` - todo pasa por \`human_input_gate\`. Implementa el patrón \`chitchat\` para manejar digressions: cuando el usuario pregunta "¿cuál es mi saldo?" en medio de una transferencia, el sistema maneja la pregunta y automáticamente regresa al contexto de transferencia. Luego implementa \`correct_slot\` - ahora cuando un usuario dice "no espera, quiero transferir $500 no $50", el sistema corrige retroactivamente sin romper el flujo.

Al cuarto día de trabajo con v0.5.0, Alex ejecuta su suite de tests E2E que nunca habían pasado al 100% en v0.4.0. Todos los tests pasan. Prueba manualmente el escenario más complejo: inicio de transferencia → digresión para consultar saldo → regreso a transferencia → corrección del monto → cancelación de flow → inicio de un pago de facturas. Todo funciona perfectamente.

Cuando algo falla en pruebas de QA, Alex puede debuggear en minutos porque sabe exactamente dónde mirar: \`human_input_gate.py\`. Ya no pierde horas buscando en múltiples nodos.

Dos semanas después, Alex despliega el bot bancario a producción por primera vez. El sistema maneja conversaciones complejas confiablemente. Los clientes pueden divagar, cambiar de opinión, corregir inputs - el bot se mantiene estable. Alex ahora tiene confianza para agregar nuevas features (pagos de servicios, inversiones) porque sabe que la arquitectura no va a pelear contra él. Su manager está impresionado con la velocidad de entrega y la calidad del producto final.

### Journey 2: Sarah Martinez - Extending the Framework Without Fear

Sarah es una desarrolladora senior que lidera un equipo construyendo asistentes virtuales para e-commerce. Necesita implementar un patrón conversacional custom: "suggerir alternativas" - cuando un producto está agotado, el bot debe sugerir productos similares sin perder el contexto de compra. En frameworks anteriores, esto requería hackear el core y arriesgarse a romper funcionalidad existente.

Sarah revisa la documentación de Soni v0.5.0 y ve que los 6 patrones de Rasa CALM están localizados en \`human_input_gate\`. Lee el código fuente (claramente separado gracias a \`INLUProvider\` y \`IDialogueManager\` protocols) y entiende exactamente cómo implementar su patrón custom.

Extiende el NLU provider para detectar el patrón "suggest alternatives" y lo integra en el gate. Como todo está centralizado, su implementación es limpia y no afecta otros flows.

Ejecuta los tests E2E existentes - todos pasan. Su nuevo patrón funciona perfectamente. No rompió nada.

Sarah decide contribuir su patrón de vuelta al proyecto de Soni como open source. Gracias a la arquitectura limpia y la documentación precisa (que refleja el código real en \`src/soni\`), puede crear un PR de calidad rápidamente. Su equipo ahora puede iterar en nuevos features sin miedo a regresiones.

### Journey 3: Marcus Johnson - Escaping Rasa's Complexity Tax

Marcus Johnson es un desarrollador con 2 años de experiencia construyendo bots conversacionales con Rasa para una startup de salud mental. Su bot de apoyo emocional usa Rasa CALM para manejar conversaciones complejas donde los usuarios frecuentemente cambian de tema (ansiedad → depresión → técnicas de respiración → agenda de terapia). El bot funciona, pero Marcus se siente atrapado:

- **Sobrecarga de configuración**: Múltiples archivos YAML (\`domain.yml\`, \`flows.yml\`, \`nlu.yml\`, \`rules.yml\`) que debe mantener sincronizados
- **Debugging opaco**: Cuando algo falla, tiene que rastrear a través de FlowPolicy, TensorFlow models, y múltiples capas de abstracción
- **Lentitud de iteración**: Cada cambio requiere re-entrenar modelos, lo que toma minutos. No puede iterar rápidamente
- **Vendor lock-in**: Está considerando features enterprise de Rasa pero los precios son prohibitivos para una startup

Marcus escucha sobre Soni v0.5.0 - un framework "developer-first" que promete la misma capacidad de conversation repair de Rasa CALM pero con optimización automática DSPy y arquitectura más simple.

Un viernes por la tarde, Marcus decide experimentar. Crea un nuevo proyecto Soni y empieza a migrar un flujo simple de "reserva de sesión de terapia".

En lugar de 4-5 archivos YAML, Soni usa archivos organizados por feature (\`slots.yaml\`, \`actions.yaml\`, \`therapy-booking.yaml\`). Marcus encuentra esto más intuitivo. Implementa \`start flow\`, \`cancel flow\`, \`chitchat\`, y \`correct slot\` para su flujo de reservas. No necesita configurar policies ni entrenar modelos - DSPy optimiza automáticamente. Hace un cambio en el NLU y lo prueba inmediatamente. No hay "training time" de 3-5 minutos.

Cuando un usuario test dice algo ambiguo y activa el patrón \`clarify flows\`, Marcus puede ver exactamente qué pasó en \`human_input_gate.py\`. El código es Python puro, sin capas de abstracción. Puede hacer \`print()\` debugging si quiere.

Después de 3 días de trabajo, Marcus tiene su flujo de reservas funcionando en Soni con los mismos 6 patrones conversacionales que tenía en Rasa, pero con iteración 10x más rápida, código más claro, y mismo comportamiento confiable. Ejecuta benchmarks de latencia: Soni responde en ~200ms vs ~500ms de Rasa (gracias a no tener overhead de TensorFlow).

Marcus presenta Soni a su equipo. Deciden migrar gradualmente - empiezan con nuevos flujos en Soni mientras mantienen los existentes en Rasa. En 2 meses, han migrado el 70% de su bot.

Los beneficios son tangibles: velocidad de desarrollo (features en días vs semanas), menos bugs (arquitectura centralizada), y costo reducido (no necesitan Rasa Enterprise).

Marcus se convierte en contributor de Soni, aportando mejoras al soporte de patrones de salud mental. La arquitectura limpia hace que sus contribuciones sean fáciles de integrar.

### Journey Requirements Summary

Estos tres journeys revelan los siguientes capabilities necesarios para v0.5.0:

**Core Framework Stability:**
- Centralized interrupt architecture (\`human_input_gate\`) que permite conversaciones complejas confiables
- Todos los 6 patrones de Rasa CALM funcionando at Level 3 (detect + handle + graceful recovery)
- 100% de tests E2E passing para validar escenarios complejos

**Developer Debuggability:**
- Un solo punto de investigación (\`human_input_gate.py\`) para troubleshooting
- Código Python puro y transparente, sin capas de abstracción opacas
- Debugging tiempo reducido de horas a minutos

**Extensibility \& Maintainability:**
- Arquitectura limpia basada en protocols (\`INLUProvider\`, \`IDialogueManager\`) que permite agregar patrones custom sin romper existentes
- Zero-leakage audit completado - business logic separada de infrastructure
- Facilita contribuciones open source de calidad

**Documentation Accuracy:**
- Docs que reflejan el código real en \`src/soni\` (single source of truth)
- Guías claras para bot builders
- Migration path documentation para usuarios de Rasa

**Performance \& Developer Velocity:**
- Iteración rápida sin steps de "training" lentos (gracias a DSPy auto-optimization)
- Respuestas rápidas (~200ms) sin overhead de ML training loops
- Feature-organized YAML configuration (más intuitivo que múltiples archivos desincronizados)
