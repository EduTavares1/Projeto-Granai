import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import './Login.css';

const Login = () => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [nome, setNome] = useState('');
  const [telefone, setTelefone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setIsLoading(true);

    try {
      if (isRegistering) {
        // Fluxo de Cadastro
        await api.post('/register', {
          email: email,
          password: password,
          nome: nome,
          telefone: telefone
        });
        
        setSuccessMsg('Conta criada com sucesso! Você já pode entrar.');
        setIsRegistering(false); // Volta para a tela de login
        setPassword(''); // Limpa a senha por segurança
      } else {
        // Fluxo de Login
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post('/login', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });

      // Salva o token no LocalStorage
        localStorage.setItem('token', response.data.access_token);
        
        // Redireciona para o Dashboard (somente no fluxo de login)
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao processar requisição. Verifique os dados.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    setIsRegistering(!isRegistering);
    setError('');
    setSuccessMsg('');
  };

  return (
    <div className="login-container">
      <div className="glass-panel login-card">
        <div className="login-header">
          <h2>Projeto Trill</h2>
          <p>{isRegistering ? 'Crie sua nova conta' : 'Acesse seu painel financeiro'}</p>
        </div>

        {error && <div className="error-message">{error}</div>}
        {successMsg && <div className="success-message">{successMsg}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          {isRegistering && (
            <>
              <div className="form-group">
                <label htmlFor="nome">Nome de Usuário</label>
                <input
                  type="text"
                  id="nome"
                  className="input-field"
                  placeholder="Ex: João Silva"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  required={isRegistering}
                />
              </div>

              <div className="form-group">
                <label htmlFor="telefone">Telefone (WhatsApp)</label>
                <input
                  type="text"
                  id="telefone"
                  className="input-field"
                  placeholder="(11) 99999-9999"
                  value={telefone}
                  onChange={(e) => setTelefone(e.target.value)}
                  required={isRegistering}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="email">E-mail</label>
            <input
              type="email"
              id="email"
              className="input-field"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Senha</label>
            <input
              type="password"
              id="password"
              className="input-field"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary login-btn" disabled={isLoading}>
            {isLoading ? 'Processando...' : (isRegistering ? 'Cadastrar' : 'Entrar')}
          </button>
        </form>

        <div className="toggle-mode">
          <p>
            {isRegistering ? 'Já tem uma conta?' : 'Ainda não tem conta?'}
            <button type="button" className="toggle-btn" onClick={toggleMode}>
              {isRegistering ? ' Faça login aqui' : ' Cadastre-se grátis'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
