from flask import Flask, request, Response, g, session, render_template, redirect, url_for
from flask_bcrypt import Bcrypt
import sqlite3

app = Flask(__name__)
app.secret_key = '1902oskdhjays%@#'
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
    try:
        cursor = cursor.execute(query)
    except:
        return redirect(url_for("index"))
    stock_dict = [{'id': row[0], 'serial': row[1], 'modelo':row[2], 'quantidade':row[3], 'defeito':row[4]}
                  for row in cursor.fetchall()]
    return stock_dict


# salva as credencias do usuário na variável session para serem usadas posteriormente
def log_user(session_data):
    session['user_id'] = session_data[0]
    session['username'] = session_data[1]
    return
def login_check():
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
        history, (session['user_id'], form['type'], form['quantidade'], form['code']))
    cursor.execute("DELETE FROM tec WHERE quantidade = 0;")
    g.conn.commit()
#22

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
            print("codigo:", request.form['code'])
            # integralizando os parametros do usuário no filtro
            if len(request.form['modelo']):
                filter = filter + \
                    f" modelo LIKE '%{request.form['modelo']}%' AND"
            # integralizando os parametros do usuário no filtro
            if len(request.form['code']):
                filter = filter + f" id = {request.form['code']} AND"
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
                    # print(query_creator("list",request.form))
                    query = f" SELECT * FROM tec {filter}"
                case "remove":  # decrementa a quantidade de um item selecionado via id
                    if filter:
                        cursor = g.conn.cursor()
                        try:
                            quantidade = cursor.execute(
                                f"SELECT quantidade FROM tec WHERE serial = '{request.form['serial']}'")
                            if quantidade.fetchone()[0] < int(request.form['quantidade']):
                                return redirect("index")
                        except TypeError:
                            return redirect(url_for("index"))
                        query = f"UPDATE tec SET quantidade = quantidade - {request.form['quantidade']} WHERE serial = '{request.form['serial']}'"
                        altering(query, session, request.form)
                        query = "SELECT * FROM tec"
                case "add":  # incrementa a quantidade de um item selecionado via id
                    if filter:
                        print(filter)
                        cursor = g.conn.cursor()
                        query = f"UPDATE tec SET quantidade = quantidade + {request.form['quantidade']} WHERE serial = '{request.form['serial']}'"
                        altering(query, session, request.form)
                        query = "SELECT * FROM tec"
                        print(request.form)
                case "new":  # adiciona um novo item à db, é necessário que sejam passados todos os parâmetros
                    if filter:
                        cursor = g.conn.cursor()
                        # caso ja tenha algo registrado com esse id
                        if cursor.execute("SELECT * FROM tec WHERE serial = ?", (request.form['serial'],)).fetchone():
                            return redirect(url_for("index"))
                        values = ""
                        query = "INSERT INTO tec("
                        for value in request.form:
                            if request.form[value] == "" and value not in ['code', 'defeito']:
                                return redirect(url_for("index"))

                            if value not in ["type", "code"] and request.form[value]:
                                values += f"'{request.form[value]}',"
                                query += f"{value},"
                        values = values[:-1]
                        query = query[:-1] + f") VALUES({values})"
                        print("values:", values)
                        print("query:", query)
                        altering(query, session, request.form)
                        query = "SELECT * FROM tec"
                case "change":  # altera os valores de um item da tabela(somente altera os atributos que o usuário preencheu os campos)
                    if filter:
                        columns = ""
                        for value in request.form:
                            if value == 'code' and request.form[value] == "":
                                return redirect(url_for("index"))
                            if request.form[value] != "" and value not in ['code', 'type']:
                                columns += f"{value} = '{request.form[value]}', "
                        columns = columns[:-2]
                        query = f"UPDATE tec SET {columns} WHERE id = '{request.form['code']}'"
                        altering(query, session, request.form)
                        query = query = "SELECT * FROM tec"
            if filter == "WHERE(":
                return redirect(url_for("index"))
            # retorna o json
            return render_template("table.html", result=query_table_to_dict(query))
        case 'GET':  # redireciona para o login
            if login_check():
                return render_template("index.html")
            return redirect(url_for("login"))

# TODO formated string nos values do SQL
# def query_creator(method, form):
#     filter = "WHERE("
#     inputs = ",("
#     changed = False
#     for value in form:
#         if form[value] and value != "type":
#             if value in ['modelo','defeito']:
#                 filter += f" {value} LIKE %?% AND"
#             else:
#                 filter += f" {value} = ? AND"
#             inputs += f" {form[value]},"
#             changed = True
#     if changed:
#         filter = filter[:-3] + ")"
#         inputs = inputs[:-1] + ")"
#     else:
#         filter = ""
#         inputs = ""
#     match method:
#         case "list":
#             print(inputs)
#             cursor = g.conn.cursor()
#             print(cursor.execute(f"""
#         SELECT * FROM tec""")).fetchone()
#             return f"""
#         'SELECT * FROM tec {filter}'{inputs}
#         """

#adicionar e alterar
if __name__ == '__main__':
    app.debug = True
    app.run(port=5000)
