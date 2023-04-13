from flask import Flask, request, Response, g, session, render_template, redirect, url_for
from flask_bcrypt import Bcrypt
from datetime import timedelta
import sqlite3
# TODO JAVASCRIPT fazer com que enquanto os vermelhos estiverem vazios n tenha como apertar enviar. DICA:
# selecionar todas as inputs e filtrar só pelas que tem a background color vermelha
app = Flask(__name__)
app.secret_key = '1902oskdhjays%@#'
app.permanent_session_lifetime = timedelta(seconds=180)
bcrypt = Bcrypt(app)
DB_URL = "estoque.db"
app.jinja_env.globals.update(len=len, list=list)


@app.before_request
def before_request():
    print("Conectando ao Banco")
    conn = sqlite3.connect(DB_URL)
    g.conn = conn


@app.teardown_request
def after_request(exception):
    if g.conn is not None:
        g.conn = None
        print("Desconectando ao banco")


# retorna a tabela sql selecionada em json(suporta apenas a tabela tec)
def query_table_to_dict(query):
    cursor = g.conn.cursor()
    if cursor.execute(query).fetchone() is None:
        print("NÃO PASSOU")
        return False
    try:
        cursor = cursor.execute(query)
    except:
        return False
    stock_dict = [{'id': row[0], 'serial': row[1], 'modelo':row[2], 'quantidade':row[3], 'defeito':row[4]}
                  for row in cursor.fetchall()]
    return stock_dict


# salva as credencias do usuário na variável session para serem usadas posteriormente
def log_user(session_data):
    session['user_id'] = session_data[0]
    session['username'] = session_data[1]
    return


def login_check():
    print("username:", session.get('username'))
    if not session.get('username'):
        return False
    return True

# altera a tabela tec conforme a query fornecida e registra no histórico a alteração


def altering(query, session, form):
    cursor = g.conn.cursor()
    cursor.execute(query)
    print(query)
    history = """INSERT INTO history (user_id, type, quantity, item_id) VALUES(?,?,?,?);"""
    cursor.execute(
        history, (session['user_id'], form['type'], form['quantidade'], form['id']))
    cursor.execute("DELETE FROM tec WHERE quantidade = 0;")
    g.conn.commit()
# 22


@app.route("/")
def home():  # redireciona para o login
    session.clear()
    return redirect(url_for("login"))


@app.route("/login", methods=['GET', 'POST'])
def login():  # efetua o login do usuário
    if request.method == 'POST':  # caso seja uma entrada de usuário verifica o login do mesmo
        cursor = g.conn.cursor()
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM user WHERE(username = ?)", (username,))
        user_data = cursor.fetchone()
        if user_data == None:  # username não costa no banco de dados
            print("incorrect username")
            return render_template("login.html")
        # verifica a senha fornecida com a senha criptografada guardada no sistema
        elif bcrypt.check_password_hash(user_data[2], password):
            log_user(user_data)
            return redirect(url_for("index"))  # login efetuado com sucesso
        else:
            print("incorrect password")
            # redireciona o usuário para efetuar o login novamente
            return render_template("login.html")
    else:
        return render_template("login.html")


@app.route("/index", methods=['GET', 'POST'])
def index():  # interpreta solicitações do usuário e retorna dados conforme o solicitado
    match request.method:
        case 'POST':  # interpreta entradas e altera/exibe o banco de dados como uma saída json
            filter = "WHERE("  # inicializa a variável filter
            query = "SELECT * FROM tec"  # inicializa a query
            if session['username'] is None:  # caso o usuário não esteja logado
                return redirect(url_for("login"))
            # integralizando os parametros do usuário no filtro
            if len(request.form['modelo']):
                filter = filter + \
                    f" modelo LIKE '%{request.form['modelo']}%' AND"
            # integralizando os parametros do usuário no filtro
            if len(request.form['id']):
                filter = filter + f" id = {request.form['id']} AND"
            # integralizando os parametros do usuário no filtro
            if len(request.form['quantidade']):
                filter = filter + \
                    f" quantidade = {request.form['quantidade']} AND"
            # integralizando os parametros do usuário no filtro
            if len(request.form['defeito']):
                filter = filter + \
                    f" defeito LIKE '%{request.form['defeito']}%' AND"
            # integralizando os parametros do usuário no filtro
            if len(request.form['serial']):
                filter = filter + \
                    f" serial LIKE '%{request.form['serial']}%' AND"
            filter = filter[:-3]  # removendo o "AND" no final da string
            if len(filter) == 3:  # caso o usuário não tenha colocado nenhum parâmetro de entrada "desabilita" o filtro
                filter = ""
            else:
                # caso tenha parâmetros, é adicionado um parênteses ao final para que funcione corretamente no sql
                filter = filter + ")"
            match request.form['type']:  # considera os variadas opções do usuário
                case "list":  # apenas mostra a tabela de acordo com a solicitação
                    return render_template("table.html", result=query_creator("list", request.form))
                case "remove":  # decrementa a quantidade de um item selecionado via id
                    result = query_creator("list", request.form)
                    if result:
                        return render_template("table.html", result = result)
                    return redirect(url_for("index"))
                case "add":  # incrementa a quantidade de um item selecionado via id
                    return render_template("table.html", result = query_creator("list", request.form))
                case "new":  # adiciona um novo item à db, é necessário que sejam passados todos os parâmetros
                    result = query_creator("list", request.form)
                    if result:
                        return render_template("table.html", result = result)
                    return redirect(url_for("index"))
                # altera os valores de um item da tabela(somente altera os atributos que o usuário preencheu os campos)
                case "change":
                    result = query_creator("list", request.form)
                    if result:
                        return render_template("table.html", result = result)
                    return redirect(url_for("index"))
                    if filter:
                        columns = ""
                        for value in request.form:
                            if value == 'id' and request.form[value] == "":
                                return redirect(url_for("index"))
                            if request.form[value] != "" and value not in ['id', 'type']:
                                columns += f"{value} = '{request.form[value]}', "
                        columns = columns[:-2]
                        query = f"UPDATE tec SET {columns} WHERE id = '{request.form['id']}'"
                        altering(query, session, request.form)
                        query = query = "SELECT * FROM tec"
            if filter == "WHERE(":
                return redirect(url_for("index"))
            # retorna o json
            result = query_table_to_dict(query)
            if result is False:
                return redirect(url_for("index"))
            return render_template("table.html", result=result)
        case 'GET':  # redireciona para o login
            if login_check():
                return render_template("index.html")
            return redirect(url_for("login"))

