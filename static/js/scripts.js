/**
 * Projeto_Contas_Orcamento - Scripts Principais
 * Desenvolvedor Sênior: Antigravity
 */

let registroSelecionado = null;
let chartCategorias = null;
let chartEvolucao = null;
let chartStatus = null;
let chartRankingMensal = null;

const coresCategorias = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
    '#FF9F40', '#C9CBCF', '#7B68EE', '#32CD32', '#FF69B4'
];

// ============================================================================
// 🛠 FUNÇÕES AUXILIARES
// ============================================================================

const paraISO = (dataBr) => {
    if (!dataBr || dataBr === 'None' || dataBr.length < 10) return '';
    try {
        const p = dataBr.split(/[\/\-]/);
        if (p.length === 3) {
            const [dia, mes, ano] = p;
            return `${ano}-${mes.padStart(2, '0')}-${dia.padStart(2, '0')}`;
        }
    } catch (e) {
        console.error("Erro ao converter data:", dataBr, e);
    }
    return dataBr;
};

const paraBR = (valor) => {
    if (valor === null || valor === undefined || valor === '' || valor === 'None') return '';
    const num = parseFloat(valor);
    return isNaN(num) ? '' : num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

function selecionarOuCriarOption(selectElement, valor) {
    if (!selectElement || !valor || valor === 'None') return;
    const valorLimpo = valor.trim();
    let exists = Array.from(selectElement.options).some(opt => opt.value === valorLimpo);
    if (!exists) {
        const newOpt = new Option(valorLimpo, valorLimpo, true, true);
        selectElement.add(newOpt);
    } else {
        selectElement.value = valorLimpo;
    }
}

function filtrarCategoriasPorTipo() {
    const radioReceita = document.querySelector('input[name="ReceitaDespesa"][value="R"]');
    const selectCategoria = document.getElementById('inpCategoria');
    if (!selectCategoria) return;
    const tipoSelecionado = radioReceita && radioReceita.checked ? 'R' : 'D';
    Array.from(selectCategoria.options).forEach(option => {
        if (option.value === '' || option.value === 'Outros') return;
        const tipoCategoria = option.getAttribute('data-tipo');
        if (tipoCategoria === tipoSelecionado || tipoCategoria === null) {
            option.style.display = 'block';
        } else {
            option.style.display = 'none';
            if (option.selected) option.selected = false;
        }
    });
}

function atualizarTipoCategoria() {
    const tipoR = document.getElementById('tipoR').checked;
    const label = document.getElementById('labelTipoNovaCategoria');
    if (label) {
        if (tipoR) {
            label.textContent = 'Receita (R)';
            label.className = 'text-success';
        } else {
            label.textContent = 'Despesa (D)';
            label.className = 'text-danger';
        }
    }
}

function sincronizarBotaoPorCategoria() {
    const form = document.getElementById('mainForm');
    if (!form || form.method.toUpperCase() === 'GET') return;
    
    const select = document.getElementById('inpCategoria');
    const inputTipoR = document.getElementById('tipoR');
    const inputTipoD = document.getElementById('tipoD');
    const btnReceita = inputTipoR?.parentElement;
    const btnDespesa = inputTipoD?.parentElement;
    
    if (!select) return;
    
    const texto = select.options[select.selectedIndex].text.toUpperCase();
    
    if (texto.includes('(RECEITA)') || texto.includes('SALÁRIO') || texto.includes('APOSENTADORIA')) {
        if (inputTipoR) { inputTipoR.checked = true; inputTipoR.dispatchEvent(new Event('change')); }
        if (btnReceita) { btnReceita.className = 'btn btn-success'; btnReceita.classList.remove('btn-outline-success'); }
        if (btnDespesa) { btnDespesa.className = 'btn btn-outline-danger'; btnDespesa.classList.remove('btn-danger'); }
    } else {
        if (inputTipoD) { inputTipoD.checked = true; inputTipoD.dispatchEvent(new Event('change')); }
        if (btnDespesa) { btnDespesa.className = 'btn btn-danger'; btnDespesa.classList.remove('btn-outline-danger'); }
        if (btnReceita) { btnReceita.className = 'btn btn-outline-success'; btnReceita.classList.remove('btn-success'); }
    }
}

// ============================================================================
// 🔍 BUSCA E FILTROS
// ============================================================================

function buscarRegistros() {
    const filtros = {
        MesAno: (document.getElementById('inpMesAno')?.value || '').trim(),
        Conta: (document.getElementById('inpConta')?.value || '').trim(),
        Instituicao: (document.getElementById('inpInst')?.value || '').trim(),
        Fontepaga: (document.getElementById('inpFonte')?.value || '').trim(),
        Competencia: (document.getElementById('inpCompetencia')?.value || '').trim(),
        Categoria: document.getElementById('inpCategoria')?.value || '',
        data_inicio: (document.querySelector('input[name="data_inicio"]')?.value || ''),
        data_fim: (document.querySelector('input[name="data_fim"]')?.value || '')
    };
    
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([chave, valor]) => {
        if (valor && valor.length > 0) params.append(chave, valor);
    });
    
    window.location.href = params.toString() ? `/?${params.toString()}` : '/';
}

