# PRD — mowanettest

**Produto:** mowanettest — medidor de velocidade de internet para Windows
**Versão do documento:** 1.0
**Data:** 09/09/2026
**Autor:** Victor Alves Carmona
**Status:** Rascunho para implementação

---

## 1. Visão geral

O **mowanettest** é um aplicativo desktop executável (`.exe`) para Windows que mede a velocidade da conexão de internet (download, upload, ping) e mantém um histórico local de todos os testes realizados.

O foco é ser **leve, offline-first (sem servidor próprio), portátil e com tema escuro**. O usuário baixa um único executável, roda, testa e vê o histórico — sem instalação obrigatória, sem login, sem banco de dados.

### 1.1 Problema

Ferramentas de speedtest hoje vivem no navegador, exigem conexão com sites cheios de anúncios e não guardam histórico local em formato aberto. Quem precisa acompanhar a qualidade da conexão ao longo do tempo (home office, suporte técnico, diagnóstico de rede) acaba tirando print ou anotando manualmente.

### 1.2 Objetivo

Entregar um app desktop que:
- rode um teste de velocidade em poucos cliques;
- grave cada resultado em um arquivo `.txt` legível dentro da pasta `hist/`;
- exiba o histórico de forma organizada dentro do próprio app;
- ocupe pouca memória e inicie rápido.

### 1.3 Não-objetivos (fora do escopo v1)

- Versões para macOS e Linux
- Testes agendados/automáticos em background
- Sincronização em nuvem ou conta de usuário
- Teste de rota (traceroute), DNS ou análise de Wi-Fi
- Exportação para PDF/Excel
- Gráficos avançados de série temporal (previsto para v1.1)

---

## 2. Público-alvo

| Persona | Necessidade | Uso típico |
|---|---|---|
| Usuário doméstico | Saber se está recebendo a velocidade contratada | Roda o teste quando a internet "cai" |
| Profissional em home office | Comprovar qualidade de conexão em horários de reunião | Testa antes de calls, consulta histórico |
| Suporte técnico / TI | Registro auditável de medições em campo | Roda em várias máquinas, coleta os `.txt` |

---

## 3. Lista de tecnologias avaliadas

### 3.1 Camada de interface (UI)

| Tecnologia | Stack | Peso do .exe | Prós | Contras |
|---|---|---|---|---|
| **pywebview** ✅ *recomendado* | Python + HTML/CSS/JS | ~15–25 MB | UI web moderna, tema escuro trivial, API Python↔JS simples, usa o WebView2 do próprio Windows | Depende do runtime Edge WebView2 (já presente no Win10/11) |
| CustomTkinter | Python puro | ~12–20 MB | Sem dependência de runtime, dark mode nativo | Layout limitado, animações pobres |
| Flet | Python + Flutter | ~40–80 MB | Visual muito bom, componentes prontos | Executável pesado, empacota engine Flutter |
| PySide6 / PyQt6 | Python + Qt | ~60–120 MB | Maduro, poderoso, nativo | Licença (PyQt), .exe grande, curva de aprendizado |
| Eel | Python + Chrome | ~15 MB | Simples | Precisa do Chrome instalado |
| NiceGUI | Python + web | ~30 MB+ | Ótimo para dashboards | Roda servidor local, exagero aqui |
| DearPyGui | Python + GPU | ~30 MB | Rápido, ideal para gráficos em tempo real | Estética não-nativa |
| Tauri | Rust + web | ~5–10 MB | Executável mínimo, muito performático | Sai do ecossistema Python |
| Electron | Node + web | ~120 MB+ | Universal | Pesado demais para o objetivo |
| Wails | Go + web | ~10 MB | Leve e rápido | Reescrever backend em Go |
| WinUI 3 / WPF / Avalonia | .NET | ~20–60 MB | Nativo do Windows | Stack C#, mais verboso para o caso |

**Escolha: pywebview.** Melhor relação entre leveza, liberdade visual (tema escuro sob medida em CSS) e produtividade em Python.

### 3.2 Motor do teste de velocidade

