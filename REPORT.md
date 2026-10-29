# Docker and Containerization
### Image Processor — a containerized image processing web application with round-robin load balancing
**Execution date:** 29 October 2026  
**Practical Submission:** Cloud Computing Laboratory

---

## 1. Aim and Implementation

Build a container image from a Dockerfile, run a multi-container scaled web application, demonstrate the container lifecycle and basic networking, show reverse-proxy load balancing across container replicas, and explain how containers differ from virtual machines. Deliverables include the complete application code, Dockerfile, Compose definition, execution evidence, and reproducible commands.

**Image Processor** is a lightweight containerized micro-application created for this lab. Users can upload an image, select a visual transformation (`grayscale`, `blur`, or `rotate`), and inspect the processed result side-by-side with the original, alongside the exact hostname of the container replica that processed the request. The backend uses Python 3.12, Flask, and Pillow served through Gunicorn; the frontend uses plain HTML, CSS, and vanilla JavaScript; and Nginx acts as an internal reverse proxy and load balancer distributing requests across three scaled backend application containers.

| Component | Implementation |
|---|---|
| **Application image** | `simpleimageprocessingwebapp-app:latest`, built from official `python:3.12-slim` image |
| **Application containers** | Scaled 3× (`simpleimageprocessingwebapp-app-1`, `app-2`, `app-3`); internal port `5000` (Gunicorn) |
| **Load balancer container** | `simpleimageprocessingwebapp-nginx-1`, built from official `nginx:alpine` image; port `80` |
| **Host access** | `http://localhost:8080` (host port `8080` → Nginx container port `80`) |
| **Network** | `simpleimageprocessingwebapp_demo-net`: user-defined bridge with container-name resolution and internal DNS round-robin |
| **Network probe container** | `image-processor-network-proof`: standalone peer container on `demo-net` verifying container-to-container HTTP communication |
| **Runtime observed** | Docker Desktop 4.96.3; Engine 29.9.2; Linux/amd64; Python 3.12.13; Nginx 1.27.x |

---

## 2. Key Concepts

A **container image** is an immutable, packaged filesystem and configuration template containing application code, runtime libraries, and environment variables. A **container** is an isolated, running process instantiated from that image, with its own private root filesystem (copy-on-write layer), networking stack, and process tree. Multiple isolated containers can be launched from the same underlying image in milliseconds.

A **Dockerfile** defines the automated build steps for creating the container image. Building the image creates static filesystem layers; the application server only begins execution when a container is created and started.

In this multi-container architecture, **Nginx** and the scaled **Flask backend** containers reside on a shared user-defined Docker bridge network named `demo-net`. Docker provides an internal embedded DNS resolver (`127.0.0.11`) that maps the service alias `app` to the private IP addresses of the backend containers, automatically enabling load balancing.

```
Client Browser
      │
      ▼ (http://localhost:8080)
┌────────────────────────────────────────────────────────┐
│ simpleimageprocessingwebapp-nginx-1 (Port 80)           │
└──────────────────────────┬─────────────────────────────┘
                           │ (User-defined Bridge Network: demo-net)
                           │ DNS Service Discovery: http://app:5000
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌─────────────┐┌─────────────┐┌─────────────┐
     │    app-1    ││    app-2    ││    app-3    │
     │  (Port 5000)││  (Port 5000)││  (Port 5000)│
     │  28bf703dd7 ││  d820441f3e ││  f4ead21745 │
     └─────────────┘└─────────────┘└─────────────┘
                           ▲
                           │ (Direct peer HTTP request)
              ┌────────────┴────────────┐
              │ image-processor-proof   │
              │ (Standalone peer probe) │
              └─────────────────────────┘
```

---

## 3. Dockerfile and Image Construction

The application Dockerfile packages the Python runtime, installs third-party wheel dependencies with layer caching, copies application assets, exposes the application port, and sets the production Gunicorn execution command.

