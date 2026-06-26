const POR_PAGINA = 20;
const state = { ofertas: [], geradoEm: null, pagina: 1 };

const elements = {
    grid: document.querySelector("#offer-grid"),
    count: document.querySelector("#offer-count"),
    search: document.querySelector("#search"),
    category: document.querySelector("#category"),
    discount: document.querySelector("#discount"),
    record: document.querySelector("#record"),
    sort: document.querySelector("#sort"),
    clear: document.querySelector("#clear-filters"),
    generatedAt: document.querySelector("#generated-at"),
    previous: document.querySelector("#previous-page"),
    next: document.querySelector("#next-page"),
    pageIndicator: document.querySelector("#page-indicator"),
    quickForm: document.querySelector("#quick-assistant-form"),
    quickQuestion: document.querySelector("#quick-question"),
    quickAnswer: document.querySelector("#quick-assistant-answer"),
    analyticsUrl: document.body.dataset.analyticsUrl.trim(),
    telegramLinks: document.querySelectorAll("[data-telegram-link]")
};

function normalizarData(valor) {
    if (!valor) return null;
    const data = new Date(String(valor).replace(" ", "T"));
    return Number.isNaN(data.getTime()) ? null : data;
}

function formatarData(valor) {
    const data = normalizarData(valor);
    return data ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data) : "data indisponível";
}

function formatarPreco(valor, precoFormatado) {
    if (precoFormatado) return precoFormatado;
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor) || 0);
}

function textoSeguro(valor) {
    return String(valor || "").trim();
}

function normalizarTexto(valor) {
    return textoSeguro(valor).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
}

function imagemPublica(url) {
    try {
        const imagem = new URL(textoSeguro(url));
        return imagem.protocol === "https:" || imagem.protocol === "http:" ? imagem.href : "";
    } catch (_) {
        return "";
    }
}

function preencherSelect(select, valores, textoPadrao, contagens = {}) {
    select.replaceChildren(new Option(textoPadrao, ""));
    valores.sort((a, b) => a.localeCompare(b, "pt-BR")).forEach((valor) => {
        const total = Number(contagens[valor]) || 0;
        select.add(new Option(total ? `${valor} (${total})` : valor, valor));
    });
}

function scoreCustoBeneficio(oferta) {
    return (Number(oferta.desconto_percentual) || 0) * 2
        + (Number(oferta.economia_valor) || 0) / 10
        + (oferta.destaque_menor_preco ? 35 : 0)
        + (Number(oferta.variacao_preco) < 0 ? 18 : 0);
}

function contarCategorias(ofertas) {
    return ofertas.reduce((acc, oferta) => {
        const categoria = textoSeguro(oferta.categoria);
        if (categoria) acc[categoria] = (acc[categoria] || 0) + 1;
        return acc;
    }, {});
}

function aplicarFiltrosDaUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("q")) elements.search.value = params.get("q") || "";
    if (params.has("categoria")) elements.category.value = params.get("categoria") || "";
    if (params.has("desconto")) elements.discount.value = params.get("desconto") || "0";
    if (params.has("historico")) elements.record.value = params.get("historico") || "";
    if (params.has("ordem")) elements.sort.value = params.get("ordem") || "recentes";
    const pagina = Number(params.get("pagina") || 1);
    state.pagina = Number.isFinite(pagina) && pagina > 0 ? pagina : 1;
}

function atualizarUrlFiltros() {
    const params = new URLSearchParams();
    if (textoSeguro(elements.search.value)) params.set("q", textoSeguro(elements.search.value));
    if (textoSeguro(elements.category.value)) params.set("categoria", textoSeguro(elements.category.value));
    if (Number(elements.discount?.value || 0) > 0) params.set("desconto", elements.discount.value);
    if (textoSeguro(elements.record?.value)) params.set("historico", elements.record.value);
    if (textoSeguro(elements.sort?.value) && elements.sort.value !== "recentes") params.set("ordem", elements.sort.value);
    if (state.pagina > 1) params.set("pagina", String(state.pagina));
    const query = params.toString();
    history.replaceState(null, "", query ? `${location.pathname}?${query}${location.hash}` : `${location.pathname}${location.hash}`);
}