| Opção | Como funciona | Observação |
|---|---|---|
| **Implementação própria via HTTP (Cloudflare)** ✅ *recomendado* | `GET https://speed.cloudflare.com/__down?bytes=N` para download e `POST /__up` para upload, com threads paralelas | Sem dependência externa, sem licença, endpoints públicos e estáveis, controle total sobre a medição |
| `speedtest-cli` (PyPI) | Wrapper não-oficial da rede Ookla | Projeto sem manutenção ativa, quebra quando a Ookla muda a API |
| Ookla Speedtest CLI (`speedtest.exe`) | Binário oficial embarcado | Resultado "oficial", mas exige aceite de EULA e distribuição do binário |
| LibreSpeed CLI | Binário Go open-source, rede de servidores comunitária | Boa alternativa, MIT, mas adiciona ~10 MB ao pacote |
| `iperf3` | Teste ponto a ponto | Exige servidor próprio, inadequado para usuário final |

**Estratégia:** motor próprio como padrão, com a arquitetura preparada para plugar um segundo provedor no futuro (interface `SpeedProvider`).

### 3.3 Demais componentes

| Função | Tecnologia | Motivo |
|---|---|---|
| Linguagem | Python 3.11+ | Produtividade, ecossistema |
| HTTP | `httpx` ou `requests` + `concurrent.futures` | Conexões paralelas para saturar o link |
| Ping / jitter | `socket` + TCP handshake timing | Evita ICMP (precisa de admin no Windows) |
| Empacotamento | **PyInstaller** (`--onefile --windowed`) | Padrão de mercado, simples |
| Alternativa de empacotamento | Nuitka | Compila para C, inicia mais rápido, build mais lento |
| Instalador (opcional) | Inno Setup | Cria atalho e desinstalador |
| Ícone | `.ico` 256×256 | Identidade visual |
| Gráfico do histórico (v1.1) | uPlot ou Chart.js via CDN local | uPlot pesa ~45 KB |
| Fonte | Inter ou Segoe UI Variable | Legibilidade, já disponível no Windows |
| Testes | pytest | Cobertura do parser e do storage |

---

## 4. Requisitos funcionais

### 4.1 Tela de Teste (tela inicial)

| ID | Requisito | Prioridade |
|---|---|---|
| RF-01 | Exibir botão central **"Iniciar teste"** como ação primária | Must |
| RF-02 | Ao iniciar, executar as etapas em sequência: *ping → download → upload* | Must |
| RF-03 | Exibir indicador de progresso por etapa (ex.: "Medindo download… 42%") | Must |
| RF-04 | Exibir valores em tempo real durante a medição, atualizando a cada ~200 ms | Should |
| RF-05 | Ao final, exibir card de resultado com **Download (Mbps)**, **Upload (Mbps)**, **Ping (ms)** e **Jitter (ms)** | Must |
| RF-06 | Exibir IP público e provedor (ISP) quando disponível | Should |
| RF-07 | Permitir cancelar o teste em andamento | Should |
| RF-08 | Gravar automaticamente o resultado em `hist/` ao concluir | Must |
| RF-09 | Exibir mensagem de erro amigável quando não houver conexão | Must |
| RF-10 | Botão "Testar novamente" após a conclusão | Must |

### 4.2 Tela de Histórico

| ID | Requisito | Prioridade |
|---|---|---|
| RF-11 | Listar todos os testes lidos da pasta `hist/`, ordenados do mais recente para o mais antigo | Must |
| RF-12 | Cada item da lista exibe: data/hora, download, upload e ping | Must |
| RF-13 | Exibir cards de resumo no topo: **média de download**, **média de upload** e **total de testes** | Should |
| RF-14 | Botão "Abrir pasta hist" que chama o Explorer na pasta de histórico | Should |
| RF-15 | Botão para excluir um registro individual (remove o `.txt` correspondente) | Could |
| RF-16 | Estado vazio: mensagem "Nenhum teste registrado ainda" com atalho para a tela de teste | Must |
| RF-17 | Recarregar a lista automaticamente ao entrar na tela | Must |
| RF-18 | Ignorar arquivos corrompidos ou fora do padrão sem quebrar a aplicação | Must |

### 4.3 Navegação

| ID | Requisito | Prioridade |
|---|---|---|
| RF-19 | Barra lateral (ou superior) fixa com dois itens: **Teste** e **Histórico** | Must |
| RF-20 | Indicar visualmente a tela ativa | Must |
| RF-21 | Janela com título "mowanettest", tamanho padrão 900×620 px, redimensionável, mínimo 780×560 px | Must |

