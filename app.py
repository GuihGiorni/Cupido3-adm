from flask import Flask, render_template_string, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'banco_dados.json'

ESTOQUE_INICIAL = {
    "vendas": [],
    "estoque": {
        "Carta Normal": 390,
        "Carta + Pirulito": 50,
        "Carta + Bombom": 50,
        "Anel de plástico": 48,
        "Serenata": "Infinita"
    }
}

def carregar_dados():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(ESTOQUE_INICIAL, f, ensure_ascii=False, indent=4)
        return ESTOQUE_INICIAL
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/api/dados', methods=['GET'])
def obter_dados():
    return jsonify(carregar_dados())

@app.route('/api/venda', methods=['POST'])
def registrar_venda():
    req = request.json
    dados = carregar_dados()
    
    produto = req.get('produto')
    qtd = int(req.get('quantidade', 1))
    adicional_anel = req.get('anel') == 'Sim'
    envio = req.get('envio')
    
    pode_revelar_inicial = "Sim" if envio == "Revelado" else "Não"
    if produto == "Revelar":
        pode_revelar_inicial = "Sim (Pago)"

    itens_para_descontar = []
    if produto == "Carta Normal":
        itens_para_descontar.append("Carta Normal")
    elif produto == "Carta Pirulito":
        itens_para_descontar.append("Carta Normal")
        itens_para_descontar.append("Carta + Pirulito")
    elif produto == "Carta Bombom":
        itens_para_descontar.append("Carta Normal")
        itens_para_descontar.append("Carta + Bombom")
    elif produto in dados['estoque'] and dados['estoque'][produto] not in ["Infinita", "Infinito"]:
        itens_para_descontar.append(produto)

    for item in itens_para_descontar:
        if dados['estoque'][item] < qtd:
            return jsonify({"status": "erro", "mensagem": f"Estoque insuficiente de {item}!"}), 400
            
    if adicional_anel:
        if dados['estoque']['Anel de plástico'] < qtd:
            return jsonify({"status": "erro", "mensagem": "Estoque insuficiente de Anel de plástico!"}), 400
            
    for item in itens_para_descontar:
        dados['estoque'][item] -= qtd
        
    if adicional_anel:
        dados['estoque']['Anel de plástico'] -= qtd
    
    nova_venda = {
        "id": len(dados['vendas']) + 1,
        "horario": datetime.now().strftime("%H:%M"),
        "remetente": req.get('remetente') or "Anônimo",
        "destinatario": req.get('destinatario') or "Geral",
        "produto": produto,
        "quantidade": qtd,
        "envio": envio,
        "pode_revelar": pode_revelar_inicial,
        "caracteristicas": req.get('caracteristicas') or "Não informada",
        "anel_adicional": adicional_anel,
        "saiu_entrega": "Não"
    }
    
    dados['vendas'].append(nova_venda)
    salvar_dados(dados)
    return jsonify({"status": "sucesso"})

@app.route('/api/atualizar_status', methods=['POST'])
def atualizar_status():
    req = request.json
    venda_id = int(req.get('id'))
    novo_status = req.get('pode_revelar')
    
    dados = carregar_dados()
    for v in dados['vendas']:
        if v['id'] == venda_id:
            v['pode_revelar'] = novo_status
            break
            
    salvar_dados(dados)
    return jsonify({"status": "sucesso"})

@app.route('/api/atualizar_entrega', methods=['POST'])
def atualizar_entrega():
    req = request.json
    venda_id = int(req.get('id'))
    novo_status = req.get('saiu_entrega')
    
    dados = carregar_dados()
    for v in dados['vendas']:
        if v['id'] == venda_id:
            v['saiu_entrega'] = novo_status
            break
            
    salvar_dados(dados)
    return jsonify({"status": "sucesso"})