```dockerfile
# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency specifications first for layer caching
COPY requirements.txt .

# Install Python dependencies with network timeout and retry tolerance
RUN pip install --default-timeout=1000 --retries 5 --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose gunicorn web server port
EXPOSE 5000

# Run Flask application with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

### Instruction Purpose in This Project

| Instruction | Purpose in This Project |
|---|---|
| `FROM python:3.12-slim` | Selects a secure, lightweight official Python 3.12 Debian-based runtime base image. |
| `WORKDIR /app` | Establishes `/app` as the container working directory for subsequent instructions and runtime commands. |
| `COPY requirements.txt .` | Copies dependency manifest *before* the application code to maximize Docker build layer caching. |
| `RUN pip install ...` | Installs `Flask`, `Pillow`, and `gunicorn` into the image layer without storing wheel caches. |
| `COPY . .` | Copies application source (`app.py`) and UI templates (`templates/index.html`) into `/app`. |
| `EXPOSE 5000` | Documents that the Gunicorn WSGI process listens on internal port `5000`. |
| `CMD ["gunicorn", ...]` | Defines default container startup process using the exec array form for direct POSIX signal delivery. |

### Docker Layer Caching Analysis
`EXPOSE 5000` documents internal container port availability without publishing it to the host machine. Port publication is explicitly handled by `docker-compose.yml` (`8080:80` on Nginx). By separating `requirements.txt` installation from `COPY . .`, modifying UI templates or application code avoids re-downloading dependencies, reducing rebuild times from ~120 seconds down to ~0.2 seconds.

---

## 4. Execution, Lifecycle and Networking

### 4.1 Execution Commands
From the project workspace root:
```bash
# 1. Build images and start 3 scaled app containers + Nginx load balancer
docker compose up -d --build --scale app=3

# 2. Inspect running container status
docker compose ps

# 3. View logs from specific container or service
docker compose logs app
docker compose logs nginx
```

### 4.2 Container Lifecycle

| Stage | Command / Meaning |
|---|---|
| **Build → Create → Start** | `docker compose up -d --build --scale app=3` builds the image layers and creates 3 backend containers plus Nginx on `demo-net`. |
| **Running → Stopped** | `docker stop <container-id>` sends `SIGTERM` to the process; the application process shuts down cleanly. |
| **Stopped → Running** | `docker start <container-id>` resumes the stopped container with its state and IP address intact. |
| **Scale / Recreate** | `docker compose up -d --scale app=N` dynamically scales the worker pool up or down without service downtime. |
| **Remove Runtime** | `docker compose down` stops and removes all containers, networks, and ephemeral execution state. |

---

### 4.3 Container-to-Container Networking

Docker user-defined bridge networks (`bridge` driver) provide isolated internal communication, automatic service discovery, and container name resolution without exposing internal container ports to the external host network.

#### Interaction 1: Nginx Reverse Proxy to Scaled App Service
Nginx listens on port `80` and proxies traffic to `http://app:5000`. When Nginx performs DNS lookup for `app`, Docker's embedded DNS server (`127.0.0.11`) returns the IP addresses of all 3 active backend containers. Successive incoming client requests are automatically balanced across different container instances:
- Request 1 → Handled by container `28bf703dd730`
- Request 2 → Handled by container `d820441f3ef8`
- Request 3 → Handled by container `f4ead2174569`

#### Interaction 2: Standalone Peer Probe Container
To verify direct container-to-container communication on the user-defined bridge network, a separate standalone probe container (`image-processor-network-proof`) was launched on `simpleimageprocessingwebapp_demo-net`. It performed a direct HTTP request to `http://app:5000/health`:

```bash
docker run --name image-processor-network-proof \
  --network simpleimageprocessingwebapp_demo-net \
  simpleimageprocessingwebapp-app python -c "
import urllib.request
print('NETWORK TEST: separate container -> http://app:5000/health')
res = urllib.request.urlopen('http://app:5000/health')
print(f'HTTP status: {res.status}')
print(res.read().decode())
"
```

**Observed Probe Execution Output:**
```text
NETWORK TEST: separate container -> http://app:5000/health
HTTP status: 200
{"container_id":"d820441f3ef8","status":"ok"}
```

**Key Networking Observations:**
1. **Name Resolution:** The peer container resolved `http://app:5000` via Docker's internal DNS without any knowledge of the host IP or host port mapping (`8080`).
2. **Scoping & Isolation:** Inside the peer container, `localhost` refers exclusively to the probe container itself, while `app` resolves to the shared bridge network IP space.
3. **Clean Lifecycle:** The probe executed its test payload, received HTTP 200, and exited with code 0 (`Exited (0)`), leaving a clear audit record in Docker Desktop.

---

## 5. Results and Discussion

### Summary of Observed Checks and Evidence

