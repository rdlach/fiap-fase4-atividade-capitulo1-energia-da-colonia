"""
=====================================================================
 SIGIC - Sistema Inteligente de Gerenciamento da Infraestrutura
         da Colônia Aurora Siger (Marte)
 FIAP - Fase 4 - Atividade em equipe
=====================================================================

ARQUIVO PRINCIPAL DO SISTEMA.

Como executar (somente biblioteca padrão do Python 3.8+):
    python codigo_fonte.py            -> abre o menu interativo
    python codigo_fonte.py --demo     -> executa todas as funções com
                                         exemplos e mostra os resultados

Organização do código:
    1. Dados da colônia (tuplas, listas e dicionários)
    2. Construção do grafo (lista de adjacência e matriz de adjacência)
    3. Algoritmos de redes (BFS, DFS, Dijkstra, conexões críticas)
    4. Análise de eficiência e otimização de rotas
    5. Simulações operacionais (falhas, manutenção, crise, tempestade,
       expansão)
    6. Modelagem matemática (perda energética e crescimento do consumo)
    7. Interface de terminal (menus, entradas e saídas)
"""

import csv
import math
from itertools import combinations
import os
import sys
from contextlib import redirect_stdout

# Evita erros com acentos em terminais que não usam UTF-8 por padrão.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (ValueError, OSError):
        pass

# Pasta onde o sistema grava relatórios e exportações.
PASTA_AUXILIAR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "arquivos_auxiliares")

INF = float("inf")  # Representa "sem caminho" nos algoritmos.


# =====================================================================
# 1. DADOS DA COLÔNIA
# =====================================================================

# TUPLA com a ordem dos campos fixos de cada módulo. Como a estrutura de
# um módulo não muda durante a execução, a tupla (imutável) protege
# essas informações contra alterações acidentais.
CAMPOS_MODULO = ("sigla", "nome", "consumo_kw", "prioridade",
                 "capacidade_kwh", "comunicacao_msg_min", "descricao")

# LISTA DE TUPLAS com os dados fixos dos 8 módulos da base.
#   consumo_kw          -> potência média exigida pelo módulo (kW)
#   prioridade          -> 1 = crítica (sobrevivência) ... 4 = baixa
#   capacidade_kwh      -> energia que o módulo consegue armazenar (kWh)
#   comunicacao_msg_min -> necessidade de comunicação (mensagens/minuto)
MODULOS_BASE = [
    ("AE", "Armazenamento de Energia", 5.0, 1, 2000.0, 30,
     "Banco de baterias que recebe a energia gerada e distribui para a base."),
    ("CC", "Centro de Controle", 12.0, 2, 40.0, 120,
     "Monitora sensores, coordena operações e executa o SIGIC."),
    ("H", "Habitação", 18.0, 1, 50.0, 40,
     "Acomodação da tripulação e suporte básico à vida (pressão e calor)."),
    ("AG", "Agricultura", 22.0, 3, 30.0, 20,
     "Estufas hidropônicas para produção de alimentos e reciclagem de CO2."),
    ("LC", "Laboratório Científico", 15.0, 4, 25.0, 60,
     "Pesquisa e análise de amostras do solo e da atmosfera marciana."),
    ("CM", "Comunicação", 10.0, 2, 20.0, 150,
     "Antena de longo alcance e roteamento de dados entre módulos e Terra."),
    ("SM", "Suporte Médico", 9.0, 1, 35.0, 50,
     "Atendimento médico e monitoramento da saúde da tripulação."),
    ("PO", "Produção de Oxigênio", 25.0, 1, 60.0, 30,
     "Eletrólise e extração de O2 a partir do CO2 e do gelo marciano."),
]

# DICIONÁRIO sigla -> tupla. Permite acesso direto (O(1)) aos dados de
# um módulo a partir da sua sigla, sem percorrer a lista.
MODULOS = {m[0]: m for m in MODULOS_BASE}

# LISTA com a ordem oficial dos vértices. Ela define o índice de cada
# módulo nas linhas e colunas da matriz de adjacência.
ORDEM = [m[0] for m in MODULOS_BASE]

# DICIONÁRIO com o status operacional (dado que MUDA durante a execução,
# por isso não fica na tupla).
STATUS_VALIDOS = ("ativo", "em alerta", "em manutenção", "falha")
status_modulos = {sigla: "ativo" for sigla in ORDEM}

# LISTA DE TUPLAS com as conexões (arestas) da rede:
#   (origem, destino, distância em metros, resistência do cabo em ohm/m,
#    latência de transmissão de dados em ms)
# A resistência por metro varia porque os cabos têm idades e tipos
# diferentes (o cabo H-SM é o mais antigo e está degradado pela poeira).
# Todos os valores numéricos da colônia são hipotéticos (simulação).
CONEXOES_BASE = [
    ("AE", "CC", 40, 0.0008, 3),
    ("AE", "PO", 35, 0.0008, 3),
    ("AE", "H", 60, 0.0008, 4),
    ("AE", "AG", 70, 0.0010, 5),
    ("CC", "H", 45, 0.0008, 2),
    ("CC", "LC", 55, 0.0008, 2),
    ("CC", "CM", 80, 0.0006, 1),   # fibra dedicada até a antena
    ("CC", "SM", 60, 0.0008, 2),
    ("H", "SM", 30, 0.0015, 3),    # cabo antigo, maior perda
    ("H", "PO", 40, 0.0008, 4),
    ("PO", "AG", 45, 0.0008, 4),
    ("AG", "LC", 65, 0.0010, 5),
]

# DICIONÁRIO com os critérios de peso que podem ser usados nas rotas.
CRITERIOS = {
    "distancia": ("Distância", "m"),
    "perda": ("Resistência elétrica (proxy de perda)", "mΩ"),
    "latencia": ("Latência de comunicação", "ms"),
}

# LISTA DE TUPLAS com as fontes de geração de energia (nome, kW).
FONTES_GERACAO = [
    ("Painéis solares", 120.0),
    ("Turbinas eólicas", 20.0),
    ("Reator compacto de fissão", 40.0),
]

TENSAO_NOMINAL_V = 400.0       # Tensão de distribuição da rede (V)
CARGA_INICIAL_BATERIA = 0.70   # Fração da capacidade do AE carregada
ORIGEM_ENERGIA = "AE"          # Módulo que distribui energia

NOMES_PRIORIDADE = {1: "Crítica", 2: "Alta", 3: "Média", 4: "Baixa"}


# ---------------------------------------------------------------------
# Funções de acesso aos dados de um módulo (desempacotam a tupla)
# ---------------------------------------------------------------------
def nome(sigla):
    return MODULOS[sigla][1]


def consumo(sigla):
    return MODULOS[sigla][2]


def prioridade(sigla):
    return MODULOS[sigla][3]


def capacidade(sigla):
    return MODULOS[sigla][4]


def comunicacao(sigla):
    return MODULOS[sigla][5]


def nivel_comunicacao(sigla):
    """Classifica a necessidade de comunicação em alta, média ou baixa."""
    msg = comunicacao(sigla)
    if msg >= 100:
        return "alta"
    if msg >= 40:
        return "média"
    return "baixa"


def rotulo(sigla):
    return f"{nome(sigla)} ({sigla})"


def geracao_total(fator_solar=1.0):
    """Soma a potência das fontes; fator_solar reduz a geração solar."""
    total = 0.0
    for fonte, potencia in FONTES_GERACAO:
        if fonte == "Painéis solares":
            total += potencia * fator_solar
        else:
            total += potencia
    return total


# =====================================================================
# 2. CONSTRUÇÃO DO GRAFO
# =====================================================================
def esta_operando(status):
    """Módulos em manutenção ou em falha não recebem nem repassam energia."""
    return status in ("ativo", "em alerta")


def construir_grafo(status=None, conexoes=None):
    """
    Monta a LISTA DE ADJACÊNCIA do grafo (não direcionado e ponderado).

    Formato: dicionário {vértice: [(vizinho, {pesos}), ...]}
    Cada aresta guarda os três pesos possíveis: distância (m),
    perda (resistência em mΩ) e latência (ms).
    Módulos parados (manutenção/falha) ficam de fora do grafo.
    """
    if status is None:
        status = status_modulos
    if conexoes is None:
        conexoes = CONEXOES_BASE

    grafo = {s: [] for s in ORDEM if esta_operando(status[s])}
    for origem, destino, dist, r_ohm_m, lat in conexoes:
        if origem in grafo and destino in grafo:
            pesos = {
                "distancia": dist,
                "perda": round(dist * r_ohm_m * 1000, 1),  # mΩ
                "latencia": lat,
                "resistencia_ohm": dist * r_ohm_m,
            }
            grafo[origem].append((destino, pesos))
            grafo[destino].append((origem, pesos))  # não direcionado
    return grafo