function ofertasFiltradas() {
    const busca = normalizarTexto(elements.search.value);
    const categoria = elements.category.value;
    const descontoMinimo = Number(elements.discount?.value || 0);
    const filtroHistorico = elements.record?.value || "";
    const ofertas = state.ofertas.filter((oferta) => {
        const titulo = normalizarTexto(oferta.titulo);
        const categoriaOferta = textoSeguro(oferta.categoria);
        const categoriaBusca = normalizarTexto(categoriaOferta);
        const desconto = Number(oferta.desconto_percentual) || 0;
        const variacao = Number(oferta.variacao_preco) || 0;
        return (!busca || titulo.includes(busca) || categoriaBusca.includes(busca))
            && (!categoria || categoriaOferta === categoria)
            && desconto >= descontoMinimo
            && (!filtroHistorico || (filtroHistorico === "record" && oferta.destaque_menor_preco) || (filtroHistorico === "queda" && variacao < 0));
    });
    return ofertas.sort((a, b) => {
        if (elements.sort.value === "menor-preco") return Number(a.preco) - Number(b.preco);
        if (elements.sort.value === "maior-preco") return Number(b.preco) - Number(a.preco);
        if (elements.sort.value === "maior-desconto") return (Number(b.desconto_percentual) || 0) - (Number(a.desconto_percentual) || 0);
        if (elements.sort.value === "maior-economia") return (Number(b.economia_valor) || 0) - (Number(a.economia_valor) || 0);
        return (normalizarData(b.ultima_verificacao || b.data_publicacao)?.getTime() || 0)
            - (normalizarData(a.ultima_verificacao || a.data_publicacao)?.getTime() || 0);
    });
}

function criarMidia(oferta) {
    const midia = document.createElement("div");
    midia.className = "offer-media";
    const url = imagemPublica(oferta.imagem_url);
    if (!url) {
        const fallback = document.createElement("span");
        fallback.className = "image-fallback";
        fallback.textContent = "Promogg";
        midia.append(fallback);
        return midia;
    }
    const imagem = document.createElement("img");
    imagem.src = url;
    imagem.alt = textoSeguro(oferta.titulo) || "Produto em oferta";
    imagem.loading = "lazy";
    imagem.addEventListener("error", () => {
        imagem.remove();
        const fallback = document.createElement("span");
        fallback.className = "image-fallback";
        fallback.textContent = "Imagem indisponível";
        midia.append(fallback);
    }, { once: true });
    midia.append(imagem);
    return midia;
}

function registrarClique(oferta, tipoEvento) {
    if (!window.PromoggAnalytics) return;
    window.PromoggAnalytics.enviar({
        item_id: textoSeguro(oferta.item_id), titulo: textoSeguro(oferta.titulo),
        categoria: textoSeguro(oferta.categoria) || "ofertas", tipo_evento: tipoEvento || "ver_oferta"
    });
}

