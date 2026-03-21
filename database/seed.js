// ============================================
// SEED DATA - Datos de Ejemplo
// ============================================
// Ejecutar en MongoDB shell para poblar la base de datos

use gym_reservas_universitario;

// Limpiar colecciones (opcional - quitar si no se quiere borrar datos existentes)
db.users.deleteMany({});
db.schedules.deleteMany({});
db.reservations.deleteMany({});
db.audit_log.deleteMany({});
db.configuration.deleteMany({});

print("Insertando configuración...");

// ============================================
// CONFIGURACIÓN
// ============================================
const adminId = ObjectId();

db.configuration.insertMany([
  {
    _id: ObjectId(),
    clave: "AFORO_DEFAULT",
    valor: 30,
    descripcion: "Aforo máximo por defecto para nuevos horarios",
    ultima_actualizacion: new Date(),
    actualizado_por: adminId
  },
  {
    _id: ObjectId(),
    clave: "BLOQUES_HORARIOS",
    valor: ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00"],
    descripcion: "Horarios de inicio de bloques disponibles",
    ultima_actualizacion: new Date(),
    actualizado_por: adminId
  },
  {
    _id: ObjectId(),
    clave: "MAX_RESERVAS_ACTIVAS",
    valor: 2,
    descripcion: "Máximo de reservas activas por usuario",
    ultima_actualizacion: new Date(),
    actualizado_por: adminId
  },
  {
    _id: ObjectId(),
    clave: "HORAS_CANCELLATION_WINDOW",
    valor: 2,
    descripcion: "Horas antes del horario para permitir cancelación",
    ultima_actualizacion: new Date(),
    actualizado_por: adminId
  }
]);

print("Insertando usuarios...");

// ============================================
// USUARIOS
// ============================================
const usuarios = [
  // Estudiantes
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
    nombre: "María Fernanda García",
    correo_institucional: "maria.garcia@universidad.edu",
    rol: "ESTUDIANTE",
    estado: "PENALIZADO",
    fecha_creacion: new Date("2025-01-20T14:00:00Z"),
    ultimo_acceso: new Date("2025-03-18T07:00:00Z"),
    penalizacion_hasta: new Date("2025-03-25T23:59:59Z")
  },
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9c004"),
    nombre: "Luis Alberto Torres",
    correo_institucional: "luis.torres@universidad.edu",
    rol: "ESTUDIANTE",
    estado: "ACTIVO",
    fecha_creacion: new Date("2025-02-01T11:00:00Z")
  },
  // Entrenadores
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9c005"),
    nombre: "Pedro Sánchez Vega",
    correo_institucional: "pedro.sanchez@universidad.edu",
    rol: "ENTRENADOR",
    estado: "ACTIVO",
    fecha_creacion: new Date("2024-08-01T08:00:00Z"),
    ultimo_acceso: new Date("2025-03-20T06:00:00Z")
  },
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9c006"),
    nombre: "Diana Patricia Castro",
    correo_institucional: "diana.castro@universidad.edu",
    rol: "ENTRENADOR",
    estado: "ACTIVO",
    fecha_creacion: new Date("2024-09-15T10:00:00Z"),
    ultimo_acceso: new Date("2025-03-20T09:00:00Z")
  },
  // Admin
  {
    _id: adminId,
    nombre: "Roberto Administrator",
    correo_institucional: "admin@universidad.edu",
    rol: "ADMIN",
    estado: "ACTIVO",
    fecha_creacion: new Date("2024-01-01T00:00:00Z"),
    ultimo_acceso: new Date("2025-03-20T12:00:00Z")
  }
];

db.users.insertMany(usuarios);

print("Insertando horarios...");

// ============================================
// HORARIOS (Schedules)
// ============================================
// Generar horarios para la semana del 24-28 de marzo 2025 (lunes-viernes)

