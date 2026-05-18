import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Plus, DollarSign, Tag, Calendar, Trash2, Edit2, User } from 'lucide-react';
import api from '../api/axios';
import './Dashboard.css';

const Dashboard = () => {
  const [gastos, setGastos] = useState([]);
  const [userProfile, setUserProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  
  // Estados do Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [novoValor, setNovoValor] = useState('');
  const [novaDescricao, setNovaDescricao] = useState('');
  const [novaCategoria, setNovaCategoria] = useState('Geral');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [gastoEmEdicao, setGastoEmEdicao] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [gastosResponse, userResponse] = await Promise.all([
        api.get('/gastos/'),
        api.get('/users/me')
      ]);
      setGastos(gastosResponse.data);
      setUserProfile(userResponse.data);
    } catch (error) {
      if (error.response?.status === 401) {
        handleLogout();
      }
      console.error('Erro ao buscar dados', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchGastos = async () => {
    try {
      const response = await api.get('/gastos/');
      setGastos(response.data);
    } catch (error) {
      console.error('Erro ao buscar gastos', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const openModalForCreate = () => {
    setGastoEmEdicao(null);
    setNovoValor('');
    setNovaDescricao('');
    setNovaCategoria('Geral');
    setIsModalOpen(true);
  };

  const openModalForEdit = (gasto) => {
    setGastoEmEdicao(gasto);
    setNovoValor(gasto.valor);
    setNovaDescricao(gasto.descricao);
    setNovaCategoria(gasto.categoria);
    setIsModalOpen(true);
  };

  const handleSaveGasto = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        valor: parseFloat(novoValor),
        descricao: novaDescricao,
        categoria: novaCategoria
      };

      if (gastoEmEdicao) {
        await api.put(`/gastos/${gastoEmEdicao.id}`, payload);
      } else {
        await api.post('/gastos/', payload);
      }
      
      // Fecha o modal e recarrega a lista
      setIsModalOpen(false);
      fetchGastos();
    } catch (error) {
      console.error('Erro ao salvar gasto', error);
      alert('Erro ao salvar o gasto.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteGasto = async (id) => {
    if (window.confirm('Tem certeza que deseja deletar este gasto?')) {
      try {
        await api.delete(`/gastos/${id}`);
        fetchGastos();
      } catch (error) {
        console.error('Erro ao deletar gasto', error);
        alert('Erro ao deletar gasto.');
      }
    }
  };

  const totalGasto = gastos.reduce((acc, curr) => acc + curr.valor, 0);

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Monitor Financeiro</h1>
          
          <div className="profile-widget">
            <button 
              className="avatar-btn" 
              onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
            >
              {userProfile?.nome ? userProfile.nome.charAt(0).toUpperCase() : <User size={20} />}
            </button>

            {isProfileMenuOpen && (
              <div className="profile-dropdown glass-panel">
                <div className="dropdown-header">
                  <strong>{userProfile?.nome ? userProfile.nome.split(' ')[0] : 'Usuário'}</strong>
                  <span>{userProfile?.email}</span>
                </div>
                <div className="dropdown-divider"></div>
                <button onClick={handleLogout} className="dropdown-item text-danger">
                  <LogOut size={16} />
                  <span>Sair da conta</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="dashboard-main">
        {/* Resumo Card */}
        <div className="summary-cards">
          <div className="glass-panel summary-card">
            <div className="summary-icon">
              <DollarSign size={24} />
            </div>
            <div className="summary-info">
              <p>Total Gasto</p>
              <h3>R$ {totalGasto.toFixed(2)}</h3>
            </div>
          </div>
        </div>

        {/* Lista de Gastos */}
        <div className="gastos-section">
          <div className="section-header">
            <h2>Transações Recentes</h2>
            <button className="btn-primary add-btn" onClick={openModalForCreate}>
              <Plus size={18} /> Novo Gasto
            </button>
          </div>

          <div className="glass-panel gastos-list">
            {isLoading ? (
              <p className="loading-text">Carregando...</p>
            ) : gastos.length === 0 ? (
              <p className="empty-state">Nenhum gasto registrado ainda.</p>
            ) : (
              <ul>
                {gastos.map((gasto) => (
                  <li key={gasto.id} className="gasto-item">
                    <div className="gasto-details">
                      <h4>{gasto.descricao}</h4>
                      <div className="gasto-meta">
                        <span className="tag">
                          <Tag size={12} /> {gasto.categoria}
                        </span>
                        <span className="date">
                          <Calendar size={12} /> 
                          {new Date(gasto.data_registro).toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                    </div>
                    <div className="gasto-amount-actions">
                      <div className="gasto-amount">
                        R$ {gasto.valor.toFixed(2)}
                      </div>
                      <div className="gasto-actions">
                        <button className="action-btn edit" onClick={() => openModalForEdit(gasto)} title="Editar">
                          <Edit2 size={16} />
                        </button>
                        <button className="action-btn delete" onClick={() => handleDeleteGasto(gasto.id)} title="Excluir">
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
      </main>

      {/* Modal de Novo Gasto */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="glass-panel modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{gastoEmEdicao ? 'Editar Gasto' : 'Novo Gasto'}</h2>
              <button className="close-btn" onClick={() => setIsModalOpen(false)}>&times;</button>
            </div>
            
            <form onSubmit={handleSaveGasto}>
              <div className="form-group">
                <label>Valor (R$)</label>
                <input 
                  type="number" 
                  step="0.01" 
                  min="0"
                  className="input-field" 
                  placeholder="0.00"
                  value={novoValor}
                  onChange={e => setNovoValor(e.target.value)}
                  required 
                />
              </div>
              <div className="form-group">
                <label>Descrição</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="Ex: Supermercado"
                  value={novaDescricao}
                  onChange={e => setNovaDescricao(e.target.value)}
                  required 
                />
              </div>
              <div className="form-group">
                <label>Categoria</label>
                <select 
                  className="input-field"
                  value={novaCategoria}
                  onChange={e => setNovaCategoria(e.target.value)}
                >
                  <option value="Geral">Geral</option>
                  <option value="Alimentação">Alimentação</option>
                  <option value="Transporte">Transporte</option>
                  <option value="Moradia">Moradia</option>
                  <option value="Lazer">Lazer</option>
                </select>
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
    </div>
  );
};

export default Dashboard;
