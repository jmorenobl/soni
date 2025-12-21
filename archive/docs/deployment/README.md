# Soni Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure

Create `soni.yaml`:

```yaml
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.0
  persistence:
    backend: sqlite
    path: "./dialogue_state.db"
  logging:
    level: INFO
flows: {}
slots: {}
actions: {}
```

### 3. Run Server

```bash
uv run uvicorn soni.server.api:app --host 0.0.0.0 --port 8000
```

### 4. Test

```bash
curl -X POST http://localhost:8000/chat/test-user \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### 5. Health Check

```bash
curl http://localhost:8000/health
```

## Production Deployment

### Prerequisites

- Python 3.11+
- `uv` package manager
- OpenAI API key (or other LLM provider)
- PostgreSQL or Redis (for production persistence)

### Configuration

#### Environment Variables

- `SONI_CONFIG_PATH`: Path to configuration file (default: `examples/flight_booking/soni.yaml`)
- `SONI_OPTIMIZED_DU_PATH`: Path to optimized DSPy module (optional)
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)

#### Production Settings

```yaml
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.0
  persistence:
    backend: postgresql  # or redis
    connection_string: "postgresql://user:pass@localhost/soni"
  logging:
    level: INFO
  security:
    enable_guardrails: true
    allowed_actions: []  # Empty means all allowed
    blocked_intents: []
flows: {}
slots: {}
actions: {}
```

### Deployment Checklist

- [ ] Configuration file validated
- [ ] Environment variables set
- [ ] Database/Redis connection tested
- [ ] LLM API key configured
- [ ] Logging configured
- [ ] Health check endpoint verified
- [ ] Error handling tested
- [ ] Security guardrails enabled
- [ ] Performance acceptable
- [ ] Monitoring configured

### Running with Systemd

Create `/etc/systemd/system/soni.service`:

```ini
[Unit]
Description=Soni Dialogue System
After=network.target

[Service]
Type=simple
User=soni
WorkingDirectory=/opt/soni
Environment="SONI_CONFIG_PATH=/opt/soni/soni.yaml"
Environment="OPENAI_API_KEY=your-key-here"
ExecStart=/opt/soni/.venv/bin/uvicorn soni.server.api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "uvicorn", "soni.server.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Server Won't Start

- Check configuration file path
- Verify all dependencies are installed
- Check logs for error messages

### Health Check Fails

- Verify runtime is initialized
- Check configuration is valid
- Review server logs

### NLU Errors

- Verify LLM API key is set
- Check API rate limits
- Review NLU provider logs

### Persistence Issues

- Verify database connection string
- Check database permissions
- Review persistence logs

## Monitoring

### Logs

Logs are written to:
- Console (structured format)
- File: `soni.log` (JSON format, if jsonlogger installed)

### Metrics

Monitor:
- Request latency
- Error rates
- NLU call frequency
- Database connection pool

## Security

- Use environment variables for secrets
- Enable security guardrails
- Restrict allowed actions if needed
- Use HTTPS in production
- Implement rate limiting
- Regular security updates
