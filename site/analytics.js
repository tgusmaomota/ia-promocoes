(() => {
const endpoint = String(document.body?.dataset.analyticsUrl || "").trim();
const valido = valor => { try { return new URL(valor).protocol === "https:"; } catch (_) { return false; } };
function enviar(dados) {
  if (!valido(endpoint)) return;
  const evento = JSON.stringify({
    oferta_id: String(dados.item_id || "").trim(), item_id: String(dados.item_id || "").trim(),
    titulo: String(dados.titulo || "").trim(), categoria: String(dados.categoria || "ofertas").trim() || "ofertas",
    origem: "site_publico", pagina_origem: window.location.pathname || "/", tipo_evento: dados.tipo_evento || "ver_oferta"
  });
  const blob = new Blob([evento], { type: "application/json" });
  if (navigator.sendBeacon && navigator.sendBeacon(endpoint, blob)) return;
  fetch(endpoint, { method: "POST", body: evento, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(() => {});
}
window.PromoggAnalytics = { enviar };
document.addEventListener("click", evento => {
  const alvo = evento.target.closest("[data-analytics-click]");
  if (!alvo) return;
  enviar({ item_id: alvo.dataset.itemId, titulo: alvo.dataset.titulo, categoria: alvo.dataset.categoria, tipo_evento: alvo.dataset.analyticsClick });
});
})();
