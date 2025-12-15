# Framework de Asistentes Conversacionales

## ¿Qué es?

Un **framework open-source para crear asistentes conversacionales empresariales** que combina lo mejor de Rasa CALM con tecnología LLM moderna. Piensa en ello como "Rasa para la era de los LLMs".

## El Problema que Resuelve

**Rasa** es potente pero:
- No usa LLMs nativamente (pre-ChatGPT era)
- Requiere mucho training data
- Complicado de escalar

**Frameworks LLM actuales** (LangChain, etc):
- Demasiado código imperativo
- Difíciles de mantener
- No hay buenas prácticas para diálogos complejos

**Mi framework llena ese gap**.

## Arquitectura en 3 Capas

### 1. **Definición Declarativa (YAML)**
Como Rasa, defines flows en YAML sin código:

```yaml
flows:
  book_flight:
    slots: [origin, destination, date]
    steps:
      - collect_slots
      - if: passengers > 4
        then: check_group_discount
        else: check_standard_price
      - while: not confirmed
        do: [present_options, ask_confirmation]
      - execute_command: book_flight
```

### 2. **Orquestación con LangGraph**
Un compilador convierte el YAML en grafos LangGraph:
- **Subgrafos** por cada flow (booking, cancelación, consulta)
- **Manejo de interrupciones** (chit-chat, cambios de intención)
- **Loops y condicionales** complejos
- **Stack de diálogos** para flows anidados

### 3. **Inteligencia con DSPy**
En lugar de reglas rígidas, usa LLMs optimizados:
- **Command Generator**: LLM que genera comandos ejecutables desde input del usuario
- **Slot Extraction**: Extracción inteligente de información
- **Auto-optimización**: DSPy mejora los prompts automáticamente con ejemplos

## Ventajas Clave

✅ **Declarativo como Rasa** - No código spaghetti
✅ **LLM-native** - Usa ChatGPT/Claude directamente
✅ **Menos training data** - DSPy optimiza con pocos ejemplos
✅ **Escalable** - Arquitectura modular con subgrafos
✅ **Explicable** - Command pattern + trazabilidad completa

## Ejemplo de Uso

```python
# El desarrollador solo define flows en YAML
framework = ConversationalFramework()
framework.load_flows("flows/")  # book_flight.yaml, cancel_booking.yaml, etc.

# El framework compila automáticamente a LangGraph
framework.compile()

# Y ejecuta
response = framework.run("Quiero reservar un vuelo a París mañana")
```

## Diferenciadores vs Competencia

| Feature | Rasa | LangChain | Mi Framework |
|---------|------|-----------|--------------|
| Sintaxis declarativa | ✅ | ❌ | ✅ |
| LLM nativo | ❌ | ✅ | ✅ |
| Diálogos complejos | ✅ | ⚠️ | ✅ |
| Auto-optimización | ❌ | ❌ | ✅ (DSPy) |
| Interrupciones | ✅ | ❌ | ✅ |

## Stack Tecnológico

- **LangGraph**: Motor de orquestación (grafos de estados)
- **DSPy**: Generación y optimización de comandos
- **Pydantic**: Validación de comandos y slots
- **YAML/JSON**: Definición de flows

## Target

Empresas que necesitan asistentes conversacionales complejos:
- E-commerce (compras multi-paso)
- Banca (transacciones, consultas)
- Travel (reservas complejas)
- Soporte técnico (troubleshooting guiado)

---

**En una frase**: Es Rasa CALM reimaginado para usar LLMs de forma nativa, con sintaxis declarativa + orquestación LangGraph + optimización DSPy.
