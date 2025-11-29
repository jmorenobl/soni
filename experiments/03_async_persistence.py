#!/usr/bin/env python3
"""
Experimento 0.3: Validación Persistencia Async (aiosqlite)

Objetivo: Garantizar que es viable usar aiosqlite para checkpointing
y persistencia del estado de conversación en un contexto altamente concurrente.

Criterios de éxito:
- Estado persiste entre invocaciones
- Múltiples conversaciones simultáneas funcionan
- No hay race conditions
- Performance aceptable (<100ms por operación)
"""

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

# Configuración
RESULTS_DIR = Path("experiments/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = RESULTS_DIR / "test_persistence.db"


class DialogueState:
    """Simplified dialogue state for testing"""

    def __init__(
        self,
        conversation_id: str,
        messages: list[dict],
        current_flow: str = "none",
        slots: dict = None,
        turn_count: int = 0,
    ):
        self.conversation_id = conversation_id
        self.messages = messages
        self.current_flow = current_flow
        self.slots = slots or {}
        self.turn_count = turn_count
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "messages": self.messages,
            "current_flow": self.current_flow,
            "slots": self.slots,
            "turn_count": self.turn_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogueState":
        state = cls(
            conversation_id=data["conversation_id"],
            messages=data["messages"],
            current_flow=data.get("current_flow", "none"),
            slots=data.get("slots", {}),
            turn_count=data.get("turn_count", 0),
        )
        state.created_at = data.get("created_at", datetime.now().isoformat())
        state.updated_at = data.get("updated_at", datetime.now().isoformat())
        return state


class AsyncPersistenceManager:
    """Manager for async persistence using aiosqlite"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection = None

    async def initialize(self):
        """Initialize database schema"""
        self._connection = await aiosqlite.connect(str(self.db_path))

        # Create table for dialogue states
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dialogue_states (
                conversation_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        # Create index for faster lookups
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversation_id
            ON dialogue_states(conversation_id)
        """
        )

        await self._connection.commit()

    async def save_state(self, state: DialogueState) -> bool:
        """Save or update dialogue state"""
        try:
            state.updated_at = datetime.now().isoformat()
            state_data = json.dumps(state.to_dict())

            await self._connection.execute(
                """
                INSERT OR REPLACE INTO dialogue_states
                (conversation_id, state_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """,
                (state.conversation_id, state_data, state.created_at, state.updated_at),
            )

            await self._connection.commit()
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    async def load_state(self, conversation_id: str) -> DialogueState | None:
        """Load dialogue state by conversation ID"""
        try:
            cursor = await self._connection.execute(
                """
                SELECT state_data FROM dialogue_states
                WHERE conversation_id = ?
            """,
                (conversation_id,),
            )

            row = await cursor.fetchone()
            if row:
                state_dict = json.loads(row[0])
                return DialogueState.from_dict(state_dict)
            return None
        except Exception as e:
            print(f"Error loading state: {e}")
            return None

    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()


async def test_basic_persistence():
    """Test basic save/load functionality"""
    print("\n1. Probando persistencia básica...")

    manager = AsyncPersistenceManager(DB_PATH)
    await manager.initialize()

    # Create and save state
    original_state = DialogueState(
        conversation_id="test-1",
        messages=[{"role": "user", "content": "Hello"}],
        current_flow="greeting",
        slots={"name": "Alice"},
        turn_count=1,
    )

    save_start = time.time()
    success = await manager.save_state(original_state)
    save_time = (time.time() - save_start) * 1000  # ms

    if not success:
        print("   ✗ Error guardando estado")
        await manager.close()
        return False

    print(f"   ✓ Estado guardado en {save_time:.2f} ms")

    # Load state
    load_start = time.time()
    loaded_state = await manager.load_state("test-1")
    load_time = (time.time() - load_start) * 1000  # ms

    if not loaded_state:
        print("   ✗ Error cargando estado")
        await manager.close()
        return False

    print(f"   ✓ Estado cargado en {load_time:.2f} ms")

    # Verify data integrity
    if (
        loaded_state.conversation_id == original_state.conversation_id
        and loaded_state.current_flow == original_state.current_flow
        and loaded_state.slots == original_state.slots
        and loaded_state.turn_count == original_state.turn_count
    ):
        print("   ✓ Integridad de datos verificada")
        await manager.close()
        return True, save_time, load_time
    else:
        print("   ✗ Datos no coinciden")
        await manager.close()
        return False, save_time, load_time


