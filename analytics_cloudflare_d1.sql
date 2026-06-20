CREATE TABLE IF NOT EXISTS cliques (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL,
  titulo TEXT NOT NULL,
  categoria TEXT NOT NULL,
  origem TEXT NOT NULL,
  pagina_origem TEXT NOT NULL,
  tipo_evento TEXT NOT NULL,
  criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cliques_item ON cliques(item_id);
CREATE INDEX IF NOT EXISTS idx_cliques_data ON cliques(criado_em);
CREATE INDEX IF NOT EXISTS idx_cliques_categoria ON cliques(categoria);
