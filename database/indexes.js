// ============================================
// ÍNDICES RECOMENDADOS PARA MONGODB
// ============================================
// Ejecutar en MongoDB shell o mongosh

use gym_reservas_universitario;

// ============================================
// COLECCIÓN: users
// ============================================

// Índice único para correo institucional (autenticación)
db.users.createIndex(
  { "correo_institucional": 1 },
  { unique: true, name: "idx_users_email_unique" }
);

// Índice para búsqueda por rol (filtros de administrador)
db.users.createIndex(
  { "rol": 1 },
  { name: "idx_users_rol" }
);

// Índice compuesto para búsqueda de usuarios activos por rol
db.users.createIndex(
  { "estado": 1, "rol": 1 },
  { name: "idx_users_estado_rol" }
);

// Índice para verificar penalizaciones (TTL opcional para auto-limpieza)
db.users.createIndex(
  { "penalizacion_hasta": 1 },
  {
    name: "idx_users_penalizacion",
    sparse: true,
    expireAfterSeconds: 0  // Opcional: elimina documentos cuando expira (si se quiere auto-limpiar)
  }
);

// ============================================
// COLECCIÓN: schedules
// ============================================

// Índice compuesto para búsqueda de horarios por fecha y hora
// USO PRINCIPAL: Mostrar horarios disponibles de un día
db.schedules.createIndex(
  { "fecha": 1, "hora_inicio": 1 },
  { name: "idx_schedules_fecha_hora" }
);

// Índice para filtrar por estado (lleno/disponible)
db.schedules.createIndex(
  { "fecha": 1, "estado": 1 },
  { name: "idx_schedules_fecha_estado" }
);

// Índice compuesto único para evitar horarios duplicados
// MISMA FECHA + MISMA HORA_INICIO = UN SOLO HORARIO
db.schedules.createIndex(
  { "fecha": 1, "hora_inicio": 1 },
  { unique: true, name: "idx_schedules_unique_fecha_hora" }
);

// Índice para búsqueda por entrenador
db.schedules.createIndex(
  { "entrenador_id": 1, "fecha": 1 },
  { name: "idx_schedules_entrenador_fecha", sparse: true }
);

// Índice para búsqueda de horarios con cupos disponibles
db.schedules.createIndex(
  { "fecha": 1, "cupos_disponibles": 1, "estado": 1 },
  { name: "idx_schedules_disponibilidad" }
);

// ============================================
// COLECCIÓN: reservations
// ============================================

// Índice compuesto PRINCIPAL: Verificar reservas activas de un usuario
// USO: Validar regla de máximo 2 reservas activas
db.reservations.createIndex(
  { "usuario_id": 1, "estado": 1, "fecha_reserva": 1 },
  { name: "idx_reservations_user_estado_fecha" }
);

// Índice para búsqueda de reservas por horario
// USO: Verificar cupos, listar reservas de un horario
db.reservations.createIndex(
  { "horario_id": 1, "estado": 1 },
  { name: "idx_reservations_horario_estado" }
);

// Índice compuesto único: UN USUARIO NO PUEDE TENER DOS RESERVAS ACTIVAS
// EN EL MISMO HORARIO
db.reservations.createIndex(
  { "usuario_id": 1, "horario_id": 1, "estado": 1 },
  {
    unique: true,
    partialFilterExpression: { "estado": "ACTIVA" },
    name: "idx_reservations_unique_user_horario_activa"
  }
);

// Índice para búsqueda por fecha (reportes, estadísticas)
db.reservations.createIndex(
  { "fecha_reserva": 1, "estado": 1 },
  { name: "idx_reservations_fecha_estado" }
);

// Índice para TTL: Auto-archivar reservas viejas (opcional)
// Elimina reservas completadas/canceladas después de 1 año
db.reservations.createIndex(
  { "fecha_creacion": 1 },
  {
    name: "idx_reservations_ttl",
    expireAfterSeconds: 31536000,  // 1 año
    partialFilterExpression: {
      "estado": { "$in": ["COMPLETADA", "CANCELADA"] }
    }
  }
);

// Índice para reportes de asistencia
db.reservations.createIndex(
  { "usuario_id": 1, "fecha_creacion": -1 },
  { name: "idx_reservations_user_fecha_desc" }
);

// ============================================
// COLECCIÓN: audit_log
// ============================================

// Índice para consultas de auditoría por tipo
db.audit_log.createIndex(
  { "tipo_operacion": 1, "timestamp": -1 },
  { name: "idx_audit_tipo_timestamp" }
);

// Índice para consultar operaciones de un documento específico
db.audit_log.createIndex(
  { "coleccion_afectada": 1, "documento_id": 1, "timestamp": -1 },
  { name: "idx_audit_documento" }
);

// Índice TTL: Borrar logs antiguos después de 2 años
db.audit_log.createIndex(
  { "timestamp": 1 },
  {
    name: "idx_audit_ttl",
    expireAfterSeconds: 63072000  // 2 años
  }
);

// ============================================
// COLECCIÓN: configuration
// ============================================

db.configuration.createIndex(
  { "clave": 1 },
  { unique: true, name: "idx_config_clave_unique" }
);

// ============================================
// VERIFICACIÓN DE ÍNDICES CREADOS
// ============================================

print("Índices creados correctamente:");
print("\n=== users ===");
db.users.getIndexes().forEach(i => printjson(i));

print("\n=== schedules ===");
db.schedules.getIndexes().forEach(i => printjson(i));

print("\n=== reservations ===");
db.reservations.getIndexes().forEach(i => printjson(i));

print("\n=== audit_log ===");
db.audit_log.getIndexes().forEach(i => printjson(i));

print("\n=== configuration ===");
db.configuration.getIndexes().forEach(i => printjson(i));