async def test_concurrent_conversations():
    """Test multiple simultaneous conversations"""
    print("\n2. Probando múltiples conversaciones simultáneas...")

    manager = AsyncPersistenceManager(DB_PATH)
    await manager.initialize()

    num_conversations = 10
    conversation_ids = [f"conv-{i}" for i in range(num_conversations)]

    async def save_conversation(conv_id: str, delay: float):
        """Save a conversation state with random delay"""
        await asyncio.sleep(delay)  # Random delay to force interleaving
        state = DialogueState(
            conversation_id=conv_id,
            messages=[{"role": "user", "content": f"Message from {conv_id}"}],
            current_flow="test",
            slots={"id": conv_id},
            turn_count=random.randint(1, 10),
        )
        return await manager.save_state(state)

    # Save all conversations concurrently
    tasks = [save_conversation(conv_id, random.uniform(0, 0.1)) for conv_id in conversation_ids]

    start_time = time.time()
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    if all(results):
        print(f"   ✓ {num_conversations} conversaciones guardadas concurrentemente")
        print(f"   ✓ Tiempo total: {total_time*1000:.2f} ms")
    else:
        print("   ✗ Algunas conversaciones fallaron al guardar")
        await manager.close()
        return False

    # Load all conversations and verify
    load_tasks = [manager.load_state(conv_id) for conv_id in conversation_ids]
    loaded_states = await asyncio.gather(*load_tasks)

    # Verify all loaded correctly
    all_loaded = all(state is not None for state in loaded_states)
    all_correct = all(
        state.conversation_id == conv_id
        for state, conv_id in zip(loaded_states, conversation_ids, strict=False)
        if state
    )

    if all_loaded and all_correct:
        print("   ✓ Todas las conversaciones cargadas correctamente")
        print("   ✓ No se detectaron inconsistencias")
        await manager.close()
        return True
    else:
        print("   ✗ Error en carga o verificación")
        await manager.close()
        return False


async def test_race_conditions():
    """Test for race conditions with concurrent updates"""
    print("\n3. Probando detección de race conditions...")

    manager = AsyncPersistenceManager(DB_PATH)
    await manager.initialize()

    conversation_id = "race-test"

    # Create initial state
    initial_state = DialogueState(conversation_id=conversation_id, messages=[], turn_count=0)
    await manager.save_state(initial_state)

    # Concurrent updates with random delays
    num_updates = 5

    async def update_state(update_num: int):
        """Update state with random delay"""
        await asyncio.sleep(random.uniform(0, 0.05))
        state = await manager.load_state(conversation_id)
        if state:
            state.turn_count = update_num
            state.messages.append({"role": "user", "content": f"Update {update_num}"})
            await manager.save_state(state)
        return update_num

    # Run concurrent updates
    update_nums = list(range(num_updates))
    tasks = [update_state(num) for num in update_nums]
    await asyncio.gather(*tasks)

    # Load final state
    final_state = await manager.load_state(conversation_id)

    if final_state:
        # Verify final state is consistent (should have all updates)
        if len(final_state.messages) >= num_updates:
            print(f"   ✓ Estado final consistente: {len(final_state.messages)} mensajes")
            print("   ✓ No se detectaron race conditions evidentes")
            await manager.close()
            return True
        else:
            print(
                f"   ⚠️  Posible race condition: solo {len(final_state.messages)} de {num_updates} actualizaciones"
            )
            await manager.close()
            return False
    else:
        print("   ✗ No se pudo cargar estado final")
        await manager.close()
        return False


