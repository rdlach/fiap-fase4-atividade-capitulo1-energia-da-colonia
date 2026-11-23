# SIGIC – Sistema Inteligente de Gerenciamento da Infraestrutura da Colônia


## Integrantes do Grupo

* <a href="https://github.com/rdlach">Ronei Davi Lach</a> (RM575354)
* <a href="https://github.com/Obleynixx">Gabriel Hampel Meireles</a> (RM574600)
* <a href="https://github.com/jrzendron">José Roberto Zendron</a> (RM575414)
* <a href="https://github.com/robertoiuvata">Roberto Kenji Iuvata</a> (RM574361)
* <a href="https://github.com/David-Silva2004">David Silva</a> (RM575885)

## Professores

### Tutor(a)

* <a href="https://br.linkedin.com/in/andretritiack">André Tritiack</a>

### Coordenador(a)

* <a href="https://www.linkedin.com/in/valtersrf/">Valter Santiago Rosa Filho</a>

Entrega da Fase 4 (Colônia Aurora Siger). O arquivo principal é o **`codigo_fonte.py`**. Ele usa somente a biblioteca padrão do Python 3.8 ou superior.

```bash
python codigo_fonte.py          # menu interativo
python codigo_fonte.py --demo   # demonstração das principais funcionalidades
```

| Arquivo | Conteúdo |
| --- | --- |
| `codigo_fonte.py` | Sistema completo: grafo (lista e matriz de adjacência), BFS, DFS, Dijkstra, conexões críticas, eficiência, simulações e modelagem matemática |
| `arquivos_auxiliares/` | Relatório gerado pelo sistema, matriz de distâncias em CSV e exemplos de execução |
| `rede_colonia.pdf` | Mapa da rede e árvore ótima de distribuição de energia |
| `documentacao_complementar.pdf` | Justificativas, algoritmos, modelagem matemática e análise ESG |
| `link_video.txt` | Link do vídeo no YouTube (não listado) |

## Como interpretar os resultados

O peso chamado `perda` representa resistência em miliohms. A perda em watts depende também da potência transportada e da tensão. A árvore de distribuição escolhe um caminho por módulo. A redução teórica de 50% ao dividir uma carga pressupõe dois caminhos de mesma resistência recebendo metade da carga cada.

O relatório registra o estado atual e é substituído a cada exportação. A indicação de trocar o cabo H–SM considera a resistência elétrica. O modelo não calcula o retorno financeiro da troca.
