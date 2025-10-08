<div align="center">

# ❤️ Health Check

**API health and status monitoring**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

</div>

---

## 📋 Overview

Health check endpoint provides a simple way to verify that the API is running and accessible. Useful for monitoring, load balancers, and uptime checks.

**🔓 Authentication:** Not required

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Get API health status |

---

## Health Check

### `GET /health`

Check if the API is running and get basic service information.

### Request

**Headers:**
```
(No headers required)
```

**Query Parameters:**
```
(No parameters required)
```

### Response

**Success (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-08T10:30:45.123456",
  "version": "1.0.0"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Service health status (always `"healthy"`) |
| `timestamp` | string | Current server timestamp (ISO 8601 format) |
| `version` | string | API version number |

---

## Postman Testing

### Basic Health Check

**Step 1:** Create new GET request
```
GET http://localhost:8000/health
```

**Step 2:** Send request (no authentication needed)

**Step 3:** Verify response status is 200 OK

**Step 4:** Check response body has `"status": "healthy"`

### Automated Testing

**Add to Tests tab in Postman:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("API is healthy", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("healthy");
});

pm.test("Response has version", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.version).to.exist;
});
```

---

## cURL Examples

### Basic Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

### With Verbose Output
```bash
curl -v -X GET "http://localhost:8000/health"
```

### Silent Check (Exit Code Only)
```bash
curl -s -f -o /dev/null "http://localhost:8000/health" && echo "API is up" || echo "API is down"
```

---

## 🔧 Use Cases

### 1. Uptime Monitoring

Monitor API availability with cron job:

```bash
#!/bin/bash
# check_api_health.sh

URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): API is healthy"
else
    echo "$(date): API is DOWN! Status code: $RESPONSE"
    # Send alert email/notification
fi
```

**Cron schedule (check every 5 minutes):**
```bash
*/5 * * * * /path/to/check_api_health.sh >> /var/log/api_health.log
```

---

### 2. Docker Health Check

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

# ... app setup ...

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**docker-compose.yml:**
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

### 3. Kubernetes Liveness Probe

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: chatbot-api:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

### 4. Load Balancer Health Check

**NGINX:**
```nginx
upstream api_backend {
    server api1.example.com:8000;
    server api2.example.com:8000;
    server api3.example.com:8000;
}

server {
    location / {
        proxy_pass http://api_backend;

        # Health check
        health_check interval=10s fails=3 passes=2 uri=/health;
    }
}
```

**AWS Application Load Balancer (ALB):**
```json
{
  "HealthCheckPath": "/health",
  "HealthCheckIntervalSeconds": 30,
  "HealthCheckTimeoutSeconds": 5,
  "HealthyThresholdCount": 2,
  "UnhealthyThresholdCount": 3
}
```

---

### 5. Monitoring Script (Python)

```python
import requests
import time
from datetime import datetime

def check_api_health(url="http://localhost:8000/health"):
    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"{datetime.now()}: ✓ API healthy - v{data['version']}")
            return True
        else:
            print(f"{datetime.now()}: ✗ API unhealthy - Status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"{datetime.now()}: ✗ API unreachable - {str(e)}")
        return False

if __name__ == "__main__":
    while True:
        check_api_health()
        time.sleep(60)  # Check every minute
```

---

## 📊 Monitoring Integration

### Prometheus Metrics (Future Enhancement)

While current health check is simple, you can enhance it with metrics:

```python
# Example enhancement
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": settings.app_version,
        "services": {
            "redis": check_redis_connection(),
            "postgres": check_postgres_connection(),
            "pinecone": check_pinecone_connection(),
        },
        "metrics": {
            "uptime_seconds": get_uptime(),
            "total_requests": get_request_count(),
        }
    }
```

### Grafana Dashboard

Monitor health check metrics:
- Response time trends
- Uptime percentage
- Service availability

---

## 🛠️ Troubleshooting

### Issue 1: Health Check Returns 404

**Cause:** API not running or wrong URL

**Solutions:**
```bash
# Check if API is running
ps aux | grep uvicorn

# Check correct port
netstat -tuln | grep 8000

# Try different URL
curl http://localhost:8000/health  # Local
curl http://0.0.0.0:8000/health    # All interfaces
curl http://SERVER_IP:8000/health  # Remote
```

---

### Issue 2: Connection Refused

**Cause:** API not started or firewall blocking

**Solutions:**
```bash
# Start API
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check firewall
sudo ufw status
sudo ufw allow 8000

# Check if port is in use
lsof -i :8000
```

---

### Issue 3: Slow Response Time

**Cause:** Server overloaded or network issues

**Solutions:**
```bash
# Check response time
time curl http://localhost:8000/health

# Monitor system resources
top
htop
free -h

# Check network latency
ping SERVER_IP
traceroute SERVER_IP
```

---

## 📈 Expected Performance

| Metric | Expected Value |
|--------|----------------|
| Response time | < 100ms |
| Success rate | 99.9%+ |
| Payload size | < 200 bytes |
| Memory usage | Minimal |
| CPU usage | Negligible |

---

## 💡 Best Practices

### 1. Don't Rely Solely on Health Check

Health check only verifies the API is responding, not that all features work.

**Better approach:**
- Use health check for basic availability
- Add separate endpoints for deep health checks
- Monitor actual user requests and errors

### 2. Set Appropriate Timeouts

```python
# Good: Short timeout
response = requests.get("/health", timeout=5)

# Bad: No timeout or too long
response = requests.get("/health", timeout=30)
```

### 3. Monitor Trends, Not Just Status

```
✅ Good: Alert if health check fails 3 times in 5 minutes
❌ Bad: Alert on single health check failure
```

### 4. Include Health Check in CI/CD

```yaml
# GitHub Actions example
- name: Health Check
  run: |
    curl -f http://localhost:8000/health || exit 1
```

---

## 🔍 Testing

### Manual Test
```bash
curl http://localhost:8000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-08T10:30:45.123456",
  "version": "1.0.0"
}
```

### Automated Test (bash)
```bash
#!/bin/bash
response=$(curl -s http://localhost:8000/health)
status=$(echo $response | jq -r '.status')

if [ "$status" == "healthy" ]; then
    echo "✓ Health check passed"
    exit 0
else
    echo "✗ Health check failed"
    exit 1
fi
```

---

## 📚 Related Documentation

- [← Previous: Chat History](./05-chat-history.md)
- [Back to API Index](./README.md)

---

## 🔗 Quick Links

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

---

<div align="center">

**Built with** FastAPI

[⬆️ Back to Top](#️-health-check)

</div>
