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
2. **Registrarse** con **nombre, correo institucional y documento de identidad** (RF01).
   El **dominio del correo define el rol** (RF03):

   | Dominio | Rol |
   |---|---|
   | `@soyudemedellin.edu.co` | Estudiante |
   | `@udem.edu.co` | Entrenador |
   | `@udemedellin.edu.co` | Administrador |

3. **Iniciar sesión** con el correo y el **documento de identidad como contraseña** (RF02)
4. **Perfil** — el estudiante gestiona edad, peso, altura y objetivo (RF04); el entrenador y
   el administrador consultan su nombre, documento y rol (RF05)
5. **Ver bloques horarios y cupos** en el Dashboard — la reserva es **para el día siguiente**
   y se muestra la fecha exacta (RF06/RF07/RF08)
6. **Crear una reserva** — llega la notificación de confirmación (RF23); si intentas una
   segunda para el mismo día, el sistema lo impide y avisa (RF09/RF24)
7. **Recargar la página (F5)** — la sesión se mantiene abierta
8. **"Mis Reservas" → cancelar** — el cupo se libera al instante y llega la notificación
   de cancelación (RF10/RF25)
9. **Entrar como entrenador o administrador** — se ve el **panel**, sin interfaz de reserva (RF12):
   - Buscar al estudiante **por su documento de identidad** y **registrar su asistencia** (RF11/RF13)
   - Ver los **estudiantes sin asistencia registrada** de la jornada (RF14)
   - **Procesar de forma general las inasistencias**: se penaliza a quien llegue a
     **5 inasistencias** (RF15/RF16)
   - Consultar el **reporte general diario** e **imprimirlo en PDF** (RF19/RF20)
10. **Como estudiante**, revisar el **historial** (RF17) y el **reporte personal** de
    inasistencias y penalizaciones en el Perfil (RF18)
11. **Como administrador principal** (el primer ADMIN registrado), crear otras cuentas de
    administrador y **retirarles el rol** en "Usuarios" (RF21/RF22)
12. **Verificar en Swagger UI** (`http://localhost:8000/swagger/`) que todos los endpoints
    responden con los códigos esperados

### Trazabilidad: requisito → endpoint

| Requisito | Endpoint |
|---|---|
| RF01 Registro con nombre, correo y documento | `POST /api/auth/register/` |
| RF02 Login con documento como contraseña | `POST /api/auth/login/` |
| RF03 Rol automático según el dominio | `POST /api/auth/register/` (campo `role` de la respuesta) |
| RF04 Perfil del estudiante (edad, peso, altura, objetivo) | `GET/PUT /api/users/profile/` |
| RF05 Perfil de entrenador/administrador | `GET /api/users/profile/` |
| RF06 Bloques horarios disponibles | `GET /api/slots/` |
| RF07 Cupos ocupados y disponibles | `GET /api/slots/` · `GET /api/reports/occupancy/` |
| RF08 Reserva para el día siguiente | `POST /api/reservations/` |
| RF09 Una sola reserva por día | `POST /api/reservations/` (409) |
| RF10 Consultar y cancelar la reserva | `GET /api/reservations/` · `DELETE /api/reservations/<id>/` |
| RF11 Buscar la reserva por documento | `GET /api/students/lookup/?documento=&actor_email=` |
| RF12 Staff visualiza sin reservar | `GET /api/reports/occupancy/` · `POST /api/reservations/` (403) |
| RF13 Registrar asistencia | `POST /api/attendance/register/` |
| RF14 Estudiantes sin asistencia registrada | `GET /api/attendance/pending/?actor_email=` |
| RF15 Procesar inasistencias en general | `POST /api/attendance/process/` |
| RF16 Penalización a las 5 inasistencias | `POST /api/attendance/process/` (`total_penalizados`) |
| RF17 Historial del estudiante | `GET /api/reservations/history/?email=` |
| RF18 Reporte personal | `GET /api/reports/personal/?email=` |
| RF19 Reporte general diario | `GET /api/reports/daily/?actor_email=` |
| RF20 Reporte general diario en PDF | `GET /api/reports/daily.pdf?actor_email=` |
| RF21 Crear cuentas de administrador | `POST /api/admin/users/` (solo el principal) |
| RF22 Retirar el rol de administrador | `PATCH /api/admin/users/<correo>/` con `accion: retirar` |
| RF23/RF24/RF25 Notificaciones | campo `notificacion` de `POST /api/reservations/` y `DELETE /api/reservations/<id>/` |

### Verificación rápida con curl

