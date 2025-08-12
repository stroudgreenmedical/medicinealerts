# RAG Practice App - Deployment Notes

## Architecture-Specific Gotchas and Solutions

This document captures important deployment considerations, common failure scenarios, and their solutions based on real-world experience deploying the RAG Practice App to Synology NAS.

## 🏗️ Architecture Mismatch

### The Problem
- **Development Environment**: Apple Silicon Mac (ARM64)
- **Production Environment**: Synology NAS (x86_64/AMD64)
- **Issue**: Docker images built on ARM64 won't run on x86_64

### The Solution
**Always build Docker images directly on the Synology NAS** using `deploy-and-build-synology.sh`:
- Avoids cross-platform compatibility issues
- Ensures native x86_64 binaries
- Prevents "exec format error" at runtime

### What NOT to Do
```bash
# ❌ DON'T build locally and push
docker build -t myapp .
docker save myapp | ssh synology "docker load"

# ✅ DO build on Synology
ssh synology "cd /app && docker-compose build"
```

## 🚫 Common Deployment Failures

### 1. SCP Transfer Failures
**Problem**: SCP often fails with Synology due to path handling and protocol issues.

**Solution**: Always use `tar` over SSH:
```bash
# Transfer files using tar
tar czf - . | ssh anjan@192.168.0.32 "cd /volume1/docker/rag-practice-app && tar xzf -"
```

### 2. Port Already in Use
**Problem**: Previous deployments leave processes running on ports 8080, 6333, 6334.

**Solution**: Kill lingering processes before deployment:
```bash
ssh synology 'pkill -f uvicorn; pkill -f "python.*main"; lsof -ti:8080 | xargs kill -9 2>/dev/null || true'
```

### 3. Service Startup Order
**Problem**: FastAPI starts before Qdrant is ready, causing connection errors.

**Solution**: Start services in order with delays:
```bash
docker-compose up -d qdrant_rag
sleep 10
docker-compose up -d fastapi_rag_api
docker-compose up -d file_watcher_rag
```

### 4. Memory Exhaustion During Build
**Problem**: Building all services simultaneously exhausts Synology's memory.

**Solution**: 
- Use `--no-cache` to prevent bloated layer accumulation
- Clean up old images before building: `docker image prune -f`
- Consider building services one at a time if memory is limited

### 5. Python Async Blocking
**Problem**: Server hangs during startup due to blocking async operations.

**Symptoms**:
- TCP socket shows CLOSED state but process still running
- No response on port 8080
- Logs stop after "Starting server..."

**Solution**: 
- Check for blocking operations in async functions
- Use proper async/await patterns
- Test with direct uvicorn command for better error visibility

## 📦 Docker Compose Gotchas

### Path Handling
**Problem**: Synology's docker-compose has different path resolution than standard installations.

**Solution**: Always use full paths for docker-compose:
```bash
DOCKER_COMPOSE="/usr/local/bin/docker-compose"
```

### Volume Mounts
**Problem**: Relative paths in docker-compose.yml may not resolve correctly.

**Solution**: Use explicit volume declarations:
```yaml
volumes:
  - /volume1/docker/rag-practice-app/data:/app/data
  - /volume1/docker/rag-practice-app/logs:/app/logs
```

## 🔧 Environment-Specific Configurations

### spaCy Model Downloads
**Problem**: spaCy models fail to download during Docker build due to network restrictions.

**Solution**: Pre-download in Dockerfile:
```dockerfile
RUN python -m spacy download en_core_web_sm
```

### API Keys and Secrets
**Problem**: Missing or incorrectly formatted API keys cause silent failures.

**Solution**: Validate all required keys before deployment:
- GEMINI_API_KEY
- CLAUDE_API_KEY (if using Claude agents)
- ADMIN_USERNAME/PASSWORD
- QDRANT_URL

## 🚀 Performance Considerations

### Resource Limits
**Synology Specifications** (typical):
- RAM: 4-8GB
- CPU: 2-4 cores
- Storage: Varies

**Recommendations**:
- Limit concurrent connections: `--workers 2`
- Set memory limits in docker-compose.yml
- Monitor with `docker stats`

### Network Configuration
**Problem**: Cloudflare Access tokens expire or fail validation.

**Solution**: Set `BYPASS_CLOUDFLARE_AUTH=true` for internal deployments.

## 🛠️ Debugging Deployment Issues

### Essential Commands
```bash
# View real-time logs
ssh synology 'cd /volume1/docker/rag-practice-app && docker-compose logs -f'

# Check container health
ssh synology 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# Test API directly
ssh synology 'curl -s http://localhost:8080/health | jq .'

# Check disk space
ssh synology 'df -h /volume1'

# View Python errors
ssh synology 'cd /volume1/docker/rag-practice-app && docker-compose logs fastapi_rag_api | grep -i error'
```

### When All Else Fails
1. **Full cleanup and rebuild**:
   ```bash
   ssh synology 'cd /volume1/docker/rag-practice-app && docker-compose down -v'
   ssh synology 'docker system prune -af'
   ./deploy-and-build-synology.sh
   ```

2. **Manual startup for debugging**:
   ```bash
   ssh synology 'cd /volume1/docker/rag-practice-app/api && python -m uvicorn main:app --host 0.0.0.0 --port 8080 --log-level debug'
   ```

## 📋 Pre-Deployment Checklist

Before running deployment:
1. ✅ Run `./pre-deploy-check.sh` to validate prerequisites
2. ✅ Create backup with `./deploy-rollback.sh create`
3. ✅ Ensure `.env` file has all required keys
4. ✅ Verify Synology has sufficient disk space (5GB+)
5. ✅ Check no critical services are using required ports

## 🔄 Rollback Procedures

If deployment fails:
1. **List available backups**:
   ```bash
   ./deploy-rollback.sh list
   ```

2. **Rollback to previous version**:
   ```bash
   ./deploy-rollback.sh rollback backup_YYYYMMDD_HHMMSS
   ```

3. **Manual recovery** (if rollback script fails):
   ```bash
   ssh synology 'cd /volume1/docker && mv rag-practice-app rag-practice-app-failed'
   ssh synology 'cd /volume1/docker && mv rag-practice-app-backups/backup_latest rag-practice-app'
   ssh synology 'cd /volume1/docker/rag-practice-app && docker-compose up -d'
   ```

## 📚 Additional Resources

- [Synology Docker Documentation](https://www.synology.com/en-us/dsm/packages/Docker)
- [Docker Architecture Compatibility](https://docs.docker.com/desktop/multi-arch/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Qdrant Operations Manual](https://qdrant.tech/documentation/guides/administration/)

---

*Last Updated: January 2025*
*Based on real deployment experiences with RAG Practice App v2.0*