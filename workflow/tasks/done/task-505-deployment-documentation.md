## Task: 5.5 - Deployment Documentation

**ID de tarea:** 505
**Hito:** Phase 5 - Production Readiness
**Dependencias:** Task 501, Task 502, Task 503, Task 504
**Duración estimada:** 1-2 horas

### Objetivo

Create comprehensive deployment documentation with quick start guide, production checklist, and troubleshooting section.

### Contexto

Deployment documentation is essential for production readiness. It enables users to quickly get started with Soni and provides a checklist for production deployments. This documentation should be clear, complete, and include all necessary information for deploying Soni in production.

**Reference:** [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.5

### Entregables

- [ ] `docs/deployment/` directory created
- [ ] `docs/deployment/README.md` created
- [ ] Quick start guide included
- [ ] Configuration examples included
- [ ] Production deployment checklist included
- [ ] Health check verification documented
- [ ] Troubleshooting section included

### Implementación Detallada

#### Paso 1: Create deployment directory

**Archivo(s) a crear:** `docs/deployment/README.md`

**Contenido:**

```markdown
# Soni Deployment Guide

## Quick Start

### 1. Install Dependencies

\`\`\`bash
uv sync
\`\`\`

### 2. Configure

Create `soni.yaml`:

\`\`\`yaml
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
\`\`\`

### 3. Run Server

\`\`\`bash
uv run uvicorn soni.server.api:app --host 0.0.0.0 --port 8000
\`\`\`

### 4. Test

\`\`\`bash
curl -X POST http://localhost:8000/chat/test-user \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello"}'
\`\`\`

### 5. Health Check

\`\`\`bash
curl http://localhost:8000/health
\`\`\`

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

\`\`\`yaml
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
\`\`\`

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

\`\`\`ini
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
\`\`\`

### Docker Deployment

\`\`\`dockerfile
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
\`\`\`

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
```

**Explicación:**
- Create comprehensive deployment guide
- Include quick start for development
- Include production deployment checklist
- Add troubleshooting section
- Include monitoring and security sections

### Tests Requeridos

**Validación:**
- Documentation is complete
- All code examples are valid
- Links are working (if any)
- No broken references

### Criterios de Éxito

- [ ] Deployment documentation created
- [ ] Quick start guide included
- [ ] Production checklist included
- [ ] Troubleshooting section included
- [ ] All code examples are valid
- [ ] Documentation is clear and complete

### Validación Manual

**Comandos para validar:**

```bash
# Check documentation exists
ls docs/deployment/README.md

# Review content
cat docs/deployment/README.md
```

**Resultado esperado:**
- Documentation file exists
- Content is complete and accurate
- Code examples are valid

### Referencias

- [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.5
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/)

### Notas Adicionales

- All documentation must be in English
- Code examples should be tested
- Include both development and production scenarios
- Security considerations are important
- Monitoring guidance helps operations
