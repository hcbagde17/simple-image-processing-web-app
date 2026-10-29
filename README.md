# Image Processor - Docker Demo

A containerized image processing web application designed as a simple showcase for a Cloud Computing course. Users upload an image, select a visual transformation (grayscale, blur, or rotate), and observe which container replica processed the request behind an Nginx load balancer.

## Quick Start

```bash
# 1. Build and run the application with 3 scaled app containers
docker compose up -d --build --scale app=3

# 2. Open the web interface in your browser
# Navigate to: http://localhost:8080

# 3. Stop and clean up containers and networks
docker compose down
```

## Course Topics in This Project

| Course Topic | Where it Appears in the Project |
|---|---|
| **Container Images** | Base image (`python:3.12-slim`), custom built application image (`app`), and lightweight proxy image (`nginx:alpine`) |
| **Dockerfile** | `app/Dockerfile` with layered instructions and caching for dependency installation |
| **Container Lifecycle** | Scaling up replicas (`--scale app=3`), inspecting running states (`docker ps`), stopping, and restarting containers |
| **Basic Networking** | User-defined bridge network (`demo-net`), internal DNS service discovery (`http://app:5000`), and published host port (`8080:80`) |
| **Containers vs VMs** | Running multiple isolated application instances on a shared host OS kernel with near-instant startup |

## Showcase Demo Commands

```bash
# List local images and running containers
docker images
docker ps

# Demonstrate container lifecycle & fault tolerance (app keeps running on remaining containers)
docker stop <id>
docker start <id>

# View application logs from a container instance
docker logs <id>

# Inspect Docker networks
docker network ls

# Test container-to-container networking (peer container queries backend service alias via internal DNS)
docker run --name image-processor-network-proof --rm --network simpleimageprocessingwebapp_demo-net simpleimageprocessingwebapp-app python -c "import urllib.request; res = urllib.request.urlopen('http://app:5000/health'); print(f'HTTP {res.status}: {res.read().decode()}')"

# Inspect container resource utilization snapshot
docker stats --no-stream
```

## Containers vs Virtual Machines (VMs)

| Dimension | Containers | Virtual Machines (VMs) |
|---|---|---|
| **Start Time** | Seconds (executes as standard process on host kernel) | Minutes (must boot full operating system) |
| **Size** | Megabytes (application code and userland libraries only) | Gigabytes (contains complete guest OS and kernel) |
| **Isolation** | Process-level isolation via kernel namespaces and cgroups | Hardware-level isolation via hypervisor virtualization |
| **Overhead** | Very low (native system calls directly on host kernel) | High (hypervisor abstraction and duplicated guest OS) |