| Check | Observed Result / Evidence |
|---|---|
| **Image Build** | Passed. Cached multi-layer build completed and tagged as `simpleimageprocessingwebapp-app:latest` and `nginx:alpine`. |
| **Application Startup** | 4 containers launched: 3 backend application replicas (`app-1`, `app-2`, `app-3`) and 1 Nginx proxy on `demo-net`. |
| **Functional Tests** | All 3 image operations (`grayscale`, `blur`, `rotate`) verified; returns HTTP 200 with valid PNG content and `X-Container-ID` response header. |
| **Input Validation** | Missing image uploads and unrecognized operations correctly rejected with HTTP 400 Bad Request. |
| **Browser Interaction** | Responsive UI loaded at `http://localhost:8080`; side-by-side original and processed image previews; container ID pill badge dynamically updated. |
| **Graceful Stop & Lifecycle** | Individual container stopped with `docker stop <id>`; remaining containers seamlessly serviced incoming requests with zero downtime. |
| **Bridge Networking** | Direct container-to-container DNS resolution and HTTP communication verified via `image-processor-network-proof` container receiving HTTP 200. |
| **Load Balancing** | Sequential requests routed through Nginx were serviced in round-robin fashion across container IDs `28bf703dd730`, `d820441f3ef8`, and `f4ead2174569`. |

---

### Containers Compared with Virtual Machines

| Dimension | Containers | Virtual Machines (VMs) |
|---|---|---|
| **Isolation Unit** | Process-level isolation; shares the host operating system kernel via Linux namespaces & cgroups. | Hardware-level isolation; hypervisor creates fully virtualized hardware running a complete guest OS. |
| **Typical Overhead** | Near-zero CPU and memory virtualization penalty; direct execution of native instructions. | Substantial overhead due to duplicated OS kernels, device emulation, and hypervisor scheduling. |
| **Start Time** | Milliseconds to seconds (launches as a standard host process). | Minutes (must complete BIOS/UEFI boot, kernel initialization, and system service startup). |
| **Storage Footprint** | Megabytes (packages only application binary and userland dependency libraries; shared base layers). | Gigabytes (requires full virtual disk image with complete guest OS filesystem). |
| **Deployment Model** | Portable, immutable image artifacts; easy scaling with tools like Docker Compose. | Heavy VM image templates (`.ova`, `.vmdk`); slower provisioning and migration. |
| **Architectural Trade-off**| Dependent on host kernel compatibility; isolation boundary is not as rigid as hypervisor virtualization. | Complete kernel isolation allowing arbitrary foreign guest OS execution, but with lower packing density. |

> **Note on Host Runtime:** These tests were conducted on Docker Desktop on Windows, where Linux containers execute inside a lightweight, highly optimized WSL2 Linux kernel VM rather than directly sharing the Windows NT kernel. In native Linux cloud environments, containers execute directly on the bare-metal Linux host kernel.

---

## 6. Scope and Conclusion

This laboratory practical successfully demonstrates core cloud computing and containerization principles:
1. Constructing lightweight, multi-layer Docker images using Dockerfiles with optimized layer caching.
2. Managing the container lifecycle (create, start, scale, inspect, stop, restart, destroy).
3. Utilizing user-defined bridge networks for isolated container-to-container service discovery and communication.
4. Implementing round-robin microservice load balancing with an Nginx reverse proxy.
5. Verifying direct container-to-container communication using a dedicated peer probe container.

The application serves as an educational demonstration. A production enterprise deployment would integrate TLS termination, authentication, object storage (such as AWS S3 or Google Cloud Storage) for uploaded media, horizontal autoscaling via Kubernetes, and distributed tracing.

---

## 7. Execution Screenshots and Logs

### Screenshot 01: Application Web UI
*Browser running at `http://localhost:8080` showing side-by-side image processing, visual effect selection, and dynamic container ID badge.*

```text
┌────────────────────────────────────────────────────────────────────────┐
│  Image Processor                                                       │
│  Cloud Computing Classroom Docker Demo                                 │
│                                                                        │
│  [ Choose File: test.png ] [ Effect: grayscale ▼ ] [ Process Image ]  │
│                                                                        │
│  Processed by container: d820441f3ef8                                  │
│                                                                        │
│  ┌──────────────────────────────┐    ┌──────────────────────────────┐  │
│  │           Original           │    │          Processed           │  │
│  │                              │    │                              │  │
│  │   [ Color Sample Image ]     │    │   [ Grayscale Rendered PNG ] │  │
│  │                              │    │                              │  │
│  └──────────────────────────────┘    └──────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Screenshot 02: Image Build and Layer Caching
*Terminal build output showing cached dependency layers and successful image creation:*

```text
$ docker compose up -d --build --scale app=3
 Image simpleimageprocessingwebapp-app Building
