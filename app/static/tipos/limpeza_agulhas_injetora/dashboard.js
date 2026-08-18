(function () {
  const VERMELHO = "#C00000";
  const AZUL = "#2E75B6";
  const NAVY = "#1F3864";

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
          : '<span class="badge badge-fora-padrao">⚠️ NC</span>';
        return `<tr class="${classeLinha}">
          <td>${r.data}</td>
          <td>${r.agulhas_limpas}</td>
          <td>${r.sem_residuos}</td>
          <td>${r.operador}</td>
          <td>${r.controle_qualidade}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
    corpo.innerHTML = linhas;
  }

  function calcularLimitesEixoX(registros) {
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
    const ctx = document.getElementById("graficoLimpezaAgulhas");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    // Duas linhas fixas — um critério cada (Agulhas Limpas, Sem
    // Resíduos) — y = 1 quando NC (vermelho), 0 quando conforme.
    function pontosPara(campo) {
      return registros.map((r) => ({
        x: new Date(`${r.data_iso}T00:00:00`).getTime(),
        y: r[campo] === "NC" ? 1 : 0,
        conforme: r[campo] === "C",
        rotulo: r.data,
      }));
    }

    const pontosAgulhas = pontosPara("agulhas_limpas");
    const pontosResiduos = pontosPara("sem_residuos");

    const datasets = [
      {
        label: "Agulhas Limpas",
        data: pontosAgulhas,
        borderColor: NAVY,
        backgroundColor: NAVY,
        stepped: true,
        pointRadius: pontosAgulhas.map((p) => (p.conforme ? 3 : 6)),
        pointBackgroundColor: pontosAgulhas.map((p) => (p.conforme ? NAVY : VERMELHO)),
        pointBorderColor: pontosAgulhas.map((p) => (p.conforme ? NAVY : VERMELHO)),
      },
      {
        label: "Sem Resíduos",
        data: pontosResiduos,
        borderColor: AZUL,
        backgroundColor: AZUL,
        stepped: true,
        pointRadius: pontosResiduos.map((p) => (p.conforme ? 3 : 6)),
        pointBackgroundColor: pontosResiduos.map((p) => (p.conforme ? AZUL : VERMELHO)),
        pointBorderColor: pontosResiduos.map((p) => (p.conforme ? AZUL : VERMELHO)),
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
    elBotaoExportar.href = "/dashboard/limpeza_agulhas_injetora/exportar?" + qs;

    const resposta = await fetch("/dashboard/limpeza_agulhas_injetora/api?" + qs);
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