def matriz_adjacencia(grafo, criterio=None):
    """
    Gera a MATRIZ DE ADJACÊNCIA (lista de listas) seguindo a ORDEM.
    criterio=None -> matriz binária (1 = existe conexão, 0 = não existe)
    criterio="distancia"/"perda"/"latencia" -> matriz de pesos
    """
    vertices = [v for v in ORDEM if v in grafo]
    indice = {v: i for i, v in enumerate(vertices)}
    n = len(vertices)
    matriz = [[0] * n for _ in range(n)]
    for u in vertices:
        for v, pesos in grafo[u]:
            matriz[indice[u]][indice[v]] = 1 if criterio is None else pesos[criterio]
    return vertices, matriz


def lista_arestas(grafo):
    """Lista de tuplas (u, v, pesos) sem repetição de arestas."""
    arestas = []
    vistos = set()
    for u in grafo:
        for v, pesos in grafo[u]:
            chave = tuple(sorted((u, v)))
            if chave not in vistos:
                vistos.add(chave)
                arestas.append((u, v, pesos))
    return arestas


def peso_aresta(grafo, u, v, criterio):
    for vizinho, pesos in grafo[u]:
        if vizinho == v:
            return pesos[criterio]
    return INF


# =====================================================================
# 3. ALGORITMOS DE REDES
# =====================================================================
def bfs(grafo, origem):
    """
    BUSCA EM LARGURA: visita a rede "por camadas" a partir da origem.
    Retorna a ordem de visita, o nível (nº de saltos) de cada módulo e o
    pai de cada vértice (permite reconstruir a rota com menos saltos).
    Complexidade: O(V + E).
    """
    ordem = [origem]
    nivel = {origem: 0}
    pai = {origem: None}
    fila = [origem]          # lista usada como fila (FIFO)
    inicio = 0               # índice do próximo da fila
    while inicio < len(fila):
        atual = fila[inicio]
        inicio += 1
        for vizinho, _ in grafo[atual]:
            if vizinho not in nivel:
                nivel[vizinho] = nivel[atual] + 1
                pai[vizinho] = atual
                fila.append(vizinho)
                ordem.append(vizinho)
    return ordem, nivel, pai


def dfs(grafo, origem, visitados=None, ordem=None, arestas_arvore=None):
    """
    BUSCA EM PROFUNDIDADE (recursiva): segue um caminho até o fim antes
    de voltar (backtracking). Retorna a ordem de visita e as arestas da
    árvore de busca. Complexidade: O(V + E).
    """
    if visitados is None:
        visitados, ordem, arestas_arvore = set(), [], []
    visitados.add(origem)
    ordem.append(origem)
    for vizinho, _ in grafo[origem]:
        if vizinho not in visitados:
            arestas_arvore.append((origem, vizinho))
            dfs(grafo, vizinho, visitados, ordem, arestas_arvore)
    return ordem, arestas_arvore


def componentes_conexos(grafo):
    """Usa BFS repetidas vezes para achar grupos de módulos conectados."""
    restantes = set(grafo)
    componentes = []
    for v in ORDEM:
        if v in restantes:
            ordem, _, _ = bfs(grafo, v)
            componentes.append(ordem)
            restantes -= set(ordem)
    return componentes


def dijkstra(grafo, origem, criterio="distancia", passos=None):
    """
    ALGORITMO DE DIJKSTRA (versão com vetor, O(V²)): encontra o menor
    custo da origem até todos os módulos, segundo o critério escolhido.
    Se 'passos' for uma lista, registra cada etapa (para explicação).
    """
    dist = {v: INF for v in grafo}
    anterior = {v: None for v in grafo}
    dist[origem] = 0
    visitados = set()

    while len(visitados) < len(grafo):
        # 1) escolhe o vértice não visitado com menor distância provisória
        atual = None
        for v in grafo:
            if v not in visitados and (atual is None or dist[v] < dist[atual]):
                atual = v
        if dist[atual] == INF:
            break  # o restante é inalcançável
        visitados.add(atual)

        # 2) relaxa as arestas: tenta melhorar a distância dos vizinhos
        melhorados = []
        for vizinho, pesos in grafo[atual]:
            if vizinho in visitados:
                continue
            nova = dist[atual] + pesos[criterio]
            if nova < dist[vizinho]:
                dist[vizinho] = nova
                anterior[vizinho] = atual
                melhorados.append((vizinho, round(nova, 1)))
        if passos is not None:
            passos.append((atual, round(dist[atual], 1), melhorados))
    return dist, anterior


def reconstruir_caminho(anterior, destino):
    """Volta pelos 'anteriores' do destino até a origem."""
    caminho = []
    atual = destino
    while atual is not None:
        caminho.append(atual)
        atual = anterior.get(atual)
    caminho.reverse()
    return caminho


def menor_caminho(grafo, origem, destino, criterio="distancia"):
    """Retorna (caminho, custo) ou ([], INF) se não houver rota."""
    if origem not in grafo or destino not in grafo:
        return [], INF
    dist, anterior = dijkstra(grafo, origem, criterio)
    if dist[destino] == INF:
        return [], INF
    return reconstruir_caminho(anterior, destino), dist[destino]


def custo_caminho(grafo, caminho, criterio):
    total = 0
    for i in range(len(caminho) - 1):
        total += peso_aresta(grafo, caminho[i], caminho[i + 1], criterio)
    return total


def conexoes_criticas(grafo):
    """
    Detecta PONTOS DE ARTICULAÇÃO (módulos cuja falha desconecta a rede)
    e PONTES (conexões cuja falha desconecta a rede) com uma DFS que
    registra o tempo de descoberta (desc) e o menor tempo alcançável
    (low) de cada vértice - algoritmo de Tarjan.
    """
    desc, low, pai = {}, {}, {}
    articulacoes, pontes = set(), []
    tempo = [0]

    def visitar(u):
        tempo[0] += 1
        desc[u] = low[u] = tempo[0]
        filhos = 0
        for v, _ in grafo[u]:
            if v not in desc:
                pai[v] = u
                filhos += 1
                visitar(v)
                low[u] = min(low[u], low[v])
                # raiz com 2+ filhos ou vértice sem "caminho de volta"
                if pai[u] is None and filhos > 1:
                    articulacoes.add(u)
                if pai[u] is not None and low[v] >= desc[u]:
                    articulacoes.add(u)
                if low[v] > desc[u]:
                    pontes.append((u, v))
            elif v != pai[u]:
                low[u] = min(low[u], desc[v])

    for v in ORDEM:
        if v in grafo and v not in desc:
            pai[v] = None
            visitar(v)
    return [v for v in ORDEM if v in articulacoes], pontes


def impacto_falha(status, conexoes, sigla):
    """
    Índice de criticidade de um módulo: remove o módulo, roda BFS a
    partir do Armazenamento de Energia e mede quem fica sem energia.
    Peso por prioridade: crítica=4, alta=3, média=2, baixa=1.
    """
    simulado = dict(status)
    simulado[sigla] = "falha"
    grafo = construir_grafo(simulado, conexoes)
    if ORIGEM_ENERGIA not in grafo:
        alcancados = set()
    else:
        alcancados = set(bfs(grafo, ORIGEM_ENERGIA)[0])
    sem_energia = [v for v in grafo if v not in alcancados]
    indice = sum(5 - prioridade(v) for v in sem_energia)
    return sem_energia, indice


# =====================================================================
# 4. DISTRIBUIÇÃO DE ENERGIA, EFICIÊNCIA E OTIMIZAÇÃO DE ROTAS
# =====================================================================
def perda_fluxo_w(potencia_w, resistencia_ohm, tensao=TENSAO_NOMINAL_V):
    """Perda Joule em um cabo: P_perda = (P/V)² · R  (watts)."""
    corrente = potencia_w / tensao
    return corrente ** 2 * resistencia_ohm


def arvore_distribuicao(grafo, origem=ORIGEM_ENERGIA, criterio="perda"):
    """
    Árvore de caminhos mínimos a partir do armazenamento: cada módulo
    recebe energia pela rota de menor custo. Retorna o dicionário de
    anteriores (pai de cada módulo na árvore).
    """
    if origem not in grafo:
        return {}
    _, anterior = dijkstra(grafo, origem, criterio)
    return anterior


def arvore_bfs(grafo, origem=ORIGEM_ENERGIA):
    if origem not in grafo:
        return {}
    return bfs(grafo, origem)[2]