---

## 5. Persistência do histórico

### 5.1 Regras

- A pasta `hist/` é criada **automaticamente na conclusão do primeiro teste**, no mesmo diretório do executável.
- Caso o diretório do executável não tenha permissão de escrita (ex.: `Program Files`), o app usa como fallback `%APPDATA%\mowanettest\hist\` e informa o caminho na interface.
- Cada teste gera **um arquivo `.txt` independente** (append nunca é usado — um teste, um arquivo).
- Nome do arquivo: `AAAA-MM-DD HH-MM-SS.txt` (data e hora locais do término do teste).
  Hífens no lugar de dois-pontos porque `:` é caractere inválido em nomes de arquivo no Windows.

```
mowanettest.exe
hist/
├── 2026-09-02 12-01-04.txt
├── 2026-09-05 20-05-56.txt
└── 2026-09-10 15-57-34.txt
```

### 5.2 Conteúdo do arquivo

Formato `chave: valor`, UTF-8, uma chave por linha — legível por humanos e trivial de parsear.

```
data: 2026-09-10
hora: 15:57:34
download: 248.73 Mbps
upload: 96.41 Mbps
ping: 12.4 ms
jitter: 2.1 ms
ip: 189.xx.xx.xx
provedor: Exemplo Telecom
servidor: Cloudflare - GRU
duracao: 24.8 s
versao: 1.0.0
```

### 5.3 Leitura

- O parser aceita chaves ausentes (campos opcionais viram `—` na interface).
- Linhas desconhecidas são ignoradas.
- Se a data/hora do conteúdo divergir do nome do arquivo, **o conteúdo prevalece**; se o conteúdo não tiver data, usa-se o nome do arquivo.

---

## 6. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | Executável único (`.exe`), sem necessidade de instalar Python |
| RNF-02 | Tamanho do executável ≤ 40 MB |
| RNF-03 | Tempo de inicialização até a janela visível ≤ 3 s em máquina com SSD |
| RNF-04 | Consumo de RAM em repouso ≤ 150 MB |
| RNF-05 | Funcionar sem privilégios de administrador |
| RNF-06 | Compatível com Windows 10 (1809+) e Windows 11, 64 bits |
| RNF-07 | Nenhum dado é enviado a servidores próprios; nenhuma telemetria |
| RNF-08 | Interface 100% em português (pt-BR) |
| RNF-09 | Interface não pode travar durante o teste — medição em thread separada |
| RNF-10 | Duração total do teste entre 20 e 40 segundos |

---

## 7. Design — tema escuro

### 7.1 Paleta

| Token | Hex | Uso |
|---|---|---|
| `--bg` | `#0F1115` | Fundo da janela |
| `--surface` | `#171A21` | Cards e barra lateral |
| `--surface-2` | `#1E222B` | Hover, linhas alternadas |
| `--border` | `#262B36` | Bordas e divisórias |
| `--text` | `#E6E9EF` | Texto principal |
| `--text-muted` | `#8B93A7` | Rótulos e legendas |
| `--download` | `#00D68F` | Métrica de download |
| `--upload` | `#4C8DFF` | Métrica de upload |
| `--accent` | `#00D68F` | Botão primário, item ativo |
| `--danger` | `#FF5C5C` | Erros e exclusão |

### 7.2 Tipografia

- Família: `Inter`, fallback `Segoe UI Variable`, `Segoe UI`, `sans-serif`
- Valor da métrica: 48 px / 700
- Título de seção: 20 px / 600
- Corpo: 14 px / 400
- Rótulo: 12 px / 500, `letter-spacing: 0.04em`, maiúsculas

### 7.3 Estrutura das telas

**Tela de Teste**
```
┌───────────┬──────────────────────────────────────────┐
│           │                                          │
│ ● Teste   │            [ estado: pronto ]            │
│   Histór. │                                          │
│           │          ⬤  INICIAR TESTE                │
│           │                                          │
│           │   ┌──────────┬──────────┬──────────┐     │
│           │   │ DOWNLOAD │  UPLOAD  │   PING   │     │
│           │   │  248.73  │   96.41  │   12.4   │     │
│           │   │   Mbps   │   Mbps   │    ms    │     │
│           │   └──────────┴──────────┴──────────┘     │
│           │                                          │
│ v1.0.0    │   189.xx.xx.xx · Exemplo Telecom         │
└───────────┴──────────────────────────────────────────┘
```

