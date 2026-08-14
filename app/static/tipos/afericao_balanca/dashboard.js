(function () {
  const VERMELHO = "#C00000";

  const elPeriodo = document.getElementById("filtroPeriodo");
  const elBalanca = document.getElementById("filtroBalanca");
  const elDataInicio = document.getElementById("filtroDataInicio");
  const elDataFim = document.getElementById("filtroDataFim");
  const elCampoDataInicio = document.getElementById("campoDataInicio");
  const elCampoDataFim = document.getElementById("campoDataFim");
  const elBotaoExportar = document.getElementById("botaoExportar");

  let grafico = null;

  function corParaIndice(indice, total) {
    // Mesmo esquema gerado usado em temperatura_setor, pso e
    // ventilacao — evita escolher 20 cores à mão.
    const faixaUtil = 300;
    const inicioFaixa = 40;
    const matiz = inicioFaixa + Math.round((faixaUtil / Math.max(total, 1)) * indice);
    return `hsl(${matiz % 360}, 60%, 40%)`;
  }

  function montarQueryString() {
    const params = new URLSearchParams();
    params.set("periodo", elPeriodo.value);
    params.set("balanca", elBalanca.value);
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
          <td>${r.setor}</td>
          <td>${r.balanca}</td>
          <td>${r.leitura.toFixed(1)}</td>
          <td>${r.responsavel}</td>
          <td>${badge}</td>
        </tr>`;
      })
      .join("");
    corpo.innerHTML = linhas;
  }

  function calcularLimitesEixoX(registros) {
    // Igual aos painéis do PAC 11 e do PAC 08-E: granularidade de
    // dia, sem horário.
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
    const ctx = document.getElementById("graficoAfericaoBalanca");
    const { min: minEixoX, max: maxEixoX } = calcularLimitesEixoX(registros);

    // Uma linha por balança presente no período — cada ponto é uma
    // leitura numa data, y = 1 quando NC (vermelho) e 0 quando
    // conforme. O filtro de balança existe pra isolar uma balança
    // específica e ver se ela é recorrente em NC (indício de
    // descalibração persistente).
    const balancasPresentes = [...new Set(registros.map((r) => r.balanca))];
    const datasets = balancasPresentes.map((balanca, indice) => {
      const pontos = registros
        .filter((r) => r.balanca === balanca)
        .map((r) => ({
          x: new Date(`${r.data_iso}T00:00:00`).getTime(),
          y: r.conforme ? 0 : 1,
          conforme: r.conforme,
          rotulo: r.data,
          leitura: r.leitura,
        }));
      const cor = corParaIndice(indice, balancasPresentes.length);
      return {
        label: balanca,
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
          legend: { position: "bottom", display: balancasPresentes.length <= 8 },
          tooltip: {
            callbacks: {
              title: function (items) {
                return items[0]?.raw?.rotulo || "";
              },
              label: function (item) {
                const p = item.raw;
                return `${item.dataset.label}: ${p.leitura.toFixed(1)}g (${p.conforme ? "Conforme" : "⚠️ NC"})`;
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
    elBotaoExportar.href = "/dashboard/afericao_balanca/exportar?" + qs;

    const resposta = await fetch("/dashboard/afericao_balanca/api?" + qs);
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
  elBalanca.addEventListener("change", carregarDados);
  elDataInicio.addEventListener("change", carregarDados);
  elDataFim.addEventListener("change", carregarDados);
})();
