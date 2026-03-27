# ADR-002: MessageBus vs Direct Function Calls

## Status
Accepted

## Context
Two options for inter-agent communication:
1. **Direct function calls**: Agent A calls agent_b.process(data)
2. **MessageBus**: Async message queue with pub/sub

## Decision
We chose **MessageBus** architecture.

```python
# Direct calls (REJECTED)
result = section_writer.process(protocol_data)

# MessageBus (ACCEPTED)
message = AgentMessage(
    sender="ProtocolAnalyzer",
    recipient="SectionWriter",
    payload=protocol_data
)
await message_bus.publish(message)
```

## Why MessageBus Won

### 1. Loose Coupling
Agents don't know about each other. They only know the message format.
```python
# Agent is independent
def process(self, message: AgentMessage) -> AgentMessage:
    # Doesn't care who sent it
    return AgentMessage(sender=self.agent_id, ...)
```

### 2. Async by Design
```python
# Parallel section generation
await asyncio.gather(
    message_bus.publish(msg_to_writer_1),
    message_bus.publish(msg_to_writer_2),
    message_bus.publish(msg_to_writer_3),
)
```

### 3. Audit Trail
Every message logged automatically:
```python
@dataclass
class AgentMessage:
    message_id: str          # UUID
    timestamp: datetime      # When sent
    input_hash: str          # SHA-256
    output_hash: str         # SHA-256
    # FDA 21 CFR Part 11 compliant
```

### 4. Scalability
Can replace in-memory bus with Redis/RabbitMQ:
```python
# Current (single machine)
class InMemoryMessageBus:
    async def publish(self, message): ...

# Future (distributed)
class RedisMessageBus:
    async def publish(self, message): 
        await redis.publish("agent_queue", message)
```

## Consequences

### Positive
- Horizontal scaling ready
- Perfect audit trail (FDA compliance)
- Agents can crash/restart independently
- Easy to add new agents

### Negative
- +5-10ms latency per hop
- Debugging harder (stack traces across async boundaries)
- Need to handle message ordering

## Mitigation
- Structured logging with correlation IDs
- Message ordering via timestamps
- Local debugging mode with sync calls

## Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Direct calls | Simple, fast | Tight coupling, no audit | ❌ Rejected |
| gRPC | Fast, typed | Complex, needs protobuf | ⚠️ Future |
| MessageBus | Flexible, auditable | Slightly slower | ✅ Accepted |

## References
- `core/message_protocol.py` - Message dataclasses
- `core/orchestrator.py` - MessageBus implementation
