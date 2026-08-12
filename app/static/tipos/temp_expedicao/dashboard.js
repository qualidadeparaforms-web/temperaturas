(function () {
  const VERMELHO = "#C00000";
  // Só 4 locais fixos — cores escolhidas à mão (mesma família de
  // cores usada no gráfico de temperatura de processo), em vez do
  // esquema de cores geradas automaticamente usado onde a lista é
  // maior ou de texto livre (temperatura de setor, temp_produto).
  const CORES_LOCAL = {
    "Câmara de Congelado 1": "#2E75B6",
    "Câmara de Congelado 2": "#1F3864",
    "Câmara de Resfriados": "#00B0F0",
    "Matéria Prima - Quebra de Gelo": "#548235",
  };

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elLocal = document.getElementById("filtroLocal");
  const elCategoria = document.getElementById("filtroCategoria");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

  function montarQueryString() {
    const params = new URLSearchParams();
    params.set("periodo", elPeriodo.value);
    params.set("local", elLocal.value);
    params.set("categoria", elCategoria.value);
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
          : '<span class="badge badge-fora-padrao">⚠️ Fora do padrão</span>';
        return `<tr class="${classeLinha}">
          <td>${r.data}</td>
          <td>${r.horario}</td>
          <td>${r.local}</td>
          <td>${r.categoria || "—"}</td>
          <td>${r.temperatura.toFixed(1)}°C</td>
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
    const ctx = document.getElementById("graficoExpedicao");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    const locaisPresentes = [...new Set(registros.map((r) => r.local))];
    const datasets = locaisPresentes.map((local) => {
      const pontos = registros
        .filter((r) => r.local === local)
        .map((r) => ({
          x: new Date(`${r.data_iso}T${r.horario}:00`).getTime(),
          y: r.temperatura,
          conforme: r.conforme,
          rotulo: `${r.data} ${r.horario}` + (r.categoria ? ` — ${r.categoria}` : ""),
        }));
      const cor = CORES_LOCAL[local] || "#2E75B6";
      return {
        label: local,
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
    elBotaoExportar.href = "/dashboard/temp_expedicao/exportar?" + qs;

    const resposta = await fetch("/dashboard/temp_expedicao/api?" + qs);
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
  elLocal.addEventListener("change", carregarDados);
  elCategoria.addEventListener("change", carregarDados);
  elDataInicio.addEventListener("change", carregarDados);
  elDataFim.addEventListener("change", carregarDados);
})();
