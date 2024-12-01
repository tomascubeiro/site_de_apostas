from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from decimal import Decimal
from mysql.connector import errorcode

app = Flask(__name__)
app.secret_key = 'geleia'

config = {
        'user': 'root',
        'password': 'admin',
        'host': '127.0.0.1',
        'database': 'bet',
        'port': '3306'
    }

def get_db_connection():
        try:
            conn = mysql.connector.connect(**config)
            return conn
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                flash("Erro de acesso: Verifique usuário e senha.", 'error')
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                flash("Banco de dados não existe.", 'error')
            else:
                flash(f"Erro: {err}", 'error')
            return None

@app.route('/')
def landing():
        return render_template('landing.html')

from datetime import datetime, timedelta

@app.route('/home')
def home():
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('landing'))

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT e.*, COUNT(a.id) AS total_apostas
        FROM eventos e
        LEFT JOIN apostas a ON e.id = a.evento_id
        WHERE e.status = 'aprovado' AND e.status != 'finalizado'
        GROUP BY e.id
        ORDER BY total_apostas DESC
        LIMIT 5;
    """)
        eventos_mais_apostados = cursor.fetchall()

        cursor.execute("""
        SELECT *
        FROM eventos
        WHERE status = 'aprovado' AND status != 'finalizado' AND fim_apostas >= NOW()
        ORDER BY fim_apostas ASC
        LIMIT 5;
    """)
        eventos_proximos = cursor.fetchall()

        cursor.execute("""
        SELECT *
        FROM eventos
        WHERE status = 'aprovado' AND status != 'finalizado';
    """)
        eventos_disponiveis = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            'home.html',
            eventos_disponiveis=eventos_disponiveis,
            eventos_mais_apostados=eventos_mais_apostados,
            eventos_proximos=eventos_proximos
        )


@app.route('/searchEvents', methods=['GET'])
def search_events():
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('login'))
        
        query = request.args.get('query', '').strip()
        categoria = request.args.get('categoria', '').strip()
        
        if not query and not categoria:
            flash('Por favor, insira um termo de busca ou selecione uma categoria.', 'warning')
            return redirect(url_for('home'))

        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('home'))
        
        cursor = conn.cursor(dictionary=True)
        try:
            sql_query = """
                SELECT * FROM eventos 
                WHERE status='aprovado' AND status != 'finalizado'
                AND (titulo LIKE %s OR descricao LIKE %s)
            """
            params = [f"%{query}%", f"%{query}%"]
            
            if categoria:
                sql_query += " AND categoria = %s"
                params.append(categoria)
            
            cursor.execute(sql_query, tuple(params))
            eventos = cursor.fetchall()
        except mysql.connector.Error as err:
            flash(f'Erro ao buscar eventos: {err}', 'error')
            eventos = []
        finally:
            cursor.close()
            conn.close()

        if not eventos:
            flash('Nenhum evento encontrado para o termo de busca ou categoria selecionada.', 'info')

        return render_template('home.html', eventos_disponiveis=eventos)

@app.route('/moderator_home')
def moderator_home():
        if 'user_id' not in session or not session.get('is_moderator'):
            flash('Você precisa estar logado como moderador para acessar esta página.', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('landing'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM eventos WHERE status='aguardando_aprovacao'")
        eventos_pendentes = cursor.fetchall()
        cursor.execute("SELECT * FROM eventos WHERE status='aprovado' AND status != 'finalizado'")
        eventos_aprovados = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('moderator_home.html', eventos_pendentes=eventos_pendentes, eventos_aprovados=eventos_aprovados)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
        if request.method == 'POST':
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            data_nascimento = request.form['data_nascimento']
            
            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('signup'))

            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO usuarios (nome, email, senha, data_nascimento, saldo, is_moderator) VALUES (%s, %s, %s, %s, %s, %s)",
                            (nome, email, senha, data_nascimento, 0, False))
                conn.commit()
                flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
            except mysql.connector.Error as err:
                flash(f'Erro ao cadastrar: {err}', 'error')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('login'))
        return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
        if request.method == 'POST':
            email = request.form['email']
            senha = request.form['senha']
            
            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('login'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE email=%s AND senha=%s", (email, senha))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['nome']
                session['is_moderator'] = user['is_moderator']
                if user['is_moderator']:
                    return redirect(url_for('moderator_home'))
                else:
                    return redirect(url_for('home'))
            else:
                flash('Usuário ou senha incorretos.', 'error')
        return render_template('login.html')


@app.route('/addNewEvent', methods=['GET', 'POST'])
def add_new_event():
        if 'user_id' not in session:
            flash('Você precisa estar logado para criar um evento.', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            valor_cota = request.form['valor_cota']
            data_evento = request.form['data_evento']
            inicio_apostas = request.form['inicio_apostas']
            fim_apostas = request.form['fim_apostas']
            categoria = request.form['categoria']
            
            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('add_new_event'))

            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO eventos (titulo, descricao, valor_cota, data_evento, inicio_apostas, fim_apostas, criador_id, status, categoria) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (titulo, descricao, valor_cota, data_evento, inicio_apostas, fim_apostas, session['user_id'], 'aguardando_aprovacao', categoria))
                conn.commit()
                flash('Evento criado com sucesso! Aguarde aprovação.', 'success')
            except mysql.connector.Error as err:
                flash(f'Erro ao criar evento: {err}', 'error')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('home'))
        return render_template('add_event.html')


@app.route('/addFunds', methods=['GET', 'POST'])
def add_funds():
        if 'user_id' not in session:
            flash('Você precisa estar logado para adicionar fundos.', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            valor = request.form['valor']
            
            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('add_funds'))

            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE usuarios SET saldo = saldo + %s WHERE id = %s", (valor, session['user_id']))
                conn.commit()
                flash('Fundos adicionados com sucesso!', 'success')
            except mysql.connector.Error as err:
                flash(f'Erro ao adicionar fundos: {err}', 'error')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('wallet'))
        return render_template('add_funds.html')


@app.route('/wallet')
def wallet():
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar a carteira.', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('home'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT saldo FROM usuarios WHERE id=%s", (session['user_id'],))
        saldo = cursor.fetchone()['saldo']
        cursor.execute("SELECT * FROM apostas WHERE usuario_id=%s", (session['user_id'],))
        apostas = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('wallet.html', saldo=saldo, apostas=apostas)

def calcular_taxa(valor):
        if valor <= 100:
            return valor * Decimal(0.04)
        elif 101 <= valor <= 1000:
            return valor * Decimal(0.03)
        elif 1001 <= valor <= 5000:
            return valor * Decimal(0.02)
        elif 5001 <= valor <= 100000:
            return valor * Decimal(0.01)
        else:
            return Decimal(0)

def total_sacado_hoje(usuario_id, conn):
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT SUM(valor_saque) AS total_sacado
            FROM saques
            WHERE usuario_id = %s AND DATE(data_saque) = CURDATE()
        """, (usuario_id,))
        resultado = cursor.fetchone()
        cursor.close()
        return resultado['total_sacado'] if resultado['total_sacado'] else Decimal(0)

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar a funcionalidade de saque.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('wallet'))

        if request.method == 'POST':
            try:
                valor_saque = Decimal(request.form['valor_saque'])
                banco = request.form['banco']
                agencia = request.form['agencia']
                conta = request.form['conta']
                chave_pix = request.form.get('chave_pix', None)

                total_sacado = total_sacado_hoje(session['user_id'], conn)
                if total_sacado + valor_saque > Decimal(101000):
                    flash('O valor máximo de saque por dia é R$ 101.000,00.', 'error')
                    return redirect(url_for('withdraw'))

                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT saldo FROM usuarios WHERE id = %s", (session['user_id'],))
                usuario = cursor.fetchone()
                if not usuario:
                    flash('Usuário não encontrado.', 'error')
                    return redirect(url_for('wallet'))

                saldo_atual = usuario['saldo']

                taxa = calcular_taxa(valor_saque)
                total_deducao = valor_saque + taxa

                if saldo_atual < total_deducao:
                    flash('Saldo insuficiente para realizar o saque.', 'error')
                    return redirect(url_for('withdraw'))

                novo_saldo = saldo_atual - total_deducao
                cursor.execute("UPDATE usuarios SET saldo = %s WHERE id = %s", (novo_saldo, session['user_id']))
                cursor.execute("""
                    INSERT INTO saques (usuario_id, valor_saque, taxa, banco, agencia, conta, chave_pix)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (session['user_id'], valor_saque, taxa, banco, agencia, conta, chave_pix))
                conn.commit()

                flash(f'Saque de R$ {valor_saque:.2f} realizado com sucesso! Taxa aplicada: R$ {taxa:.2f}', 'success')
                return redirect(url_for('wallet'))
            except Exception as e:
                flash(f'Erro ao processar o saque: {e}', 'error')
            finally:
                conn.close()
                
        return render_template('withdraw.html')


@app.route('/betOnEvent/<int:event_id>', methods=['GET', 'POST'])
def bet_on_event(event_id):
        if 'user_id' not in session:
            flash('Você precisa estar logado para fazer uma aposta.', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            valor_aposta = request.form['valor_aposta']
            escolha = request.form['escolha']
            
            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('bet_on_event', event_id=event_id))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT saldo FROM usuarios WHERE id=%s", (session['user_id'],))
            saldo = cursor.fetchone()['saldo']
            
            if saldo >= float(valor_aposta):
                try:
                    cursor.execute("INSERT INTO apostas (evento_id, usuario_id, valor, escolha) VALUES (%s, %s, %s, %s)",
                                (event_id, session['user_id'], valor_aposta, escolha))
                    cursor.execute("UPDATE usuarios SET saldo = saldo - %s WHERE id = %s", (valor_aposta, session['user_id']))
                    conn.commit()
                    flash('Aposta realizada com sucesso!', 'success')
                except mysql.connector.Error as err:
                    flash(f'Erro ao realizar aposta: {err}', 'error')
                finally:
                    cursor.close()
                    conn.close()
            else:
                flash('Saldo insuficiente para realizar a aposta.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('bet_on_event', event_id=event_id))
            return redirect(url_for('home'))
        
        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('home'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM eventos WHERE id=%s AND status != 'finalizado'", (event_id,))
        evento = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('bet_on_event.html', evento=evento)


@app.route('/evaluateEvent/<int:event_id>', methods=['GET', 'POST'])
def evaluate_event(event_id):
        if 'user_id' not in session or not session.get('is_moderator'):
            flash('Você precisa estar logado como moderador para acessar esta página.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            status = request.form['status']
            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('moderator_home'))

            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE eventos SET status=%s WHERE id=%s", (status, event_id))
                conn.commit()
                flash('Evento avaliado com sucesso!', 'success')
            except mysql.connector.Error as err:
                flash(f'Erro ao avaliar evento: {err}', 'error')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('moderator_home'))

        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('moderator_home'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM eventos WHERE id=%s", (event_id,))
        evento = cursor.fetchone()
        cursor.close()
        conn.close()

        return render_template('evaluate_event.html', evento=evento)

@app.route('/finishEvent/<int:event_id>', methods=['GET', 'POST'])
def finish_event(event_id):
        if 'user_id' not in session or not session.get('is_moderator'):
            flash('Você precisa estar logado como moderador para acessar esta página.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            resultado = request.form['resultado']

            conn = get_db_connection()
            if conn is None:
                flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
                return redirect(url_for('moderator_home'))

            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM apostas WHERE evento_id=%s AND escolha=%s", (event_id, resultado))
                apostas_vencedoras = cursor.fetchall()
                cursor.execute("SELECT SUM(valor) as total_apostado FROM apostas WHERE evento_id=%s", (event_id,))
                total_apostado = cursor.fetchone()['total_apostado']
                
                if apostas_vencedoras:
                    total_vencedores = sum([aposta['valor'] for aposta in apostas_vencedoras])
                    for aposta in apostas_vencedoras:
                        premio = (aposta['valor'] / total_vencedores) * total_apostado
                        cursor.execute("UPDATE usuarios SET saldo = saldo + %s WHERE id = %s", (premio, aposta['usuario_id']))
                cursor.execute("UPDATE eventos SET status='finalizado' WHERE id=%s", (event_id,))
                conn.commit()
                flash('Evento finalizado e prêmios distribuídos com sucesso!', 'success')
            except mysql.connector.Error as err:
                flash(f'Erro ao finalizar evento: {err}', 'error')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('moderator_home'))

        conn = get_db_connection()
        if conn is None:
            flash('Erro ao conectar ao banco de dados. Por favor, tente mais tarde.', 'error')
            return redirect(url_for('moderator_home'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM eventos WHERE id=%s", (event_id,))
        evento = cursor.fetchone()
        cursor.close()
        conn.close()

        return render_template('finish_event.html', evento=evento)

@app.route('/logout')
def logout():
        session.clear()
        flash('Logout realizado com sucesso!', 'success')
        return redirect(url_for('landing'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)