function crearHorario(fechaStr, horaInicio, horaFin, cuposDisp, entrenadorId = null, notas = null) {
  return {
    _id: ObjectId(),
    fecha: new Date(fechaStr),
    hora_inicio: horaInicio,
    hora_fin: horaFin,
    aforo_maximo: 30,
    cupos_disponibles: cuposDisp,
    estado: cuposDisp === 0 ? "LLENO" : "DISPONIBLE",
    entrenador_id: entrenadorId,
    notas: notas,
    fecha_creacion: new Date("2025-03-01T00:00:00Z"),
    ultima_actualizacion: new Date()
  };
}

const entrenador1 = ObjectId("65f8a2b3c4d5e6f7a8b9c005");
const entrenador2 = ObjectId("65f8a2b3c4d5e6f7a8b9c006");

const horarios = [
  // Lunes 24 de marzo
  crearHorario("2025-03-24", "06:00", "08:00", 5, entrenador1, "CrossFit básico"),
  crearHorario("2025-03-24", "08:00", "10:00", 12, null, null),
  crearHorario("2025-03-24", "10:00", "12:00", 0, entrenador2, "Clase llena"),
  crearHorario("2025-03-24", "12:00", "14:00", 25, null, null),
  crearHorario("2025-03-24", "14:00", "16:00", 18, entrenador1, "Yoga"),
  crearHorario("2025-03-24", "16:00", "18:00", 30, null, null),

  // Martes 25 de marzo
  crearHorario("2025-03-25", "06:00", "08:00", 20, null, null),
  crearHorario("2025-03-25", "08:00", "10:00", 15, entrenador2, "Spinning"),
  crearHorario("2025-03-25", "10:00", "12:00", 28, null, null),
  crearHorario("2025-03-25", "12:00", "14:00", 30, null, null),
  crearHorario("2025-03-25", "14:00", "16:00", 22, entrenador1, "Pilates"),
  crearHorario("2025-03-25", "16:00", "18:00", 8, null, null),

  // Miércoles 26 de marzo
  crearHorario("2025-03-26", "06:00", "08:00", 25, entrenador1, null),
  crearHorario("2025-03-26", "08:00", "10:00", 0, null, "Horario cancelado temporalmente"),
  crearHorario("2025-03-26", "10:00", "12:00", 20, null, null),
  crearHorario("2025-03-26", "12:00", "14:00", 15, entrenador2, "Zumba"),
  crearHorario("2025-03-26", "14:00", "16:00", 10, null, null),
  crearHorario("2025-03-26", "16:00", "18:00", 30, entrenador1, null),

  // Jueves 27 de marzo
  crearHorario("2025-03-27", "06:00", "08:00", 30, null, null),
  crearHorario("2025-03-27", "08:00", "10:00", 25, entrenador2, null),
  crearHorario("2025-03-27", "10:00", "12:00", 20, null, null),
  crearHorario("2025-03-27", "12:00", "14:00", 18, entrenador1, "Funcional"),
  crearHorario("2025-03-27", "14:00", "16:00", 25, null, null),
  crearHorario("2025-03-27", "16:00", "18:00", 12, null, null),

  // Viernes 28 de marzo
  crearHorario("2025-03-28", "06:00", "08:00", 28, entrenador1, null),
  crearHorario("2025-03-28", "08:00", "10:00", 30, null, null),
  crearHorario("2025-03-28", "10:00", "12:00", 25, entrenador2, "Baile"),
  crearHorario("2025-03-28", "12:00", "14:00", 20, null, null),
  crearHorario("2025-03-28", "14:00", "16:00", 15, entrenador1, "Boxeo"),
  crearHorario("2025-03-28", "16:00", "18:00", 30, null, null),

  // Lunes siguiente (31 de marzo) - para caso especial viernes-lunes
  crearHorario("2025-03-31", "06:00", "08:00", 30, entrenador1, null),
  crearHorario("2025-03-31", "08:00", "10:00", 30, null, null),
  crearHorario("2025-03-31", "10:00", "12:00", 30, entrenador2, null)
];