def fluxos_e_perdas(grafo, anterior, tensao=TENSAO_NOMINAL_V, demanda=None):
    """
    Calcula o fluxo de potência em cada cabo da árvore de distribuição
    (soma do consumo dos módulos "abaixo" dele) e a perda em cada cabo.
    Retorna (lista de (u, v, fluxo_w, perda_w), perda_total_w).
    """
    if demanda is None:
        demanda = {v: consumo(v) * 1000 for v in grafo}
    fluxo = {}  # (pai, filho) -> W
    for v in grafo:
        if v == ORIGEM_ENERGIA or anterior.get(v) is None:
            continue
        atual = v
        while anterior.get(atual) is not None:   # sobe até a origem
            aresta = (anterior[atual], atual)
            fluxo[aresta] = fluxo.get(aresta, 0) + demanda.get(v, 0)
            atual = anterior[atual]
    detalhes = []
    total = 0.0
    for (u, v), f in fluxo.items():
        r = peso_aresta(grafo, u, v, "resistencia_ohm")
        p = perda_fluxo_w(f, r, tensao)
        detalhes.append((u, v, f, p))
        total += p
    detalhes.sort(key=lambda x: ORDEM.index(x[1]))
    return detalhes, total


def arvore_otima(grafo, origem=ORIGEM_ENERGIA, tensao=TENSAO_NOMINAL_V, demanda=None):
    """
    OTIMIZAÇÃO COMPUTACIONAL (busca exaustiva): testa todas as árvores
    geradoras da rede (combinações de V-1 conexões que ligam todos os
    módulos) e escolhe a de MENOR perda estimada, considerando que os
    fluxos se somam nos cabos. Uma árvore com 8 módulos tem exatamente
    7 conexões; escolher 7 das 12 conexões dá C(12,7) = 792 combinações.
    Só 169 delas ligam todos os módulos sem formar ciclo (árvores
    válidas); as outras deixam algum módulo isolado e são descartadas.
    Como são poucas, a busca completa é viável e garante o ótimo global.
    Retorna (anterior, perda_w, árvores_válidas).
    """
    if origem not in grafo:
        return {}, 0.0, 0
    alcancaveis = set(bfs(grafo, origem)[0])
    arestas = [(u, v) for u, v, _ in lista_arestas(grafo)
               if u in alcancaveis and v in alcancaveis]
    n = len(alcancaveis)
    melhor = (None, INF)
    testadas = 0
    for combo in combinations(arestas, n - 1):
        sub = {v: [] for v in alcancaveis}
        for u, v in combo:
            sub[u].append((v, None))
            sub[v].append((u, None))
        _, _, pai = bfs(sub, origem)
        if len(pai) < n:
            continue  # não liga todos os módulos: não é árvore geradora
        testadas += 1
        _, perda = fluxos_e_perdas(grafo, pai, tensao, demanda)
        if perda < melhor[1]:
            melhor = (pai, perda)
    return melhor[0], melhor[1], testadas


def constante_perdas(grafo, anterior):
    """K = Σ F² · R da árvore (W²·Ω). Perdas(V) = K / V²."""
    detalhes, _ = fluxos_e_perdas(grafo, anterior, tensao=1.0)
    return sum(p for _, _, _, p in detalhes)


def todas_distancias(grafo, criterio):
    """Matriz de menores caminhos entre todos os pares (Dijkstra em cada)."""
    return {v: dijkstra(grafo, v, criterio)[0] for v in grafo}


