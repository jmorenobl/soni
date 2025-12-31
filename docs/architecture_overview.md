# Arquitectura de Soni Framework

Este diagrama visualiza la arquitectura implementada en `src/soni`, destacando el flujo de ejecución, el ciclo de vida de la conversación y la gestión del estado "Human-in-the-loop".

```mermaid
graph TD
    User([User]) -->|Message| RL[RuntimeLoop]

    subgraph "Runtime Cycle"
        RL -->|1. Resume/Start| Orchestrator[Orchestrator Graph]

        subgraph "Orchestrator Nodes"
            UN[understand_node] -->|2. Flow Stack Updates| ORCH[orchestrator_node]
            ORCH -->|4. Final Response| END((END))
        end

        subgraph "Dialogue Understanding (Two-Pass)"
            UN -->|Pass 1: Intent| DU[SoniDU]
            DU -->|StartFlow CMD?| SE[SlotExtractor]
            SE -->|Pass 2: Slots| UN
        end

        subgraph "Execution & Interrupts"
            ORCH -->|3. Invoke| SubG[Active Subgraph]
            SubG -->|Result| ORCH

            ORCH -.->|Need Input?| INT{Interrupt}
            INT -->|Prompt User| RL
        end
    end

    subgraph "State Management"
        FM[FlowManager]
        State[(DialogueState)]

        UN -.->|FlowDelta| FM
        ORCH -.->|FlowDelta| FM
        FM -.->|Updates| State
    end

    style RL fill:#f9f,stroke:#333,stroke-width:2px
    style Orchestrator fill:#eee,stroke:#333,stroke-width:2px
    style State fill:#e1f5fe,stroke:#333,stroke-width:2px
    style INT fill:#fff9c4,stroke:#d4a017,stroke-width:2px
```

## Detalles del Flujo

1.  **Entrada**: `RuntimeLoop` recibe el mensaje. Si hay una interrupción pendiente, se reanuda con `Command(resume=...)`.
2.  **Understand**:
    - Ejecuta NLU (Doble pasada).
    - Procesa `StartFlow`/`CancelFlow` inmediatamente para persistir cambios en el stack.
3.  **Execute**:
    - Invoca el subgrafo del flujo activo.
    - Si el subgrafo necesita input, dispara `interrupt()`.
    - Al reanudarse, procesa la respuesta del usuario con NLU interno si es necesario y continúa el bucle.
4.  **Estado**:
    - `FlowManager` genera deltas inmutables (`FlowDelta`).
    - El estado global se actualiza mediante reducers.
# Flujo de Interrupción

Este diagrama de secuencia detalla exactamente qué sucede cuando el sistema necesita preguntar algo al usuario y esperar su respuesta.

```mermaid
sequenceDiagram
    participant User
    participant RL as RuntimeLoop
    participant ORCH as orchestrator_node
    participant Sub as Subgraph (Flow)
    participant NLU as SoniDU (NLU)

    Note over User, Sub: 1. Ejecución Inicial (o reanudación previa)

    RL->>ORCH: Invoke
    loop Execution Loop
        ORCH->>Sub: ainvoke(state)
        Sub-->>ORCH: result (need_input=True, prompt="¿Edad?")

        opt Si necesita input
            ORCH->>RL: interrupt("¿Edad?")
            RL-->>User: Output: "¿Edad?"

            Note right of RL: 🛑 EL SISTEMA SE DETIENE AQUÍ <br/>(Estado persistido)

            User->>RL: Input: "25 años"
            RL->>ORCH: Command(resume="25 años")

            Note right of ORCH: ▶️ Se reanuda ejecución justo después del interrupt

            ORCH->>NLU: acall("25 años")
            NLU-->>ORCH: commands=[SetSlot(age=25)]

            ORCH->>ORCH: Update state (commands, history)
        end
    end
    ORCH-->>RL: Final Response
```

## Explicación paso a paso

1.  **Detección de necesidad**: El subgrafo del flujo (ej. `onboarding`) detecta que falta un dato (ej. la edad) y devuelve `need_input=True` junto con la pregunta (`prompt`).
2.  **La Interrupción**:
    - El nodo `orchestrator_node` ve esta señal y retorna `TaskAction.INTERRUPT`.
    - **Punto Clave**: La ejecución del código Python se detiene y retorna el control. El estado se guarda en la base de datos (Checkpointer).
    - El usuario recibe la pregunta.
3.  **La Espera**: El sistema no está corriendo. Está esperando pasivamente.
4.  **La Reanudación**:
    - Cuando el usuario responde ("25 años"), `RuntimeLoop` busca el hilo pausado y envía un comando de reanudación (`Command(resume=...)`).
    - `orchestrator_node` "despierta" procesando el comando de reanudación. La variable que recogía el resultado de `interrupt()` ahora contiene "25 años".
5.  **Procesamiento**:
    - Como el subgrafo no sabe de lenguaje natural, `orchestrator_node` llama al NLU (`SoniDU`) con la respuesta del usuario.
    - El NLU traduce "25 años" a comandos estructurados: `SetSlot(age=25)`.
    - Se actualiza el estado y el bucle continúa, volviendo a invocar al subgrafo, que ahora ya tendrá el dato y avanzará al siguiente paso.