```bash
EST=test@soyudemedellin.edu.co;  DOC_EST=1001234567
COACH=coach@udem.edu.co;         DOC_COACH=7009998881
JEFA=jefa@udemedellin.edu.co;    DOC_JEFA=3005554442

# RF01 — Registro con nombre, correo institucional y documento de identidad
curl -X POST http://localhost:8000/api/auth/register/ -H "Content-Type: application/json" \
  -d "{\"name\":\"Test\",\"email\":\"$EST\",\"documento\":\"$DOC_EST\"}"
curl -X POST http://localhost:8000/api/auth/register/ -H "Content-Type: application/json" \
  -d "{\"name\":\"Coach\",\"email\":\"$COACH\",\"documento\":\"$DOC_COACH\"}"
curl -X POST http://localhost:8000/api/auth/register/ -H "Content-Type: application/json" \
  -d "{\"name\":\"Jefa\",\"email\":\"$JEFA\",\"documento\":\"$DOC_JEFA\"}"   # primer ADMIN = principal

# RF02 — Login con el documento como contraseña
curl -X POST http://localhost:8000/api/auth/login/ -H "Content-Type: application/json" \
  -d "{\"email\":\"$EST\",\"documento\":\"$DOC_EST\"}"

# RF04 — Edad, peso, altura y objetivo de entrenamiento
curl -X PUT http://localhost:8000/api/users/profile/ -H "Content-Type: application/json" \
  -d "{\"email\":\"$EST\",\"edad\":21,\"peso\":72,\"altura\":178,\"meta\":\"Ganar resistencia\"}"

# RF06/RF07 — Bloques horarios y cupos (la fecha es la de mañana)
curl http://localhost:8000/api/slots/
FECHA=$(curl -s http://localhost:8000/api/slots/ | python3 -c 'import json,sys;print(json.load(sys.stdin)["fecha"])')

# RF08/RF23 — Reserva del día siguiente y su notificación
curl -X POST http://localhost:8000/api/reservations/ -H "Content-Type: application/json" \
  -d "{\"email\":\"$EST\",\"slotId\":1}"

# RF09/RF24 — Segunda reserva del mismo día: rechazada y notificada
curl -X POST http://localhost:8000/api/reservations/ -H "Content-Type: application/json" \
  -d "{\"email\":\"$EST\",\"slotId\":2}"

# RF11 — El entrenador busca al estudiante por su documento
curl "http://localhost:8000/api/students/lookup/?documento=$DOC_EST&actor_email=$COACH"

# RF14 — Estudiantes con reserva y sin asistencia registrada
curl "http://localhost:8000/api/attendance/pending/?actor_email=$COACH&fecha=$FECHA"

# RF13 — Registrar la asistencia
curl -X POST http://localhost:8000/api/attendance/register/ -H "Content-Type: application/json" \
  -d "{\"actor_email\":\"$COACH\",\"documento\":\"$DOC_EST\",\"fecha\":\"$FECHA\"}"

# RF15/RF16 — Procesar las inasistencias de la jornada (penaliza a las 5)
curl -X POST http://localhost:8000/api/attendance/process/ -H "Content-Type: application/json" \
  -d "{\"actor_email\":\"$COACH\",\"fecha\":\"$FECHA\"}"

# RF17 — Historial · RF18 — Reporte personal del estudiante
curl "http://localhost:8000/api/reservations/history/?email=$EST"
curl "http://localhost:8000/api/reports/personal/?email=$EST"

# RF19/RF20 — Reporte general diario y su PDF
curl "http://localhost:8000/api/reports/daily/?actor_email=$COACH&fecha=$FECHA"
curl -o reporte_diario.pdf "http://localhost:8000/api/reports/daily.pdf?actor_email=$COACH&fecha=$FECHA"

# RF21 — El administrador principal crea otra cuenta de administrador
curl -X POST http://localhost:8000/api/admin/users/ -H "Content-Type: application/json" \
  -d "{\"actor_email\":\"$JEFA\",\"name\":\"Nueva Admin\",
       \"email\":\"nueva@udemedellin.edu.co\",\"documento\":\"3001112223\"}"

# RF22 — Retirarle el rol de administrador
curl -X PATCH http://localhost:8000/api/admin/users/nueva@udemedellin.edu.co/ \
  -H "Content-Type: application/json" -d "{\"actor_email\":\"$JEFA\",\"accion\":\"retirar\"}"
```

### Pruebas automatizadas

```bash
# Backend: 98 pruebas (reglas de negocio y RF01–RF25)
cd backend && python manage.py test api

# Frontend: pruebas unitarias de componentes y del cliente HTTP
cd frontend && npm test

# End-to-end con el stack levantado (docker compose up -d)
cd frontend && npx playwright test
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
