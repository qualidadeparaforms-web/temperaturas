(function () {
  const VERMELHO = "#C00000";

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elPso = document.getElementById("filtroPso");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

  function corParaIndice(indice, total) {
    // Paleta gerada (mesmo esquema de temperatura_setor): os 7 PSOs
    // são fixos, mas gerar em vez de escolher à mão evita cores
    // parecidas e deixa o gráfico pronto se a lista crescer.
    const faixaUtil = 300;
    const inicioFaixa = 40;
    const matiz = inicioFaixa + Math.round((faixaUtil / Math.max(total, 1)) * indice);
    return `hsl(${matiz % 360}, 60%, 40%)`;
  }

  function montarQueryString() {
    const params = new URLSearchParams();
    params.set("periodo", elPeriodo.value);
    params.set("pso", elPso.value);
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
        '<tr><td colspan="4" class="text-center text-muted py-4">Nenhum registro encontrado para o filtro selecionado.</td></tr>';
      return;
    }

    const linhas = registros
      .slice()
      .reverse()
      .map((r) => {
        const classeLinha = r.conforme ? "" : "linha-fora-padrao";
        const badge = r.conforme
          ? '<span class="badge badge-conforme">Conforme</span>'
          : '<span class="badge badge-fora-padrao">⚠️ NC</span>';
        return `<tr class="${classeLinha}">
          <td>${r.data}</td>
          <td>${r.pso}</td>
          <td>${r.responsavel}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
    corpo.innerHTML = linhas;
  }

  function calcularLimitesEixoX(registros) {
    // Igual aos outros tipos, mas em granularidade de dia (não há
    // horário aqui): sem min/max explícitos, o Chart.js quebra
    // quando todos os pontos caem no mesmo dia.
    if (!registros.length) return { min: undefined, max: undefined };
    const timestamps = registros.map((r) => new Date(`${r.data_iso}T00:00:00`).getTime());
    let min = Math.min(...timestamps);
    let max = Math.max(...timestamps);
    const folgaMinimaMs = 12 * 60 * 60 * 1000;
    if (max - min < folgaMinimaMs * 2) {
      const centro = (min + max) / 2;
      min = centro - folgaMinimaMs;
      max = centro + folgaMinimaMs;
    }
    return { min, max };
  }

  function atualizarGrafico(registros) {
    const ctx = document.getElementById("graficoPso");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    // Uma linha por PSO — cada ponto é um checklist daquele PSO num
    // dia, y = 1 quando NC (vermelho) e 0 quando conforme. Ajuda a
    // enxergar visualmente se algum PSO específico é recorrente.
    const psosPresentes = [...new Set(registros.map((r) => r.pso))];
    const datasets = psosPresentes.map((pso, indice) => {
      const pontos = registros
        .filter((r) => r.pso === pso)
        .map((r) => ({
          x: new Date(`${r.data_iso}T00:00:00`).getTime(),
          y: r.conforme ? 0 : 1,
          conforme: r.conforme,
          rotulo: r.data,
        }));
      const cor = corParaIndice(indice, psosPresentes.length);
      return {
        label: pso,
        data: pontos,
        borderColor: cor,
        backgroundColor: cor,
        stepped: true,
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
                return `${item.dataset.label}: ${p.conforme ? "Conforme" : "⚠️ NC"}`;
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
                return new Date(valor).toLocaleDateString("pt-BR");
              },
            },
            title: { display: true, text: "Dia" },
          },
          y: {
            min: 0,
            max: 1,
            ticks: {
              stepSize: 1,
              callback: function (valor) {
                return valor === 1 ? "NC" : "C";
              },
            },
            title: { display: true, text: "Situação" },
          },
        },
      },
    });
  }

  async function carregarDados() {
    const qs = montarQueryString();
    elBotaoExportar.href = "/dashboard/pso/exportar?" + qs;

    const resposta = await fetch("/dashboard/pso/api?" + qs);
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
  elPso.addEventListener("change", carregarDados);
  elDataInicio.addEventListener("change", carregarDados);
  elDataFim.addEventListener("change", carregarDados);
})();
