import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LogOut, Plus, DollarSign, Tag, Calendar, Trash2, Edit2, User,
  TrendingUp, TrendingDown, Minus, CalendarDays, BarChart2, Target
} from 'lucide-react';
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, Legend, ResponsiveContainer
} from 'recharts';
import api from '../api/axios';
import './Dashboard.css';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const STATUS_CONFIG = {
  seguro:    { color: '#10B981', bg: 'rgba(16,185,129,0.12)', icon: '✅' },
  atencao:   { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', icon: '⚠️' },
  alerta:    { color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  icon: '🚨' },
  estourado: { color: '#EF4444', bg: 'rgba(239,68,68,0.18)',  icon: '❌' },
  sem_meta:  { color: '#94A3B8', bg: 'rgba(148,163,184,0.1)', icon: 'ℹ️' },
};

const Dashboard = () => {
  const [gastos, setGastos]               = useState([]);
  const [receitas, setReceitas]           = useState([]);
  const [userProfile, setUserProfile]     = useState(null);
  const [analytics, setAnalytics]         = useState(null);
  const [isLoading, setIsLoading]         = useState(true);
  const [activeTab, setActiveTab]         = useState('transacoes');
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

  // Modal de transação (gasto ou receita)
  const [isModalOpen, setIsModalOpen]     = useState(false);
  const [tipoLancamento, setTipoLancamento] = useState('gasto'); // 'gasto' ou 'receita'
  const [novoValor, setNovoValor]         = useState('');
  const [novaDescricao, setNovaDescricao] = useState('');
  const [novaCategoria, setNovaCategoria] = useState('Geral');
  const [novaData, setNovaData]           = useState('');
  const [isSubmitting, setIsSubmitting]   = useState(false);
  const [gastoEmEdicao, setGastoEmEdicao] = useState(null);

  // Modal de meta
  const [isMetaModalOpen, setIsMetaModalOpen]   = useState(false);
  const [novaMeta, setNovaMeta]                 = useState('');
  const [isSubmittingMeta, setIsSubmittingMeta] = useState(false);

  const navigate = useNavigate();

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [gastosRes, receitasRes, userRes, analyticsRes] = await Promise.all([
        api.get('/gastos/'),
        api.get('/receitas/'),
        api.get('/users/me'),
        api.get('/analytics/completo'),
      ]);
      setGastos(gastosRes.data);
      setReceitas(receitasRes.data);
      setUserProfile(userRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      if (error.response?.status === 401) handleLogout();
      console.error('Erro ao buscar dados', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchGastos = async () => {
    try {
      const [gastosRes, receitasRes, analyticsRes] = await Promise.all([
        api.get('/gastos/'),
        api.get('/receitas/'),
        api.get('/analytics/completo'),
      ]);
      setGastos(gastosRes.data);
      setReceitas(receitasRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error('Erro ao buscar transações', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const openModalForCreate = () => {
    setGastoEmEdicao(null);
    setTipoLancamento('gasto');
    setNovoValor(''); setNovaDescricao(''); setNovaCategoria('Geral'); setNovaData('');
    setIsModalOpen(true);
  };

  const openModalForEdit = (transacao) => {
    setGastoEmEdicao(transacao);
    setTipoLancamento(transacao.tipo);
    setNovoValor(transacao.valor);
    setNovaDescricao(transacao.descricao);
    setNovaCategoria(transacao.categoria);
    setNovaData(transacao.data_registro ? new Date(transacao.data_registro).toISOString().split('T')[0] : '');
    setIsModalOpen(true);
  };

  const handleSaveGasto = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = { valor: parseFloat(novoValor), descricao: novaDescricao, categoria: novaCategoria };
      if (novaData) payload.data_registro = `${novaData}T12:00:00Z`;
      
      if (gastoEmEdicao) {
        const endpoint = gastoEmEdicao.tipo === 'gasto' ? `/gastos/${gastoEmEdicao.id}` : `/receitas/${gastoEmEdicao.id}`;
        await api.put(endpoint, payload);
      } else {
        const endpoint = tipoLancamento === 'gasto' ? '/gastos/' : '/receitas/';
        await api.post(endpoint, payload);
      }
      setIsModalOpen(false);
      fetchGastos();
    } catch (error) {
      console.error('Erro ao salvar lançamento', error);
      alert('Erro ao salvar lançamento.');
    } finally { setIsSubmitting(false); }
  };

  const handleDeleteGasto = async (transacao) => {
    const confirmMsg = transacao.tipo === 'gasto' 
      ? 'Tem certeza que deseja deletar este gasto?' 
      : 'Tem certeza que deseja deletar esta receita?';
    if (window.confirm(confirmMsg)) {
      try {
        const endpoint = transacao.tipo === 'gasto' ? `/gastos/${transacao.id}` : `/receitas/${transacao.id}`;
        await api.delete(endpoint);
        fetchGastos();
      } catch (error) { alert('Erro ao deletar item.'); }
    }
  };

  const handleSaveMeta = async (e) => {
    e.preventDefault();
    setIsSubmittingMeta(true);
    try {
      const response = await api.put('/users/me/meta', { meta_mensal: parseFloat(novaMeta) });
      setUserProfile(response.data);
      setIsMetaModalOpen(false);
      fetchGastos();
    } catch (error) { alert('Erro ao salvar a meta.'); }
    finally { setIsSubmittingMeta(false); }
  };

  // ── Dados derivados ──────────────────────────────────────────────
  const resumo    = analytics?.resumo_mensal;
  const statusMeta = analytics?.status_meta;
  const semanal   = analytics?.resumo_semanal;
  const categorias = analytics?.por_categoria || [];
  const comparativo = analytics?.comparativo_3_meses || [];

  const totalGasto = gastos.reduce((acc, curr) => acc + curr.valor, 0);
  const statusCfg  = STATUS_CONFIG[statusMeta?.status || 'sem_meta'];

  const transacoes = [
    ...gastos.map(g => ({ ...g, tipo: 'gasto' })),
    ...receitas.map(r => ({ ...r, tipo: 'receita' }))
  ].sort((a, b) => new Date(b.data_registro || b.data) - new Date(a.data_registro || a.data));

  const variacao = comparativo.length >= 2
    ? comparativo[comparativo.length - 1].variacao_percentual
    : null;

  return (
    <div className="dashboard-container">
      {/* ── Header ── */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Monitor Financeiro</h1>
          <div className="profile-widget">
            <button className="avatar-btn" onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}>
              {userProfile?.nome ? userProfile.nome.charAt(0).toUpperCase() : <User size={20} />}
            </button>
            {isProfileMenuOpen && (
              <div className="profile-dropdown glass-panel">
                <div className="dropdown-header">
                  <strong>{userProfile?.nome?.split(' ')[0] || 'Usuário'}</strong>
                  <span>{userProfile?.email}</span>
                </div>
                <div className="dropdown-divider" />
                <button onClick={handleLogout} className="dropdown-item text-danger">
                  <LogOut size={16} /><span>Sair da conta</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="dashboard-main">

        {/* ── Banner de status da meta ── */}
        {statusMeta && (
          <div className="status-banner" style={{ background: statusCfg.bg, borderColor: statusCfg.color }}>
            <span className="status-banner-icon">{statusCfg.icon}</span>
            <span className="status-banner-msg" style={{ color: statusCfg.color }}>
              {statusMeta.mensagem}
            </span>
          </div>
        )}

        {/* ── Cards de resumo ── */}
        <div className="summary-cards">

          {/* Total geral */}
          <div className="glass-panel summary-card">
            <div className="summary-icon">
              <DollarSign size={24} />
            </div>
            <div className="summary-info">
              <p>Total Gasto (Histórico)</p>
              <h3>R$ {totalGasto.toFixed(2)}</h3>
            </div>
          </div>

          {/* Resumo mensal */}
          {resumo && (
            <div className="glass-panel summary-card">
              <div className="summary-icon" style={{ background: 'rgba(139,92,246,0.2)', color: '#8B5CF6' }}>
                <CalendarDays size={24} />
              </div>
              <div className="summary-info">
                <p>Gasto em {resumo.mes_nome}</p>
                <h3>R$ {resumo.total_gasto.toFixed(2)}</h3>
                <span className="card-sub">{resumo.quantidade_transacoes} transações</span>
              </div>
            </div>
          )}

          {/* Total Recebido (Mês) */}
          {resumo && (
            <div className="glass-panel summary-card">
              <div className="summary-icon" style={{ background: 'rgba(16,185,129,0.2)', color: '#10B981' }}>
                <TrendingUp size={24} />
              </div>
              <div className="summary-info">
                <p>Recebido em {resumo.mes_nome}</p>
                <h3>R$ {resumo.total_receita ? resumo.total_receita.toFixed(2) : '0.00'}</h3>
              </div>
            </div>
          )}

          {/* Saldo Líquido (Mês) */}
          {resumo && (
            <div className="glass-panel summary-card">
              <div className="summary-icon" style={{ 
                background: (resumo.saldo_liquido >= 0) ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                color: (resumo.saldo_liquido >= 0) ? '#10B981' : '#EF4444'
              }}>
                {(resumo.saldo_liquido >= 0) ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
              </div>
              <div className="summary-info">
                <p>Saldo Líquido ({resumo.mes_nome})</p>
                <h3 style={{ color: (resumo.saldo_liquido >= 0) ? '#10B981' : '#EF4444' }}>
                  R$ {resumo.saldo_liquido ? resumo.saldo_liquido.toFixed(2) : '0.00'}
                </h3>
              </div>
            </div>
          )}

          {/* Resumo semanal */}
          {semanal && (
            <div className="glass-panel summary-card">
              <div className="summary-icon" style={{ background: 'rgba(16,185,129,0.2)', color: '#10B981' }}>
                <BarChart2 size={24} />
              </div>
              <div className="summary-info">
                <p>Esta Semana</p>
                <h3>R$ {semanal.total_gasto.toFixed(2)}</h3>
                <span className="card-sub">Média: R$ {semanal.media_diaria.toFixed(2)}/dia</span>
              </div>
            </div>
          )}

          {/* Meta mensal */}
          <div className="glass-panel summary-card meta-card">
            <div className="meta-header">
              <div className="summary-info">
                <p>Meta Mensal</p>
                <h3>{userProfile?.meta_mensal ? `R$ ${userProfile.meta_mensal.toFixed(2)}` : 'Não definida'}</h3>
              </div>
              <button
                className="btn-secondary small-btn"
                onClick={() => { setNovaMeta(userProfile?.meta_mensal || ''); setIsMetaModalOpen(true); }}
              >
                Configurar
              </button>
            </div>
            {userProfile?.meta_mensal && resumo && (
              <div className="meta-progress-container">
                <div className="meta-progress-labels">
                  <span>Gasto no mês: R$ {resumo.total_gasto.toFixed(2)}</span>
                  <span>Restante: R$ {Math.max(userProfile.meta_mensal - resumo.total_gasto, 0).toFixed(2)}</span>
                </div>
                <div className="progress-bar-bg">
                  <div
                    className={`progress-bar-fill ${
                      resumo.total_gasto > userProfile.meta_mensal ? 'danger'
                      : resumo.total_gasto > userProfile.meta_mensal * 0.6 ? 'warning'
                      : 'safe'
                    }`}
                    style={{ width: `${Math.min((resumo.total_gasto / userProfile.meta_mensal) * 100, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="tabs-container">
          {['transacoes', 'estatisticas', 'analytics'].map((tab) => (
            <button
              key={tab}
              className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'transacoes' ? 'Transações' : tab === 'estatisticas' ? 'Gráficos' : 'Analytics'}
            </button>
          ))}
        </div>

        {/* ══════════════ ABA TRANSAÇÕES ══════════════ */}
        {activeTab === 'transacoes' && (
          <div className="gastos-section">
            <div className="section-header">
              <h2>Transações Recentes</h2>
              <button className="btn-primary add-btn" onClick={openModalForCreate}>
                <Plus size={18} /> Novo Lançamento
              </button>
            </div>
            <div className="glass-panel gastos-list">
              {isLoading ? (
                <p className="loading-text">Carregando...</p>
              ) : transacoes.length === 0 ? (
                <p className="empty-state">Nenhuma transação registrada ainda.</p>
              ) : (
                <ul>
                  {transacoes.map((transacao) => (
                    <li key={`${transacao.tipo}-${transacao.id}`} className="gasto-item">
                      <div className="gasto-details">
                        <h4>{transacao.descricao}</h4>
                        <div className="gasto-meta">
                          <span className="tag"><Tag size={12} /> {transacao.categoria}</span>
                          <span className="date">
                            <Calendar size={12} />
                            {new Date(transacao.data_registro).toLocaleDateString('pt-BR')}
                          </span>
                          <span className="tag" style={{
                            backgroundColor: transacao.tipo === 'receita' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                            color: transacao.tipo === 'receita' ? '#10B981' : '#EF4444',
                            fontWeight: 500
                          }}>
                            {transacao.tipo === 'receita' ? 'Receita' : 'Despesa'}
                          </span>
                        </div>
                      </div>
                      <div className="gasto-amount-actions">
                        <div className={`gasto-amount ${transacao.tipo === 'receita' ? 'receita' : ''}`}>
                          {transacao.tipo === 'receita' ? '+' : '-'} R$ {transacao.valor.toFixed(2)}
                        </div>
                        <div className="gasto-actions">
                          <button className="action-btn edit" onClick={() => openModalForEdit(transacao)} title="Editar">
                            <Edit2 size={16} />
                          </button>
                          <button className="action-btn delete" onClick={() => handleDeleteGasto(transacao)} title="Excluir">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* ══════════════ ABA GRÁFICOS ══════════════ */}
        {activeTab === 'estatisticas' && (
          <div className="estatisticas-section">
            <div className="charts-grid">
              <div className="glass-panel chart-container">
                <h3>Gastos por Categoria</h3>
                {categorias.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={categorias} cx="50%" cy="50%" outerRadius={100}
                        dataKey="total" nameKey="categoria"
                        label={({ categoria, percent }) => `${categoria} ${(percent * 100).toFixed(0)}%`}
                      >
                        {categorias.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip
                          formatter={(v, name) => [`R$ ${Number(v).toFixed(2)}`, name]}
                          contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                        />
                        <Legend formatter={(value) => value} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : <p className="empty-state">Adicione gastos para ver os gráficos.</p>}
              </div>

              <div className="glass-panel chart-container">
                <h3>Comparativo Mensal</h3>
                {comparativo.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={comparativo} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="mes" stroke="var(--text-secondary)" />
                      <YAxis stroke="var(--text-secondary)" />
                      <RechartsTooltip
                        formatter={(v) => `R$ ${Number(v).toFixed(2)}`}
                        contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                      />
                      <Bar dataKey="total" fill="var(--accent)" radius={[4, 4, 0, 0]} name="Total" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <p className="empty-state">Adicione gastos para ver o comparativo.</p>}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════ ABA ANALYTICS ══════════════ */}
        {activeTab === 'analytics' && (
          <div className="analytics-section">

            {/* Linha superior: Resumo Mensal + Resumo Semanal */}
            <div className="analytics-row">

              {/* Card: Resumo Mensal */}
              {resumo && (
                <div className="glass-panel analytics-card">
                  <div className="analytics-card-header">
                    <CalendarDays size={20} />
                    <h3>Resumo de {resumo.mes_nome}/{resumo.ano}</h3>
                  </div>
                  <div className="analytics-stat-grid">
                    <div className="analytics-stat">
                      <span>Total Gasto</span>
                      <strong>R$ {resumo.total_gasto.toFixed(2)}</strong>
                    </div>
                    <div className="analytics-stat">
                      <span>Transações</span>
                      <strong>{resumo.quantidade_transacoes}</strong>
                    </div>
                    {resumo.percentual_meta !== null && (
                      <div className="analytics-stat">
                        <span>Meta Utilizada</span>
                        <strong style={{ color: statusCfg.color }}>{resumo.percentual_meta}%</strong>
                      </div>
                    )}
                    {resumo.saldo_restante !== null && (
                      <div className="analytics-stat">
                        <span>Saldo Restante</span>
                        <strong style={{ color: resumo.saldo_restante >= 0 ? '#10B981' : '#EF4444' }}>
                          R$ {resumo.saldo_restante.toFixed(2)}
                        </strong>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Card: Resumo Semanal */}
              {semanal && (
                <div className="glass-panel analytics-card">
                  <div className="analytics-card-header">
                    <BarChart2 size={20} />
                    <h3>Semana Atual</h3>
                  </div>
                  <p className="analytics-period">{semanal.periodo}</p>
                  <div className="analytics-stat-grid">
                    <div className="analytics-stat">
                      <span>Total Gasto</span>
                      <strong>R$ {semanal.total_gasto.toFixed(2)}</strong>
                    </div>
                    <div className="analytics-stat">
                      <span>Transações</span>
                      <strong>{semanal.quantidade_transacoes}</strong>
                    </div>
                    <div className="analytics-stat">
                      <span>Média/dia</span>
                      <strong>R$ {semanal.media_diaria.toFixed(2)}</strong>
                    </div>
                    <div className="analytics-stat">
                      <span>Projeção semana</span>
                      <strong>R$ {semanal.projecao_semana.toFixed(2)}</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Card: Ranking de Categorias */}
            {categorias.length > 0 && (
              <div className="glass-panel analytics-card full-width">
                <div className="analytics-card-header">
                  <Target size={20} />
                  <h3>Ranking de Categorias — {resumo?.mes_nome}</h3>
                </div>
                <div className="categoria-ranking">
                  {categorias.map((cat, i) => (
                    <div key={cat.categoria} className="categoria-row">
                      <div className="categoria-rank-num">#{i + 1}</div>
                      <div className="categoria-info">
                        <div className="categoria-top-row">
                          <span className="categoria-nome">{cat.categoria}</span>
                          <span className="categoria-valor">R$ {cat.total.toFixed(2)}</span>
                        </div>
                        <div className="categoria-bar-bg">
                          <div
                            className="categoria-bar-fill"
                            style={{
                              width: `${cat.percentual}%`,
                              background: COLORS[i % COLORS.length],
                            }}
                          />
                        </div>
                        <div className="categoria-bottom-row">
                          <span>{cat.quantidade} transação{cat.quantidade !== 1 ? 'ões' : ''}</span>
                          <span>{cat.percentual}% do total</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Card: Comparativo Mensal com variação */}
            {comparativo.length > 0 && (
              <div className="glass-panel analytics-card full-width">
                <div className="analytics-card-header">
                  <TrendingUp size={20} />
                  <h3>Comparativo dos Últimos {comparativo.length} Meses</h3>
                </div>
                <div className="comparativo-grid">
                  {comparativo.map((m) => {
                    const vp = m.variacao_percentual;
                    const isUp   = vp > 0;
                    const isDown = vp < 0;
                    return (
                      <div key={`${m.mes}-${m.ano}`} className="comparativo-card glass-panel">
                        <p className="comp-mes">{m.mes_nome}</p>
                        <p className="comp-ano">{m.ano}</p>
                        <p className="comp-total">R$ {m.total.toFixed(2)}</p>
                        {vp !== null && vp !== undefined ? (
                          <div className={`comp-variacao ${isUp ? 'up' : isDown ? 'down' : 'neutral'}`}>
                            {isUp   ? <TrendingUp  size={14} /> :
                             isDown ? <TrendingDown size={14} /> :
                                      <Minus size={14} />}
                            <span>{isUp ? '+' : ''}{vp}%</span>
                          </div>
                        ) : (
                          <span className="comp-variacao neutral">Referência</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* ── Modal Lançamento ── */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="glass-panel modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{gastoEmEdicao ? `Editar ${gastoEmEdicao.tipo === 'gasto' ? 'Despesa' : 'Receita'}` : 'Novo Lançamento'}</h2>
              <button className="close-btn" onClick={() => setIsModalOpen(false)}>&times;</button>
            </div>
            <form onSubmit={handleSaveGasto}>
              {/* Escolha do tipo de lançamento (apenas se for novo lançamento) */}
              {!gastoEmEdicao && (
                <div className="form-group">
                  <label>Tipo de Lançamento</label>
                  <div style={{ display: 'flex', gap: '24px', marginTop: '8px', marginBottom: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem' }}>
                      <input type="radio" name="tipoLancamento" value="gasto" checked={tipoLancamento === 'gasto'} onChange={() => { setTipoLancamento('gasto'); setNovaCategoria('Geral'); }} />
                      Despesa (Gasto)
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem' }}>
                      <input type="radio" name="tipoLancamento" value="receita" checked={tipoLancamento === 'receita'} onChange={() => { setTipoLancamento('receita'); setNovaCategoria('Geral'); }} />
                      Receita (Ganho)
                    </label>
                  </div>
                </div>
              )}
              
              <div className="form-group">
                <label>Valor (R$)</label>
                <input type="number" step="0.01" min="0" className="input-field" placeholder="0.00"
                  value={novoValor} onChange={e => setNovoValor(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Descrição</label>
                <input type="text" className="input-field" placeholder={tipoLancamento === 'gasto' ? 'Ex: Supermercado' : 'Ex: Salário Mensal'}
                  value={novaDescricao} onChange={e => setNovaDescricao(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Categoria</label>
                <select className="input-field" value={novaCategoria} onChange={e => setNovaCategoria(e.target.value)}>
                  {tipoLancamento === 'gasto' ? (
                    <>
                      <option value="Geral">Geral</option>
                      <option value="Alimentação">Alimentação</option>
                      <option value="Transporte">Transporte</option>
                      <option value="Moradia">Moradia</option>
                      <option value="Lazer">Lazer</option>
                      <option value="Saúde">Saúde</option>
                      <option value="Educação">Educação</option>
                    </>
                  ) : (
                    <>
                      <option value="Geral">Geral</option>
                      <option value="Salário">Salário</option>
                      <option value="Investimentos">Investimentos</option>
                      <option value="Freelance">Freelance</option>
                      <option value="Prêmio">Prêmio</option>
                      <option value="Outros">Outros</option>
                    </>
                  )}
                </select>
              </div>
              <div className="form-group">
                <label>Data (Opcional — padrão: Hoje)</label>
                <input type="date" className="input-field" value={novaData}
                  onChange={e => setNovaData(e.target.value)} />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal Meta ── */}
      {isMetaModalOpen && (
        <div className="modal-overlay" onClick={() => setIsMetaModalOpen(false)}>
          <div className="glass-panel modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Configurar Meta Mensal</h2>
              <button className="close-btn" onClick={() => setIsMetaModalOpen(false)}>&times;</button>
            </div>
            <form onSubmit={handleSaveMeta}>
              <div className="form-group">
                <label>Valor da Meta (R$)</label>
                <input type="number" step="0.01" min="0" className="input-field" placeholder="0.00"
                  value={novaMeta} onChange={e => setNovaMeta(e.target.value)} required />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsMetaModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={isSubmittingMeta}>
                  {isSubmittingMeta ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
