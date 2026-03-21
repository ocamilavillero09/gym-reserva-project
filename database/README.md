# Diseño de Base de Datos MongoDB - Sistema de Reservas de Gimnasio Universitario

## Estructura del Proyecto

```
database/
├── schema.json           # Esquema de colecciones y ejemplos
├── validations.js        # Validaciones de esquema MongoDB
├── indexes.js            # Índices recomendados
├── queries.js            # Queries para reglas de negocio
├── init.mongodb.js       # Script de inicialización para Docker
├── Dockerfile            # Imagen MongoDB personalizada
├── docker-compose.yml    # Orquestación del contenedor
└── README.md             # Este archivo
```

## Colecciones Principales

### 1. `users`
Estudiantes, entrenadores y administradores.

```javascript
{
  _id: ObjectId,
  nombre: string,
  correo_institucional: string (único),
  rol: enum["ESTUDIANTE", "ENTRENADOR", "ADMIN"],
  estado: enum["ACTIVO", "PENALIZADO", "INACTIVO"],
  fecha_creacion: ISODate,
  penalizacion_hasta: ISODate (opcional)
}
```

### 2. `schedules`
Horarios disponibles de lunes a viernes.

```javascript
{
  _id: ObjectId,
  fecha: ISODate (solo fecha),
  hora_inicio: string ("06:00" | "08:00" | "10:00" | "12:00" | "14:00" | "16:00"),
  hora_fin: string ("08:00" | "10:00" | "12:00" | "14:00" | "16:00" | "18:00"),
  aforo_maximo: integer,
  cupos_disponibles: integer,
  estado: enum["DISPONIBLE", "LLENO", "CANCELADO"],
  entrenador_id: ObjectId (opcional)
}
```

### 3. `reservations`
Reservas realizadas por usuarios.

```javascript
{
  _id: ObjectId,
  usuario_id: ObjectId,
  horario_id: ObjectId,
  fecha_reserva: ISODate,
  hora_inicio: string,
  hora_fin: string,
  estado: enum["ACTIVA", "CANCELADA", "COMPLETADA", "NO_SHOW"],
  creada_por: ObjectId,
  fecha_creacion: ISODate
}
```

### 4. `audit_log` (Auditoría)
Registro de operaciones importantes.

### 5. `configuration`
Configuración del sistema (aforo default, horarios, etc.).

---

## Reglas de Negocio y Estrategia de Implementación

### Regla: Máximo 2 Reservas Activas

**Restricción de BD:**
- Índice parcial único: `{ usuario_id: 1, horario_id: 1 }` con `partialFilterExpression: { estado: "ACTIVA" }`
- Esto impide que un usuario tenga dos reservas activas para el mismo horario

**Validación de límite (2 reservas):**
```javascript
// Query para contar reservas activas del usuario
const reservasActivas = db.reservations.countDocuments({
  usuario_id: usuarioId,
  estado: "ACTIVA",
  fecha_reserva: { $gte: hoy, $lte: fechaMaxima }
});

if (reservasActivas >= 2) {
  // Rechazar nueva reserva
}
```

**Caso especial viernes → lunes:**
- Calcular `fechaMaxima` según el día de la semana actual
- Si hoy es viernes (getDay() === 5), permitir hasta el lunes siguiente (+3 días)
- Si es otro día, permitir solo hasta mañana (+1 día)

### Regla: Bloques Horarios Fijos (06:00 a 16:00)

**Validación de BD:**
```javascript
// Regex para validar hora_inicio
pattern: "^(06|08|10|12|14|16):00$"
```

**Configuración:**
Almacenar bloques en colección `configuration` para fácil modificación:
```javascript
{
  clave: "BLOQUES_HORARIOS",
  valor: ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00"]
}
```

### Regla: Solo Lunes a Viernes

**Validación:**
```javascript
const diaSemana = fecha.getDay();
if (diaSemana === 0 || diaSemana === 6) {
  // Rechazar: domingo o sábado
}
```

**Índice TTL (opcional):** Para auto-limpiar horarios antiguos.

### Regla: Cupos Disponibles en Tiempo Real

**Estrategia de actualización:**
1. **Al crear reserva:** Decrementar `cupos_disponibles` en la misma transacción
2. **Al cancelar:** Incrementar `cupos_disponibles` en la misma transacción
3. **Verificación antes de reservar:**
   ```javascript
   const horario = db.schedules.findOne(
     { _id: horarioId },
     { cupos_disponibles: 1, estado: 1 }
   );
   if (horario.cupos_disponibles <= 0 || horario.estado === "LLENO") {
     // Rechazar
   }
   ```

### Regla: Cancelación Libera Cupo