# TODO formated string nos values do SQL


def query_creator(method, form):
    filter = "WHERE "
    inputs = []
    default = "SELECT * FROM tec"
    for value in form:
        if form[value] and value != "type":
            if value in ['modelo', 'defeito', 'serial']:
                filter += f"{value} LIKE ? AND "
                inputs.append(f"%{form[value]}%")
            else:
                filter += f"{value} = ? AND "
                inputs.append(form[value])
    if filter != "WHERE ":
        filter = filter[:-5]
    else:
        filter = ""
    cursor = g.conn.cursor()
    match form["type"]:
        case "list":
            query = f"SELECT * FROM tec {filter}"
            print(f"{query},{tuple(inputs)}")
            cursor.execute(query, tuple(inputs))
            return table_to_dict(cursor.fetchall())
        case "add":
            query = f"UPDATE tec SET quantidade = quantidade + ? WHERE serial = ?"
            cursor.execute(query, (form['quantidade'], form['serial']))
            g.conn.commit()
            return table_to_dict(cursor.execute(default).fetchall())
        case "remove":
            quantidade = cursor.execute("SELECT quantidade FROM tec WHERE serial = ?", (form['serial'],)).fetchone()[0]
            print(quantidade,"quantidade", int(form['quantidade']))
            if quantidade < int(form['quantidade']):
                return False
            if quantidade == int(form['quantidade']):
                cursor.execute("DELETE FROM tec WHERE serial = ?",(form["serial"],))
                g.conn.commit()
                return table_to_dict(cursor.execute(default).fetchall())
            query = f"UPDATE tec SET quantidade = quantidade - ? WHERE serial = ?"
            cursor.execute(query,(form['quantidade'], form["serial"]))
            g.conn.commit()
            return table_to_dict(cursor.execute(default).fetchall())
        case "new":
            print("cursor: ", cursor.execute("SELECT * FROM tec WHERE serial = ?", (form['serial'],)).fetchone())
            if cursor.execute("SELECT * FROM tec WHERE serial = ?", (form['serial'],)).fetchone():
                return False
            query = "INSERT INTO tec("
            values = "VALUES ("
            for value in form:
                if value not in ["type", "id"] and form[value]:
                    values+= "?,"
                    query += f"{value},"
            query = query[:-1] + f")"
            values = values[:-1] + ")"
            for i in range(0,len(inputs)):
                inputs[i] = inputs[i].replace("%","")
            cursor.execute(query + values,inputs)
            g.conn.commit()
            return table_to_dict(cursor.execute(default))
        case "change":
            columns = ""
            for value in form:
                if value == 'id' and form[value] == "":
                    return False
                if request.form[value] != "" and value not in ['id', 'type']:
                    columns += f"{value} = ?, "
            columns = columns[:-2]
            query = f"UPDATE tec SET {columns} WHERE id = '?'"
            inputs = inputs.append(form["id"])
            print(cursor.execute(query, tuple(inputs)))
            g.conn.commit()
            return table_to_dict(cursor.execute(default))

def table_to_dict(table):
    stock_dict = [{'id': row[0], 'serial': row[1], 'modelo':row[2], 'quantidade':row[3], 'defeito':row[4]}
                  for row in table]
    return stock_dict


# adicionar e alterar
if __name__ == '__main__':
    app.debug = True
    app.run(port=5000)