function criarCard(oferta) {
    const card = document.createElement("article");
    card.className = "offer-card";
    const topo = document.createElement("div");
    topo.className = "card-topline";
    const plataforma = document.createElement("span");
    plataforma.className = "marketplace";
    plataforma.textContent = textoSeguro(oferta.plataforma) || "Mercado Livre";
    const categoria = document.createElement("span");
    categoria.className = "tag";
    categoria.textContent = textoSeguro(oferta.categoria) || "ofertas";
    categoria.title = categoria.textContent;
    topo.append(plataforma, categoria);
    const badges = document.createElement("div");
    badges.className = "badges";
    const descontoBadge = Number(oferta.desconto_percentual) || 0;
    const variacaoBadge = Number(oferta.variacao_preco) || 0;
    if (descontoBadge > 0) {
        const badge = document.createElement("span");
        badge.className = "badge badge-discount";
        badge.textContent = `${descontoBadge.toFixed(0)}% OFF`;
        badges.append(badge);
    }
    if (oferta.destaque_menor_preco || variacaoBadge < 0) {
        const badge = document.createElement("span");
        badge.className = "badge badge-record";
        badge.textContent = oferta.destaque_menor_preco ? "Menor preço" : "Preço caiu";
        badges.append(badge);
    }
    const titulo = document.createElement("h3");
    titulo.textContent = textoSeguro(oferta.titulo) || "Oferta sem título";
    titulo.title = titulo.textContent;
    const label = document.createElement("p");
    label.className = "price-label";
    label.textContent = "Preço atual";
    const preco = document.createElement("p");
    preco.className = "price";
    preco.textContent = formatarPreco(oferta.preco, oferta.preco_formatado);
    const historico = document.createElement("div");
    historico.className = "price-history";
    const menorLabel = document.createElement("span");
    menorLabel.textContent = "Menor preço já visto";
    const menorPreco = document.createElement("strong");
    menorPreco.textContent = formatarPreco(oferta.menor_preco, oferta.menor_preco_formatado);
    const variacao = document.createElement("span");
    const valorVariacao = Number(oferta.variacao_preco) || 0;
    const precoAtual = Number(oferta.preco) || 0;
    const menorHistorico = Number(oferta.menor_preco) || precoAtual;
    const distanciaMenor = precoAtual - menorHistorico;
    variacao.className = valorVariacao < 0 ? "variation-down" : valorVariacao > 0 ? "variation-up" : "variation-stable";
    variacao.textContent = valorVariacao < 0 ? `Caiu ${formatarPreco(Math.abs(valorVariacao))}` : oferta.destaque_menor_preco ? "Menor preço" : distanciaMenor > 0 ? "Acima do menor histórico" : "Preço estável";
    const notaHistorico = document.createElement("span");
    notaHistorico.className = "history-note";
    if (Math.abs(distanciaMenor) < 0.01) {
        notaHistorico.textContent = "Igual ao menor histórico.";
    } else if (distanciaMenor > 0) {
        notaHistorico.textContent = `${formatarPreco(distanciaMenor)} acima do menor histórico.`;
    } else {
        notaHistorico.textContent = "Novo menor preço registrado.";
    }
    historico.append(menorLabel, menorPreco, variacao, notaHistorico);
    const destaque = document.createElement("span");
    destaque.className = "record-badge";
    destaque.textContent = "Menor preço já visto";
    destaque.hidden = !oferta.destaque_menor_preco;
    const link = document.createElement("a");
    link.className = "button button-secondary";
    link.href = textoSeguro(oferta.link);
    link.target = "_blank";
    link.rel = "noopener sponsored";
    link.textContent = "Ver oferta";
    link.addEventListener("click", () => registrarClique(oferta, "ver_oferta"));
    const detalhes = document.createElement("a");
    detalhes.className = "details-link";
    detalhes.href = textoSeguro(oferta.produto_url);
    detalhes.textContent = "Detalhes";
    detalhes.addEventListener("click", () => registrarClique(oferta, "card_oferta"));
    card.append(criarMidia(oferta), topo, badges, titulo, label, preco, historico, destaque, link, detalhes);
    return card;
}

function exibirFeedback(titulo, mensagem) {
    const feedback = document.createElement("section");
    feedback.className = "feedback";
    const heading = document.createElement("h3");
    heading.textContent = titulo;
    const texto = document.createElement("p");
    texto.textContent = mensagem;
    feedback.append(heading, texto);
    elements.grid.replaceChildren(feedback);
}

function rolarParaOfertas() {
    const ofertasSection = document.querySelector("#ofertas") || document.querySelector("[data-ofertas]");
    if (ofertasSection) {
        ofertasSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
    }
}

function renderizar(rolar = false) {
    const ofertas = ofertasFiltradas();
    const totalPaginas = Math.max(1, Math.ceil(ofertas.length / POR_PAGINA));
    state.pagina = Math.min(Math.max(state.pagina, 1), totalPaginas);
    const inicio = (state.pagina - 1) * POR_PAGINA;
    const pagina = ofertas.slice(inicio, inicio + POR_PAGINA);
    elements.count.textContent = `${ofertas.length} ${ofertas.length === 1 ? "oferta encontrada" : "ofertas encontradas"}`;
    elements.pageIndicator.textContent = `Página ${state.pagina} de ${totalPaginas}`;
    elements.previous.disabled = state.pagina === 1;
    elements.next.disabled = state.pagina === totalPaginas;
    atualizarUrlFiltros();
    if (!ofertas.length) {
        exibirFeedback("Nenhuma oferta encontrada", "Ajuste os filtros ou volte mais tarde para ver novas seleções.");
        if (rolar) rolarParaOfertas();
        return;
    }
    elements.grid.replaceChildren(...pagina.map(criarCard));
    if (rolar) rolarParaOfertas();
}

