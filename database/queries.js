// ============================================
// QUERIES Y OPERACIONES PARA REGLAS DE NEGOCIO
// ============================================

use gym_reservas_universitario;

// ============================================
// REGLA 1: Verificar máximo 2 reservas activas
// ============================================
// Un usuario puede tener máximo 2 reservas activas:
// - una para el día actual
// - una para el día siguiente
// Caso especial: los viernes se permite reservar para el lunes

// Query: Contar reservas activas de un usuario
function contarReservasActivas(usuarioId, hoy, manana) {
  return db.reservations.countDocuments({
    usuario_id: usuarioId,
    estado: "ACTIVA",
    fecha_reserva: {
      $gte: hoy,
      $lte: manana
    }
  });
}

// Query: Verificar si usuario puede reservar (considerando caso viernes-lunes)
function puedeReservar(usuarioId, fechaDeseada) {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);

  const diaSemanaHoy = hoy.getDay(); // 0=Domingo, 1=Lunes, ..., 6=Sábado, 5=Viernes
  const fechaDeseadaNormalizada = new Date(fechaDeseada);
  fechaDeseadaNormalizada.setHours(0, 0, 0, 0);

  // Calcular fecha máxima permitida
  let fechaMaxima = new Date(hoy);

  if (diaSemanaHoy === 5) { // Viernes
    // Permitir hasta el lunes siguiente
    fechaMaxima.setDate(hoy.getDate() + 3);
  } else {
    // Normal: permitir hasta mañana
    fechaMaxima.setDate(hoy.getDate() + 1);
  }

  // Verificar que la fecha deseada está en el rango permitido
  if (fechaDeseadaNormalizada < hoy || fechaDeseadaNormalizada > fechaMaxima) {
    return {
      puede: false,
      razon: "Solo puede reservar para hoy y mañana (o lunes si es viernes)"
    };
  }

  // Contar reservas activas en el rango permitido
  const reservasActivas = db.reservations.countDocuments({
    usuario_id: usuarioId,
    estado: "ACTIVA",
    fecha_reserva: { $gte: hoy, $lte: fechaMaxima }
  });

  // Verificar que no tenga reserva activa para la misma fecha
  const reservaMismaFecha = db.reservations.findOne({
    usuario_id: usuarioId,
    estado: "ACTIVA",
    fecha_reserva: fechaDeseadaNormalizada
  });

  if (reservaMismaFecha) {
    return {
      puede: false,
      razon: "Ya tiene una reserva activa para esta fecha"
    };
  }

  // Verificar límite de reservas
  const MAX_RESERVAS = 2;
  if (reservasActivas >= MAX_RESERVAS) {
    return {
      puede: false,
      razon: `Ya tiene ${MAX_RESERVAS} reservas activas (máximo permitido)`
    };
  }

  return { puede: true };
}

// ============================================
// REGLA 2: Verificar disponibilidad de cupos
// ============================================

// Query: Verificar si hay cupos disponibles
function hayCuposDisponibles(horarioId) {
  const horario = db.schedules.findOne(
    { _id: horarioId },
    { cupos_disponibles: 1, estado: 1, aforo_maximo: 1 }
  );

  if (!horario) {
    return { disponible: false, razon: "Horario no existe" };
  }

  if (horario.estado === "LLENO") {
    return { disponible: false, razon: "Horario está lleno" };
  }

  if (horario.estado === "CANCELADO") {
    return { disponible: false, razon: "Horario fue cancelado" };
  }

  if (horario.cupos_disponibles <= 0) {
    return { disponible: false, razon: "No hay cupos disponibles" };
  }

  return {
    disponible: true,
    cupos: horario.cupos_disponibles
  };
}

// ============================================
// REGLA 3: Verificar gimnasio opera lunes-viernes
// ============================================

function esDiaOperativo(fecha) {
  const fechaObj = new Date(fecha);
  const diaSemana = fechaObj.getDay(); // 0=Domingo, 6=Sábado

  // 1=Lunes, 2=Martes, 3=Miércoles, 4=Jueves, 5=Viernes
  if (diaSemana >= 1 && diaSemana <= 5) {
    return { operativo: true };
  }

  return {
    operativo: false,
    razon: "El gimnasio solo opera de lunes a viernes"
  };
}

// Query: Obtener horarios disponibles para una fecha
function getHorariosDisponibles(fecha) {
  // Primero verificar si es día operativo
  const check = esDiaOperativo(fecha);
  if (!check.operativo) {
    return [];
  }

  const fechaNormalizada = new Date(fecha);
  fechaNormalizada.setHours(0, 0, 0, 0);

  return db.schedules.find({
    fecha: fechaNormalizada,
    estado: "DISPONIBLE",
    cupos_disponibles: { $gt: 0 }
  }).sort({ hora_inicio: 1 }).toArray();
}

// ============================================
// REGLA 4: Crear reserva con actualización atómica
// ============================================