**Tela de Histórico**
```
┌───────────┬──────────────────────────────────────────┐
│   Teste   │  Média ↓ 231.5   Média ↑ 88.2   Testes 14│
│ ● Histór. │  ──────────────────────────────────────  │
│           │  10/09/2026 15:57   ↓248.73  ↑96.41  12ms│
│           │  05/09/2026 20:05   ↓198.02  ↑74.10  18ms│
│           │  02/09/2026 12:01   ↓251.44  ↑91.83  11ms│
│           │                                          │
│           │  [ Abrir pasta hist ]                    │
└───────────┴──────────────────────────────────────────┘
```

---

## 8. Arquitetura

```
mowanettest/
├── app.py                 # bootstrap do pywebview e da janela
├── core/
│   ├── speedtest.py       # motor de medição (download, upload, ping, jitter)
│   ├── storage.py         # criação da pasta hist/, escrita e leitura dos .txt
│   ├── models.py          # dataclass TestResult
│   └── paths.py           # resolução do diretório base (exe vs. dev vs. APPDATA)
├── api/
│   └── bridge.py          # classe exposta ao JS: run_test, get_history, open_folder
├── ui/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── assets/
│   └── icon.ico
├── build.spec             # configuração do PyInstaller
├── requirements.txt
└── README.md
```

**Fluxo de um teste**
1. JS chama `pywebview.api.run_test()`
2. `bridge.py` dispara o teste em uma thread
3. `speedtest.py` emite progresso via `window.evaluate_js()`
4. Ao concluir, `storage.py` grava o `.txt` em `hist/`
5. O resultado final retorna ao JS, que renderiza os cards

---

## 9. Build e distribuição

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name mowanettest \
            --icon assets/icon.ico \
            --add-data "ui;ui" \
            app.py
```

Saída: `dist/mowanettest.exe` — arquivo único, portátil, que cria a pasta `hist/` ao lado de si.

---

## 10. Critérios de aceite

- [ ] O `.exe` abre em máquina limpa com Windows 10/11 sem Python instalado
- [ ] Um teste completo entrega download, upload, ping e jitter com valores plausíveis (comparação com Speedtest/Fast.com com desvio ≤ 10%)
- [ ] A pasta `hist/` é criada exatamente no primeiro teste concluído
- [ ] O arquivo gerado segue o padrão `AAAA-MM-DD HH-MM-SS.txt`
- [ ] A tela de histórico lista corretamente todos os `.txt` da pasta
- [ ] Excluir manualmente um `.txt` remove o item da lista após recarregar
- [ ] Um `.txt` inválido na pasta não quebra a tela de histórico
- [ ] A interface permanece responsiva durante todo o teste
- [ ] Sem conexão, o app exibe erro claro e não grava arquivo
- [ ] Tema escuro aplicado em 100% das telas, sem "flash branco" na abertura

---

## 11. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Ausência do runtime WebView2 | App não abre | Detectar na inicialização e orientar o download; ou embarcar o bootstrapper no instalador |
| Antivírus sinalizar o `.exe` do PyInstaller | Falso positivo bloqueia o uso | Assinar o executável; documentar no README |
| Endpoint de medição mudar ou limitar taxa | Testes falham | Interface `SpeedProvider` com provedor alternativo (LibreSpeed) |
| Medição imprecisa em links > 500 Mbps | Resultado subestimado | Aumentar conexões paralelas e tamanho dos blocos conforme a banda detectada |
| Pasta do exe sem permissão de escrita | Histórico não grava | Fallback para `%APPDATA%` já previsto (RF-08 / seção 5.1) |

---

## 12. Roadmap

**v1.0 — MVP**
Tela de teste, tela de histórico, gravação em `hist/`, tema escuro, `.exe` portátil.

**v1.1**
Gráfico de evolução no histórico, filtro por período, exportação para CSV.

**v1.2**
Teste agendado em background com ícone na bandeja, notificação quando a velocidade cair abaixo de um limite configurável.

**v2.0**
Versões para macOS e Linux, seleção manual de servidor, comparação com a velocidade contratada.
