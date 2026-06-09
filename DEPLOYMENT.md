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

## CI/CD con GitHub Actions + ArgoCD (entrega continua real)

`.github/workflows/ci-cd.yml` hace, en cada push a `main`:
1. **test** — pruebas unitarias backend (Django + `coverage`) y frontend
   (Vitest + cobertura v8).
2. **e2e** — Playwright contra el stack completo levantado con `docker compose`
   (registro → login → reservar → cancelar). Local: `cd frontend && npm run test:e2e`.
3. **build-and-push** — si pasan tests y e2e, construye y publica en Docker Hub
   con dos tags: `:latest` y `:<sha-del-commit>`.
4. **deploy** — `kustomize edit set image` fija el tag al SHA en `k8s/kustomization.yaml`
   y lo commitea. **ArgoCD** detecta el cambio y despliega esa imagen exacta en
   minikube, bajándola desde Docker Hub (CD real).

Cobertura local:
- Backend: `cd backend && coverage run manage.py test api && coverage report` (~93%).
- Frontend: `cd frontend && npm run test:coverage`.

> Configurar en GitHub → Settings → Secrets and variables → Actions:
> `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`.

El pipeline de **Jenkins** (`jenkins/Jenkinsfile`) hace lo mismo (tests→build→push)
y queda como alternativa on-prem.

## Reglas de negocio implementadas (documento de análisis)

- **RF02 / HU11** — Roles ESTUDIANTE / ENTRENADOR / ADMIN (el panel del entrenador
  solo aparece para esos roles).
- **RF07** — El entrenador/admin reserva para un tercero (`actor_email`).
- **RN05 / HU08** — Máximo 2 reservas activas por usuario.
- **RN07** — Una reserva activa por usuario y bloque.
- **RN09 / HU20** — 3 inasistencias (No-Show, marcadas por el entrenador) → estado
  PENALIZADO por 5 días hábiles; el penalizado no puede reservar.
- **RNF2** — Frontend como PWA instalable (manifest + service worker).
- **RF11** — Historial de entrenamiento (`/reservations/history/`).
- **RF12** — Lista de espera para bloques llenos; al liberarse un cupo se avisa al primero.
- **RF13** — Perfil de usuario y metas (peso/altura/meta).
- **RF14** — Notificaciones push web (VAPID + service worker); disparo desde el panel del entrenador.
- **RF15** — Calificación del servicio (estrellas + comentarios).
- **RF16** — Dashboard de aforo proyectado (vista del entrenador).
- **RF17** — Asistencia (COMPLETADA) e inasistencia (No-Show) + reporte.
- **RF18** — Mantenimiento de máquinas (estado DISPONIBLE / FUERA_DE_SERVICIO).
- **RF19** — Exportación de reportes de uso en CSV y PDF (`/reports/usage.csv|pdf`).

Módulos backend: `api/views.py` (core), `api/features.py` (RF11–RF18),
`api/reports.py` (RF19), `api/push.py` (RF14).

## Casos de uso críticos

Marcados en `backend/api/views.py` como `CASO DE USO CRÍTICO #N`:

1. **Registro** con correo institucional + contraseña hasheada (PBKDF2).
2. **Login** con verificación de hash y mensaje genérico (anti-enumeración).
3. **Consulta de cupos** en tiempo real.
4. **Crear reserva** con descuento **atómico** de cupo (`find_one_and_update`) — evita sobreventa bajo concurrencia.
5. **Cancelar reserva** liberando cupo solo si el borrado ocurrió (anti doble-liberación).