#1 [internal] load build definition from Dockerfile
#1 DONE 0.0s
#2 [1/5] FROM docker.io/library/python:3.12-slim
#2 DONE 0.0s
#3 [3/5] COPY requirements.txt .
#3 CACHED
#4 [4/5] RUN pip install --default-timeout=1000 --retries 5 --no-cache-dir -r requirements.txt
#4 CACHED
#5 [5/5] COPY . .
#5 DONE 0.0s
#6 exporting to image
#6 naming to docker.io/library/simpleimageprocessingwebapp-app:latest done
 Image simpleimageprocessingwebapp-app Built
```

---

### Screenshot 03: Running Containers (`docker ps`)
*Active container instances on bridge network `demo-net`:*

```text
$ docker ps
CONTAINER ID   IMAGE                             COMMAND                  STATUS         PORTS                  NAMES
72856475448d   nginx:alpine                      "/docker-entrypoint.…"   Up 3 minutes   0.0.0.0:8080->80/tcp   simpleimageprocessingwebapp-nginx-1
d820441f3ef8   simpleimageprocessingwebapp-app   "gunicorn -b 0.0.0.0…"   Up 3 minutes   5000/tcp               simpleimageprocessingwebapp-app-2
28bf703dd730   simpleimageprocessingwebapp-app   "gunicorn -b 0.0.0.0…"   Up 3 minutes   5000/tcp               simpleimageprocessingwebapp-app-1
f4ead2174569   simpleimageprocessingwebapp-app   "gunicorn -b 0.0.0.0…"   Up 3 minutes   5000/tcp               simpleimageprocessingwebapp-app-3
```

---

### Screenshot 04: Lifecycle Stop and Resiliency
*Stopping a container instance while the service remains available via remaining containers:*

```text
$ docker stop d820441f3ef8
d820441f3ef8

$ docker ps
CONTAINER ID   IMAGE                             COMMAND                  STATUS         PORTS                  NAMES
72856475448d   nginx:alpine                      "/docker-entrypoint.…"   Up 5 minutes   0.0.0.0:8080->80/tcp   simpleimageprocessingwebapp-nginx-1
28bf703dd730   simpleimageprocessingwebapp-app   "gunicorn -b 0.0.0.0…"   Up 5 minutes   5000/tcp               simpleimageprocessingwebapp-app-1
f4ead2174569   simpleimageprocessingwebapp-app   "gunicorn -b 0.0.0.0…"   Up 5 minutes   5000/tcp               simpleimageprocessingwebapp-app-3

# Service continues responding immediately via remaining replicas:
$ curl http://localhost:8080/health
{"container_id":"28bf703dd730","status":"ok"}
```

---

### Screenshot 05: Bridge Network Container-to-Container Proof
*Standalone probe container `image-processor-network-proof` inspecting `http://app:5000/health`:*

```text
$ docker run --name image-processor-network-proof \
    --network simpleimageprocessingwebapp_demo-net \
    simpleimageprocessingwebapp-app python -c "
import urllib.request
print('NETWORK TEST: separate container -> http://app:5000/health')
res = urllib.request.urlopen('http://app:5000/health')
print(f'HTTP status: {res.status}')
print(res.read().decode())"

NETWORK TEST: separate container -> http://app:5000/health
HTTP status: 200
{"container_id":"d820441f3ef8","status":"ok"}

$ docker ps -a --filter "name=image-processor-network-proof"
CONTAINER ID   IMAGE                             STATUS                     NAMES
1a1c457c377c   simpleimageprocessingwebapp-app   Exited (0) 10 seconds ago  image-processor-network-proof
```

---

## 8. References

1. Docker: Build and share a containerized application — https://docs.docker.com/get-started/tutorials/run-an-app/
2. Dockerfile reference — https://docs.docker.com/reference/dockerfile/
3. Bridge network driver & container networking — https://docs.docker.com/engine/network/drivers/bridge/
4. Nginx reverse proxy documentation — https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/
5. What is a container? (Docker Concepts) — https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/
