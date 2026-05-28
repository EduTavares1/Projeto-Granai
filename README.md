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
- **Meta Mensal** — Definição de orçamento mensal com barra de progresso visual (verde → amarelo → vermelho)
- **Dashboard Interativo** — Visão geral dos gastos com cards de resumo e lista de transações
- **Estatísticas** — Gráficos de pizza (por categoria) e barras comparativas usando Recharts
- **Rotas protegidas** — Acesso ao Dashboard apenas com token válido
- **Deploy com Docker** — Backend containerizado com Uvicorn e suporte a auto-reload

### 🔜 Em desenvolvimento
- **Agente de IA via WhatsApp** — Bot inteligente que interpreta comandos em linguagem natural
- **Análises avançadas** — Relatórios mensais, tendências e previsão de gastos
- **Notificações e alertas** — Avisos automáticos ao atingir a meta mensal

---

## 🛠️ Stack Tecnológica

### Backend
| Tecnologia | Função |
|---|---|
| **FastAPI** | Framework web para a API REST |
| **SQLAlchemy** | ORM para mapeamento objeto-relacional |
| **PostgreSQL / Supabase** | Banco de dados relacional em nuvem |
| **Pydantic v2** | Validação de dados e schemas |
| **python-jose** | Geração e validação de tokens JWT |
| **bcrypt** | Hash seguro de senhas |
| **Poetry** | Gerenciamento de dependências |
| **Docker** | Containerização do backend |

### Frontend
| Tecnologia | Função |
|---|---|
| **React 19** | Biblioteca de interface de usuário |
| **Vite 5** | Build tool e servidor de desenvolvimento |
| **React Router v7** | Roteamento SPA com rotas protegidas |
| **Recharts** | Gráficos interativos (Pizza + Barras) |
| **Axios** | Cliente HTTP para consumo da API |
| **Lucide React** | Ícones modernos e consistentes |
| **Vanilla CSS** | Estilização com glassmorphism e tema escuro |

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
│   │   ├── models.py             # Modelos do banco: User e Gasto
│   │   └── schemas/
│   │       └── schemas.py        # Schemas Pydantic (request/response)
│   ├── services/
│   │   ├── bot.py                # [Em desenvolvimento] Serviço do agente WhatsApp
│   │   └── finance.py            # [Em desenvolvimento] Lógica de análise financeira
│   └── main.py                   # Ponto de entrada da API (rotas e middlewares)
│
├── frontend/                     # Frontend — React + Vite
│   └── src/
│       ├── api/
│       │   └── axios.js          # Instância Axios com interceptors de token
│       ├── pages/
│       │   ├── Login.jsx         # Tela de login e cadastro
│       │   ├── Login.css
│       │   ├── Dashboard.jsx     # Painel principal do usuário
│       │   └── Dashboard.css
│       ├── App.jsx               # Roteamento e PrivateRoute
│       └── main.jsx              # Ponto de entrada do React
│
├── tests/                        # Testes automatizados
├── Dockerfile                    # Imagem Docker do backend
├── docker-compose.yml            # Orquestração dos serviços
├── pyproject.toml                # Dependências do Python (Poetry)
└── .env                          # Variáveis de ambiente (não versionado)
```

---

## ⚙️ Como Rodar Localmente

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose
- [Node.js](https://nodejs.org/) (v18+) e npm
- Conta no [Supabase](https://supabase.com/) (ou outro PostgreSQL)

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
```

> 💡 Se estiver usando o Supabase, a `DATABASE_URL` pode ser encontrada em **Project Settings → Database → Connection string (URI)**.

### 3. Suba o Backend com Docker

```bash
docker-compose up --build
```

A API estará disponível em: `http://localhost:8000`

Documentação interativa: `http://localhost:8000/docs`

### 4. Rode o Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend estará disponível em: `http://localhost:5173`

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

---

## 🗺️ Roadmap

- [x] API REST com FastAPI e autenticação JWT
- [x] CRUD completo de gastos por usuário
- [x] Dashboard interativo com gráficos
- [x] Meta mensal com barra de progresso
- [x] Containerização com Docker
- [ ] Serviço de análise financeira (`finance.py`)
- [ ] Integração com WhatsApp via API
- [ ] Agente de IA com processamento de linguagem natural
- [ ] Notificações automáticas de limite de meta
- [ ] Testes automatizados com Pytest

---

## 🧠 Arquitetura Futura — Agente WhatsApp

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

