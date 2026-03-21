// ============================================
// VALIDACIONES DE ESQUEMA (Schema Validation)
// ============================================
// MongoDB permite validar documentos al insertar/actualizar
// Estas validaciones son de nivel de base de datos

use gym_reservas_universitario;

// ============================================
// VALIDACIÓN: users
// ============================================

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

// ============================================
// VALIDACIÓN: schedules
// ============================================

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

// ============================================
// VALIDACIÓN: reservations
// ============================================

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
          description: "Usuario que creó la reserva (puede ser admin)"
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

// ============================================
// VALIDACIÓN: audit_log
// ============================================

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

// ============================================
// VALIDACIÓN: configuration
// ============================================

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
// EJEMPLOS DE USO DE LAS VALIDACIONES
// ============================================

/*
// Esto FALLARÁ: correo no tiene dominio .edu
db.users.insertOne({
  nombre: "Test User",
  correo_institucional: "test@gmail.com",  // ERROR
  rol: "ESTUDIANTE",
  estado: "ACTIVO",
  fecha_creacion: new Date()
});

// Esto FALLARÁ: hora_inicio no es un bloque válido
db.schedules.insertOne({
  fecha: new Date("2025-03-24"),
  hora_inicio: "07:00",  // ERROR - debe ser 06, 08, 10, 12, 14 o 16
  hora_fin: "09:00",
  aforo_maximo: 30,
  cupos_disponibles: 30,
  estado: "DISPONIBLE",
  fecha_creacion: new Date()
});

// Esto FALLARÁ: estado no válido
db.reservations.insertOne({
  usuario_id: ObjectId(),
  horario_id: ObjectId(),
  fecha_reserva: new Date("2025-03-24"),
  hora_inicio: "06:00",
  hora_fin: "08:00",
  estado: "PENDIENTE",  // ERROR - debe ser ACTIVA, CANCELADA, COMPLETADA o NO_SHOW
  creada_por: ObjectId(),
  fecha_creacion: new Date()
});
*/
