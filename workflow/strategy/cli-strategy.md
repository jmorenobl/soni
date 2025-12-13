# CLI Interface Design Strategy

This document outlines the strategy and milestones for implementing the Soni Framework CLI interface. The goal is to provide a user-friendly command-line interface for testing and interacting with Soni dialogue systems.

## Current State

The CLI currently has:
- `soni optimize` - Optimize NLU modules with DSPy
- `soni server` - Start the FastAPI server
- Basic version and help commands

**Missing**: Interactive console for testing the assistant directly in the terminal.

## Design Principles

1. **Progressive Enhancement**: Start simple, add features incrementally
2. **User Experience First**: Make it easy to test and debug dialogue flows
3. **Consistency**: Follow existing CLI patterns (Typer, similar to `server` command)
4. **Async Support**: Support both regular and streaming responses
5. **Developer-Friendly**: Provide debugging information when needed

## Milestones

### Milestone 1: Basic Interactive Console (MVP) 🎯 **PRIORITY**

**Goal**: Enable users to test the assistant in a simple interactive console.

**Features**:
- `soni chat --config <path>` command
- Simple read-eval-print loop (REPL)
- Basic input/output:
  - User types message
  - System processes and displays response
  - Continue conversation until exit
- Exit commands: `exit`, `quit`, `Ctrl+C`, `Ctrl+D`
- Single user session (user_id can be auto-generated or provided)

**Implementation Details**:
- Use `RuntimeLoop` to process messages
- Use `asyncio` for async message processing
- Simple prompt: `You: ` for user input, `Assistant: ` for responses
- Handle errors gracefully with clear messages

**Acceptance Criteria**:
- ✅ Can start interactive session with `soni chat -c examples/flight_booking/soni.yaml`
- ✅ Can send messages and receive responses
- ✅ Conversation state persists within session
- ✅ Can exit cleanly with `exit` or `Ctrl+C`
- ✅ Error messages are clear and helpful

**Estimated Complexity**: Low-Medium

---

### Milestone 2: Enhanced Console Features

**Goal**: Improve the console experience with better UX and debugging options.

**Features**:
- Configurable user_id: `--user-id <id>` option
- Streaming mode: `--stream` option for real-time token streaming
- Verbose mode: `--verbose` to show NLU results, intents, slots
- Clear conversation: `clear` command to reset state
- History: `history` command to show conversation history
- Better formatting:
  - Color-coded messages (user vs assistant)
  - Timestamps (optional with `--timestamps`)
  - Message numbering

**Implementation Details**:
- Use `rich` library for colored output (optional dependency)
- Implement command parsing for special commands (`clear`, `history`)
- Add streaming support using `process_message_stream()`
- Display NLU debugging info when verbose mode is enabled

**Acceptance Criteria**:
- ✅ Can specify custom user_id
- ✅ Streaming mode works correctly
- ✅ Verbose mode shows NLU debugging information
- ✅ `clear` command resets conversation state
- ✅ `history` command displays conversation history
- ✅ Output is well-formatted and readable

**Estimated Complexity**: Medium

---

### Milestone 3: Multi-Conversation Management

**Goal**: Support managing multiple conversations in the same session.

**Features**:
- Switch conversations: `switch <user_id>` command
- List conversations: `conversations` command
- Delete conversation: `delete <user_id>` command
- Show conversation info: `info <user_id>` command
- Auto-complete for user_ids

**Implementation Details**:
- Track active conversation
- List conversations from checkpoint storage
- Allow switching between conversations
- Update prompt to show current conversation

**Acceptance Criteria**:
- ✅ Can switch between multiple conversations
- ✅ Can list all conversations
- ✅ Can delete specific conversations
- ✅ Can view conversation metadata
- ✅ Prompt shows current conversation ID

**Estimated Complexity**: Medium-High

---

### Milestone 4: Advanced Debugging Tools

**Goal**: Provide powerful debugging capabilities for developers.

**Features**:
- Debug mode: `--debug` flag
- Show state: `state` command to display current dialogue state
- Show slots: `slots` command to show collected slots
- Show flow: `flow` command to show current flow and step
- Show graph: `graph` command to visualize the dialogue graph
- Export conversation: `export <format>` (JSON, YAML, Markdown)
- Import conversation: `import <file>` to load conversation history