**Transacción atómica:**
```javascript
session.startTransaction();
// 1. Actualizar reserva: estado = "CANCELADA"
// 2. Incrementar schedules.cupos_disponibles
// 3. Actualizar estado si pasaba de LLENO a DISPONIBLE
// 4. Registrar en audit_log
session.commitTransaction();
```

---

## Índices Clave

| Colección | Índice | Propósito |
|-----------|--------|-----------|
| users | `{ correo_institucional: 1 }` unique | Autenticación |
| users | `{ estado: 1, rol: 1 }` | Filtros de admin |
| schedules | `{ fecha: 1, hora_inicio: 1 }` unique | Evitar duplicados |
| schedules | `{ fecha: 1, estado: 1 }` | Query horarios disponibles |
| reservations | `{ usuario_id: 1, estado: 1, fecha_reserva: 1 }` | Contar reservas activas |
| reservations | `{ usuario_id: 1, horario_id: 1, estado: 1 }` partial unique | Evitar doble reserva misma hora |
| reservations | `{ horario_id: 1, estado: 1 }` | Verificar cupos |

---

## Instrucciones de Uso

### 1. Crear Base de Datos y Colecciones con Validaciones

```bash
mongosh < validations.js
```

### 2. Crear Índices

```bash
mongosh < indexes.js
```

### 3. Cargar Queries (para desarrollo/testing)

```bash
mongosh < queries.js
```

### 4. Insertar Configuración Inicial

```javascript
db.configuration.insertMany([
  { clave: "AFORO_DEFAULT", valor: 30, descripcion: "Aforo por defecto", ultima_actualizacion: new Date(), actualizado_por: ObjectId() },
  { clave: "BLOQUES_HORARIOS", valor: ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00"], descripcion: "Bloques horarios", ultima_actualizacion: new Date(), actualizado_por: ObjectId() },
  { clave: "MAX_RESERVAS_ACTIVAS", valor: 2, descripcion: "Máx reservas por usuario", ultima_actualizacion: new Date(), actualizado_por: ObjectId() }
]);
```

---

## Ejecutar con Docker

### Iniciar el contenedor

```bash
cd database
docker-compose up -d
```

### Verificar que está corriendo

```bash
docker-compose ps
docker-compose logs mongodb
```

### Detener el contenedor

```bash
docker-compose down
```

### Detener y eliminar volúmenes (borra todos los datos)

```bash
docker-compose down -v
```

---

## Conectar con mongosh

### Conexión local (sin Docker)

```bash
mongosh
```

### Conexión a Docker (con autenticación)

```bash
mongosh "mongodb://admin:password@localhost:27017/gym_reservas_universitario?authSource=admin"
```
### Conexión a Docker (con autenticación) No se tiene Mongo Shell instalado

```bash
docker exec -it gym-mongodb mongosh -u admin -p password --authenticationDatabase admin
```


### Usar la base de datos

```javascript
use gym_reservas_universitario
```

### Comandos útiles

```javascript
// Ver colecciones
show collections

// Contar documentos
db.users.countDocuments()
db.schedules.countDocuments()
db.reservations.countDocuments()

// Ver usuarios
db.users.find().pretty()

// Ver configuración
db.configuration.find().pretty()

// Ver horarios disponibles para una fecha
db.schedules.find({ fecha: new Date("2025-03-24"), estado: "DISPONIBLE" }).pretty()
```

### Salir de mongosh

```javascript
exit
```

---

## Notas de Diseño

### Transacciones
MongoDB soporta transacciones multi-documento desde v4.0 (replica sets) y v4.2 (sharded clusters). Las operaciones de **crear reserva** y **cancelar reserva** deben ejecutarse en transacciones para garantizar:
- Atomicidad de la operación completa
- Consistencia de cupos disponibles
- No race conditions en concurrencia

### Denormalización
Se almacenan copias de `hora_inicio` y `hora_fin` en `reservations` para:
- Evitar joins innecesarios al listar reservas del usuario
- Tener histórico si el horario se modifica

### Soft Deletes
Las reservas canceladas se mantienen con estado "CANCELADA" (no se borran físicamente) para:
- Historial completo
- Estadísticas
- Auditoría

### TTL (Time To Live)
- `audit_log`: Auto-eliminar después de 2 años
- `reservations` completadas/canceladas: Auto-eliminar después de 1 año (opcional)

---

## Patrones Utilizados

1. **Schema Validation**: Validaciones a nivel de base de datos
2. **Partial Indexes**: Índices únicos condicionados (reservas activas)
3. **Compound Indexes**: Índices compuestos para queries frecuentes
4. **Audit Trail**: Registro de todas las operaciones importantes
5. **Configuration Collection**: Settings centralizados y versionados