const horariosInsertados = db.schedules.insertMany(horarios);
const idsHorarios = Object.values(horariosInsertados.insertedIds);

print("Insertando reservas...");

// ============================================
// RESERVAS
// ============================================
const usuarioAna = ObjectId("65f8a2b3c4d5e6f7a8b9c001");
const usuarioCarlos = ObjectId("65f8a2b3c4d5e6f7a8b9c002");
const usuarioMaria = ObjectId("65f8a2b3c4d5e6f7a8b9c003");
const usuarioLuis = ObjectId("65f8a2b3c4d5e6f7a8b9c004");

const reservas = [
  // Ana tiene 2 reservas activas (una hoy, una mañana) - OK
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9d001"),
    usuario_id: usuarioAna,
    horario_id: idsHorarios[0],  // Lunes 24 mar 06:00
    fecha_reserva: new Date("2025-03-24"),
    hora_inicio: "06:00",
    hora_fin: "08:00",
    estado: "ACTIVA",
    creada_por: usuarioAna,
    fecha_creacion: new Date("2025-03-20T10:00:00Z")
  },
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9d002"),
    usuario_id: usuarioAna,
    horario_id: idsHorarios[6],  // Martes 25 mar 06:00
    fecha_reserva: new Date("2025-03-25"),
    hora_inicio: "06:00",
    hora_fin: "08:00",
    estado: "ACTIVA",
    creada_por: usuarioAna,
    fecha_creacion: new Date("2025-03-20T10:05:00Z")
  },

  // Carlos tiene 1 reserva activa
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9d003"),
    usuario_id: usuarioCarlos,
    horario_id: idsHorarios[1],  // Lunes 24 mar 08:00
    fecha_reserva: new Date("2025-03-24"),
    hora_inicio: "08:00",
    hora_fin: "10:00",
    estado: "ACTIVA",
    creada_por: usuarioCarlos,
    fecha_creacion: new Date("2025-03-20T14:00:00Z")
  },

  // María tiene 1 reserva cancelada
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9d004"),
    usuario_id: usuarioMaria,
    horario_id: idsHorarios[12], // Miércoles 26 mar 06:00
    fecha_reserva: new Date("2025-03-26"),
    hora_inicio: "06:00",
    hora_fin: "08:00",
    estado: "CANCELADA",
    creada_por: usuarioMaria,
    fecha_creacion: new Date("2025-03-18T09:00:00Z"),
    fecha_cancelacion: new Date("2025-03-19T16:00:00Z"),
    motivo_cancelacion: "Emergencia personal"
  },

  // Luis tiene 1 reserva completada (asistió)
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9d005"),
    usuario_id: usuarioLuis,
    horario_id: idsHorarios[2],  // Lunes 24 mar 10:00
    fecha_reserva: new Date("2025-03-24"),
    hora_inicio: "10:00",
    hora_fin: "12:00",
    estado: "COMPLETADA",
    creada_por: usuarioLuis,
    fecha_creacion: new Date("2025-03-17T11:00:00Z"),
    fecha_completacion: new Date("2025-03-24T12:00:00Z")
  },

  // Más reservas para llenar horarios
  {
    _id: ObjectId("65f8a2b3c4d5e6f7a8b9d006"),
    usuario_id: usuarioCarlos,
    horario_id: idsHorarios[6],  // Martes 25 mar 06:00
    fecha_reserva: new Date("2025-03-25"),
    hora_inicio: "06:00",
    hora_fin: "08:00",
    estado: "ACTIVA",
    creada_por: usuarioCarlos,
    fecha_creacion: new Date("2025-03-20T15:00:00Z")
  }
];

db.reservations.insertMany(reservas);

print("Insertando logs de auditoría...");