async def test_performance():
    """Test performance of save/load operations"""
    print("\n4. Probando performance de operaciones...")

    manager = AsyncPersistenceManager(DB_PATH)
    await manager.initialize()

    num_operations = 50
    save_times = []
    load_times = []

    for i in range(num_operations):
        state = DialogueState(
            conversation_id=f"perf-test-{i}",
            messages=[{"role": "user", "content": f"Message {i}"}],
            turn_count=i,
        )

        # Measure save time
        start = time.time()
        await manager.save_state(state)
        save_times.append((time.time() - start) * 1000)

        # Measure load time
        start = time.time()
        await manager.load_state(f"perf-test-{i}")
        load_times.append((time.time() - start) * 1000)

    avg_save = sum(save_times) / len(save_times)
    avg_load = sum(load_times) / len(load_times)
    max_save = max(save_times)
    max_load = max(load_times)

    print(f"   ✓ Operaciones de guardado: {num_operations}")
    print(f"     - Promedio: {avg_save:.2f} ms")
    print(f"     - Máximo: {max_save:.2f} ms")
    print(f"   ✓ Operaciones de carga: {num_operations}")
    print(f"     - Promedio: {avg_load:.2f} ms")
    print(f"     - Máximo: {max_load:.2f} ms")

    # Check if performance meets criteria (< 100ms)
    performance_ok = avg_save < 100 and avg_load < 100

    if performance_ok:
        print("   ✓ Performance < 100ms: CUMPLE criterio")
    else:
        print("   ✗ Performance ≥ 100ms: NO CUMPLE criterio")

    await manager.close()
    return performance_ok, avg_save, avg_load


async def main():
    """Run all persistence tests"""
    print("=" * 60)
    print("Experimento 0.3: Validación Persistencia Async (aiosqlite)")
    print("=" * 60)

    # Clean up old database
    if DB_PATH.exists():
        DB_PATH.unlink()

    results = {
        "basic_persistence": False,
        "concurrent_conversations": False,
        "race_conditions": False,
        "performance_ok": False,
        "metrics": {},
    }

    try:
        # Test 1: Basic persistence
        basic_result = await test_basic_persistence()
        if isinstance(basic_result, tuple):
            results["basic_persistence"] = basic_result[0]
            results["metrics"]["save_time_ms"] = basic_result[1]
            results["metrics"]["load_time_ms"] = basic_result[2]
        else:
            results["basic_persistence"] = basic_result

        # Test 2: Concurrent conversations
        results["concurrent_conversations"] = await test_concurrent_conversations()

        # Test 3: Race conditions
        results["race_conditions"] = await test_race_conditions()

        # Test 4: Performance
        perf_result = await test_performance()
        if isinstance(perf_result, tuple):
            results["performance_ok"] = perf_result[0]
            results["metrics"]["avg_save_ms"] = perf_result[1]
            results["metrics"]["avg_load_ms"] = perf_result[2]
        else:
            results["performance_ok"] = perf_result

    except Exception as e:
        print(f"\n✗ Error durante tests: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("RESUMEN DEL EXPERIMENTO")
    print("=" * 60)
    print(f"✓ Persistencia básica: {'Sí' if results['basic_persistence'] else 'No'}")
    print(f"✓ Conversaciones concurrentes: {'Sí' if results['concurrent_conversations'] else 'No'}")
    print(f"✓ Sin race conditions: {'Sí' if results['race_conditions'] else 'No'}")
    print(f"✓ Performance < 100ms: {'Sí' if results['performance_ok'] else 'No'}")

    if results.get("metrics"):
        print("\nMétricas:")
        for key, value in results["metrics"].items():
            print(f"  - {key}: {value:.2f} ms")

    # Save results
    results_file = RESULTS_DIR / "async_persistence_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✓ Resultados guardados en: {results_file}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
