# Despliegue — Gym Reserva (minikube + Jenkins + ArgoCD + Grafana/Loki)

Arquitectura desplegada en un cluster local de **minikube**:

```
                  ┌──────────────────────── minikube ────────────────────────┐
  navegador  ──►  │  Service frontend (NodePort 30080)                         │
                  │      └─ nginx (React build)  ──/api──►  Service backend     │
                  │                                          └─ Django+DRF      │
                  │                                              └─► Service mongodb (Mongo 6 + PVC)
                  │                                                              │
                  │  observability: Loki + Promtail + Grafana (NodePort 30030)  │
                  │  argocd: sincroniza k8s/ desde GitHub                        │
                  └──────────────────────────────────────────────────────────┘

  Jenkins (CI):  tests unitarios ─► build imágenes ─► push a Docker Hub (ocamilavillero09)
```

## Componentes y carpetas

| Carpeta            | Qué contiene |
|--------------------|--------------|
| `backend/`         | API Django + DRF (Mongo via pymongo). Casos de uso críticos marcados en `api/views.py`. Tests en `api/tests.py`. |
| `frontend/`        | React + Vite. `Dockerfile.prod` + `nginx.conf` = imagen de producción que sirve estáticos y hace proxy `/api`. |
| `k8s/`             | Manifiestos del cluster (namespace, mongo, backend, frontend). **Fuente de verdad de ArgoCD**. |
| `observability/`   | Valores de Helm para Grafana + Loki + Promtail. |
| `jenkins/`         | `Jenkinsfile` del pipeline CI. |
| `argocd/`          | `Application` de ArgoCD que apunta a `k8s/`. |

## 1. Cluster + app

```bash
minikube start --cpus=4 --memory=6144 --driver=docker

# Imágenes (o dejar que Jenkins las publique en Docker Hub):
docker build -f backend/dockerfile      -t ocamilavillero09/gym-backend:latest  ./backend
docker build -f frontend/Dockerfile.prod -t ocamilavillero09/gym-frontend:latest ./frontend
minikube image load ocamilavillero09/gym-backend:latest
minikube image load ocamilavillero09/gym-frontend:latest

kubectl apply -f k8s/        # (o dejar que ArgoCD lo haga)
```

Acceso al frontend (driver docker en macOS necesita túnel):
```bash
minikube service frontend -n gym        # abre el navegador
# o:  kubectl port-forward -n gym svc/frontend 8080:80
```

## 2. Observabilidad (Grafana + Loki)

```bash
helm repo add grafana https://grafana.github.io/helm-charts && helm repo update
helm upgrade --install loki grafana/loki-stack \
  --namespace observability --create-namespace \
  -f observability/loki-stack-values.yaml

# Contraseña de admin de Grafana:
kubectl get secret loki-grafana -n observability -o jsonpath='{.data.admin-password}' | base64 -d
# Abrir Grafana:
minikube service loki-grafana -n observability
# Explore → datasource Loki → query: {namespace="gym"}
```

## 3. ArgoCD (GitOps)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f argocd/application.yaml

# Contraseña inicial de admin:
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
# UI:
kubectl port-forward svc/argocd-server -n argocd 8443:443   # https://localhost:8443
```

ArgoCD vigila `k8s/` en la rama `main` y sincroniza automáticamente (prune + selfHeal).

## 4. Jenkins (CI → Docker Hub)

```bash
# Jenkins con acceso al socket de Docker del host:
docker run -d --name jenkins -p 8081:8080 -p 50000:50000 \
  -v jenkins_home:/var/lib/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
# Password inicial:
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

En Jenkins:
1. Instalar plugins sugeridos + el plugin **Docker Pipeline**.
2. Crear credencial *Username/Password* con **ID: `dockerhub-creds`** (usuario `ocamilavillero09` + token de Docker Hub).
3. Crear un *Pipeline* que use `jenkins/Jenkinsfile` desde este repo (SCM).
4. Ejecutar: corre los tests, construye y publica `gym-backend:latest` y `gym-frontend:latest`.

Cuando Jenkins publica una nueva imagen `:latest`, ArgoCD/k8s la toma en el siguiente rollout.

## Casos de uso críticos

Marcados en `backend/api/views.py` como `CASO DE USO CRÍTICO #N`:

1. **Registro** con correo institucional + contraseña hasheada (PBKDF2).
2. **Login** con verificación de hash y mensaje genérico (anti-enumeración).
3. **Consulta de cupos** en tiempo real.
4. **Crear reserva** con descuento **atómico** de cupo (`find_one_and_update`) — evita sobreventa bajo concurrencia.
5. **Cancelar reserva** liberando cupo solo si el borrado ocurrió (anti doble-liberación).