// Transaction: Crear reserva y decrementar cupos atomically
function crearReserva(datosReserva) {
  const session = db.getMongo().startSession();

  try {
    session.startTransaction({
      readConcern: { level: "snapshot" },
      writeConcern: { w: "majority" }
    });

    const { usuario_id, horario_id, fecha_reserva, hora_inicio, hora_fin, creada_por } = datosReserva;

    // 1. Verificar cupos disponibles (con lock implícito por la transacción)
    const horario = session.getDatabase("gym_reservas_universitario")
      .schedules.findOne({ _id: horario_id }, { session });

    if (!horario || horario.cupos_disponibles <= 0) {
      throw new Error("No hay cupos disponibles");
    }

    // 2. Verificar que usuario no tenga reserva activa para este horario
    const reservaExistente = session.getDatabase("gym_reservas_universitario")
      .reservations.findOne({
        usuario_id: usuario_id,
        horario_id: horario_id,
        estado: "ACTIVA"
      }, { session });

    if (reservaExistente) {
      throw new Error("Ya tiene una reserva activa para este horario");
    }

    // 3. Crear la reserva
    const fechaHoraActual = new Date();
    const resultadoReserva = session.getDatabase("gym_reservas_universitario")
      .reservations.insertOne({
        usuario_id: usuario_id,
        horario_id: horario_id,
        fecha_reserva: new Date(fecha_reserva),
        hora_inicio: hora_inicio,
        hora_fin: hora_fin,
        estado: "ACTIVA",
        creada_por: creada_por,
        fecha_creacion: fechaHoraActual
      }, { session });

    // 4. Decrementar cupos disponibles
    const nuevoCupos = horario.cupos_disponibles - 1;
    const nuevoEstado = nuevoCupos === 0 ? "LLENO" : "DISPONIBLE";

    session.getDatabase("gym_reservas_universitario")
      .schedules.updateOne(
        { _id: horario_id },
        {
          $set: {
            cupos_disponibles: nuevoCupos,
            estado: nuevoEstado,
            ultima_actualizacion: fechaHoraActual
          }
        },
        { session }
      );

    // 5. Registrar en audit_log
    session.getDatabase("gym_reservas_universitario")
      .audit_log.insertOne({
        tipo_operacion: "RESERVA_CREADA",
        coleccion_afectada: "reservations",
        documento_id: resultadoReserva.insertedId,
        usuario_ejecutor: creada_por,
        datos_nuevos: {
          usuario_id: usuario_id,
          horario_id: horario_id,
          estado: "ACTIVA"
        },
        timestamp: fechaHoraActual
      }, { session });

    session.commitTransaction();

    return {
      exito: true,
      reserva_id: resultadoReserva.insertedId,
      cupos_restantes: nuevoCupos
    };

  } catch (error) {
    session.abortTransaction();
    return {
      exito: false,
      error: error.message
    };
  } finally {
    session.endSession();
  }
}

// ============================================
// REGLA 5: Cancelar reserva y liberar cupo
// ============================================

function cancelarReserva(reservaId, usuarioId, motivo = null) {
  const session = db.getMongo().startSession();

  try {
    session.startTransaction({
      readConcern: { level: "snapshot" },
      writeConcern: { w: "majority" }
    });

    const dbSession = session.getDatabase("gym_reservas_universitario");
    const fechaHoraActual = new Date();

    // 1. Obtener la reserva
    const reserva = dbSession.reservations.findOne(
      { _id: reservaId },
      { session }
    );

    if (!reserva) {
      throw new Error("Reserva no encontrada");
    }

    if (reserva.estado !== "ACTIVA") {
      throw new Error("La reserva no está activa");
    }

    // Opcional: Verificar que el usuario que cancela sea el dueño o admin
    // (lógica omitida, se maneja en el backend)

    // 2. Actualizar estado de la reserva
    const datosAnteriores = {
      estado: reserva.estado,
      // Agregar más campos si es necesario
    };

    dbSession.reservations.updateOne(
      { _id: reservaId },
      {
        $set: {
          estado: "CANCELADA",
          fecha_cancelacion: fechaHoraActual,
          motivo_cancelacion: motivo
        }
      },
      { session }
    );

    // 3. Incrementar cupos disponibles
    const horario = dbSession.schedules.findOne(
      { _id: reserva.horario_id },
      { session }
    );

    if (horario) {
      const nuevoCupos = horario.cupos_disponibles + 1;
      const nuevoEstado = horario.estado === "LLENO" ? "DISPONIBLE" : horario.estado;

      dbSession.schedules.updateOne(
        { _id: reserva.horario_id },
        {
          $set: {
            cupos_disponibles: nuevoCupos,
            estado: nuevoEstado,
            ultima_actualizacion: fechaHoraActual
          }
        },
        { session }
      );
    }

    // 4. Registrar en audit_log
    dbSession.audit_log.insertOne({
      tipo_operacion: "RESERVA_CANCELADA",
      coleccion_afectada: "reservations",
      documento_id: reservaId,
      usuario_ejecutor: usuarioId,
      datos_anteriores: datosAnteriores,
      datos_nuevos: { estado: "CANCELADA" },
      timestamp: fechaHoraActual
    }, { session });

    session.commitTransaction();

    return {
      exito: true,
      mensaje: "Reserva cancelada exitosamente"
    };

  } catch (error) {
    session.abortTransaction();
    return {
      exito: false,
      error: error.message
    };
  } finally {
    session.endSession();
  }
}

