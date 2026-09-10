# 💸 Projeto Trill — Monitor Financeiro Inteligente

> Plataforma web fullstack de controle de gastos mensais com autenticação, metas financeiras, visualização de dados e integração futura com agente de IA via WhatsApp.

---

## 📌 Sobre o Projeto

O **Projeto Trill** é uma aplicação de portfólio desenvolvida para demonstrar habilidades em desenvolvimento fullstack moderno. A plataforma permite que usuários registrem, categorizem e monitorem seus gastos mensais através de um painel interativo com gráficos e métricas em tempo real.

O projeto foi arquitetado para receber, em fases futuras, um **agente inteligente integrado ao WhatsApp**, que permitirá ao usuário registrar gastos, consultar resumos e receber alertas diretamente pelo aplicativo de mensagens — sem precisar abrir o browser.

---

## 🚀 Funcionalidades

### ✅ Implementadas
- **Autenticação completa** — Cadastro e login de usuários com JWT (Bearer Token)
- **CRUD de Gastos** — Criar, listar, editar e excluir transações com valor, descrição, categoria e data
- **CRUD de Receitas (Ganhos)** — Cadastro e gerenciamento de ganhos com recálculo instantâneo de saldo líquido e recebidos totais
- **Meta Mensal** — Definição de orçamento mensal com barra de progresso visual (verde → amarelo → vermelho)
- **Dashboard Interativo** — Visão geral consolidada dos gastos e receitas com cards de resumo (Recebido, Gasto, Saldo Líquido) e histórico unificado de transações
- **Estatísticas & Analytics** — Gráficos interativos (pizza por categoria e barras comparativas usando Recharts) e relatórios de resumos semanais/mensais
- **Agente de IA via WhatsApp** — Bot inteligente integrado com a **Evolution API** e o modelo **Gemini 2.5 Flash** (com saída estruturada via JSON Schema) para interpretar comandos em linguagem natural e responder de forma amigável, possuindo fallback automático para Expressões Regulares
- **Rotas protegidas** — Acesso ao Dashboard apenas com token válido
- **Deploy com Docker** — Infraestrutura multi-containerizada (API FastAPI, Evolution API, Postgres DB do WhatsApp e Cache Redis)

### 🔜 Em desenvolvimento
- **Análises avançadas** — Projeções complexas de tendências de consumo
- **Notificações e alertas** — Avisos de limite de meta emitidos de forma automatizada pelo WhatsApp

---

## 🛠️ Stack Tecnológica

### Backend & Inteligência Artificial
| Tecnologia | Função |
|---|---|
| **FastAPI** | Framework web assíncrono para a API REST |
| **Google Gemini API (2.5 Flash)** | Agente de IA para classificação de intenções e extração estruturada de dados |
| **Evolution API** | Gateway WhatsApp Web para envio de mensagens e recebimento de webhooks |
| **SQLAlchemy** | ORM para mapeamento objeto-relacional |
| **PostgreSQL / Supabase** | Banco de dados relacional principal |
| **Redis** | Armazenamento de cache para a Evolution API |
| **Pydantic v2** | Validação de dados e schemas |
| **python-jose** | Geração e validação de tokens JWT |
| **bcrypt** | Hash seguro de senhas |
| **Poetry** | Gerenciamento de dependências |
| **Docker & Compose** | Containerização e orquestração de toda a infraestrutura |

### Frontend
| Tecnologia | Função |
|---|---|
| **React 19** | Biblioteca de interface de usuário |
| **Vite 5** | Build tool e servidor de desenvolvimento |
| **React Router v7** | Roteamento SPA com rotas protegidas |
| **Recharts** | Gráficos interativos (Pizza + Comparativos) |
| **Axios** | Cliente HTTP com interceptors de autenticação |
| **Lucide React** | Ícones modernos e consistentes |
| **Vanilla CSS** | Estilização customizada com glassmorphism e dark mode |

---

## 📂 Estrutura do Projeto

```
Projeto-Trill/
│
├── app/                          # Backend — FastAPI
│   ├── core/
│   │   ├── config.py             # Configurações globais
│   │   ├── database.py           # Conexão com o banco de dados (SQLAlchemy)
│   │   ├── deps.py               # Dependências injetáveis (ex: get_current_user)
│   │   └── security.py           # Hash de senha e geração de JWT
│   ├── models/
│   │   ├── models.py             # Modelos do banco: User, Gasto e Receita (3NF)
│   │   └── schemas/
│   │       └── schemas.py        # Schemas Pydantic (request/response)
│   ├── services/
│   │   ├── bot.py                # Serviço do agente WhatsApp (Gemini 2.5 + Fallback Regex)
│   │   └── finance.py            # Lógica de análise financeira, comparativos e CRUD
│   └── main.py                   # Rotas de Auth, Gastos, Receitas, Analytics e Webhook
│
├── frontend/                     # Frontend — React + Vite
│   └── src/
│       ├── api/
│       │   └── axios.js          # Instância Axios com interceptores de token
│       ├── pages/
│       │   ├── Login.jsx         # Tela de login e cadastro
│       │   ├── Login.css
│       │   ├── Dashboard.jsx     # Painel principal com receitas, despesas e gráficos
│       │   └── Dashboard.css
│       ├── App.jsx               # Roteamento e PrivateRoute
│       └── main.jsx              # Ponto de entrada do React
│
├── tests/                        # Testes automatizados
├── Dockerfile                    # Imagem Docker do backend
├── docker-compose.yml            # Orquestração de todos os serviços (API, Redis, Evolution)
├── pyproject.toml                # Dependências do Python (Poetry)
└── .env                          # Variáveis de ambiente (não versionado)
```