**Implementation Details**:
- Access internal state from RuntimeLoop
- Format state display nicely
- Support multiple export formats
- Graph visualization (text-based or using graphviz if available)

**Acceptance Criteria**:
- ✅ Debug mode shows detailed internal state
- ✅ Can inspect current dialogue state
- ✅ Can view collected slots
- ✅ Can see current flow and step
- ✅ Can export conversations in multiple formats
- ✅ Can import conversation history

**Estimated Complexity**: High

---

### Milestone 5: Batch Testing and Scripting

**Goal**: Support automated testing and scripting scenarios.

**Features**:
- Batch mode: `soni chat --batch <file>` to process multiple messages
- Script mode: `soni chat --script <file>` to run conversation scripts
- Assertions: Support for test assertions in scripts
- Output format: `--output <format>` (JSON, YAML, text)
- Non-interactive mode: `--non-interactive` for CI/CD

**Implementation Details**:
- Parse batch files (JSON, YAML, or simple text)
- Support script format with assertions
- Generate structured output for automation
- Support piping input/output

**Acceptance Criteria**:
- ✅ Can process batch files
- ✅ Can run conversation scripts
- ✅ Supports test assertions
- ✅ Generates structured output
- ✅ Works in non-interactive environments

**Estimated Complexity**: High

---

## Implementation Plan

### Phase 1: MVP (Milestone 1)
**Focus**: Get basic console working
**Timeline**: 1-2 days
**Dependencies**: None (uses existing RuntimeLoop)

### Phase 2: Polish (Milestone 2)
**Focus**: Improve UX and add useful features
**Timeline**: 2-3 days
**Dependencies**: Milestone 1

### Phase 3: Advanced Features (Milestones 3-5)
**Focus**: Add advanced capabilities
**Timeline**: 1-2 weeks
**Dependencies**: Milestones 1-2

## Technical Considerations

### Dependencies
- **Required**: `typer` (already in dependencies)
- **Optional**: `rich` for enhanced formatting (add as optional dependency)
- **Optional**: `graphviz` for graph visualization (add as optional dependency)

### Async Handling
- Use `asyncio.run()` for the main chat loop
- Handle async RuntimeLoop methods properly
- Support both sync and async input reading (use `asyncio` for input)

### Error Handling
- Graceful error messages
- Continue on non-fatal errors
- Clear exit on fatal errors
- Log errors appropriately

### Testing
- Unit tests for command parsing
- Integration tests for full conversation flows
- Test error handling scenarios
- Test streaming mode

## Example Usage (After Milestone 1)

```bash
# Start interactive chat
$ soni chat --config examples/flight_booking/soni.yaml

Welcome to Soni Interactive Console!
Type 'exit' or 'quit' to end the session.
Type 'help' for available commands.

You: I want to book a flight
Assistant: I'd be happy to help you book a flight. Where would you like to go?

You: New York
Assistant: Great! When would you like to travel?

You: exit
Goodbye!
```

## Example Usage (After Milestone 2)

```bash
# Start with streaming and verbose mode
$ soni chat --config examples/flight_booking/soni.yaml --stream --verbose

You: I want to book a flight
[NLU] Intent: book_flight (confidence: 0.95)
[NLU] Slots: {}
Assistant: I'd be happy to help you book a flight. Where would you like to go?

You: clear
Conversation cleared.

You: exit
Goodbye!
```

## Future Considerations

- **GUI Mode**: Consider a TUI (Text User Interface) using `rich` or `textual`
- **WebSocket Mode**: Connect to running server via WebSocket
- **Plugin System**: Allow plugins for custom commands
- **Configuration**: Support `.sonirc` config file for default settings
- **Themes**: Support different color themes
- **Multi-language**: Support for different languages in UI (though framework is English-only)

## Notes

- All user-facing text must be in English (per project rules)
- Follow existing code style and conventions
- Add comprehensive tests for each milestone
- Update documentation as features are added
- Consider backward compatibility when adding new features