/**
 * Especialista Sênior: Função robusta para limpar todos os filtros de busca
 */
function limparBuscaGeral() {
    // 1. Limpa os inputs visuais
    const inputs = ['inpMesAno', 'inpConta', 'inpInst', 'inpFonte', 'inpCompetencia'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    
    // 2. Limpa datas da action bar
    document.querySelectorAll('input[type="date"]').forEach(input => input.value = '');
    
    // 3. Reseta categoria
    const selectCat = document.getElementById('inpCategoria');
    if (selectCat) selectCat.value = '';
    
    // 4. Redireciona para URL limpa
    window.location.href = '/';
}

function limparFormulario() {
    const form = document.getElementById('mainForm');
    if (form) form.reset();
    document.getElementById('cod_registro').value = '';
    document.getElementById('tipoD').checked = true;
    document.getElementById('categoriaCustomContainer').classList.remove('active');
    document.getElementById('inpNovaCategoria').value = '';
    document.getElementById('statusAnexoContainer').style.display = 'none';
    removerSelecao();
    registroSelecionado = null;
    document.getElementById('btnAlterar').disabled = true;
    document.getElementById('btnApagar').disabled = true;
    document.getElementById('mainForm').action = "/add";
}

function removerSelecao() {
    document.querySelectorAll('tbody tr').forEach(tr => tr.classList.remove('selected', 'table-active'));
}

// ============================================================================
// 🖱️ MANIPULAÇÃO DA TABELA
// ============================================================================

function selecionarLinhaClick(linha) {
    removerSelecao();
    linha.classList.add('selected', 'table-active');
}

function selecionarLinha(row) {
    try {
        removerSelecao();
        row.classList.add('selected', 'table-active');
        
        const id = row.getAttribute('data-cod');
        if (!id) return;
        
        document.getElementById('cod_registro').value = id;
        registroSelecionado = id;
        
        const preencher = (idInput, dataAttr, isSelect = false) => {
            const campo = document.getElementById(idInput);
            if (!campo) return;
            let valor = row.getAttribute(dataAttr);
            const valorLimpo = (valor && valor !== 'None' && valor !== 'null') ? valor.trim() : '';
            
            if (isSelect && valorLimpo) {
                selecionarOuCriarOption(campo, valorLimpo);
            } else {
                campo.value = valorLimpo;
            }
        };
        
        preencher('inpMesAno', 'data-mes_ano');
        preencher('inpCompetencia', 'data-competencia');
        preencher('inpConta', 'data-conta');
        preencher('inpInst', 'data-instituicao');
        preencher('inpFonte', 'data-fonte_paga');
        preencher('inpParcela', 'data-parcela');
        preencher('inpObs', 'data-observacao');
        preencher('inpJuros', 'data-juros');
        preencher('inpDesconto', 'data-desconto');
        preencher('inpCategoria', 'data-categoria', true);
        
        const tipo = row.getAttribute('data-tipo');
        if (tipo === 'R') document.getElementById('tipoR').checked = true;
        else document.getElementById('tipoD').checked = true;
        atualizarTipoCategoria();
        
        document.getElementById('inpVenc').value = paraISO(row.getAttribute('data-data_venc'));
        document.getElementById('inpDataPago').value = paraISO(row.getAttribute('data-data_pago'));
        
        document.getElementById('inpValPagar').value = paraBR(row.getAttribute('data-valor_pagar'));
        const vPago = row.getAttribute('data-valor_pago');
        document.getElementById('inpValPago').value = parseFloat(vPago || 0) > 0 ? paraBR(vPago) : '';
        
        const temAnexo = row.getAttribute('data-tem-anexo');
        document.getElementById('statusAnexoContainer').style.display = (temAnexo === 'true') ? 'inline-block' : 'none';
        
        document.getElementById('btnAlterar').disabled = false;
        document.getElementById('btnApagar').disabled = false;
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        console.error("Erro ao carregar registro:", error);
    }
}

// ============================================================================
// 💾 OPERAÇÕES CRUD
// ============================================================================

function executarAlteracao() {
    const cod = document.getElementById('cod_registro').value;
    const form = document.getElementById('mainForm');
    if (!cod) {
        alert('Selecione um registro primeiro!');
        return;
    }
    if (confirm("Deseja salvar as alterações?")) {
        form.action = "/alterar";
        form.submit();
    }
}

function confirmarExclusao() {
    if (!registroSelecionado) {
        alert('Selecione um registro!');
        return;
    }
    if (confirm("Tem certeza que deseja excluir permanentemente este registro?")) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = "/apagar";
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'cod';
        input.value = registroSelecionado;
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
}

// ============================================================================
// 📂 DOCUMENTOS E BACKUP
// ============================================================================

function fazerUploadPDF() {
    const fileInput = document.getElementById('fileDocumento');
    const codRegistro = document.getElementById('cod_registro').value;
    const statusDiv = document.getElementById('uploadStatus');
    
    if (!codRegistro) {
        alert('Salve o registro primeiro!');
        return;
    }
    if (!fileInput.files?.length) {
        alert('Selecione um PDF!');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('documento', file);
    statusDiv.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>IA Lendo Boleto...';
    
    fetch(`/upload_documento/${codRegistro}`, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.sucesso) {
            statusDiv.innerHTML = '<span class="text-success"><i class="bi bi-check-circle-fill me-1"></i>IA: Dados Extraídos!</span>';
            
            // Especialista Sênior: Preenchimento Automático (Auto-Fill)
            if (data.ocr) {
                if (data.ocr.valor) document.getElementById('Valor_pagar').value = data.ocr.valor;
                if (data.ocr.vencimento) {
                    // Converte DD/MM/YYYY para YYYY-MM-DD para o input date
                    const partes = data.ocr.vencimento.split('/');
                    if (partes.length === 3) {
                        document.getElementById('Data_venc').value = `${partes[2]}-${partes[1]}-${partes[0]}`;
                    }
                }
                if (data.ocr.conta && !document.getElementById('Conta').value) {
                    document.getElementById('Conta').value = data.ocr.conta;
                }
            }
            
            setTimeout(() => {
                alert("SmartWallet IA: Dados extraídos com sucesso! Verifique os campos antes de confirmar.");
                location.reload();
            }, 1500);
        } else throw new Error(data.erro);
    })
    .catch(err => {
        statusDiv.textContent = 'Erro!';
        alert(err.message);
    });
}