def analisar_eficiencia(grafo):
    """Calcula indicadores de desempenho da rede. Retorna um dicionário."""
    vertices = [v for v in ORDEM if v in grafo]
    n = len(vertices)
    m = len(lista_arestas(grafo))
    resultado = {"n": n, "m": m}
    resultado["densidade"] = (2 * m) / (n * (n - 1)) if n > 1 else 0
    resultado["grau"] = {v: len(grafo[v]) for v in vertices}

    # Saltos (BFS) entre todos os pares -> eficiência global
    soma_inv, pares, desconexos = 0.0, 0, 0
    for u in vertices:
        nivel = bfs(grafo, u)[1]
        for v in vertices:
            if u != v:
                pares += 1
                if v in nivel:
                    soma_inv += 1 / nivel[v]
                else:
                    desconexos += 1
    resultado["eficiencia_global"] = soma_inv / pares if pares else 0
    resultado["pares_desconectados"] = desconexos // 2

    # Distância média, diâmetro e proximidade (closeness) em metros
    dist = todas_distancias(grafo, "distancia")
    valores = [dist[u][v] for u in vertices for v in vertices
               if u != v and dist[u][v] < INF]
    resultado["distancia_media_m"] = sum(valores) / len(valores) if valores else 0
    resultado["diametro_m"] = max(valores) if valores else 0
    resultado["proximidade"] = {}
    for u in vertices:
        alc = [dist[u][v] for v in vertices if v != u and dist[u][v] < INF]
        resultado["proximidade"][u] = len(alc) / sum(alc) * 100 if alc else 0

    # Intermediação simples: quantas rotas mínimas passam por cada módulo
    passagem = {v: 0 for v in vertices}
    for u in vertices:
        _, anterior = dijkstra(grafo, u, "distancia")
        for v in vertices:
            if v != u:
                for meio in reconstruir_caminho(anterior, v)[1:-1]:
                    passagem[meio] += 1
    resultado["intermediacao"] = {v: passagem[v] // 2 for v in vertices}

    # Perdas na distribuição a partir do armazenamento
    demanda_kw = sum(consumo(v) for v in vertices)
    resultado["demanda_kw"] = demanda_kw
    if ORIGEM_ENERGIA in grafo:
        _, p_otima, testadas = arvore_otima(grafo)
        _, p_dijk = fluxos_e_perdas(grafo, arvore_distribuicao(grafo, criterio="perda"))
        resultado["perda_dijkstra_w"] = p_dijk
        resultado["arvores_testadas"] = testadas
        _, p_dist = fluxos_e_perdas(grafo, arvore_distribuicao(grafo, criterio="distancia"))
        _, p_bfs = fluxos_e_perdas(grafo, arvore_bfs(grafo))
        resultado["perda_otima_w"] = p_otima
        resultado["perda_distancia_w"] = p_dist
        resultado["perda_bfs_w"] = p_bfs
        resultado["eficiencia_distribuicao"] = demanda_kw * 1000 / (demanda_kw * 1000 + p_otima)
    art, pontes = conexoes_criticas(grafo)
    resultado["articulacoes"] = art
    resultado["pontes"] = pontes
    return resultado


# =====================================================================
# 6. MODELAGEM MATEMÁTICA (definida antes das simulações que a usam)
# =====================================================================
# Modelo 1 - Perda energética e tensão ótima de operação
#   Perdas(V) = K / V²                         (W)
#   C(V) = 24·K / (1000·V²) + β·V              (kWh-equivalente por dia)
#   C'(V) = -48·K / (1000·V³) + β = 0  ->  V* = (48·K / (1000·β))^(1/3)
#   C''(V) = 144·K / (1000·V⁴) > 0     ->  V* é ponto de MÍNIMO
# ATENÇÃO: os coeficientes deste modelo (β, k, resistências dos cabos,
# consumos e geração) são valores HIPOTÉTICOS, escolhidos para fins
# didáticos. Em uma base real seriam medidos por sensores e ensaios.
BETA_ISOLAMENTO = 0.04  # kWh-eq/dia por volt (hipotético)


def custo_operacao(V, K, beta=BETA_ISOLAMENTO):
    return 24 * K / (1000 * V ** 2) + beta * V


def derivada_custo(V, K, beta=BETA_ISOLAMENTO):
    return -48 * K / (1000 * V ** 3) + beta


def segunda_derivada_custo(V, K):
    return 144 * K / (1000 * V ** 4)


def tensao_otima_analitica(K, beta=BETA_ISOLAMENTO):
    return (48 * K / (1000 * beta)) ** (1 / 3)


def tensao_otima_numerica(K, beta=BETA_ISOLAMENTO, v_min=100.0, v_max=2000.0):
    """
    Otimização computacional: busca da raiz de C'(V) pelo método da
    bisseção (C' é crescente, negativa antes de V* e positiva depois).
    """
    a, b = v_min, v_max
    iteracoes = 0
    while b - a > 0.01:
        meio = (a + b) / 2
        if derivada_custo(meio, K, beta) < 0:
            a = meio
        else:
            b = meio
        iteracoes += 1
    return (a + b) / 2, iteracoes


# Modelo 2 - Crescimento do consumo energético com a expansão
#   D(t) = D0 · e^(k·t)        (kW, t em meses)
#   D'(t) = k · D0 · e^(k·t)   (taxa de crescimento, kW/mês)
#   D(t*) = G  ->  t* = ln(G / D0) / k
TAXA_CRESCIMENTO = 0.035  # 3,5% ao mês (hipotético)


def demanda_futura(D0, k, t):
    return D0 * math.exp(k * t)


def taxa_demanda(D0, k, t):
    return k * D0 * math.exp(k * t)


def tempo_saturacao(D0, G, k):
    if D0 >= G:
        return 0.0
    return math.log(G / D0) / k


# =====================================================================
# 5. SIMULAÇÕES OPERACIONAIS
# =====================================================================
def simular_racionamento(potencia_disponivel_kw, status=None, conexoes=None):
    """
    Smart grid em crise: distribui a potência disponível priorizando os
    módulos críticos. Ordena por prioridade (1 primeiro) e, em empate,
    pelo menor consumo. Cada módulo custa seu consumo + perda da rota.
    Retorna lista de (sigla, situação, kW entregues).
    """
    if status is None:
        status = status_modulos
    grafo = construir_grafo(status, conexoes)
    if ORIGEM_ENERGIA not in grafo:
        return [], potencia_disponivel_kw
    alcancados = set(bfs(grafo, ORIGEM_ENERGIA)[0])
    dist, _ = dijkstra(grafo, ORIGEM_ENERGIA, "perda")
    fila = sorted([v for v in grafo if v in alcancados],
                  key=lambda v: (prioridade(v), consumo(v)))
    restante = potencia_disponivel_kw
    plano = []
    for v in fila:
        r_ohm = dist[v] / 1000
        p_w = consumo(v) * 1000
        necessario = consumo(v) + perda_fluxo_w(p_w, r_ohm) / 1000
        if restante >= necessario:
            plano.append((v, "atendido", consumo(v)))
            restante -= necessario
        elif prioridade(v) <= 2 and restante > 0:
            plano.append((v, "parcial", restante))   # críticos ficam com o que sobra
            restante = 0
        else:
            plano.append((v, "desligado", 0.0))
    for v in grafo:
        if v not in alcancados:
            plano.append((v, "isolado", 0.0))
    return plano, restante


def simular_tempestade(reducao_solar, horas, modo="normal"):
    """
    Tempestade de poeira: reduz a geração solar e calcula a autonomia
    das baterias. modo: "normal", "economia" (desliga prioridade 4) ou
    "emergencia" (mantém só prioridades 1 e 2).
    """
    limite = {"normal": 4, "economia": 3, "emergencia": 2}[modo]
    ligados = [v for v in ORDEM if esta_operando(status_modulos[v])
               and prioridade(v) <= limite]
    grafo = construir_grafo()
    _, perda_w, _ = arvore_otima(grafo, demanda={v: consumo(v) * 1000 for v in ligados})
    demanda = sum(consumo(v) for v in ligados) + perda_w / 1000
    geracao = geracao_total(1 - reducao_solar)
    saldo = geracao - demanda
    reserva = capacidade(ORIGEM_ENERGIA) * CARGA_INICIAL_BATERIA
    if saldo >= 0:
        autonomia = INF
        reserva_final = min(capacidade(ORIGEM_ENERGIA), reserva + saldo * horas)
    else:
        autonomia = reserva / (-saldo)
        reserva_final = max(0.0, reserva + saldo * horas)
    return {"ligados": ligados, "demanda": demanda, "geracao": geracao,
            "saldo": saldo, "autonomia_h": autonomia,
            "reserva_inicial": reserva, "reserva_final": reserva_final,
            "sobrevive": autonomia >= horas}


# =====================================================================
# 7. INTERFACE DE TERMINAL - FUNÇÕES DE EXIBIÇÃO
# =====================================================================
def titulo(texto):
    print("\n" + "=" * 70)
    print(" " + texto)
    print("=" * 70)


def subtitulo(texto):
    print("\n--- " + texto + " " + "-" * max(0, 64 - len(texto)))


def fmt_caminho(caminho):
    return " -> ".join(caminho) if caminho else "(sem rota)"


MAPA_ASCII = r"""
                         [CM] Comunicação
                           |
                          80m
                           |
  [LC] -------55m------- [CC] -------60m------- [SM]
    |    Laboratório    /  Centro de \    Suporte |
   65m                40m  Controle   45m  Médico 30m
    |                 /                \          |
  [AG] -----70m----- [AE] -----60m----- [H ] -----+
    Agricultura  \   Armaz. Energia   /  Habitação
                 45m       |        40m
                   \      35m       /
                    \      |       /
                     +--- [PO] ---+
                     Produção de Oxigênio
"""


def mostrar_mapa():
    titulo("MAPA DA REDE DA COLÔNIA AURORA SIGER")
    print(MAPA_ASCII)
    print("Pesos mostrados: distância em metros. Cada conexão também possui")
    print("resistência elétrica (perda) e latência de comunicação.")


def mostrar_lista_adjacencia(grafo=None):
    if grafo is None:
        grafo = construir_grafo()
    subtitulo("Lista de adjacência  [vizinho (distância m | perda mΩ | latência ms)]")
    for v in ORDEM:
        if v in grafo:
            vizinhos = ", ".join(
                f"{u}({p['distancia']}|{p['perda']}|{p['latencia']})"
                for u, p in grafo[v])
            print(f"  {v:>2} [{status_modulos[v]:<13}] -> {vizinhos}")
        else:
            print(f"  {v:>2} [{status_modulos[v]:<13}] -> fora da rede")


def mostrar_matriz(grafo=None, criterio=None):
    if grafo is None:
        grafo = construir_grafo()
    vertices, matriz = matriz_adjacencia(grafo, criterio)
    nome_m = "binária (1 = conectado)" if criterio is None else \
        f"de pesos - {CRITERIOS[criterio][0]} ({CRITERIOS[criterio][1]})"
    subtitulo("Matriz de adjacência " + nome_m)
    print("      " + "".join(f"{v:>7}" for v in vertices))
    for i, v in enumerate(vertices):
        linha = "".join(f"{(matriz[i][j] if matriz[i][j] else '.'):>7}"
                        for j in range(len(vertices)))
        print(f"  {v:>3} " + linha)


def mostrar_rede_completa():
    mostrar_mapa()
    grafo = construir_grafo()
    mostrar_lista_adjacencia(grafo)
    mostrar_matriz(grafo)
    mostrar_matriz(grafo, "distancia")
    arestas = lista_arestas(grafo)
    print(f"\nTotal: {len(grafo)} módulos (vértices) e {len(arestas)} conexões (arestas).")


def mostrar_tabela_modulos():
    titulo("MÓDULOS DA COLÔNIA")
    print(f"  {'Sigla':<5} {'Nome':<26}{'Consumo':>8}  {'Prioridade':<12}"
          f"{'Armaz.':>8}  {'Comunic.':<14} Status")
    print("  " + "-" * 92)
    for s in ORDEM:
        print(f"  {s:<5} {nome(s):<26}{consumo(s):>6.1f}kW  "
              f"{prioridade(s)}-{NOMES_PRIORIDADE[prioridade(s)]:<10}"
              f"{capacidade(s):>6.0f}kWh  "
              f"{nivel_comunicacao(s):<5}({comunicacao(s):>3}/min) {status_modulos[s]}")
    total = sum(consumo(s) for s in ORDEM if esta_operando(status_modulos[s]))
    print(f"\n  Consumo total dos módulos operando: {total:.1f} kW")
    print(f"  Geração nominal disponível: {geracao_total():.1f} kW "
          f"({', '.join(f'{f}: {p:.0f} kW' for f, p in FONTES_GERACAO)})")


def mostrar_detalhes_modulo(sigla):
    titulo(f"CONSULTA DO MÓDULO {rotulo(sigla)}")
    tupla = MODULOS[sigla]
    for campo, valor in zip(CAMPOS_MODULO, tupla):   # tupla + tupla de campos
        print(f"  {campo:<20}: {valor}")
    print(f"  {'prioridade (texto)':<20}: {NOMES_PRIORIDADE[prioridade(sigla)]}")
    print(f"  {'comunicação':<20}: necessidade {nivel_comunicacao(sigla)}")
    print(f"  {'status':<20}: {status_modulos[sigla]}")

    grafo = construir_grafo()
    if sigla not in grafo:
        print("\n  Este módulo está fora da rede (manutenção ou falha).")
        return
    print("\n  Conexões diretas:")
    for v, p in grafo[sigla]:
        print(f"    - {rotulo(v):<34} {p['distancia']:>3} m | {p['perda']:>5} mΩ | {p['latencia']} ms")
    if sigla != ORIGEM_ENERGIA:
        caminho, custo = menor_caminho(grafo, ORIGEM_ENERGIA, sigla, "perda")
        print(f"\n  Rota de energia a partir do {ORIGEM_ENERGIA}: {fmt_caminho(caminho)} "
              f"({custo:.1f} mΩ)")
    sem_energia, indice = impacto_falha(status_modulos, CONEXOES_BASE, sigla)
    print(f"  Se este módulo falhar, ficam sem energia: "
          f"{', '.join(sem_energia) if sem_energia else 'nenhum outro módulo'}"
          f" (índice de criticidade {indice})")


def mostrar_dijkstra(origem, destino, criterio, mostrar_passos=True):
    grafo = construir_grafo()
    titulo(f"DIJKSTRA: {rotulo(origem)} -> {rotulo(destino)}")
    print(f"Critério de peso: {CRITERIOS[criterio][0]} ({CRITERIOS[criterio][1]})")
    if origem not in grafo or destino not in grafo:
        print("Origem ou destino fora de operação (manutenção/falha). Sem rota.")
        return
    passos = []
    dist, anterior = dijkstra(grafo, origem, criterio, passos)
    if mostrar_passos:
        subtitulo("Passo a passo")
        for i, (v, d, melhorados) in enumerate(passos, 1):
            txt = ", ".join(f"{u}={c}" for u, c in melhorados) or "nenhuma melhoria"
            print(f"  {i}. fixa {v:<2} (custo {d:>6}) | atualiza: {txt}")
    if dist[destino] == INF:
        print(f"\nNão existe rota entre {origem} e {destino}.")
        return
    caminho = reconstruir_caminho(anterior, destino)
    print(f"\n  Melhor rota: {fmt_caminho(caminho)}")
    print(f"  Custo total: {dist[destino]:.1f} {CRITERIOS[criterio][1]}")
    print(f"  Distância: {custo_caminho(grafo, caminho, 'distancia')} m | "
          f"Resistência: {custo_caminho(grafo, caminho, 'perda'):.1f} mΩ | "
          f"Latência: {custo_caminho(grafo, caminho, 'latencia')} ms")


def mostrar_envio_energia(destino):
    """Exemplo do enunciado: rota de energia do Armazenamento até um módulo."""
    grafo = construir_grafo()
    titulo(f"ENVIO DE ENERGIA: {rotulo(ORIGEM_ENERGIA)} -> {rotulo(destino)}")
    if destino not in grafo or ORIGEM_ENERGIA not in grafo:
        print("Módulo fora de operação. Não é possível enviar energia.")
        return
    if destino == ORIGEM_ENERGIA:
        print("O destino é o próprio armazenamento.")
        return
    p_w = consumo(destino) * 1000
    print(f"Demanda do módulo: {consumo(destino):.1f} kW | Tensão da rede: {TENSAO_NOMINAL_V:.0f} V\n")
    opcoes = []
    _, _, pai = bfs(grafo, ORIGEM_ENERGIA)
    opcoes.append(("BFS (menos saltos)", reconstruir_caminho(pai, destino)))
    opcoes.append(("Dijkstra - menor distância", menor_caminho(grafo, ORIGEM_ENERGIA, destino, "distancia")[0]))
    opcoes.append(("Dijkstra - menor resistência", menor_caminho(grafo, ORIGEM_ENERGIA, destino, "perda")[0]))
    print(f"  {'Método':<31}{'Rota':<22}{'Dist.':>7}{'R (mΩ)':>9}{'Perda':>9}{'Efic.':>9}")
    print("  " + "-" * 87)
    melhor = None
    for metodo, caminho in opcoes:
        r_ohm = custo_caminho(grafo, caminho, "resistencia_ohm")
        perda = perda_fluxo_w(p_w, r_ohm)
        efic = p_w / (p_w + perda) * 100
        print(f"  {metodo:<31}{fmt_caminho(caminho):<22}"
              f"{custo_caminho(grafo, caminho, 'distancia'):>5} m"
              f"{r_ohm * 1000:>9.1f}{perda:>7.1f} W{efic:>8.2f}%")
        if melhor is None or perda <= melhor[2]:   # empate: prefere Dijkstra
            melhor = (metodo, caminho, perda)
    print(f"\n  Rota recomendada pelo SIGIC: {fmt_caminho(melhor[1])} ({melhor[0]})")
    print("  A rota mais curta nem sempre é a mais eficiente: cabos degradados")
    print("  aumentam a resistência e, portanto, o desperdício de energia.")


def mostrar_exploracao(origem):
    grafo = construir_grafo()
    titulo(f"EXPLORAÇÃO DA REDE A PARTIR DE {rotulo(origem)}")
    if origem not in grafo:
        print("Módulo fora da rede.")
        return
    ordem, nivel, _ = bfs(grafo, origem)
    subtitulo("BFS - Busca em largura (camadas por número de saltos)")
    print("  Ordem de visita:", " -> ".join(ordem))
    maior = max(nivel.values())
    for n in range(maior + 1):
        camada = [v for v in ordem if nivel[v] == n]
        print(f"  Nível {n}: {', '.join(camada)}")
    ordem_d, arvore = dfs(grafo, origem)
    subtitulo("DFS - Busca em profundidade (segue um caminho até o fim)")
    print("  Ordem de visita:", " -> ".join(ordem_d))
    print("  Arestas da árvore DFS:", ", ".join(f"{u}-{v}" for u, v in arvore))
    comps = componentes_conexos(grafo)
    subtitulo("Conectividade")
    if len(comps) == 1:
        print(f"  Rede CONEXA: todos os {len(grafo)} módulos operantes se alcançam.")
    else:
        print(f"  Rede DIVIDIDA em {len(comps)} partes: " +
              " | ".join("{" + ", ".join(c) + "}" for c in comps))


def mostrar_criticos(status=None, conexoes=None, titulo_extra=""):
    grafo = construir_grafo(status, conexoes)
    titulo("CONEXÕES CRÍTICAS DA REDE" + titulo_extra)
    art, pontes = conexoes_criticas(grafo)
    print("  Pontos de articulação (módulos que, se falharem, dividem a rede):")
    print("    " + (", ".join(rotulo(v) for v in art) if art else "nenhum"))
    print("  Pontes (conexões que, se caírem, dividem a rede):")
    print("    " + (", ".join(f"{u}-{v}" for u, v in pontes) if pontes else "nenhuma"))
    if pontes:
        print("  Sugestão do SIGIC: nova conexão LC-CM (50 m) cria um caminho alternativo")
        print("  e elimina a ponte. Teste em: 8. Simulações -> 6. Expansão da rede.")
    subtitulo("Índice de criticidade (falha simulada de cada módulo)")
    st = status if status is not None else status_modulos
    cx = conexoes if conexoes is not None else CONEXOES_BASE
    ranking = []
    for v in ORDEM:
        if v in grafo and v != ORIGEM_ENERGIA:
            sem, indice = impacto_falha(st, cx, v)
            ranking.append((indice, v, sem))
    ranking.sort(reverse=True)
    for indice, v, sem in ranking:
        print(f"  {v:<3} índice {indice:>2} | sem energia: {', '.join(sem) if sem else '-'}")
    print(f"  {ORIGEM_ENERGIA:<3} índice máx. | é a fonte de toda a energia (ponto único de falha)")
    return art, pontes


def mostrar_eficiencia():
    grafo = construir_grafo()
    titulo("ANÁLISE DE EFICIÊNCIA OPERACIONAL")
    r = analisar_eficiencia(grafo)
    print(f"  Módulos (V): {r['n']} | Conexões (E): {r['m']} | Densidade: {r['densidade']:.2f}")
    print(f"  Eficiência global (média de 1/saltos): {r['eficiencia_global']:.3f}")
    print(f"  Distância média entre módulos: {r['distancia_media_m']:.1f} m | "
          f"Diâmetro: {r['diametro_m']} m")
    if r["pares_desconectados"]:
        print(f"  ATENÇÃO: {r['pares_desconectados']} pares de módulos sem conexão!")
    subtitulo("Centralidade dos módulos")
    print(f"  {'Módulo':<6}{'Grau':>6}{'Proximidade':>14}{'Intermediação':>16}")
    for v in ORDEM:
        if v in grafo:
            print(f"  {v:<6}{r['grau'][v]:>6}{r['proximidade'][v]:>14.2f}{r['intermediacao'][v]:>16}")
    if "perda_otima_w" in r:
        subtitulo(f"Distribuição de energia a partir do {ORIGEM_ENERGIA} ({TENSAO_NOMINAL_V:.0f} V)")
        print(f"  Demanda total: {r['demanda_kw']:.1f} kW")
        print(f"  Perdas com rotas BFS (menos saltos):   {r['perda_bfs_w']:>8.1f} W")
        print(f"  Perdas com rotas de menor distância:   {r['perda_distancia_w']:>8.1f} W")
        print(f"  Perdas com Dijkstra por resistência:   {r['perda_dijkstra_w']:>8.1f} W")
        print(f"  Perdas com a árvore ÓTIMA (SIGIC):     {r['perda_otima_w']:>8.1f} W")
        combos = math.comb(r["m"], r["n"] - 1)
        print(f"    (busca exaustiva: {combos} combinações de {r['n'] - 1} conexões entre as {r['m']};"
              f" {r['arvores_testadas']} formam árvores válidas)")
        economia = max(r["perda_bfs_w"], r["perda_distancia_w"], r["perda_dijkstra_w"]) - r["perda_otima_w"]
        print(f"  Economia frente à pior estratégia: {economia:.1f} W "
              f"({economia * 24 / 1000:.2f} kWh por dia; "
              f"{economia * 24 * 365 / 1000:.0f} kWh por ano)")
        print(f"  Eficiência da distribuição: {r['eficiencia_distribuicao'] * 100:.2f}%")
        detalhes, _ = fluxos_e_perdas(grafo, arvore_otima(grafo)[0])
        print("\n  Fluxo nos cabos da árvore ótima:")
        for u, v, f, p in detalhes:
            print(f"    {u}->{v:<3} fluxo {f / 1000:>5.1f} kW | perda {p:>6.1f} W")
    print(f"\n  Pontos de articulação: {', '.join(r['articulacoes']) or 'nenhum'} | "
          f"Pontes: {', '.join(f'{u}-{v}' for u, v in r['pontes']) or 'nenhuma'}")
    if r["pontes"]:
        print("  Recomendação: criar conexão redundante para eliminar as pontes"
              " (ver simulação de expansão).")
    print("  Observação: Dijkstra minimiza a resistência de cada rota isolada; como")
    print("  a perda depende do QUADRADO do fluxo somado nos cabos, a árvore ótima")
    print("  divide melhor a carga entre os cabos que saem do armazenamento.")


# ---------------------------------------------------------------------
# Simulações (exibição)
# ---------------------------------------------------------------------
def sim_falha_modulo(sigla, estado_novo="falha"):
    rotulo_estado = "MANUTENÇÃO PROGRAMADA" if estado_novo == "em manutenção" else "FALHA"
    titulo(f"SIMULAÇÃO: {rotulo_estado} DO MÓDULO {rotulo(sigla)}")
    if sigla == ORIGEM_ENERGIA and estado_novo == "em manutenção":
        print("  Aviso: o armazenamento só pode entrar em manutenção com a base")
        print("  alimentada diretamente pelas fontes (procedimento especial).")
    antes = construir_grafo()
    simulado = dict(status_modulos)
    simulado[sigla] = estado_novo
    depois = construir_grafo(simulado)
    comps = componentes_conexos(depois)
    alcancados = set(bfs(depois, ORIGEM_ENERGIA)[0]) if ORIGEM_ENERGIA in depois else set()
    sem_energia = [v for v in depois if v not in alcancados]
    print(f"  Módulos operando: {len(antes)} -> {len(depois)}")
    print(f"  Partes da rede após o evento: {len(comps)} -> " +
          " | ".join("{" + ", ".join(c) + "}" for c in comps))
    if sem_energia:
        print("  ALERTA: módulos sem energia: " + ", ".join(rotulo(v) for v in sem_energia))
        criticos = [v for v in sem_energia if prioridade(v) == 1]
        if criticos:
            print("  RISCO À VIDA: módulos críticos isolados -> ativar baterias locais.")
        for v in sem_energia:
            print(f"    {v}: autonomia local {capacidade(v) / consumo(v):.1f} h "
                  f"({capacidade(v):.0f} kWh / {consumo(v):.0f} kW)")
    else:
        print("  Todos os módulos operantes continuam recebendo energia.")
    subtitulo("Rotas de energia recalculadas (Dijkstra por menor resistência)")
    for v in ORDEM:
        if v == ORIGEM_ENERGIA or v == sigla:
            continue
        c1, r1 = menor_caminho(antes, ORIGEM_ENERGIA, v, "perda")
        c2, r2 = menor_caminho(depois, ORIGEM_ENERGIA, v, "perda")
        mudou = "" if c1 == c2 else "  <- rota alterada"
        txt2 = f"{fmt_caminho(c2)} ({r2:.0f} mΩ)" if c2 else "SEM ROTA"
        print(f"  {v:<3} antes: {fmt_caminho(c1):<18} ({r1:>3.0f} mΩ) | depois: {txt2}{mudou}")
    if depois and ORIGEM_ENERGIA in depois:
        _, p_antes, _ = arvore_otima(antes)
        _, p_depois, _ = arvore_otima(depois)
        print(f"\n  Perdas na distribuição: {p_antes:.1f} W -> {p_depois:.1f} W")


def sim_falha_conexao(u, v):
    titulo(f"SIMULAÇÃO: ROMPIMENTO DA CONEXÃO {u}-{v}")
    restantes = [c for c in CONEXOES_BASE if {c[0], c[1]} != {u, v}]
    if len(restantes) == len(CONEXOES_BASE):
        print("  Essa conexão não existe na rede.")
        return
    grafo = construir_grafo(conexoes=restantes)
    comps = componentes_conexos(grafo)
    if len(comps) > 1:
        print("  A rede foi DIVIDIDA: " + " | ".join("{" + ", ".join(c) + "}" for c in comps))
        print("  Essa conexão era uma PONTE (conexão crítica).")
    else:
        print("  A rede continua conexa: existe caminho alternativo.")
    for destino in ORDEM:
        if destino != ORIGEM_ENERGIA:
            c, r = menor_caminho(grafo, ORIGEM_ENERGIA, destino, "perda")
            print(f"  {ORIGEM_ENERGIA} -> {destino:<3}: {fmt_caminho(c)}"
                  + (f" ({r:.0f} mΩ)" if c else ""))


def sim_racionamento(potencia_kw):
    titulo(f"SIMULAÇÃO: CRISE ENERGÉTICA - {potencia_kw:.1f} kW DISPONÍVEIS")
    plano, sobra = simular_racionamento(potencia_kw)
    demanda = sum(consumo(v) for v, _, _ in plano)
    print(f"  Demanda total: {demanda:.1f} kW | Disponível: {potencia_kw:.1f} kW")
    print("  Distribuição por prioridade (smart grid):\n")
    for v, situacao, kw in plano:
        print(f"  [{prioridade(v)}-{NOMES_PRIORIDADE[prioridade(v)]:<7}] {rotulo(v):<34}"
              f"{situacao:<10}{kw:>6.1f} / {consumo(v):.1f} kW")
    desligados = [v for v, s, _ in plano if s != "atendido"]
    print(f"\n  Sobra de potência: {sobra:.1f} kW")
    if desligados:
        print("  Módulos com corte: " + ", ".join(desligados))
    else:
        print("  Todos os módulos foram atendidos.")


def sim_tempestade(reducao, horas):
    titulo(f"SIMULAÇÃO: TEMPESTADE DE POEIRA ({reducao * 100:.0f}% menos sol, {horas} h)")
    print(f"  Reserva inicial do {ORIGEM_ENERGIA}: "
          f"{capacidade(ORIGEM_ENERGIA) * CARGA_INICIAL_BATERIA:.0f} kWh "
          f"({CARGA_INICIAL_BATERIA * 100:.0f}% de {capacidade(ORIGEM_ENERGIA):.0f} kWh)\n")
    print(f"  {'Modo':<12}{'Geração':>10}{'Demanda':>10}{'Saldo':>10}{'Autonomia':>12}"
          f"{'Reserva final':>15}  Resultado")
    recomendado = None
    for modo in ("normal", "economia", "emergencia"):
        r = simular_tempestade(reducao, horas, modo)
        aut = "ilimitada" if r["autonomia_h"] == INF else f"{r['autonomia_h']:.1f} h"
        res = "OK" if r["sobrevive"] else "ESGOTA"
        print(f"  {modo:<12}{r['geracao']:>8.1f}kW{r['demanda']:>8.1f}kW{r['saldo']:>+8.1f}kW"
              f"{aut:>12}{r['reserva_final']:>11.0f} kWh  {res}")
        if recomendado is None and r["sobrevive"]:
            recomendado = (modo, r)
    print("\n  normal = todos ligados | economia = desliga prioridade 4 |"
          " emergencia = só prioridades 1 e 2")
    if recomendado:
        print(f"  Recomendação do SIGIC: operar em modo '{recomendado[0]}' "
              f"(módulos ligados: {', '.join(recomendado[1]['ligados'])}).")
    else:
        print("  Nenhum modo garante a duração informada: acionar plano de contingência.")


def sim_expansao(u="LC", v="CM", dist=50, r_ohm_m=0.0008, lat=2):
    titulo(f"SIMULAÇÃO: EXPANSÃO - NOVA CONEXÃO {u}-{v} ({dist} m)")
    if any({c[0], c[1]} == {u, v} for c in CONEXOES_BASE):
        print("  Essa conexão já existe.")
        return
    novas = CONEXOES_BASE + [(u, v, dist, r_ohm_m, lat)]
    antes = analisar_eficiencia(construir_grafo())
    depois = analisar_eficiencia(construir_grafo(conexoes=novas))
    print(f"  {'Indicador':<34}{'Antes':>12}{'Depois':>12}")
    linhas = [
        ("Conexões", antes["m"], depois["m"]),
        ("Densidade", f"{antes['densidade']:.2f}", f"{depois['densidade']:.2f}"),
        ("Eficiência global", f"{antes['eficiencia_global']:.3f}", f"{depois['eficiencia_global']:.3f}"),
        ("Distância média (m)", f"{antes['distancia_media_m']:.1f}", f"{depois['distancia_media_m']:.1f}"),
        ("Pontos de articulação", ", ".join(antes["articulacoes"]) or "-", ", ".join(depois["articulacoes"]) or "-"),
        ("Pontes", len(antes["pontes"]), len(depois["pontes"])),
        ("Perda de distribuição (W)", f"{antes['perda_otima_w']:.1f}", f"{depois['perda_otima_w']:.1f}"),
    ]
    for nome_ind, a, d in linhas:
        print(f"  {nome_ind:<34}{str(a):>12}{str(d):>12}")
    custo_cabo = dist  # metros de cabo novos
    print(f"\n  Custo da expansão: {custo_cabo} m de cabo.")
    if len(depois["pontes"]) < len(antes["pontes"]):
        print("  Benefício: a nova conexão cria redundância e elimina conexões críticas.")


def mostrar_modelagem():
    grafo = construir_grafo()
    titulo("MODELAGEM MATEMÁTICA 1: PERDA ENERGÉTICA E TENSÃO ÓTIMA")
    anterior = arvore_otima(grafo)[0]
    K = constante_perdas(grafo, anterior)
    print("  Perda Joule em cada cabo:  P_perda = (F / V)² · R")
    print("  Somando os cabos da árvore de distribuição:  Perdas(V) = K / V²")
    print("  Custo diário total:  C(V) = 24·K / (1000·V²) + β·V   [kWh-eq/dia]")
    print("    F = fluxo de potência no cabo (W)   R = resistência do cabo (Ω)")
    print("    V = tensão de distribuição (V)      K = Σ F²·R (constante da rede)")
    print("    β = custo de isolamento/proteção por volt (kWh-eq/dia/V)")
    print(f"\n  Valores da Aurora Siger: K = {K:.3e} W²·Ω | β = {BETA_ISOLAMENTO}")
    print("  (coeficientes hipotéticos, usados para fins didáticos)")
    print("\n  Derivada:  C'(V) = -48·K/(1000·V³) + β")
    print("  C'(V) = 0  ->  V* = (48·K / (1000·β))^(1/3)")
    print("  C''(V) = 144·K/(1000·V⁴) > 0  ->  V* é ponto de MÍNIMO")
    v_ana = tensao_otima_analitica(K)
    v_num, it = tensao_otima_numerica(K)
    print(f"\n  V* analítico (derivada):       {v_ana:.1f} V")
    print(f"  V* numérico (bisseção em C'):  {v_num:.1f} V  ({it} iterações)")
    print(f"  C''(V*) = {segunda_derivada_custo(v_ana, K):.2e} > 0  (confirma o mínimo)")
    subtitulo("Tabela C(V)")
    print(f"  {'V (V)':>7}{'Perdas (W)':>12}{'Perda/dia':>12}{'Isolamento':>12}{'C(V)':>10}{'C`(V)':>10}")
    for V in (200, 300, 400, 500, round(v_ana), 700, 800, 1000):
        perdas = K / V ** 2
        print(f"  {V:>7}{perdas:>12.1f}{perdas * 24 / 1000:>10.2f}kWh"
              f"{BETA_ISOLAMENTO * V:>10.2f}kWh{custo_operacao(V, K):>10.2f}{derivada_custo(V, K):>+10.4f}")
    c_atual = custo_operacao(TENSAO_NOMINAL_V, K)
    c_otimo = custo_operacao(v_ana, K)
    print(f"\n  Hoje ({TENSAO_NOMINAL_V:.0f} V): C = {c_atual:.2f} kWh-eq/dia | "
          f"Na tensão ótima: C = {c_otimo:.2f} kWh-eq/dia")
    print(f"  Economia potencial: {c_atual - c_otimo:.2f} kWh-eq/dia "
          f"({(c_atual - c_otimo) / c_atual * 100:.1f}%)")
    print("\n  Análise qualitativa: em tensões baixas a perda (1/V²) domina e o custo")
    print("  dispara; em tensões altas o isolamento (linear em V) domina. Existe um")
    print("  único ponto de equilíbrio. Como dP/dF = 2·F·R/V², a perda cresce com o")
    print("  QUADRADO do fluxo: dividir a carga entre dois caminhos reduz a perda à")
    print("  metade - por isso a rede possui rotas redundantes (smart grid).")

    titulo("MODELAGEM MATEMÁTICA 2: CRESCIMENTO DO CONSUMO ENERGÉTICO")
    D0 = sum(consumo(v) for v in grafo)
    G = geracao_total()
    k = TAXA_CRESCIMENTO
    print("  D(t) = D0 · e^(k·t)      D'(t) = k · D0 · e^(k·t)")
    print("    D0 = demanda atual (kW)   k = taxa de crescimento mensal   t = meses")
    print("    G  = capacidade de geração (kW)")
    print(f"\n  D0 = {D0:.1f} kW | k = {k} (3,5% ao mês, hipotético) | G = {G:.1f} kW")
    print(f"\n  {'Mês':>5}{'D(t) kW':>10}{'D`(t) kW/mês':>15}{'Uso de G':>10}")
    for t in (0, 3, 6, 9, 12, 15, 18, 24):
        d = demanda_futura(D0, k, t)
        print(f"  {t:>5}{d:>10.1f}{taxa_demanda(D0, k, t):>15.2f}{d / G * 100:>9.1f}%")
    t_sat = tempo_saturacao(D0, G, k)
    print(f"\n  Saturação da geração (D(t*) = G): t* = ln(G/D0)/k = {t_sat:.1f} meses")
    print("  Cenários de otimização (programas de eficiência reduzem k):")
    for k2 in (0.035, 0.025, 0.015):
        print(f"    k = {k2:.3f} -> saturação em {tempo_saturacao(D0, G, k2):>5.1f} meses")
    print("  Interpretação: a derivada cresce junto com D(t) (crescimento acelerado).")
    print("  A expansão de módulos deve ser acompanhada de nova geração ANTES de t*.")


def mostrar_esg():
    titulo("SUSTENTABILIDADE E GOVERNANÇA (ESG) APLICADA PELO SIGIC")
    print("""  Ambiental
   - Rotas de menor resistência (Dijkstra) reduzem o desperdício de energia.
   - Operação próxima da tensão ótima reduz perdas Joule nos cabos.
   - Excedente das fontes é armazenado no AE em vez de ser descartado.
   - Substituir o cabo H-SM (degradado) é a melhoria de maior retorno.
  Social
   - Prioridade 1 (Habitação, Oxigênio, Médico, Energia) nunca é cortada
     antes dos demais; o racionamento protege a vida da tripulação.
  Governança
   - Decisões do sistema são explicáveis: cada rota mostra o custo e o
     critério usado; nenhuma ação automática é escondida do operador.
   - Regras fixas e auditáveis (prioridades em tuplas imutáveis).
   - Relatórios gravados em arquivos_auxiliares/ servem como trilha de
     auditoria; mudanças de status são feitas pelo operador humano.
   - Expansão planejada: só adicionar módulos com geração disponível
     (modelo de crescimento) e com redundância (sem novas pontes).""")


# =====================================================================
# 7b. ENTRADAS DO USUÁRIO E MENU
# =====================================================================
def ler_texto(mensagem):
    try:
        return input(mensagem).strip()
    except EOFError:
        print()
        return "0"


def ler_modulo(mensagem="Informe a sigla ou o número do módulo: "):
    """Aceita sigla (ex.: SM) ou número da lista (1-8). Repete até ser válido."""
    for i, s in enumerate(ORDEM, 1):
        print(f"  {i}. {rotulo(s)} [{status_modulos[s]}]")
    while True:
        valor = ler_texto(mensagem).upper()
        if valor == "0":
            return None
        if valor in MODULOS:
            return valor
        if valor.isdigit() and 1 <= int(valor) <= len(ORDEM):
            return ORDEM[int(valor) - 1]
        print("  Módulo inválido. Tente novamente (0 cancela).")


def ler_numero(mensagem, padrao, minimo=None, maximo=None):
    while True:
        valor = ler_texto(f"{mensagem} [Enter = {padrao}]: ").replace(",", ".")
        if valor == "":
            return padrao
        try:
            numero = float(valor)
            if (minimo is not None and numero < minimo) or (maximo is not None and numero > maximo):
                print(f"  Valor fora do intervalo ({minimo} a {maximo}).")
                continue
            return numero
        except ValueError:
            print("  Digite um número válido.")


def ler_criterio():
    chaves = list(CRITERIOS)
    for i, c in enumerate(chaves, 1):
        print(f"  {i}. {CRITERIOS[c][0]} ({CRITERIOS[c][1]})")
    while True:
        valor = ler_texto("Escolha o critério de peso [Enter = 1]: ")
        if valor == "":
            return chaves[0]
        if valor.isdigit() and 1 <= int(valor) <= len(chaves):
            return chaves[int(valor) - 1]
        print("  Opção inválida.")


def pausar():
    ler_texto("\nPressione Enter para voltar ao menu...")


def alterar_status():
    titulo("ALTERAR STATUS OPERACIONAL")
    sigla = ler_modulo()
    if sigla is None:
        return
    for i, s in enumerate(STATUS_VALIDOS, 1):
        print(f"  {i}. {s}")
    valor = ler_texto("Novo status: ")
    if valor.isdigit() and 1 <= int(valor) <= len(STATUS_VALIDOS):
        status_modulos[sigla] = STATUS_VALIDOS[int(valor) - 1]
        print(f"  Status de {rotulo(sigla)} alterado para '{status_modulos[sigla]}'.")
        print("  Todas as rotas e análises passam a considerar o novo status.")
    else:
        print("  Opção inválida. Nada foi alterado.")


def menu_simulacoes():
    while True:
        titulo("SIMULAÇÕES OPERACIONAIS")
        print("  1. Falha de um módulo")
        print("  2. Manutenção programada de um módulo")
        print("  3. Rompimento de uma conexão")
        print("  4. Crise energética (racionamento por prioridade)")
        print("  5. Tempestade de poeira (autonomia das baterias)")
        print("  6. Expansão da rede (nova conexão redundante)")
        print("  0. Voltar")
        op = ler_texto("Opção: ")
        if op == "1":
            s = ler_modulo()
            if s:
                sim_falha_modulo(s, "falha")
        elif op == "2":
            s = ler_modulo()
            if s:
                sim_falha_modulo(s, "em manutenção")
        elif op == "3":
            print("  Conexões: " + ", ".join(f"{c[0]}-{c[1]}" for c in CONEXOES_BASE))
            u = ler_modulo("Primeiro módulo da conexão: ")
            v = ler_modulo("Segundo módulo da conexão: ") if u else None
            if u and v:
                sim_falha_conexao(u, v)
        elif op == "4":
            p = ler_numero("Potência disponível em kW", 80.0, 0, 1000)
            sim_racionamento(p)
        elif op == "5":
            red = ler_numero("Redução da geração solar em %", 70.0, 0, 100) / 100
            h = int(ler_numero("Duração da tempestade em horas", 72, 1, 2000))
            sim_tempestade(red, h)
        elif op == "6":
            print("  Sugestão do SIGIC: LC-CM (50 m) elimina a única ponte da rede.")
            u = ler_modulo("Primeiro módulo [ex.: LC]: ")
            v = ler_modulo("Segundo módulo [ex.: CM]: ") if u else None
            if u and v and u != v:
                d = int(ler_numero("Distância em metros", 50, 1, 1000))
                sim_expansao(u, v, d)
        elif op == "0":
            return
        else:
            print("  Opção inválida.")
            continue
        pausar()


def salvar_relatorio():
    """Grava o relatório e as matrizes em arquivos_auxiliares/."""
    os.makedirs(PASTA_AUXILIAR, exist_ok=True)
    caminho_txt = os.path.join(PASTA_AUXILIAR, "relatorio_sigic.txt")
    with open(caminho_txt, "w", encoding="utf-8") as arquivo:
        with redirect_stdout(arquivo):
            mostrar_tabela_modulos()
            mostrar_rede_completa()
            mostrar_criticos()
            mostrar_eficiencia()
            mostrar_modelagem()
    grafo = construir_grafo()
    caminho_csv = os.path.join(PASTA_AUXILIAR, "matriz_adjacencia.csv")
    vertices, matriz = matriz_adjacencia(grafo, "distancia")
    with open(caminho_csv, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["modulo"] + vertices)
        for v, linha in zip(vertices, matriz):
            escritor.writerow([v] + linha)
    print(f"  Relatório salvo em: {caminho_txt}")
    print(f"  Matriz de distâncias salva em: {caminho_csv}")


def demonstracao():
    """Executa todas as funcionalidades com exemplos (sem digitar nada)."""
    print("#" * 70)
    print("#  SIGIC - DEMONSTRAÇÃO AUTOMÁTICA DE TODAS AS FUNCIONALIDADES")
    print("#" * 70)
    mostrar_tabela_modulos()
    mostrar_rede_completa()
    mostrar_matriz(construir_grafo(), "perda")
    mostrar_detalhes_modulo("SM")
    mostrar_envio_energia("SM")      # exemplo citado no enunciado
    mostrar_dijkstra("CM", "AG", "latencia")
    mostrar_exploracao("AE")
    mostrar_criticos()
    mostrar_eficiencia()
    sim_falha_modulo("H", "falha")
    sim_falha_modulo("CC", "em manutenção")
    sim_falha_conexao("CC", "CM")
    sim_racionamento(80.0)
    sim_tempestade(0.70, 72)
    sim_expansao("LC", "CM", 50)
    mostrar_modelagem()
    mostrar_esg()


def menu_principal():
    while True:
        titulo("SIGIC - AURORA SIGER | MENU PRINCIPAL")
        print("   1. Visualizar a rede (mapa, lista e matriz de adjacência)")
        print("   2. Consultar módulos")
        print("   3. Calcular caminho mínimo entre módulos (Dijkstra)")
        print("   4. Enviar energia do Armazenamento para um módulo")
        print("   5. Explorar a rede (BFS e DFS)")
        print("   6. Detectar conexões críticas")
        print("   7. Analisar eficiência operacional")
        print("   8. Simulações operacionais")
        print("   9. Modelagem matemática e otimização")
        print("  10. Sustentabilidade e governança (ESG)")
        print("  11. Alterar status de um módulo")
        print("  12. Salvar relatório em arquivos_auxiliares/")
        print("  13. Demonstração completa (exemplos de execução)")
        print("   0. Sair")
        op = ler_texto("Escolha uma opção: ")

        if op == "1":
            mostrar_rede_completa()
            criterio = ler_texto("Ver matriz de pesos? (d=distância, p=perda, l=latência, Enter=não): ").lower()
            mapa = {"d": "distancia", "p": "perda", "l": "latencia"}
            if criterio in mapa:
                mostrar_matriz(construir_grafo(), mapa[criterio])
        elif op == "2":
            mostrar_tabela_modulos()
            print("\nDeseja ver os detalhes de um módulo? (0 para voltar)")
            s = ler_modulo()
            if s:
                mostrar_detalhes_modulo(s)
        elif op == "3":
            print("Origem:")
            o = ler_modulo()
            if not o:
                continue
            print("Destino:")
            d = ler_modulo()
            if not d:
                continue
            c = ler_criterio()
            mostrar_dijkstra(o, d, c)
        elif op == "4":
            print("Para qual módulo enviar energia?")
            d = ler_modulo()
            if d:
                mostrar_envio_energia(d)
        elif op == "5":
            print("Módulo de partida:")
            o = ler_modulo()
            if o:
                mostrar_exploracao(o)
        elif op == "6":
            mostrar_criticos()
        elif op == "7":
            mostrar_eficiencia()
        elif op == "8":
            menu_simulacoes()
            continue
        elif op == "9":
            mostrar_modelagem()
        elif op == "10":
            mostrar_esg()
        elif op == "11":
            alterar_status()
        elif op == "12":
            salvar_relatorio()
        elif op == "13":
            demonstracao()
        elif op == "0":
            print("\nEncerrando o SIGIC. Boa missão, Aurora Siger!")
            return
        else:
            print("  Opção inválida. Digite um número do menu.")
            continue
        pausar()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demonstracao()
    else:
        menu_principal()
