# Gym Reservas - Sistema de Gestión de Reservas

Sistema de gestión de reservas para el gimnasio de la Universidad de Medellín.

---

## Tecnologías y Versiones

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite 4.4
- **Lenguaje:** JavaScript (JSX)
- **Imagen Base:** Node.js 18-alpine

### Backend
- **Lenguaje:** Python 3.11
- **Framework:** Django 4.2.7
- **API Toolkit:** Django REST Framework 3.14.0
- **Documentación API:** drf-yasg 1.21.7 (Swagger/OpenAPI 2.0)
- **Base de Datos:** MongoDB (vía PyMongo 4.6.0)
- **CORS:** django-cors-headers 4.3.0

### Base de Datos
- **Motor:** MongoDB latest
- **Esquema:** Ver carpeta `database/` con validaciones e índices

### Infraestructura
- **Contenedores:** Docker 20+
- **Orquestación:** Docker Compose 2+

---

## Cómo Clonar el Repositorio

```bash
git clone https://github.com/ocamilavillero09/gym-reserva-project.git
cd gym-reserva-project
```

---

## Cómo Descargar desde DockerHub

Cada servicio tiene su imagen publicada:

```bash
# Frontend
docker pull tav07/gym-frontend:latest

# Backend
docker pull tav07/gym-backend:latest

# Database
docker pull tav07/gym-database:latest
```

Para ejecutar con imágenes de DockerHub (sin clonar):

```bash
docker run -p 5173:5173 tav07/gym-frontend:latest
docker run -p 8000:8000 -e MONGO_URI=mongodb://host.docker.internal:27017 tav07/gym-backend:latest
docker run -p 27017:27017 tav07/gym-database:latest
```

---

## Cómo Ejecutar con Docker Compose (Recomendado)

### Requisitos
- Docker 20.10+
- Docker Compose 2.0+
- Puerto 5173, 8000, 27017 disponibles

### Instrucciones

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/ocamilavillero09/gym-reserva-project.git
   cd gym-reserva-project
   ```

2. **Construir y levantar los servicios:**
   ```bash
   docker-compose up --build
   ```

3. **Acceder a las aplicaciones:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000/api/
   - Swagger UI: http://localhost:8000/swagger/
   - ReDoc: http://localhost:8000/redoc/
   - MongoDB: localhost:27017

4. **Detener los servicios:**
   ```bash
   docker-compose down
   ```

   Para eliminar también los volúmenes (borra datos):
   ```bash
   docker-compose down -v
   ```

---

## Variables de Entorno

### Frontend
| Variable | Descripción | Default |
|----------|-------------|---------|
| `VITE_API_URL` | URL del backend API | `http://localhost:8000/api` |

### Backend
| Variable | Descripción | Default |
|----------|-------------|---------|
| `MONGO_URI` | URI de conexión MongoDB | `mongodb://database:27017` |
| `MONGO_DB` | Nombre de la base de datos | `gym_udem` |

---

## Flujo de Prueba Completo

1. **Acceder al frontend** en `http://localhost:5173`
2. **Registrarse** con un correo institucional (`@udem.edu.co` o `@soyudemedellin.edu.co`)
3. **Iniciar sesión**
4. **Ver horarios disponibles** en el Dashboard
5. **Crear una reserva** (descuenta cupo automáticamente)
6. **Ver "Mis Reservas"** (lista reservas activas)
7. **Cancelar una reserva** (libera cupo inmediatamente)
8. **Verificar en Swagger UI** (`http://localhost:8000/swagger/`) que todos los endpoints responden correctamente

---

## Estructura del Proyecto

```
gym-reserva-project/
├── frontend/          # React + Vite
│   ├── dockerfile
│   ├── src/
│   └── vite.config.js
├── backend/           # Django + DRF
│   ├── dockerfile
│   ├── requirements.txt
│   ├── api/
│   └── gym_api/
├── database/          # MongoDB
│   ├── Dockerfile
│   ├── init.mongodb.js
│   └── schema.json
└── docker-compose.yml
```

---

## Desarrollo Local (Sin Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### MongoDB
Asegúrate de tener MongoDB corriendo localmente en el puerto 27017.

---

## Autores

Proyecto desarrollado para el curso de Ingeniería de Software - Universidad de Medellín.