# NOVA ROTA: Excluir venda e devolver ao estoque
@app.route('/api/excluir_venda', methods=['POST'])
def excluir_venda():
    req = request.json
    venda_id = int(req.get('id'))
    
    dados = carregar_dados()
    
    # Busca a venda pelo ID
    venda_para_excluir = None
    for v in dados['vendas']:
        if v['id'] == venda_id:
            venda_para_excluir = v
            break
            
    if not venda_para_excluir:
        return jsonify({"status": "erro", "mensagem": "Pedido não encontrado!"}), 404

    produto = venda_para_excluir['produto']
    qtd = int(venda_para_excluir['quantidade'])
    adicional_anel = venda_para_excluir.get('anel_adicional', False)
    
    # Refaz a lógica de devolução
    itens_para_devolver = []
    if produto == "Carta Normal":
        itens_para_devolver.append("Carta Normal")
    elif produto == "Carta Pirulito":
        itens_para_devolver.append("Carta Normal")
        itens_para_devolver.append("Carta + Pirulito")
    elif produto == "Carta Bombom":
        itens_para_devolver.append("Carta Normal")
        itens_para_devolver.append("Carta + Bombom")
    elif produto in dados['estoque'] and dados['estoque'][produto] not in ["Infinita", "Infinito"]:
        itens_para_devolver.append(produto)
        
    # Devolve para o estoque
    for item in itens_para_devolver:
        if item in dados['estoque'] and dados['estoque'][item] not in ["Infinita", "Infinito"]:
            dados['estoque'][item] += qtd
            
    if adicional_anel:
        dados['estoque']['Anel de plástico'] += qtd

    # Remove a venda da lista
    dados['vendas'] = [v for v in dados['vendas'] if v['id'] != venda_id]
    
    salvar_dados(dados)
    return jsonify({"status": "sucesso"})


HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Correio Elegante - Painel Operacional</title>
    <style>
        :root {
            --cor-fundo: #FFF0F2;
            --cor-primaria: #D62828;
            --cor-secundaria: #FF4D6D;
            --cor-card: #FFFFFF;
            --cor-texto: #2B2D42;
        }
        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; }
        body { background-color: var(--cor-fundo); color: var(--cor-texto); padding-bottom: 40px; }
        
        header { background: linear-gradient(135deg, var(--cor-primaria), var(--cor-secundaria)); color: white; text-align: center; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        header h1 { font-size: 1.5rem; }

        .Abas-container { display: flex; justify-content: center; background-color: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.05); flex-wrap: wrap; }
        .aba-btn { background: none; border: none; padding: 12px 15px; font-size: 0.9rem; font-weight: bold; color: #666; cursor: pointer; transition: all 0.3s; border-bottom: 4px solid transparent; flex: 1; text-align: center; min-width: 100px; }
        .aba-btn:hover { color: var(--cor-secundaria); }
        .aba-btn.ativa { color: var(--cor-primaria); border-bottom-color: var(--cor-primaria); }

        .conteudo { max-width: 1100px; margin: 25px auto; padding: 0 15px; }
        .tela { display: none; }
        .tela.ativa { display: block; }

        .card { background: var(--cor-card); padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .titulo-secao { border-bottom: 2px solid var(--cor-fundo); padding-bottom: 10px; margin-bottom: 20px; color: var(--cor-primaria); }
        
        .grid-form { display: grid; grid-template-columns: 1fr; gap: 15px; }
        @media (min-width: 768px) {
            .grid-form { grid-template-columns: 1fr 1fr; }
        }
        .campo { display: flex; flex-direction: column; }
        .campo.cheio { grid-column: 1 / -1; }
        label { font-weight: 600; margin-bottom: 8px; color: #4A4A4A; font-size: 0.9rem; }
        input, select, textarea { padding: 12px; border: 2px solid #E0E0E0; border-radius: 8px; font-size: 1rem; outline: none; width: 100%; }
        input:focus, select:focus, textarea:focus { border-color: var(--cor-secundaria); }
        
        .checkbox-container { display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: bold; margin-top: 5px; }
        .checkbox-container input { width: 22px; height: 22px; }

        .btn-sucesso { background-color: #2D6A4F; color: white; border: none; padding: 15px; font-size: 1.1rem; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; margin-top: 10px; }
        .btn-sucesso:hover { background-color: #1B4332; }

        .barra-filtros { display: flex; flex-direction: column; gap: 10px; margin-bottom: 15px; background: #fdfdfd; padding: 10px; border-radius: 8px; border: 1px solid #ddd; }
        @media (min-width: 768px) {
            .barra-filtros { flex-direction: row; align-items: center; }
        }
        .btn-filtro { background: #e0e0e0; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; }
        @media (min-width: 768px) { .btn-filtro { width: auto; } }
        
        .tabela-container { overflow-x: auto; -webkit-overflow-scrolling: touch; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: white; min-width: 600px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #EEEEEE; font-size: 0.9rem; }
        th { background-color: var(--cor-primaria); color: white; font-weight: 600; }
        
        .select-status { padding: 5px; border-radius: 4px; font-weight: bold; border: 1px solid #ccc; width: 100%; }
        .status-nao { background-color: #FEE2E2; color: #991B1B; }
        .status-sim { background-color: #D8F3DC; color: #1B4332; }
        .status-pago { background-color: #E0F2FE; color: #0369A1; }
        .status-entrega-nao { background-color: #FFF3CD; color: #856404; }
        .status-entrega-sim { background-color: #D1E7DD; color: #0F5132; }

        .btn-excluir { background-color: #FEE2E2; border: 1px solid #EF4444; color: #991B1B; padding: 6px 10px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: 0.2s; }
        .btn-excluir:hover { background-color: #FCA5A5; color: white; }

        .grid-estoque { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }
        .card-estoque { background: #fff; padding: 15px; border-radius: 10px; border-left: 5px solid var(--cor-secundaria); text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .card-estoque.alerta { border-left-color: var(--cor-primaria); background-color: #FFF5F5; }
        .card-estoque h4 { font-size: 0.85rem; color: #666; margin-bottom: 5px; }
        .card-estoque p { font-size: 1.5rem; font-weight: bold; }
    </style>
</head>
<body>

    <header>
        <h1>💘 Correio Elegante 3ºC ADM </h1>
    </header>

    <div class="Abas-container">
        <button class="aba-btn ativa" onclick="mudarAba('registrar')">📝 Vender</button>
        <button class="aba-btn" onclick="mudarAba('historico')">📋 Histórico</button>
        <button class="aba-btn" onclick="mudarAba('estoque')">📊 Estoque</button>
    </div>

    <div class="conteudo">

        <div id="tela-registrar" class="tela ativa">
            <div class="card">
                <div class="titulo-secao"><h2>Lançar Novo Pedido </h2></div>
                <form id="form-venda" onsubmit="salvarVenda(event)" class="grid-form">
                    <div class="campo">
                        <label for="produto">O que comprou?</label>
                        <select id="produto" required>
                            <option value="Carta Normal">Carta Normal</option>
                            <option value="Carta Pirulito">Carta Pirulito</option>
                            <option value="Carta Bombom">Carta Bombom</option>
                            <option value="Serenata">Serenata</option>
                            <option value="Revelar">Apenas Revelar (R$ 3,00)</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label for="quantidade">Quantidade:</label>
                        <input type="number" id="quantidade" value="1" min="1" required>
                    </div>
                    <div class="campo">
                        <label for="envio">Como será o Envio?</label>
                        <select id="envio" required>
                            <option value="Anônimo">Anônimo (Só descobre se pagar)</option>
                            <option value="Revelado">Revelado (Cupido fala na hora)</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label for="remetente">De (Remetente):</label>
                        <input type="text" id="remetente" placeholder="Nome ou Anônimo">
                    </div>

                    <div class="campo cheio">
                        <label for="destinatario">Para (Destinatário e Sala/Local):</label>
                        <input type="text" id="destinatario" placeholder="Ex: João - 2º Info">
                    </div>
                    <div class="campo cheio">
                        <label for="caracteristicas">Características físicas do Remetente:</label>
                        <textarea id="caracteristicas" rows="2" placeholder="Ex: Moletom verde, óculos..."></textarea>
                    </div>
                    <div class="campo cheio">
                        <label class="checkbox-container">
                            <input type="checkbox" id="anel"> 💍 Adicionar Anel de Plástico?
                        </label>
                    </div>
                    <div class="campo cheio">
                        <button type="submit" class="btn-sucesso">Confirmar Registro 🚀</button>
                    </div>
                </form>
            </div>
        </div>

        <div id="tela-historico" class="tela">
            <div class="card">
                <div class="titulo-secao"><h2>Fila e Histórico</h2></div>
                
                <div class="barra-filtros">
                    <div style="display:flex; gap:5px; width:100%;">
                        <button class="btn-filtro" onclick="ordenarHistorico('horario')">🕒 Hora</button>
                        <button class="btn-filtro" onclick="ordenarHistorico('produto')">📦 Prod</button>
                    </div>
                    <input type="text" id="busca-historico" oninput="filtrarHistorico()" placeholder="🔎 Buscar Destinatário..." style="width:100%;">
                </div>

                <div class="tabela-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Ação</th>
                                <th>Hora</th>
                                <th>Para Quem?</th>
                                <th>Produto</th>
                                <th>Status Entrega</th>
                                <th>Remetente</th>
                                <th>Revelar?</th>
                                <th>Características</th>
                            </tr>
                        </thead>
                        <tbody id="corpo-tabela-historico"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="tela-estoque" class="tela">
            <div class="card">
                <div class="titulo-secao"><h2>Estoque Disponível Atual</h2></div>
                <div class="grid-estoque" id="cards-estoque"></div>
            </div>
            
            <div class="card" style="border-left: 5px solid #2D6A4F;">
                <div class="titulo-secao"><h2>Relatório de Vendas</h2></div>
                <div class="tabela-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Item / Serviço</th>
                                <th>Total Distribuído</th>
                            </tr>
                        </thead>
                        <tbody id="corpo-tabela-relatorio"></tbody>
                    </table>
                </div>
            </div>
        </div>

    </div>

    <script>
        let dadosGlobais = { vendas: [], estoque: {} };
        let ordenacaoAtual = 'id';

        function mudarAba(nomeAba) {
            document.querySelectorAll('.tela').forEach(t => t.classList.remove('ativa'));
            document.querySelectorAll('.aba-btn').forEach(b => b.classList.remove('ativa'));
            document.getElementById('tela-' + nomeAba).classList.add('ativa');
            if (event && event.target) event.target.classList.add('ativa');
            atualizarDados();
        }

        function atualizarDados() {
            fetch('/api/dados')
            .then(res => res.json())
            .then(data => {
                dadosGlobais = data;
                renderizarEstoque();
                renderizarHistorico();
                renderizarRelatorio();
            });
        }

        function renderizarEstoque() {
            const container = document.getElementById('cards-estoque');
            container.innerHTML = '';
            for (const [item, qtd] of Object.entries(dadosGlobais.estoque)) {
                const alerta = (qtd !== "Infinita" && qtd !== "Infinito" && parseInt(qtd) <= 10) ? 'alerta' : '';
                container.innerHTML += `
                    <div class="card-estoque ${alerta}">
                        <h4>${item}</h4>
                        <p>${qtd}</p>
                    </div>
                `;
            }
        }

        function renderizarHistorico() {
            const corpo = document.getElementById('corpo-tabela-historico');
            corpo.innerHTML = '';
            
            let listaFormatada = [...dadosGlobais.vendas];
            
            if (ordenacaoAtual === 'horario') {
                listaFormatada.sort((a,b) => b.horario.localeCompare(a.horario));
            } else if (ordenacaoAtual === 'produto') {
                listaFormatada.sort((a,b) => a.produto.localeCompare(b.produto));
            }

            listaFormatada.forEach(v => {
                let classeSelect = 'status-nao';
                if(v.pode_revelar === 'Sim') classeSelect = 'status-sim';
                if(v.pode_revelar === 'Sim (Pago)') classeSelect = 'status-pago';
                
                let statusEntrega = v.saiu_entrega || 'Não';
                let classeEntrega = statusEntrega === 'Sim' ? 'status-entrega-sim' : 'status-entrega-nao';

                corpo.innerHTML += `
                    <tr class="linha-historico" data-destinatario="${v.destinatario.toLowerCase()}">
                        <td>
                            <button class="btn-excluir" onclick="excluirPedido(${v.id})" title="Excluir este pedido">🗑️</button>
                        </td>
                        <td><strong>${v.horario}</strong></td>
                        <td><mark style="background-color: #FFE3E8; padding:2px 5px; border-radius:4px; font-weight:bold;">${v.destinatario}</mark></td>
                        <td>${v.produto} (x${v.quantidade}) ${v.anel_adicional ? '💍' : ''}</td>
                        <td>
                            <select class="select-status ${classeEntrega}" onchange="mudarStatusEntrega(${v.id}, this.value)">
                                <option value="Não" ${statusEntrega === 'Não'?'selected':''}>⏳ Pendente</option>
                                <option value="Sim" ${statusEntrega === 'Sim'?'selected':''}>✅ Entregue</option>
                            </select>
                        </td>
                        <td>${v.remetente}</td>
                        <td>
                            <select class="select-status ${classeSelect}" onchange="mudarStatusVenda(${v.id}, this.value)">
                                <option value="Não" ${v.pode_revelar === 'Não'?'selected':''}>Não</option>
                                <option value="Sim" ${v.pode_revelar === 'Sim'?'selected':''}>Sim</option>
                                <option value="Sim (Pago)" ${v.pode_revelar === 'Sim (Pago)'?'selected':''}>Sim (Pago)</option>
                            </select>
                        </td>
                        <td>${v.caracteristicas}</td>
                    </tr>
                `;
            });
        }

        function renderizarRelatorio() {
            const corpo = document.getElementById('corpo-tabela-relatorio');
            corpo.innerHTML = '';
            
            let contagem = {
                "Carta Normal": 0, "Carta Pirulito": 0, "Carta Bombom": 0,
                "Serenata": 0, "Anel de plástico": 0, "Revelar": 0
            };

            dadosGlobais.vendas.forEach(v => {
                if (v.produto in contagem) {
                    contagem[v.produto] += v.quantidade;
                }
                if (v.anel_adicional) {
                    contagem["Anel de plástico"] += v.quantidade;
                }
            });

            for (const [item, total] of Object.entries(contagem)) {
                corpo.innerHTML += `
                    <tr>
                        <td><strong>${item}</strong></td>
                        <td>${total} und.</td>
                    </tr>
                `;
            }
        }

        function mudarStatusVenda(id, novoStatus) {
            fetch('/api/atualizar_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id, pode_revelar: novoStatus})
            }).then(() => atualizarDados());
        }

        function mudarStatusEntrega(id, novoStatus) {
            fetch('/api/atualizar_entrega', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id, saiu_entrega: novoStatus})
            }).then(() => atualizarDados());
        }

        function excluirPedido(id) {
            if(confirm("Tem certeza que deseja apagar este pedido? Os itens voltarão automaticamente para o estoque.")) {
                fetch('/api/excluir_venda', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: id})
                })
                .then(res => res.json())
                .then(data => {
                    if(data.status === "sucesso") {
                        alert("🗑️ Pedido excluído e itens devolvidos ao estoque!");
                        atualizarDados();
                    } else {
                        alert("Erro: " + data.mensagem);
                    }
                })
                .catch(err => alert("Erro ao excluir pedido."));
            }
        }

        function ordenarHistorico(campo) {
            ordenacaoAtual = campo;
            renderizarHistorico();
        }

        function filtrarHistorico() {
            const termo = document.getElementById('busca-historico').value.toLowerCase();
            document.querySelectorAll('.linha-historico').forEach(linha => {
                const dest = linha.getAttribute('data-destinatario');
                linha.style.display = dest.includes(termo) ? '' : 'none';
            });
        }

        function salvarVenda(e) {
            e.preventDefault();
            const dados = {
                produto: document.getElementById('produto').value,
                quantidade: document.getElementById('quantidade').value,
                envio: document.getElementById('envio').value,
                remetente: document.getElementById('remetente').value,
                destinatario: document.getElementById('destinatario').value,
                caracteristicas: document.getElementById('caracteristicas').value,
                anel: document.getElementById('anel').checked ? "Sim" : "Não"
            };

            fetch('/api/venda', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(dados)
            })
            .then(res => {
                if(!res.ok) return res.json().then(err => { throw new Error(err.mensagem) });
                return res.json();
            })
            .then(() => {
                alert('🚀 Lançamento registrado com sucesso!');
                document.getElementById('form-venda').reset();
                atualizarDados();
            })
            .catch(err => alert(err.message));
        }

        atualizarDados();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
