<h1 align="center">mowanettest</h1>

<p align="center">
  Teste de velocidade de internet para Windows — leve, portátil e com tema escuro.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/plataforma-Windows%2010%2F11-0F1115?style=flat-square" alt="Plataforma">
  <img src="https://img.shields.io/badge/python-3.11%2B-00D68F?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/licença-MIT-4C8DFF?style=flat-square" alt="Licença">
</p>

---

## Sobre

O **mowanettest** mede download, upload, ping e jitter da sua conexão e guarda cada teste em um arquivo de texto local. Sem anúncios, sem login, sem envio de dados para lugar nenhum.

- Teste completo em cerca de 30 segundos
- Histórico com médias de download e upload
- Executável único, não precisa instalar
- Tema escuro em todas as telas

---

## Como executar

### Opção 1 — Executável (usuário final)

1. Baixe o arquivo `mowanettest.exe`.
2. Coloque-o em uma pasta com permissão de escrita (ex.: `Documentos` ou `Área de Trabalho`).
3. Dê dois cliques.

Pronto. Na primeira vez que um teste terminar, a pasta `hist/` é criada automaticamente ao lado do executável.

> **Windows 10 antigo?** O app usa o runtime **Edge WebView2**, já presente no Windows 11 e nas versões atualizadas do Windows 10. Se o app não abrir, instale-o pelo site da Microsoft e tente novamente.

### Opção 2 — Rodando o código-fonte (desenvolvedor)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/mowanettest.git
cd mowanettest

# 2. Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode o app
python app.py
```

### Opção 3 — Gerando seu próprio executável

```bash
pip install pyinstaller
pyinstaller mowanettest.spec
```

O executável fica em `dist/mowanettest.exe` — arquivo único, portátil, com a interface e o ícone já embutidos.

Para rodar os testes automatizados do parser e do histórico:

```bash
pip install pytest
pytest
```

---

## Como usar

| Tela | O que faz |
|---|---|
| **Teste** | Clique em *Iniciar teste* e aguarde. Os resultados aparecem em cards e são salvos sozinhos. |
| **Histórico** | Lista todos os testes já feitos, do mais recente para o mais antigo, com as médias no topo. |

---

## Onde ficam os resultados

Cada teste vira um arquivo `.txt` dentro da pasta `hist/`, criada no diretório do executável:

```
mowanettest.exe
hist/
├── 2026-09-02 12-01-04.txt
├── 2026-09-05 20-05-56.txt
└── 2026-09-10 15-57-34.txt
```

Conteúdo de um arquivo:

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

São arquivos de texto comuns: dá para abrir no Bloco de Notas, versionar, copiar ou importar em uma planilha. Apagar um arquivo remove o teste do histórico.

> Se o app estiver em uma pasta protegida (como `Program Files`), o histórico é gravado em `%APPDATA%\mowanettest\hist\`.

---

## Requisitos

- Windows 10 (build 1809 ou superior) ou Windows 11, 64 bits
- Conexão com a internet
- Não requer privilégios de administrador

---

## Problemas comuns

| Situação | Solução |
|---|---|
| O app não abre | Instale o runtime Edge WebView2 da Microsoft |
| O antivírus bloqueou o `.exe` | Falso positivo comum em apps empacotados com PyInstaller — libere na quarentena |
| O histórico está vazio | Rode um teste completo; a pasta `hist/` só é criada ao final do primeiro |
| Velocidade abaixo do esperado | Teste por cabo, feche downloads em andamento e repita |

---

## Licença

MIT.
