# Gym Reservas - Sistema de Gestión de Reservas

Sistema de gestión de reservas para el gimnasio de la Universidad de Medellín.

---

## Tecnologías y Versiones

### Frontend
- **Framework:** React 18.2.0
- **Build Tool:** Vite 4.4.0
- **Lenguaje:** JavaScript (JSX)
- **Imagen Base:** Node.js 18-alpine

### Backend
- **Lenguaje:** Python 3.11
- **Framework:** Django 4.2.7
- **API Toolkit:** Django REST Framework 3.14.0
- **Documentación API:** drf-yasg 1.21.7 (Swagger/OpenAPI 2.0)
- **Base de Datos:** MongoDB 6.0 (vía PyMongo 4.6.0)
- **CORS:** django-cors-headers 4.3.0

### Base de Datos
- **Motor:** MongoDB 6.0
- **Esquema:** Ver carpeta `database/` con validaciones e índices

### Infraestructura
- **Contenedores:** Docker 20.10+
- **Orquestación:** Docker Compose 2.0+

---

## Cómo Clonar el Repositorio

```bash
git clone https://github.com/ocamilavillero09/gym-reserva-project.git
cd gym-reserva-project
```

---

## Cómo Descargar desde DockerHub

Cada servicio tiene su imagen publicada en DockerHub:

```bash
# Frontend
docker pull tav07/gym-frontend:latest

# Backend
docker pull tav07/gym-backend:latest

# Database
docker pull tav07/gym-database:latest
```

### Ejecutar con imágenes de DockerHub (sin clonar)

Usa este `docker-compose` inline para levantar los 3 servicios conectados:

```bash
cat > docker-compose-hub.yml << 'EOF'
version: "3.8"
services:
  frontend:
    image: tav07/gym-frontend:latest
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000/api
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    image: tav07/gym-backend:latest
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://database:27017
      - MONGO_DB=gym_udem
      - SECRET_KEY=django-insecure-gym-udem-2024-change-in-production
    depends_on:
      - database
    restart: unless-stopped

  database:
    image: tav07/gym-database:latest
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped

volumes:
  mongodb_data:
EOF

docker-compose -f docker-compose-hub.yml up
```

---

## Cómo Ejecutar con Docker Compose (Recomendado)

### Requisitos
- Docker 20.10+
- Docker Compose 2.0+
- Puertos 5173, 8000, 27017 disponibles

### Instrucciones paso a paso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/ocamilavillero09/gym-reserva-project.git
   cd gym-reserva-project
   ```

2. **Construir y levantar los servicios:**
   ```bash
   docker-compose up --build
   ```
   > Nota: la primera vez descarga las imágenes base e instala dependencias. Puede tardar 2-3 minutos.

3. **Acceder a las aplicaciones:**
   - Frontend: http://localhost:5173/index.html
   - Backend API: http://localhost:8000/api/
   - Swagger UI: http://localhost:8000/swagger/
   - ReDoc: http://localhost:8000/redoc/
   - MongoDB: localhost:27017

4. **Detener los servicios:**
   ```bash
   docker-compose down
   ```

   Para eliminar también los volúmenes (borra todos los datos):
   ```bash
   docker-compose down -v
   ```

---

## Variables de Entorno

### Frontend
| Variable | Descripción | Default |
|----------|-------------|---------|
| `VITE_API_URL` | URL completa del backend API | `http://localhost:8000/api` |

### Backend
| Variable | Descripción | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Clave secreta de Django | `django-insecure-gym-udem-2024-change-in-production` |
| `DEBUG` | Modo debug de Django | `True` |
| `MONGO_URI` | URI de conexión MongoDB | `mongodb://database:27017` |
| `MONGO_DB` | Nombre de la base de datos | `gym_udem` |

---

## Flujo de Prueba Completo (End-to-End)

Sigue estos pasos para verificar que frontend, backend y base de datos se comunican correctamente:

1. **Abrir el frontend** en http://localhost:5173/index.html
2. **Registrarse** con un correo institucional (`@udem.edu.co` o `@soyudemedellin.edu.co`)
3. **Iniciar sesión** con el correo registrado
4. **Ver horarios disponibles** en el Dashboard (carga desde MongoDB vía backend)
5. **Crear una reserva** — el cupo disponible se decrementa automáticamente
6. **Ver "Mis Reservas"** — lista las reservas activas guardadas en MongoDB
7. **Cancelar una reserva** — el cupo se libera inmediatamente
8. **Verificar en Swagger UI** (`http://localhost:8000/swagger/`) que todos los endpoints responden con los códigos esperados

### Verificación rápida con curl

```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@udem.edu.co","password":"test123"}'

# 2. Iniciar sesión
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@udem.edu.co","password":"test123"}'

# 3. Consultar horarios
curl http://localhost:8000/api/slots/

# 4. Crear reserva
curl -X POST http://localhost:8000/api/reservations/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@udem.edu.co","slotId":1}'

# 5. Ver reservas del usuario
curl "http://localhost:8000/api/reservations/?email=test@udem.edu.co"
```

---

## Estructura del Proyecto

```
gym-reserva-project/
├── frontend/          # React 18 + Vite
│   ├── dockerfile
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── services/
│   ├── index.html
│   └── vite.config.js
├── backend/           # Django 4.2.7 + DRF 3.14.0
│   ├── dockerfile
│   ├── requirements.txt
│   ├── api/
│   └── gym_api/
├── database/          # MongoDB 6.0
│   ├── Dockerfile
│   ├── init.mongodb.js
│   └── schema.json
└── docker-compose.yml
```

---

## Desarrollo Local (Sin Docker)

### Requisitos previos
- Node.js 18+
- Python 3.11+
- MongoDB corriendo localmente en el puerto 27017

### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env
echo SECRET_KEY=tu-clave-secreta > .env
echo DEBUG=True >> .env
echo MONGO_URI=mongodb://localhost:27017 >> .env
echo MONGO_DB=gym_udem >> .env

# Ejecutar servidor
python manage.py runserver
```

El backend estará disponible en http://localhost:8000

### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar servidor de desarrollo
npm run dev
```

El frontend estará disponible en http://localhost:5173/index.html

> Nota: Asegúrate de que el backend esté corriendo antes de abrir el frontend, ya que la aplicación React necesita conectarse a la API.

---

## Autores

Proyecto desarrollado para el curso de Ingeniería de Software — Universidad de Medellín.
