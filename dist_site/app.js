const POR_PAGINA = 20;
const state = { ofertas: [], geradoEm: null, pagina: 1 };

const elements = {
    grid: document.querySelector("#offer-grid"),
    count: document.querySelector("#offer-count"),
    search: document.querySelector("#search"),
    category: document.querySelector("#category"),
    sort: document.querySelector("#sort"),
    generatedAt: document.querySelector("#generated-at"),
    previous: document.querySelector("#previous-page"),
    next: document.querySelector("#next-page"),
    pageIndicator: document.querySelector("#page-indicator"),
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

function imagemPublica(url) {
    try {
        const imagem = new URL(textoSeguro(url));
        return imagem.protocol === "https:" || imagem.protocol === "http:" ? imagem.href : "";
    } catch (_) {
        return "";
    }
}

function preencherSelect(select, valores, textoPadrao) {
    select.replaceChildren(new Option(textoPadrao, ""));
    valores.sort((a, b) => a.localeCompare(b, "pt-BR")).forEach((valor) => select.add(new Option(valor, valor)));
}

function ofertasFiltradas() {
    const busca = elements.search.value.trim().toLocaleLowerCase("pt-BR");
    const categoria = elements.category.value;
    const ofertas = state.ofertas.filter((oferta) => {
        const titulo = textoSeguro(oferta.titulo).toLocaleLowerCase("pt-BR");
        return (!busca || titulo.includes(busca)) && (!categoria || oferta.categoria === categoria);
    });
    return ofertas.sort((a, b) => {
        if (elements.sort.value === "menor-preco") return Number(a.preco) - Number(b.preco);
        if (elements.sort.value === "maior-preco") return Number(b.preco) - Number(a.preco);
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

function registrarClique(oferta) {
    if (!imagemPublica(elements.analyticsUrl)) return;
    const evento = JSON.stringify({
        oferta_id: textoSeguro(oferta.oferta_id),
        titulo: textoSeguro(oferta.titulo),
        categoria: textoSeguro(oferta.categoria) || "ofertas"
    });
    const endpoint = elements.analyticsUrl;
    const dados = new Blob([evento], { type: "application/json" });
    if (navigator.sendBeacon && navigator.sendBeacon(endpoint, dados)) return;
    fetch(endpoint, { method: "POST", body: evento, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(() => {});
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

    const titulo = document.createElement("h3");
    titulo.textContent = textoSeguro(oferta.titulo) || "Oferta sem título";
    const atualizado = document.createElement("p");
    atualizado.className = "updated";
    atualizado.textContent = `Atualizada em ${formatarData(oferta.ultima_verificacao || oferta.data_publicacao)}`;
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
    variacao.className = valorVariacao < 0 ? "variation-down" : valorVariacao > 0 ? "variation-up" : "variation-stable";
    variacao.textContent = valorVariacao < 0 ? `Caiu ${formatarPreco(Math.abs(valorVariacao))}` : valorVariacao > 0 ? `Subiu ${formatarPreco(valorVariacao)}` : "Sem variação";
    historico.append(menorLabel, menorPreco, variacao);
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
    link.addEventListener("click", () => registrarClique(oferta));
    const detalhes = document.createElement("a");
    detalhes.className = "details-link";
    detalhes.href = textoSeguro(oferta.produto_url);
    detalhes.textContent = "Ver detalhes";
    card.append(criarMidia(oferta), topo, titulo, atualizado, label, preco, historico, destaque, link, detalhes);
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

function renderizar() {
    const ofertas = ofertasFiltradas();
    const totalPaginas = Math.max(1, Math.ceil(ofertas.length / POR_PAGINA));
    state.pagina = Math.min(Math.max(state.pagina, 1), totalPaginas);
    const inicio = (state.pagina - 1) * POR_PAGINA;
    const pagina = ofertas.slice(inicio, inicio + POR_PAGINA);
    elements.count.textContent = `${ofertas.length} ${ofertas.length === 1 ? "oferta encontrada" : "ofertas encontradas"}`;
    elements.pageIndicator.textContent = `Página ${state.pagina} de ${totalPaginas}`;
    elements.previous.disabled = state.pagina === 1;
    elements.next.disabled = state.pagina === totalPaginas;
    if (!ofertas.length) {
        exibirFeedback("Nenhuma oferta encontrada", "Ajuste os filtros ou volte mais tarde para ver novas seleções.");
        return;
    }
    elements.grid.replaceChildren(...pagina.map(criarCard));
}

function configurarTelegram() {
    const url = document.body.dataset.telegramUrl.trim();
    if (!/^https:\/\/t\.me\//.test(url)) return;
    elements.telegramLinks.forEach((link) => { link.href = url; link.hidden = false; });
}

async function carregarOfertas() {
    exibirFeedback("Carregando ofertas", "Buscando as ofertas selecionadas para você.");
    try {
        const resposta = await fetch("ofertas.json", { cache: "no-store" });
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();
        state.ofertas = Array.isArray(dados.ofertas) ? dados.ofertas.filter((oferta) => /^https?:\/\//.test(textoSeguro(oferta.link))) : [];
        state.geradoEm = dados.gerado_em;
        preencherSelect(elements.category, [...new Set(state.ofertas.map((oferta) => textoSeguro(oferta.categoria)).filter(Boolean))], "Todas as categorias");
        elements.generatedAt.textContent = state.geradoEm ? `Lista atualizada em ${formatarData(state.geradoEm)}` : "Lista atualizada";
        renderizar();
    } catch (_) {
        elements.count.textContent = "Ofertas indisponíveis";
        elements.pageIndicator.textContent = "";
        elements.previous.disabled = true;
        elements.next.disabled = true;
        exibirFeedback("Não foi possível carregar as ofertas", "Atualize a página em alguns instantes. O catálogo pode estar sendo atualizado.");
    }
}

function filtrarDaPrimeiraPagina() { state.pagina = 1; renderizar(); }
elements.search.addEventListener("input", filtrarDaPrimeiraPagina);
[elements.category, elements.sort].forEach((campo) => campo.addEventListener("change", filtrarDaPrimeiraPagina));
elements.previous.addEventListener("click", () => { state.pagina -= 1; renderizar(); });
elements.next.addEventListener("click", () => { state.pagina += 1; renderizar(); });
document.querySelector("#refresh").addEventListener("click", () => window.location.reload());
configurarTelegram();
carregarOfertas();
