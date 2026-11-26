-- Seed de zonas de cobertura (ADR-0003). La zona 1 ya se crea en la migracion 0003.
-- Ejecutar de forma idempotente:
--   mysql -u <user> -p <db> < infra/seed-zonas.sql
INSERT INTO zonas (id, nombre, distrito, tiempo_estimado_min, activo, creado_en)
VALUES
  (1, 'Botica Centro', 'Centro', 30, 1, CURRENT_TIMESTAMP),
  (2, 'Botica Norte', 'San Isidro', 45, 1, CURRENT_TIMESTAMP),
  (3, 'Botica Sur', 'Miraflores', 40, 1, CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE
  nombre = VALUES(nombre),
  distrito = VALUES(distrito),
  tiempo_estimado_min = VALUES(tiempo_estimado_min),
  activo = 1;
