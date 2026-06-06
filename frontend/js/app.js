"use strict";

// Frontend servido pelo FastAPI em /ui/ — a API está na mesma origem.
// Usar caminhos relativos ao root ("/asteroides") evita CORS e funciona
// em qualquer host ou porta sem alterar o código.
const API = "";

// ── Utilitários ──────────────────────────────────────────────────────────────

async function fetchJSON(path) {
  const resp = await fetch(API + path);
  if (!resp.ok) {
    const err = new Error(`HTTP ${resp.status}`);
    err.status = resp.status;
    throw err;
  }
  return resp.json();
}

function classeRecurso(valor) {
  if (valor >= 80) return "alto";
  if (valor >= 50) return "medio";
  return "baixo";
}

function classeScore(score) {
  if (score >= 70) return "score-alto";
  if (score >= 40) return "score-medio";
  return "score-baixo";
}

function formatarDistancia(km) {
  return new Intl.NumberFormat("pt-BR").format(Math.round(km)) + " km";
}

// ── Renderização ─────────────────────────────────────────────────────────────

function renderSaude(dados) {
  const itens = [
    { label: "CPU",     valor: dados.cpu_percent },
    { label: "Memória", valor: dados.memoria_percent },
    { label: "Disco",   valor: dados.disco_percent },
  ];
  return itens.map(({ label, valor }) => {
    const cls = classeRecurso(valor);
    return `
      <div class="saude-card">
        <div class="saude-label">${label}</div>
        <div class="saude-valor ${cls}">${valor.toFixed(1)}%</div>
        <div class="barra-bg">
          <div class="barra-fill ${cls}" style="width:${Math.min(valor, 100)}%"></div>
        </div>
      </div>`;
  }).join("");
}

function renderMetricas(rel) {
  return `
    <div class="metrica-card">
      <div class="metrica-valor">${rel.total_asteroides}</div>
      <div class="metrica-label">Total de Asteroides</div>
    </div>
    <div class="metrica-card danger">
      <div class="metrica-valor">${rel.potencialmente_perigosos}</div>
      <div class="metrica-label">Potencialmente Perigosos</div>
    </div>
    <div class="metrica-card warning">
      <div class="metrica-valor">${rel.anomalias_detectadas}</div>
      <div class="metrica-label">Anomalias Detectadas</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-valor pequeno">${rel.gerado_em}</div>
      <div class="metrica-label">Gerado em</div>
    </div>`;
}

function renderLinha(a) {
  const score = a.score_risco ?? 0;
  const badge = a.perigoso
    ? '<span class="status-badge status-perigo">PERIGOSO</span>'
    : '<span class="status-badge status-seguro">Seguro</span>';
  return `
    <tr>
      <td class="mono muted" style="font-size:0.8em">${a.id}</td>
      <td>${a.nome}</td>
      <td class="mono">${a.data_aprox ?? "—"}</td>
      <td class="mono">${formatarDistancia(a.distancia_km)}</td>
      <td><span class="score-badge ${classeScore(score)}">${score.toFixed(2)}</span></td>
      <td>${badge}</td>
    </tr>`;
}

// ── Carregamento ─────────────────────────────────────────────────────────────

async function carregarSaude() {
  const el = document.getElementById("saude");
  try {
    const dados = await fetchJSON("/saude");
    el.innerHTML = renderSaude(dados);
  } catch {
    el.innerHTML = '<p class="muted msg">Não foi possível carregar métricas do sistema.</p>';
  }
}

async function carregarMetricas() {
  const el = document.getElementById("cards");
  try {
    const rel = await fetchJSON("/relatorio");
    el.innerHTML = renderMetricas(rel);
  } catch (e) {
    const txt = e.status === 404
      ? "Sem relatório. Execute o pipeline primeiro."
      : "Erro ao carregar métricas.";
    el.innerHTML = `<p class="muted msg">${txt}</p>`;
  }
}

async function carregarTabela() {
  const corpo = document.getElementById("corpo-tabela");
  const msg   = document.getElementById("msg-tabela");
  const cont  = document.getElementById("contagem");

  msg.textContent = "";
  corpo.innerHTML = "";
  cont.textContent = "";

  try {
    const lista = await fetchJSON("/asteroides");
    corpo.innerHTML = lista.map(renderLinha).join("");
    cont.textContent = `${lista.length} registros`;
  } catch (e) {
    if (e.status === 404) {
      msg.textContent = "Nenhum dado encontrado. Execute o pipeline primeiro.";
      msg.className = "msg muted";
    } else {
      msg.textContent = "Erro ao conectar com a API.";
      msg.className = "msg erro";
    }
  }
}

// ── Controle principal ────────────────────────────────────────────────────────

async function carregar() {
  const btn = document.getElementById("btn-atualizar");
  btn.disabled = true;
  btn.textContent = "Atualizando...";

  await Promise.all([carregarSaude(), carregarMetricas(), carregarTabela()]);

  document.getElementById("ultima-atualizacao").textContent =
    "Atualizado às " + new Date().toLocaleTimeString("pt-BR");

  btn.disabled = false;
  btn.textContent = "Atualizar";
}

document.addEventListener("DOMContentLoaded", carregar);
