// ============================================
// SCRIPT DE INICIALIZACIÓN DE MONGODB
// ============================================
// Este script se ejecuta automáticamente al iniciar el contenedor
// si la base de datos aún no existe o está vacía.

print("========================================");
print("INICIANDO CONFIGURACIÓN DE BASE DE DATOS");
print("========================================");

// ============================================
// CREAR BASE DE DATOS Y COLECCIONES
// ============================================

db = db.getSiblingDB('gym_reservas_universitario');

// ============================================
// CREAR COLECCIONES CON VALIDACIÓN DE ESQUEMA
// ============================================

// Colección: users
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["nombre", "correo_institucional", "rol", "estado", "fecha_creacion"],
      properties: {
        nombre: {
          bsonType: "string",
          minLength: 2,
          maxLength: 100,
          description: "Nombre completo del usuario (2-100 caracteres)"
        },
        correo_institucional: {
          bsonType: "string",
          pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.(edu|edu\\.[a-z]{2,})$",
          description: "Correo institucional válido con dominio .edu"
        },
        rol: {
          enum: ["ESTUDIANTE", "ENTRENADOR", "ADMIN"],
          description: "Rol debe ser ESTUDIANTE, ENTRENADOR o ADMIN"
        },
        estado: {
          enum: ["ACTIVO", "PENALIZADO", "INACTIVO"],
          description: "Estado debe ser ACTIVO, PENALIZADO o INACTIVO"
        },
        fecha_creacion: {
          bsonType: "date",
          description: "Fecha de creación del usuario"
        },
        ultimo_acceso: {
          bsonType: ["date", "null"],
          description: "Último acceso del usuario"
        },
        penalizacion_hasta: {
          bsonType: ["date", "null"],
          description: "Fecha hasta la que está penalizado"
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// Colección: schedules
db.createCollection("schedules", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["fecha", "hora_inicio", "hora_fin", "aforo_maximo", "cupos_disponibles", "estado", "fecha_creacion"],
      properties: {
        fecha: {
          bsonType: "date",
          description: "Fecha del horario (sin componente de hora)"
        },
        hora_inicio: {
          bsonType: "string",
          pattern: "^(06|08|10|12|14|16):00$",
          description: "Hora de inicio debe ser: 06:00, 08:00, 10:00, 12:00, 14:00 o 16:00"
        },
        hora_fin: {
          bsonType: "string",
          pattern: "^(08|10|12|14|16|18):00$",
          description: "Hora de fin debe ser 2 horas después del inicio"
        },
        aforo_maximo: {
          bsonType: "int",
          minimum: 1,
          maximum: 500,
          description: "Aforo máximo entre 1 y 500"
        },
        cupos_disponibles: {
          bsonType: "int",
          minimum: 0,
          description: "Cupos disponibles no puede ser negativo"
        },
        estado: {
          enum: ["DISPONIBLE", "LLENO", "CANCELADO"],
          description: "Estado debe ser DISPONIBLE, LLENO o CANCELADO"
        },
        entrenador_id: {
          bsonType: ["objectId", "null"],
          description: "Referencia al entrenador (opcional)"
        },
        notas: {
          bsonType: ["string", "null"],
          maxLength: 500,
          description: "Notas opcionales (máx 500 caracteres)"
        },
        fecha_creacion: {
          bsonType: "date",
          description: "Fecha de creación del horario"
        },
        ultima_actualizacion: {
          bsonType: ["date", "null"],
          description: "Última actualización"
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// Colección: reservations
db.createCollection("reservations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["usuario_id", "horario_id", "fecha_reserva", "hora_inicio", "hora_fin", "estado", "creada_por", "fecha_creacion"],
      properties: {
        usuario_id: {
          bsonType: "objectId",
          description: "Referencia al usuario que reserva"
        },
        horario_id: {
          bsonType: "objectId",
          description: "Referencia al horario reservado"
        },
        fecha_reserva: {
          bsonType: "date",
          description: "Fecha del horario reservado"
        },
        hora_inicio: {
          bsonType: "string",
          pattern: "^(06|08|10|12|14|16):00$",
          description: "Hora de inicio debe ser un bloque válido"
        },
        hora_fin: {
          bsonType: "string",
          pattern: "^(08|10|12|14|16|18):00$",
          description: "Hora de fin correspondiente"
        },
        estado: {
          enum: ["ACTIVA", "CANCELADA", "COMPLETADA", "NO_SHOW"],
          description: "Estado debe ser ACTIVA, CANCELADA, COMPLETADA o NO_SHOW"
        },
        creada_por: {
          bsonType: "objectId",
          description: "Usuario que creó la reserva"
        },
        fecha_creacion: {
          bsonType: "date",
          description: "Timestamp de creación"
        },
        fecha_cancelacion: {
          bsonType: ["date", "null"],
          description: "Fecha de cancelación"
        },
        motivo_cancelacion: {
          bsonType: ["string", "null"],
          maxLength: 500,
          description: "Motivo de la cancelación"
        },
        fecha_completacion: {
          bsonType: ["date", "null"],
          description: "Fecha cuando completó la asistencia"
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// Colección: audit_log
db.createCollection("audit_log", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["tipo_operacion", "coleccion_afectada", "documento_id", "usuario_ejecutor", "timestamp"],
      properties: {
        tipo_operacion: {
          enum: ["RESERVA_CREADA", "RESERVA_CANCELADA", "CUPO_LIBERADO", "CUPO_OCUPADO", "PENALIZACION_APLICADA", "HORARIO_CREADO", "HORARIO_MODIFICADO"],
          description: "Tipo de operación auditada"
        },
        coleccion_afectada: {
          bsonType: "string",
          minLength: 1,
          description: "Nombre de la colección afectada"
        },
        documento_id: {
          bsonType: "objectId",
          description: "ID del documento afectado"
        },
        usuario_ejecutor: {
          bsonType: "objectId",
          description: "Usuario que ejecutó la operación"
        },
        datos_anteriores: {
          bsonType: ["object", "null"],
          description: "Estado anterior del documento"
        },
        datos_nuevos: {
          bsonType: ["object", "null"],
          description: "Nuevo estado del documento"
        },
        timestamp: {
          bsonType: "date",
          description: "Timestamp de la operación"
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// Colección: configuration
db.createCollection("configuration", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["clave", "valor", "descripcion", "ultima_actualizacion", "actualizado_por"],
      properties: {
        clave: {
          bsonType: "string",
          minLength: 1,
          maxLength: 50,
          description: "Clave de configuración única"
        },
        valor: {
          description: "Valor de la configuración (cualquier tipo)"
        },
        descripcion: {
          bsonType: "string",
          maxLength: 500,
          description: "Descripción de la configuración"
        },
        ultima_actualizacion: {
          bsonType: "date",
          description: "Última fecha de actualización"
        },
        actualizado_por: {
          bsonType: "objectId",
          description: "Usuario que actualizó la configuración"
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

print("Colecciones creadas con validaciones de esquema.");

// ============================================
// CREAR ÍNDICES
// ============================================

// Índices: users
db.users.createIndex({ "correo_institucional": 1 }, { unique: true, name: "idx_users_email_unique" });
db.users.createIndex({ "rol": 1 }, { name: "idx_users_rol" });
db.users.createIndex({ "estado": 1, "rol": 1 }, { name: "idx_users_estado_rol" });
db.users.createIndex({ "penalizacion_hasta": 1 }, { name: "idx_users_penalizacion", sparse: true });

// Índices: schedules
db.schedules.createIndex({ "fecha": 1, "hora_inicio": 1 }, { unique: true, name: "idx_schedules_unique_fecha_hora" });
db.schedules.createIndex({ "fecha": 1, "estado": 1 }, { name: "idx_schedules_fecha_estado" });
db.schedules.createIndex({ "entrenador_id": 1, "fecha": 1 }, { name: "idx_schedules_entrenador_fecha", sparse: true });
db.schedules.createIndex({ "fecha": 1, "cupos_disponibles": 1, "estado": 1 }, { name: "idx_schedules_disponibilidad" });

// Índices: reservations
db.reservations.createIndex({ "usuario_id": 1, "estado": 1, "fecha_reserva": 1 }, { name: "idx_reservations_user_estado_fecha" });
db.reservations.createIndex({ "horario_id": 1, "estado": 1 }, { name: "idx_reservations_horario_estado" });
db.reservations.createIndex(
  { "usuario_id": 1, "horario_id": 1, "estado": 1 },
  { unique: true, partialFilterExpression: { "estado": "ACTIVA" }, name: "idx_reservations_unique_user_horario_activa" }
);
db.reservations.createIndex({ "fecha_reserva": 1, "estado": 1 }, { name: "idx_reservations_fecha_estado" });
db.reservations.createIndex({ "usuario_id": 1, "fecha_creacion": -1 }, { name: "idx_reservations_user_fecha_desc" });

// Índices: audit_log
db.audit_log.createIndex({ "tipo_operacion": 1, "timestamp": -1 }, { name: "idx_audit_tipo_timestamp" });
db.audit_log.createIndex({ "coleccion_afectada": 1, "documento_id": 1, "timestamp": -1 }, { name: "idx_audit_documento" });
db.audit_log.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 63072000, name: "idx_audit_ttl" }); // 2 años TTL

// Índices: configuration
db.configuration.createIndex({ "clave": 1 }, { unique: true, name: "idx_config_clave_unique" });

print("Índices creados exitosamente.");

// ============================================
// INSERTAR DATOS INICIALES
// ============================================

// Verificar si ya existen datos
const existingUsers = db.users.countDocuments();
if (existingUsers > 0) {
  print("La base de datos ya contiene datos. Omitiendo inserción de seed data.");
} else {
  print("Insertando datos iniciales...");

  // Usuarios de ejemplo
  const adminId = ObjectId("65f8a2b3c4d5e6f7a8b9c000");

  const usuarios = [
    {
      _id: ObjectId("65f8a2b3c4d5e6f7a8b9c001"),
      nombre: "Ana María López",
      correo_institucional: "ana.lopez@universidad.edu",
      rol: "ESTUDIANTE",
      estado: "ACTIVO",
      fecha_creacion: new Date("2025-01-15T10:30:00Z"),
      ultimo_acceso: new Date("2025-03-20T08:15:00Z")
    },
    {
      _id: ObjectId("65f8a2b3c4d5e6f7a8b9c002"),
      nombre: "Carlos Rodríguez Pérez",
      correo_institucional: "carlos.rodriguez@universidad.edu",
      rol: "ESTUDIANTE",
      estado: "ACTIVO",
      fecha_creacion: new Date("2025-01-16T09:00:00Z"),
      ultimo_acceso: new Date("2025-03-19T18:30:00Z")
    },
    {
      _id: ObjectId("65f8a2b3c4d5e6f7a8b9c003"),
      nombre: "Pedro Sánchez Vega",
      correo_institucional: "pedro.sanchez@universidad.edu",
      rol: "ENTRENADOR",
      estado: "ACTIVO",
      fecha_creacion: new Date("2024-08-01T08:00:00Z"),
      ultimo_acceso: new Date("2025-03-20T06:00:00Z")
    },
    {
      _id: adminId,
      nombre: "Administrador del Sistema",
      correo_institucional: "admin@universidad.edu",
      rol: "ADMIN",
      estado: "ACTIVO",
      fecha_creacion: new Date("2024-01-01T00:00:00Z"),
      ultimo_acceso: new Date("2025-03-20T12:00:00Z")
    }
  ];
  db.users.insertMany(usuarios);

  // Configuración inicial
  const config = [
    {
      clave: "AFORO_DEFAULT",
      valor: 30,
      descripcion: "Aforo máximo por defecto para nuevos horarios",
      ultima_actualizacion: new Date(),
      actualizado_por: adminId
    },
    {
      clave: "BLOQUES_HORARIOS",
      valor: ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00"],
      descripcion: "Horarios de inicio de bloques disponibles",
      ultima_actualizacion: new Date(),
      actualizado_por: adminId
    },
    {
      clave: "MAX_RESERVAS_ACTIVAS",
      valor: 2,
      descripcion: "Máximo de reservas activas por usuario",
      ultima_actualizacion: new Date(),
      actualizado_por: adminId
    },
    {
      clave: "HORAS_CANCELLATION_WINDOW",
      valor: 2,
      descripcion: "Horas antes del horario para permitir cancelación",
      ultima_actualizacion: new Date(),
      actualizado_por: adminId
    }
  ];
  db.configuration.insertMany(config);

  print("Datos iniciales insertados exitosamente.");
}

// ============================================
// VERIFICACIÓN FINAL
// ============================================

print("\n========================================");
print("RESUMEN DE LA BASE DE DATOS");
print("========================================");
print(`Base de datos: gym_reservas_universitario`);
print(`Colecciones creadas:`);
print(`  - users: ${db.users.countDocuments()} documentos`);
print(`  - schedules: ${db.schedules.countDocuments()} documentos`);
print(`  - reservations: ${db.reservations.countDocuments()} documentos`);
print(`  - audit_log: ${db.audit_log.countDocuments()} documentos`);
print(`  - configuration: ${db.configuration.countDocuments()} documentos`);
print("\n========================================");
print("INICIALIZACIÓN COMPLETADA");
print("========================================");
