(function () {
  const VERMELHO = "#C00000";
  const COR_PH = "#2E75B6"; // azul da paleta
  const COR_CLORO = "#548235"; // verde, distinto do vermelho/amarelo reservados

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

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
    document.getElementById("resumoTotal").textContent = resumo.total;
    document.getElementById("resumoConformes").textContent = resumo.conformes;
    document.getElementById("resumoForaPadrao").textContent = resumo.fora_padrao;
    document.getElementById("resumoPercentual").textContent = resumo.percentual_conforme + "%";
  }

  function atualizarTabela(registros) {
    const corpo = document.getElementById("tabelaRegistros");
    if (!registros.length) {
      corpo.innerHTML =
        '<tr><td colspan="7" class="text-center text-muted py-4">Nenhum registro encontrado para o filtro selecionado.</td></tr>';
      return;
    }

    const linhas = registros
      .slice()
      .reverse()
      .map((r) => {
        const classeLinha = r.conforme ? "" : "linha-fora-padrao";
        const badge = r.conforme
          ? '<span class="badge badge-conforme">Conforme</span>'
          : `<span class="badge badge-fora-padrao">⚠️ ${r.situacao}</span>`;
        return `<tr class="${classeLinha}">
          <td>${r.data}</td>
          <td>${r.horario}</td>
          <td>${r.ponto}</td>
          <td>${r.ph.toFixed(2)}</td>
          <td>${r.cloro.toFixed(2)}</td>
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
    const ctx = document.getElementById("graficoAgua");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    // pH e Cloro têm faixas e unidades diferentes — em vez de uma
    // linha por "categoria" (como etapa/setor nos outros tipos),
    // aqui são duas linhas fixas (pH e Cloro), cada uma com seu
    // próprio eixo Y, para não distorcer a leitura de nenhuma delas.
    const pontosPh = registros.map((r) => ({
      x: new Date(`${r.data_iso}T${r.horario}:00`).getTime(),
      y: r.ph,
      conforme: r.ph_conforme,
      rotulo: `${r.data} ${r.horario} — ${r.ponto}`,
    }));
    const pontosCloro = registros.map((r) => ({
      x: new Date(`${r.data_iso}T${r.horario}:00`).getTime(),
      y: r.cloro,
      conforme: r.cloro_conforme,
      rotulo: `${r.data} ${r.horario} — ${r.ponto}`,
    }));

    const datasets = [
      {
        label: "pH",
        data: pontosPh,
        borderColor: COR_PH,
        backgroundColor: COR_PH,
        yAxisID: "yPh",
        tension: 0.2,
        pointRadius: pontosPh.map((p) => (p.conforme ? 3 : 6)),
        pointBackgroundColor: pontosPh.map((p) => (p.conforme ? COR_PH : VERMELHO)),
        pointBorderColor: pontosPh.map((p) => (p.conforme ? COR_PH : VERMELHO)),
      },
      {
        label: "Cloro (ppm)",
        data: pontosCloro,
        borderColor: COR_CLORO,
        backgroundColor: COR_CLORO,
        yAxisID: "yCloro",
        tension: 0.2,
        pointRadius: pontosCloro.map((p) => (p.conforme ? 3 : 6)),
        pointBackgroundColor: pontosCloro.map((p) => (p.conforme ? COR_CLORO : VERMELHO)),
        pointBorderColor: pontosCloro.map((p) => (p.conforme ? COR_CLORO : VERMELHO)),
      },
    ];

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
                return `${item.dataset.label}: ${p.y.toFixed(2)} (${situacao})`;
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
          yPh: {
            type: "linear",
            position: "left",
            suggestedMin: 0,
            suggestedMax: 14,
            title: { display: true, text: "pH" },
          },
          yCloro: {
            type: "linear",
            position: "right",
            suggestedMin: 0,
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Cloro (ppm)" },
          },
        },
      },
    });
  }

  async function carregarDados() {
    const qs = montarQueryString();
    elBotaoExportar.href = "/dashboard/agua_abastecimento/exportar?" + qs;

    const resposta = await fetch("/dashboard/agua_abastecimento/api?" + qs);
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
