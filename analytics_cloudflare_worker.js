// Opcional: endpoint público para GitHub Pages. Requer binding D1 ANALYTICS_DB.
const ORIGIN = "https://promogg.com.br";
const TIPOS = new Set(["card_oferta", "ver_oferta", "compra_produto"]);

function cors(origin) {
  return origin === ORIGIN ? { "Access-Control-Allow-Origin": ORIGIN, "Vary": "Origin" } : {};
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: origin === ORIGIN ? 204 : 403, headers: { ...cors(origin), "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type" } });
    }
    if (request.method === "GET" && url.pathname === "/health") return Response.json({ ok: true, personal_data: false });
    if (request.method !== "POST" || url.pathname !== "/api/cliques" || origin !== ORIGIN) return new Response("Not found", { status: 404 });
    try {
      const body = await request.json();
      const itemId = String(body.item_id || body.oferta_id || "").trim().toUpperCase();
      const titulo = String(body.titulo || "").trim().slice(0, 300);
      const categoria = String(body.categoria || "ofertas").trim().slice(0, 120);
      const tipo = String(body.tipo_evento || "").trim();
      const pagina = String(body.pagina_origem || "/").trim().slice(0, 300);
      if (!/^MLB\d{5,}$/.test(itemId) || !titulo || !TIPOS.has(tipo) || !pagina.startsWith("/")) throw new Error("payload inválido");
      const recentes = await env.ANALYTICS_DB.prepare("SELECT COUNT(*) AS total FROM cliques WHERE item_id = ? AND tipo_evento = ? AND criado_em >= datetime('now', '-1 minute')").bind(itemId, tipo).first();
      if (Number(recentes?.total || 0) >= 120) return Response.json({ ok: false }, { status: 429, headers: cors(origin) });
      await env.ANALYTICS_DB.prepare("INSERT INTO cliques (item_id, titulo, categoria, origem, pagina_origem, tipo_evento, criado_em) VALUES (?, ?, ?, 'site_publico', ?, ?, datetime('now'))").bind(itemId, titulo, categoria || "ofertas", pagina, tipo).run();
      return Response.json({ ok: true }, { status: 202, headers: cors(origin) });
    } catch (_) {
      return Response.json({ ok: false }, { status: 400, headers: cors(origin) });
    }
  },
};
