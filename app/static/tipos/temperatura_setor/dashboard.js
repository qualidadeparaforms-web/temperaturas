(function () {
  const VERMELHO = "#C00000";

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elSetor = document.getElementById("filtroSetor");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

  function corParaIndice(indice, total) {
    // Paleta gerada (não fixa), diferente da tela de temperatura de
    // processo: aqui são 17 setores (e a lista pode crescer), então
    // as cores são espalhadas uniformemente na roda de matizes em vez
    // de escolhidas uma a uma à mão. Evita a faixa do vermelho
    // (reservado para "fora do padrão") e do amarelo (fundo de aviso).
    const faixaUtil = 300;
    const inicioFaixa = 40;
    const matiz = inicioFaixa + Math.round((faixaUtil / Math.max(total, 1)) * indice);
    return `hsl(${matiz % 360}, 60%, 40%)`;
  }

  function montarQueryString() {
    const params = new URLSearchParams();
    params.set("periodo", elPeriodo.value);
    params.set("setor", elSetor.value);
    if (elPeriodo.value === "personalizado") {
      if (elDataInicio.value) params.set("data_inicio", elDataInicio.value);
      if (elDataFim.value) params.set("data_fim", elDataFim.value);
    }
    return params.toString();
  }

  function atualizarVisibilidadeDatas() {
    const personalizado = elPeriodo.value === "personalizado";
    elCampoDataInicio.classList.toggle("d-none", !personalizado);
    elCampoDataFim.classList.toggle("d-none", !personalizado);
  }

  function atualizarResumo(resumo) {
    document.getElementById("resumoTotal").textContent = resumo.total;
    document.getElementById("resumoConformes").textContent = resumo.conformes;
    document.getElementById("resumoForaPadrao").textContent = resumo.fora_padrao;
    document.getElementById("resumoPercentual").textContent = resumo.percentual_conforme + "%";
  }

  function atualizarTabela(registros) {
    const corpo = document.getElementById("tabelaRegistros");
    if (!registros.length) {
      corpo.innerHTML =
        '<tr><td colspan="6" class="text-center text-muted py-4">Nenhum registro encontrado para o filtro selecionado.</td></tr>';
      return;
    }

    const linhas = registros
      .slice()
      .reverse()
      .map((r) => {
        const classeLinha = r.conforme ? "" : "linha-fora-padrao";
        const badge = r.conforme
          ? '<span class="badge badge-conforme">Conforme</span>'
          : '<span class="badge badge-fora-padrao">⚠️ Fora do padrão</span>';
        return `<tr class="${classeLinha}">
          <td>${r.data}</td>
          <td>${r.horario}</td>
          <td>${r.setor}</td>
          <td>${r.temperatura.toFixed(1)}°C</td>
          <td>${r.responsavel}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
    corpo.innerHTML = linhas;
  }

  function calcularLimitesEixoX(registros) {
    // Ver comentário equivalente em tipos/temperatura/dashboard.js:
    // sem min/max explícitos, o Chart.js quebra (eixo de anos em vez
    // de horas) quando todos os pontos caem no mesmo instante.
    if (!registros.length) return { min: undefined, max: undefined };
    const timestamps = registros.map((r) => new Date(`${r.data_iso}T${r.horario}:00`).getTime());
    let min = Math.min(...timestamps);
    let max = Math.max(...timestamps);
    const folgaMinimaMs = 30 * 60 * 1000;
    if (max - min < folgaMinimaMs * 2) {
      const centro = (min + max) / 2;
      min = centro - folgaMinimaMs;
      max = centro + folgaMinimaMs;
    }
    return { min, max };
  }

  function atualizarGrafico(registros) {
    const ctx = document.getElementById("graficoTemperaturaSetor");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    const setoresPresentes = [...new Set(registros.map((r) => r.setor))];
    const datasets = setoresPresentes.map((setor, indice) => {
      const pontos = registros
        .filter((r) => r.setor === setor)
        .map((r) => ({
          x: new Date(`${r.data_iso}T${r.horario}:00`).getTime(),
          y: r.temperatura,
          conforme: r.conforme,
          rotulo: `${r.data} ${r.horario}`,
        }));
      const cor = corParaIndice(indice, setoresPresentes.length);
      return {
        label: setor,
        data: pontos,
        borderColor: cor,
        backgroundColor: cor,
        tension: 0.2,
        pointRadius: pontos.map((p) => (p.conforme ? 3 : 6)),
        pointBackgroundColor: pontos.map((p) => (p.conforme ? cor : VERMELHO)),
        pointBorderColor: pontos.map((p) => (p.conforme ? cor : VERMELHO)),
      };
    });

    if (grafico) {
      grafico.destroy();
    }
    grafico = new Chart(ctx, {
      type: "line",
      data: { datasets },
      options: {
        responsive: true,
        interaction: { mode: "nearest", intersect: false },
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              title: function (items) {
                return items[0]?.raw?.rotulo || "";
              },
              label: function (item) {
                const p = item.raw;
                const situacao = p.conforme ? "conforme" : "⚠️ fora do padrão";
                return `${item.dataset.label}: ${p.y.toFixed(1)}°C (${situacao})`;
              },
            },
          },
        },
        scales: {
          x: {
            type: "linear",
            min: minEixoX,
            max: maxEixoX,
            ticks: {
              autoSkip: true,
              maxTicksLimit: 12,
              callback: function (valor) {
                const d = new Date(valor);
                const dataFmt = d.toLocaleDateString("pt-BR");
                const horaFmt = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
                return [dataFmt, horaFmt];
              },
            },
            title: { display: true, text: "Data / Horário" },
          },
          y: {
            title: { display: true, text: "Temperatura (°C)" },
          },
        },
      },
    });
  }

  async function carregarDados() {
    const qs = montarQueryString();
    elBotaoExportar.href = "/dashboard/temperatura_setor/exportar?" + qs;

    const resposta = await fetch("/dashboard/temperatura_setor/api?" + qs);
    const dados = await resposta.json();

    atualizarResumo(dados.resumo);
    atualizarTabela(dados.registros);
    atualizarGrafico(dados.registros);
  }

  atualizarVisibilidadeDatas();
  carregarDados();

  elPeriodo.addEventListener("change", () => {
    atualizarVisibilidadeDatas();
    carregarDados();
  });
  elSetor.addEventListener("change", carregarDados);
  elDataInicio.addEventListener("change", carregarDados);
  elDataFim.addEventListener("change", carregarDados);
})();
