(function () {
  const VERMELHO = "#C00000";

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

  function corParaIndice(indice, total) {
    // Paleta gerada (mesmo esquema de temperatura_setor/temp_produto/
    // peso_produto): o produto é texto livre, quantidade variável.
    const faixaUtil = 300;
    const inicioFaixa = 40;
    const matiz = inicioFaixa + Math.round((faixaUtil / Math.max(total, 1)) * indice);
    return `hsl(${matiz % 360}, 60%, 40%)`;
  }

  function montarQueryString() {
    const params = new URLSearchParams();
    params.set("periodo", elPeriodo.value);
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
    document.getElementById("resumoTotalRegistros").textContent = resumo.total_registros;
    document.getElementById("resumoTotalPesagens").textContent = resumo.total_pesagens;
    document.getElementById("resumoTotalNc").textContent = resumo.total_nc;
    document.getElementById("resumoPercentual").textContent = resumo.percentual_conforme + "%";
  }

  function atualizarTabela(registros) {
    const corpo = document.getElementById("tabelaRegistros");
    if (!registros.length) {
      corpo.innerHTML =
        '<tr><td colspan="9" class="text-center text-muted py-4">Nenhum registro encontrado para o filtro selecionado.</td></tr>';
      return;
    }

    const linhas = registros
      .slice()
      .reverse()
      .map((r) => {
        const classeLinha = r.conforme ? "" : "linha-fora-padrao";
        const badge = r.conforme
          ? '<span class="badge badge-conforme">Conforme</span>'
          : `<span class="badge badge-fora-padrao">⚠️ ${r.total_nc} NC${r.total_nc > 1 ? "s" : ""}</span>`;
        return `<tr class="${classeLinha}">
          <td>${r.data}</td>
          <td>${r.horario}</td>
          <td>${r.produto}</td>
          <td>${r.gramatura_minima}–${r.gramatura_maxima}</td>
          <td>${r.operador}</td>
          <td>${r.total_pesagens}</td>
          <td>${r.total_nc}</td>
          <td>${r.responsavel}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
    corpo.innerHTML = linhas;
  }

  function calcularLimitesEixoX(registros) {
    // Ver comentário equivalente nos outros tipos: sem min/max
    // explícitos, o Chart.js quebra quando todos os pontos caem no
    // mesmo instante.
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
    const ctx = document.getElementById("graficoGramatura");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    // Uma linha por produto — cada ponto é UM REGISTRO (uma avaliação
    // completa do produto naquele dia), com y = total de NCs daquela
    // avaliação. O detalhe pesagem a pesagem fica na exportação.
    const produtosPresentes = [...new Set(registros.map((r) => r.produto))];
    const datasets = produtosPresentes.map((produto, indice) => {
      const pontos = registros
        .filter((r) => r.produto === produto)
        .map((r) => ({
          x: new Date(`${r.data_iso}T${r.horario}:00`).getTime(),
          y: r.total_nc,
          conforme: r.conforme,
          rotulo: `${r.data} ${r.horario} — ${r.total_pesagens} pesagem(ns)`,
        }));
      const cor = corParaIndice(indice, produtosPresentes.length);
      return {
        label: produto,
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
                const situacao = p.conforme ? "conforme" : "⚠️ com NC";
                return `${item.dataset.label}: ${p.y} NC(s) (${situacao})`;
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
            beginAtZero: true,
            ticks: { precision: 0 },
            title: { display: true, text: "Total de NCs" },
          },
        },
      },
    });
  }

  async function carregarDados() {
    const qs = montarQueryString();
    elBotaoExportar.href = "/dashboard/gramatura/exportar?" + qs;

    const resposta = await fetch("/dashboard/gramatura/api?" + qs);
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
  elDataInicio.addEventListener("change", carregarDados);
  elDataFim.addEventListener("change", carregarDados);
})();