---

## ⚙️ Como Rodar Localmente

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose
- [Node.js](https://nodejs.org/) (v18+) e npm
- Conta no [Supabase](https://supabase.com/) (ou outro PostgreSQL)
- Conta no [Google AI Studio](https://aistudio.google.com/) (Chave de API do Gemini)

---

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/Projeto-Trill.git
cd Projeto-Trill
```

### 2. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco
SECRET_KEY=sua_chave_secreta_super_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Evolution API ──
EVOLUTION_API_URL=http://evolution_api:8080
EVOLUTION_API_KEY=sua_chave_da_evolution_api
EVOLUTION_INSTANCE=trill-bot

# ── Gemini API ──
GEMINI_API_KEY=sua_chave_da_gemini_api
```

> 💡 Se estiver usando o Supabase, a `DATABASE_URL` pode ser encontrada em **Project Settings → Database → Connection string (URI)**.

### 3. Suba os Serviços com Docker

```bash
docker-compose up --build
```

Isso inicializará 4 serviços locais em paralelo:
* `monitor_gastos_api` (FastAPI em `http://localhost:8000`)
* `evolution_api` (Serviço de WhatsApp em `http://localhost:8080`)
* `evolution_db` (Postgres da Evolution API)
* `trill_redis` (Cache da Evolution API)

Documentação interativa da API: `http://localhost:8000/docs`

### 4. Rode o Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend estará disponível em: `http://localhost:5173`

### 5. Testar sem Celular (Simulador CLI)

Você pode interagir e debugar a lógica do bot, do Gemini e do banco de dados diretamente pelo terminal local, sem precisar de aparelhos de celular ou do Docker rodando. Rode:

```bash
python app/simular_bot.py
```

---

## 🔌 Endpoints da API

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `GET` | `/` | Health check da API | ❌ |
| `POST` | `/register` | Cadastro de novo usuário | ❌ |
| `POST` | `/login` | Login e geração de token JWT | ❌ |
| `GET` | `/users/me` | Dados do usuário autenticado | ✅ |
| `PUT` | `/users/me/meta` | Atualiza a meta mensal | ✅ |
| `GET` | `/gastos/` | Lista todos os gastos do usuário | ✅ |
| `POST` | `/gastos/` | Registra um novo gasto | ✅ |
| `PUT` | `/gastos/{id}` | Edita um gasto existente | ✅ |
| `DELETE` | `/gastos/{id}` | Remove um gasto | ✅ |
| `GET` | `/receitas/` | Lista todas as receitas do usuário | ✅ |
| `POST` | `/receitas/` | Registra uma nova receita | ✅ |
| `PUT` | `/receitas/{id}` | Edita uma receita existente | ✅ |
| `DELETE` | `/receitas/{id}` | Remove uma receita | ✅ |
| `GET` | `/analytics/resumo-mensal` | Resumo financeiro consolidado do mês | ✅ |
| `GET` | `/analytics/por-categoria` | Gastos do mês agrupados por categoria | ✅ |
| `GET` | `/analytics/status-meta` | Status textual da meta de gastos | ✅ |
| `GET` | `/analytics/resumo-semanal` | Resumo de gastos da semana atual com projeções | ✅ |
| `GET` | `/analytics/comparativo` | Comparativo comparado com meses anteriores | ✅ |
| `GET` | `/analytics/completo` | Resumo financeiro unificado completo | ✅ |
| `POST` | `/webhook/whatsapp` | Webhook público que recebe mensagens da Evolution API | ❌ |

---

## 🗺️ Roadmap

- [x] API REST com FastAPI e autenticação JWT
- [x] CRUD completo de gastos por usuário
- [x] CRUD completo de receitas por usuário e exibição de Saldo Líquido
- [x] Dashboard interativo com gráficos e cards adaptados
- [x] Meta mensal com barra de progresso
- [x] Containerização completa multi-serviços com Docker Compose
- [x] Serviço de consolidação financeira (`finance.py`)
- [x] Integração com WhatsApp via Evolution API
- [x] Agente de IA com processamento de linguagem natural (Gemini 2.5 Flash) e fallback de Regex
- [ ] Notificações e alertas automáticos de meta via WhatsApp
- [ ] Testes automatizados com Pytest

---

## 🧠 Arquitetura Integrada — Agente WhatsApp

```
Usuário (WhatsApp)
       │
       ▼
 [Webhook /bot]  ←── FastAPI recebe a mensagem
       │
       ▼
 [bot.py]  ←── Orquestra o agente de IA
       │
       ├──▶ [Agente LLM]  ←── Interpreta a intenção do usuário
       │
       └──▶ [finance.py]  ←── Executa ações no banco de dados
                │
                ▼
         Resposta ao usuário via WhatsApp
```

---


---

