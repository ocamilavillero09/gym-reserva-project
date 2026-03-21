FROM mongo:6

# Copiar el script de inicialización
# MongoDB ejecuta automáticamente scripts .js de /docker-entrypoint-initdb.d/
COPY init.mongodb.js /docker-entrypoint-initdb.d/

# Asegurar permisos de ejecución
RUN chmod +x /docker-entrypoint-initdb.d/init.mongodb.js

# Exponer el puerto de MongoDB
EXPOSE 27017