function visualizarAnexoExistente() {
    const row = document.querySelector('tbody tr.selected');
    if (!row) return alert('Selecione um registro!');
    const docId = row.getAttribute('data-doc-id');
    if (docId) window.open(`/visualizar_documento/${docId}`, '_blank');
    else alert('Sem anexo.');
}

function fazerBackupManual() {
    if (!confirm('Deseja criar um backup manual agora?')) return;
    const btn = document.getElementById('btnBackup');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Processando...';
    
    fetch('/api/backup/create', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) alert(data.message);
        else alert('Erro: ' + data.error);
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    });
}

// ============================================================================
// 📊 DASHBOARD E RELATÓRIOS
// ============================================================================

async function atualizarDashboard() {
    try {
        const res = await fetch('/api/dashboard/data');
        const data = await res.json();
        renderizarGraficoCategorias(data.despesas_categoria);
        renderizarGraficoEvolucao(data.evolucao_mensal);
        renderizarGraficoStatus(data.status_pagamentos);
    } catch (err) {
        console.error('Erro dashboard:', err);
    }
}

function renderizarGraficoCategorias(dados) {
    const ctx = document.getElementById('chartCategorias')?.getContext('2d');
    if (!ctx || !dados?.labels?.length) return;
    if (chartCategorias) chartCategorias.destroy();
    
    chartCategorias = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: dados.labels,
            datasets: [{ data: dados.values, backgroundColor: coresCategorias }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderizarGraficoEvolucao(dados) {
    const ctx = document.getElementById('chartEvolucao')?.getContext('2d');
    if (!ctx || !dados?.labels?.length) return;
    if (chartEvolucao) chartEvolucao.destroy();
    
    chartEvolucao = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dados.labels,
            datasets: [
                { label: 'Despesas', data: dados.despesas, backgroundColor: '#dc3545' },
                { label: 'Receitas', data: dados.receitas, backgroundColor: '#28a745' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderizarGraficoStatus(dados) {
    const ctx = document.getElementById('chartStatus')?.getContext('2d');
    if (!ctx || !dados) return;
    if (chartStatus) chartStatus.destroy();
    
    const total = (dados.pago || 0) + (dados.pendente || 0);
    chartStatus = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pago', 'Pendente'],
            datasets: [{ data: [dados.pago, dados.pendente], backgroundColor: ['#28a745', '#dc3545'] }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: R$ ${ctx.parsed.toLocaleString('pt-BR')}`
                    }
                }
            }
        }
    });
}

async function carregarRankingMensal() {
    const mesAno = document.getElementById('inputMesRanking')?.value;
    if (!mesAno) return;
    const [ano, mes] = mesAno.split('-');
    try {
        const res = await fetch(`/api/dashboard/ranking_mensal?mes_ano=${mes}/${ano}`);
        const data = await res.json();
        renderizarRankingMensal(data);
    } catch (err) { console.error(err); }
}

function limparRanking() {
    const input = document.getElementById('inputMesRanking');
    if (input) input.value = '';
    if (chartRankingMensal) {
        chartRankingMensal.destroy();
        chartRankingMensal = null;
    }
    // Opcional: recarrega com dados vazios ou padrão
    const ctx = document.getElementById('graficoRankingMensal')?.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

function renderizarRankingMensal(dados) {
    const ctx = document.getElementById('graficoRankingMensal')?.getContext('2d');
    if (!ctx || !dados?.ranking?.length) return;
    if (chartRankingMensal) chartRankingMensal.destroy();
    
    chartRankingMensal = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dados.ranking.map(i => i.conta),
            datasets: [{ label: 'Valor', data: dados.ranking.map(i => i.valor), backgroundColor: '#3498db' }]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false }
    });
}

function carregarProjecoesIA() {
    const container = document.getElementById('containerIA');
    const content = document.getElementById('iaInsightsContent');
    if (!container || !content) return;
    
    container.style.display = 'block';
    content.innerHTML = '<div class="col-12 text-center py-4"><div class="spinner-border text-primary"></div><p class="mt-2">Analisando padrões históricos...</p></div>';
    
    fetch('/api/dashboard/ia-projections')
    .then(res => res.json())
    .then(data => {
        if (!data.sucesso) throw new Error(data.error);
        
        let html = `
            <div class="col-md-4 border-end">
                <h6 class="fw-bold mb-3"><i class="bi bi-graph-up me-2 text-primary"></i>Tendência 90 Dias</h6>
                <ul class="list-unstyled">
                    ${data.projecoes.map(p => `
                        <li class="d-flex justify-content-between mb-2 border-bottom pb-1">
                            <span>${p.mes}</span>
                            <span class="fw-bold text-success">R$ ${p.saldo_acumulado.toLocaleString('pt-BR')}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
            <div class="col-md-4 border-end">
                <h6 class="fw-bold mb-3"><i class="bi bi-pie-chart me-2 text-info"></i>Análise de Custos</h6>
                <div class="text-center">
                    <h2 class="mb-0 fw-bold">${data.custo_fixed_percentual || data.custo_fixo_percentual}%</h2>
                    <p class="text-muted small">Comprometimento com Custos Fixos</p>
                    <div class="progress" style="height: 10px;">
                        <div class="progress-bar" style="width: ${data.custo_fixo_percentual}%"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <h6 class="fw-bold mb-3"><i class="bi bi-lightbulb me-2 text-warning"></i>Insights da IA</h6>
                ${data.insights.map(i => `
                    <div class="alert alert-${i.tipo} py-2 mb-2 small d-flex align-items-center">
                        <i class="bi ${i.icon} me-2 fs-5"></i>
                        <span>${i.texto}</span>
                    </div>
                `).join('')}
            </div>
        `;
        content.innerHTML = html;
    })
    .catch(err => {
        content.innerHTML = `<div class="col-12 alert alert-danger">Erro na análise: ${err.message}</div>`;
    });
}

function gerarRelatorio(tipo) {
    const mesAno = document.getElementById('inpMesAno').value;
    const conta = document.getElementById('inpConta').value;
    let url = `/gerar_pdf?tipo=${tipo}`;
    
    if (tipo === 'receita_despesa') {
        const ano = mesAno.includes('/') ? mesAno.split('/')[1] : new Date().getFullYear();
        return window.open(`/gerar_relatorio_anual?ano=${ano}`, '_blank');
    }
    if (tipo === 'anual') {
        if (!mesAno.includes('/')) return alert('Preencha MM/AAAA');
        url = `/gerar_pdf?tipo=anual&relatorio_ano=${mesAno.split('/')[1]}`;
    }
    if (tipo === 'conta') {
        if (!conta) return alert('Informe a conta');
        url += `&relatorio_conta=${encodeURIComponent(conta)}&relatorio_ano=${mesAno.split('/')[1]}`;
    } else if (mesAno) {
        url += `&MesAno=${encodeURIComponent(mesAno)}`;
    }
    window.open(url, '_blank');
}

// ============================================================================
// 📧 CONFIGURAÇÕES DE E-MAIL
// ============================================================================

function abrirConfigEmail() {
    const modalEl = document.getElementById('modalConfigEmail');
    if (!modalEl) return;
    const modal = new bootstrap.Modal(modalEl);
    fetch('/api/config/email')
    .then(res => res.json())
    .then(data => {
        if (data.sucesso) {
            document.getElementById('inpEmailNotificacao').value = data.config.email_destino || '';
            document.getElementById('chkAtivarAlertas').checked = data.config.alertas_ativos !== false;
            document.getElementById('chkAtivarBackup').checked = data.config.backup_ativos !== false;
        }
        modal.show();
    });
}

function salvarConfigEmail() {
    const email = document.getElementById('inpEmailNotificacao').value;
    const data = {
        email: email,
        alertas_ativos: document.getElementById('chkAtivarAlertas').checked,
        backup_ativos: document.getElementById('chkAtivarBackup').checked
    };
    fetch('/api/config/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(res => {
        if (res.sucesso) {
            alert('Configuração salva!');
            bootstrap.Modal.getInstance(document.getElementById('modalConfigEmail'))?.hide();
        }
    });
}

function verificarCategoriaOutros() {
    const select = document.getElementById('inpCategoria');
    const container = document.getElementById('categoriaCustomContainer');
    if (select.value === 'Outros') {
        container.classList.add('active');
        document.getElementById('inpNovaCategoria').focus();
    } else {
        container.classList.remove('active');
    }
}

function confirmarNovaCategoria() {
    const input = document.getElementById('inpNovaCategoria');
    const nome = input.value.trim().toUpperCase();
    if (nome.length < 3) return alert('Mínimo 3 letras');
    
    document.getElementById('nova_categoria').value = nome;
    document.getElementById('tipo_nova_categoria').value = document.getElementById('tipoR').checked ? 'R' : 'D';
    
    const select = document.getElementById('inpCategoria');
    const opt = new Option(nome, nome, true, true);
    select.insertBefore(opt, select.lastElementChild);
    document.getElementById('categoriaCustomContainer').classList.remove('active');
}

// ============================================================================
// 🚀 INICIALIZAÇÃO
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    filtrarCategoriasPorTipo();
    atualizarDashboard();
    carregarRankingMensal();
    
    document.querySelectorAll('input[name="ReceitaDespesa"]').forEach(r => {
        r.addEventListener('change', () => {
            filtrarCategoriasPorTipo();
            atualizarTipoCategoria();
        });
    });
    
    const select = document.getElementById('inpCategoria');
    if (select) {
        select.addEventListener('change', sincronizarBotaoPorCategoria);
        if (select.value) setTimeout(sincronizarBotaoPorCategoria, 150);
    }
});

function lancarMesSeguinte() {
    const mesAtual = document.getElementById('inpMesAno')?.value;
    if (!mesAtual || !mesAtual.includes('/')) {
        alert('Por favor, selecione um Mês/Ano (MM/AAAA) para servir de base.');
        return;
    }
    
    const [mes, ano] = mesAtual.split('/').map(Number);
    let proxMes = mes + 1;
    let proxAno = ano;
    if (proxMes > 12) {
        proxMes = 1;
        proxAno++;
    }
    const mesDestino = `${proxMes.toString().padStart(2, '0')}/${proxAno}`;
    
    if (confirm(`Deseja copiar todos os lançamentos de despesa de ${mesAtual} para ${mesDestino}?`)) {
        fetch('/api/recorrencia/copiar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({origem: mesAtual, destino: mesDestino})
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.href = `/?MesAno=${mesDestino}`;
            } else {
                alert('Erro: ' + data.error);
            }
        })
        .catch(err => {
            console.error(err);
            alert('Erro de conexão ao processar recorrência.');
        });
    }
}
