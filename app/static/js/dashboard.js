(function () {
  const CORES_ETAPA = {
    "Aparas": "#2E75B6",
    "Bifes": "#1F3864",
    "Moídas": "#00B0F0",
    "Temperados": "#548235",
    "Embalagem": "#BF8F00",
    "Selagem": "#7030A0",
  };
  const VERMELHO = "#C00000";

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elEtapa = document.getElementById("filtroEtapa");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

  function montarQueryString() {
    const params = new URLSearchParams();
    params.set("periodo", elPeriodo.value);
    params.set("etapa", elEtapa.value);
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
          <td>${r.etapa}</td>
          <td>${r.temperatura.toFixed(1)}°C</td>
          <td>${r.responsavel}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
    corpo.innerHTML = linhas;
  }

  function atualizarGrafico(registros) {
    const ctx = document.getElementById("graficoTemperatura");

    const etapasPresentes = [...new Set(registros.map((r) => r.etapa))];
    const datasets = etapasPresentes.map((etapa) => {
      const pontos = registros
        .filter((r) => r.etapa === etapa)
        .map((r) => ({
          // Eixo X numérico (timestamp), não texto: com eixo "category" o
          // Chart.js ordena pela ordem de inserção nos datasets, não por
          // data/hora real — misturando etapas diferentes gera um gráfico
          // fora de ordem. Com "linear" os pontos ficam sempre corretos.
          x: new Date(`${r.data_iso}T${r.horario}:00`).getTime(),
          y: r.temperatura,
          conforme: r.conforme,
          rotulo: `${r.data} ${r.horario}`,
        }));
      const cor = CORES_ETAPA[etapa] || "#2E75B6";
      return {
        label: etapa,
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
    elBotaoExportar.href = "/exportar?" + qs;

    const resposta = await fetch("/api/registros?" + qs);
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
  elEtapa.addEventListener("change", carregarDados);
  elDataInicio.addEventListener("change", carregarDados);
  elDataFim.addEventListener("change", carregarDados);
})();