function configurarTelegram() {
    const url = document.body.dataset.telegramUrl.trim();
    if (!/^https:\/\/t\.me\//.test(url)) return;
    elements.telegramLinks.forEach((link) => { link.href = url; link.hidden = false; });
}

function responderAssistente(pergunta) {
    const texto = textoSeguro(pergunta).toLocaleLowerCase("pt-BR");
    if (!state.ofertas.length) return "Ainda não carreguei o catálogo público. Tente novamente em instantes.";
    const money = (o) => formatarPreco(o.preco, o.preco_formatado);
    const link = (o) => `${textoSeguro(o.titulo)} — ${money(o)}`;
    if (texto.includes("menor preço") || texto.includes("mais barato")) {
        const itens = state.ofertas.filter((o) => o.destaque_menor_preco).slice(0, 5);
        return itens.length
            ? `Ofertas no menor preço histórico: ${itens.map(link).join("; ")}.`
            : "Não encontrei ofertas marcadas como menor preço histórico no catálogo atual.";
    }
    if (texto.includes("desconto") || texto.includes("queda")) {
        const itens = [...state.ofertas].sort((a, b) => (Number(b.desconto_percentual) || 0) - (Number(a.desconto_percentual) || 0)).slice(0, 5);
        return `Maiores descontos públicos agora: ${itens.map((o) => `${textoSeguro(o.titulo)} (${(Number(o.desconto_percentual) || 0).toFixed(0)}% OFF)`).join("; ")}.`;
    }
    if (texto.includes("custo") || texto.includes("vale") || texto.includes("pena") || texto.includes("melhor")) {
        const itens = [...state.ofertas].sort((a, b) => scoreCustoBeneficio(b) - scoreCustoBeneficio(a)).slice(0, 5);
        return `Boas candidatas por desconto, economia e histórico: ${itens.map(link).join("; ")}. Compare no Mercado Livre antes de comprar.`;
    }
    if (texto.includes("categoria")) {
        const contagem = {};
        state.ofertas.forEach((o) => { const c = textoSeguro(o.categoria) || "Ofertas"; contagem[c] = (contagem[c] || 0) + 1; });
        const [categoria, total] = Object.entries(contagem).sort((a, b) => b[1] - a[1])[0];
        return `A categoria com mais ofertas agora é ${categoria}, com ${total} oferta(s) públicas.`;
    }
    return "Posso responder sobre menor preço histórico, maiores descontos, categorias e custo-benefício usando apenas os dados públicos carregados nesta página.";
}

function configurarAssistenteRapido() {
    if (!elements.quickForm || !elements.quickQuestion || !elements.quickAnswer) return;
    elements.quickForm.addEventListener("submit", (evento) => {
        evento.preventDefault();
        elements.quickAnswer.textContent = responderAssistente(elements.quickQuestion.value);
    });
    document.querySelectorAll("#quick-assistant-form [data-q]").forEach((botao) => {
        botao.addEventListener("click", () => {
            elements.quickQuestion.value = botao.dataset.q;
            elements.quickAnswer.textContent = responderAssistente(botao.dataset.q);
        });
    });
}

async function carregarOfertas() {
    exibirFeedback("Carregando ofertas", "Buscando as ofertas selecionadas para você.");
    try {
        const resposta = await fetch("ofertas.json", { cache: "no-store" });
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();
        state.ofertas = Array.isArray(dados.ofertas) ? dados.ofertas.filter((oferta) => /^https?:\/\//.test(textoSeguro(oferta.link))) : [];
        state.geradoEm = dados.gerado_em;
        const categorias = [...new Set(state.ofertas.map((oferta) => textoSeguro(oferta.categoria)).filter(Boolean))];
        preencherSelect(elements.category, categorias, "Todas as categorias", contarCategorias(state.ofertas));
        aplicarFiltrosDaUrl();
        elements.generatedAt.textContent = state.geradoEm ? `Lista atualizada em ${formatarData(state.geradoEm)}` : "Lista atualizada";
        renderizar();
    } catch (_) {
        elements.count.textContent = "Ofertas indisponíveis";
        elements.pageIndicator.textContent = "";
        elements.previous.disabled = true;
        elements.next.disabled = true;
        exibirFeedback("Estamos atualizando as ofertas", "Tente novamente em instantes.");
    }
}

function filtrarDaPrimeiraPagina() { state.pagina = 1; renderizar(true); }
elements.search.addEventListener("input", filtrarDaPrimeiraPagina);
[elements.category, elements.discount, elements.record, elements.sort].forEach((campo) => campo?.addEventListener("change", filtrarDaPrimeiraPagina));
elements.clear?.addEventListener("click", () => {
    elements.search.value = "";
    elements.category.value = "";
    elements.discount.value = "0";
    elements.record.value = "";
    elements.sort.value = "recentes";
    state.pagina = 1;
    renderizar(true);
});
elements.previous.addEventListener("click", () => { state.pagina -= 1; renderizar(true); });
elements.next.addEventListener("click", () => { state.pagina += 1; renderizar(true); });
document.querySelector("#refresh").addEventListener("click", () => window.location.reload());
document.querySelector("#back-to-top")?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
configurarTelegram();
configurarAssistenteRapido();
carregarOfertas();