// ============================================
// QUERIES ADICIONALES ÚTILES
// ============================================

// Query: Obtener reservas de un usuario con detalles del horario
function getReservasUsuario(usuarioId, estado = null) {
  const matchStage = { usuario_id: usuarioId };
  if (estado) {
    matchStage.estado = estado;
  }

  return db.reservations.aggregate([
    { $match: matchStage },
    {
      $lookup: {
        from: "schedules",
        localField: "horario_id",
        foreignField: "_id",
        as: "horario"
      }
    },
    { $unwind: "$horario" },
    {
      $project: {
        _id: 1,
        fecha_reserva: 1,
        hora_inicio: 1,
        hora_fin: 1,
        estado: 1,
        fecha_creacion: 1,
        "horario.aforo_maximo": 1,
        "horario.estado": 1
      }
    },
    { $sort: { fecha_reserva: 1, hora_inicio: 1 } }
  ]).toArray();
}

// Query: Estadísticas de ocupación por fecha
function getEstadisticaOcupacion(fechaInicio, fechaFin) {
  return db.schedules.aggregate([
    {
      $match: {
        fecha: {
          $gte: new Date(fechaInicio),
          $lte: new Date(fechaFin)
        }
      }
    },
    {
      $group: {
        _id: "$fecha",
        total_horarios: { $sum: 1 },
        total_cupos: { $sum: "$aforo_maximo" },
        cupos_disponibles: { $sum: "$cupos_disponibles" },
        horarios_llenos: {
          $sum: { $cond: [{ $eq: ["$estado", "LLENO"] }, 1, 0] }
        }
      }
    },
    {
      $project: {
        fecha: "$_id",
        total_horarios: 1,
        total_cupos: 1,
        cupos_ocupados: { $subtract: ["$total_cupos", "$cupos_disponibles"] },
        porcentaje_ocupacion: {
          $multiply: [
            { $divide: [
              { $subtract: ["$total_cupos", "$cupos_disponibles"] },
              "$total_cupos"
            ]},
            100
          ]
        },
        horarios_llenos: 1
      }
    },
    { $sort: { fecha: 1 } }
  ]).toArray();
}

// Query: Generar horarios para una semana (script de administrador)
function generarHorariosSemana(fechaInicioSemana, aforoDefault = 30) {
  const bloquesHorarios = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00"];
  const horariosGenerados = [];

  const fecha = new Date(fechaInicioSemana);

  // Ajustar al lunes si no es lunes
  const diaSemana = fecha.getDay();
  if (diaSemana !== 1) {
    const diasHastaLunes = (diaSemana === 0) ? 1 : (8 - diaSemana);
    fecha.setDate(fecha.getDate() + diasHastaLunes);
  }

  // Generar 5 días (lunes a viernes)
  for (let dia = 0; dia < 5; dia++) {
    const fechaActual = new Date(fecha);
    fechaActual.setDate(fecha.getDate() + dia);
    fechaActual.setHours(0, 0, 0, 0);

    for (const horaInicio of bloquesHorarios) {
      const [horas] = horaInicio.split(":");
      const horaFin = `${parseInt(horas) + 2}:00`;

      try {
        db.schedules.insertOne({
          fecha: fechaActual,
          hora_inicio: horaInicio,
          hora_fin: horaFin,
          aforo_maximo: aforoDefault,
          cupos_disponibles: aforoDefault,
          estado: "DISPONIBLE",
          entrenador_id: null,
          notas: null,
          fecha_creacion: new Date(),
          ultima_actualizacion: new Date()
        });

        horariosGenerados.push({
          fecha: fechaActual.toISOString().split("T")[0],
          hora_inicio: horaInicio,
          hora_fin: horaFin
        });
      } catch (e) {
        // Horario duplicado, ignorar
        print(`Horario duplicado ignorado: ${fechaActual.toDateString()} ${horaInicio}`);
      }
    }
  }

  return horariosGenerados;
}

// Exportar funciones para uso
print("Funciones de queries cargadas:");
print("  - puedeReservar(usuarioId, fechaDeseada)");
print("  - hayCuposDisponibles(horarioId)");
print("  - esDiaOperativo(fecha)");
print("  - getHorariosDisponibles(fecha)");
print("  - crearReserva(datosReserva)");
print("  - cancelarReserva(reservaId, usuarioId, motivo)");
print("  - getReservasUsuario(usuarioId, estado)");
print("  - getEstadisticaOcupacion(fechaInicio, fechaFin)");
print("  - generarHorariosSemana(fechaInicioSemana, aforoDefault)");
