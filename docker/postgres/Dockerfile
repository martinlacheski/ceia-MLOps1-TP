FROM postgres:16-alpine

COPY init-multiple-databases.sh /docker-entrypoint-initdb.d/init-multiple-databases.sh
RUN chmod 755 /docker-entrypoint-initdb.d/init-multiple-databases.sh