// ============================================
// AUDIT LOG
// ============================================
db.audit_log.insertMany([
  {
    _id: ObjectId(),
    tipo_operacion: "RESERVA_CREADA",
    coleccion_afectada: "reservations",
    documento_id: ObjectId("65f8a2b3c4d5e6f7a8b9d001"),
    usuario_ejecutor: usuarioAna,
    datos_nuevos: {
      usuario_id: usuarioAna,
      horario_id: idsHorarios[0],
      estado: "ACTIVA"
    },
    timestamp: new Date("2025-03-20T10:00:00Z")
  },
  {
    _id: ObjectId(),
    tipo_operacion: "RESERVA_CREADA",
    coleccion_afectada: "reservations",
    documento_id: ObjectId("65f8a2b3c4d5e6f7a8b9d002"),
    usuario_ejecutor: usuarioAna,
    datos_nuevos: {
      usuario_id: usuarioAna,
      horario_id: idsHorarios[6],
      estado: "ACTIVA"
    },
    timestamp: new Date("2025-03-20T10:05:00Z")
  },
  {
    _id: ObjectId(),
    tipo_operacion: "RESERVA_CANCELADA",
    coleccion_afectada: "reservations",
    documento_id: ObjectId("65f8a2b3c4d5e6f7a8b9d004"),
    usuario_ejecutor: usuarioMaria,
    datos_anteriores: { estado: "ACTIVA" },
    datos_nuevos: { estado: "CANCELADA" },
    timestamp: new Date("2025-03-19T16:00:00Z")
  },
  {
    _id: ObjectId(),
    tipo_operacion: "CUPO_LIBERADO",
    coleccion_afectada: "schedules",
    documento_id: idsHorarios[12],
    usuario_ejecutor: usuarioMaria,
    datos_anteriores: { cupos_disponibles: 24 },
    datos_nuevos: { cupos_disponibles: 25 },
    timestamp: new Date("2025-03-19T16:00:00Z")
  }
]);

// ============================================
// RESUMEN
// ============================================
print("\n=== SEED DATA INSERTADO ===");
print(`Usuarios: ${db.users.countDocuments()}`);
print(`  - Estudiantes: ${db.users.countDocuments({ rol: "ESTUDIANTE" })}`);
print(`  - Entrenadores: ${db.users.countDocuments({ rol: "ENTRENADOR" })}`);
print(`  - Admins: ${db.users.countDocuments({ rol: "ADMIN" })}`);
print(`\nHorarios: ${db.schedules.countDocuments()}`);
print(`  - Disponibles: ${db.schedules.countDocuments({ estado: "DISPONIBLE" })}`);
print(`  - Llenos: ${db.schedules.countDocuments({ estado: "LLENO" })}`);
print(`\nReservas: ${db.reservations.countDocuments()}`);
print(`  - Activas: ${db.reservations.countDocuments({ estado: "ACTIVA" })}`);
print(`  - Canceladas: ${db.reservations.countDocuments({ estado: "CANCELADA" })}`);
print(`  - Completadas: ${db.reservations.countDocuments({ estado: "COMPLETADA" })}`);
print(`\nConfiguraciones: ${db.configuration.countDocuments()}`);
print("===========================\n");

// ============================================
// EJEMPLOS DE QUERIES CON DATOS
// ============================================
print("\nEjemplos de queries con datos:");

print("\n1. Horarios disponibles para el lunes 24 de marzo:");
const horariosLunes = db.schedules.find(
  { fecha: new Date("2025-03-24"), estado: "DISPONIBLE" },
  { hora_inicio: 1, cupos_disponibles: 1, _id: 0 }
).sort({ hora_inicio: 1 }).toArray();
printjson(horariosLunes);

print("\n2. Reservas activas de Ana López:");
const reservasAna = db.reservations.find(
  { usuario_id: usuarioAna, estado: "ACTIVA" },
  { fecha_reserva: 1, hora_inicio: 1, estado: 1, _id: 0 }
).toArray();
printjson(reservasAna);

print("\n3. Usuarios penalizados:");
const penalizados = db.users.find(
  { estado: "PENALIZADO" },
  { nombre: 1, correo_institucional: 1, penalizacion_hasta: 1, _id: 0 }
).toArray();
printjson(penalizados);

print("\nSeed data completado!");
