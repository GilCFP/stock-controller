from flask import Flask, request, Response, g, session, render_template, redirect, url_for
from flask_bcrypt import Bcrypt
import sqlite3
app = Flask(__name__)
app.secret_key = '1902oskdhjays%@#'
bcrypt = Bcrypt(app)
DB_URL = "estoque.db"

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


def query_table_to_dict(query):#retorna a tabela sql selecionada em json(suporta apenas a tabela tec)
    cursor = g.conn.cursor()
    cursor = cursor.execute(query)
    stock_dict = [{'id': row[0], 'name': row[1], 'quantity':row[2], 'value':row[3], 'damage': row[4]}
                      for row in cursor.fetchall()]
    return stock_dict

def log_user(session_data): #salva as credencias do usuário na variável session para serem usadas posteriormente
    session['user_id'] = session_data[0]
    session['username']= session_data[1]
    return

def altering(query,session,form): #altera a tabela tec conforme a query fornecida e registra no histórico a alteração    
    cursor = g.conn.cursor()
    cursor.execute(query)
    history = """INSERT INTO history (user_id, type, quantity, item_id) VALUES(?,?,?,?)"""
    cursor.execute(history,(session['user_id'], form['type'], form['quantity'], form['code']))
    g.conn.commit()

    

@app.route("/")
def home():#redireciona para o login
    session.clear()
    return redirect(url_for("login"))


@app.route("/login", methods=['GET','POST'])
def login():#efetua o login do usuário
    if request.method == 'POST': #caso seja uma entrada de usuário verifica o login do mesmo
        cursor = g.conn.cursor()
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM user WHERE(username = ?)", (username,))
        user_data = cursor.fetchone()
        if user_data == None: #username não costa no banco de dados
            print("incorrect username")
            return render_template("login.html")
        elif bcrypt.check_password_hash(user_data[2], password):#verifica a senha fornecida com a senha criptografada guardada no sistema
            log_user(user_data)
            return redirect(url_for("index"))#login efetuado com sucesso
        else:
            print("incorrect password")
            return render_template("login.html")#redireciona o usuário para efetuar o login novamente
    else:
        return render_template("login.html")
    

@app.route("/index", methods = ['GET','POST'])
def index():#interpreta solicitações do usuário e retorna dados conforme o solicitado
    match request.method:
        case 'POST':            #interpreta entradas e altera/exibe o banco de dados como uma saída json
            filter = "WHERE("   #inicializa a variável filter
            query = "SELECT * FROM tec"          #inicializa a query
            if session['username'] is None: #caso o usuário não esteja logado
                return redirect(url_for("login"))
            print("codigo:", request.form['code'])
            if len(request.form['name']):       #integralizando os parametros do usuário no filtro
                filter = filter + f" name LIKE '%{request.form['name']}%' AND"
            if len(request.form['code']):       #integralizando os parametros do usuário no filtro
                filter = filter + f" id = {request.form['code']} AND"
            if len(request.form['quantity']):   #integralizando os parametros do usuário no filtro
                filter = filter + f" quantity = {request.form['quantity']} AND"
            if len(request.form['damage']):     #integralizando os parametros do usuário no filtro
                filter = filter + f" damage LIKE '%{request.form['damage']}%' AND"
            if len(request.form['value']):      #integralizando os parametros do usuário no filtro
                filter = filter + f" value = {request.form['value']} AND"
            filter = filter[:-3]    #removendo o "AND" no final da string
            if len(filter) == 3:    #caso o usuário não tenha colocado nenhum parâmetro de entrada "desabilita" o filtro
                filter = ""
            else:
                filter = filter + ")"   #caso tenha parâmetros, é adicionado um parênteses ao final para que funcione corretamente no sql
            match request.form['type']: #considera os variadas opções do usuário
                case "list":    #apenas mostra a tabela de acordo com a solicitação
                    query = f" SELECT * FROM tec {filter}" 
                case "remove":  #decrementa a quantidade de um item selecionado via id
                    if filter:
                        cursor = g.conn.cursor()
                        quantidade = cursor.execute(f"SELECT quantity FROM tec WHERE id = {request.form['code']}")
                        if quantidade.fetchone()[0] < int(request.form['quantity']):
                            return redirect("index")
                        query = f"UPDATE tec SET quantity = quantity - {request.form['quantity']} WHERE id = {request.form['code']}"
                        altering(query,session,request.form)
                        query = "SELECT * FROM tec"
                case "add":     #incrementa a quantidade de um item selecionado via id
                    print("filter:", filter)
                    if filter:
                        print(filter)
                        query = f"UPDATE tec SET quantity = quantity + {request.form['quantity']} WHERE id = {request.form['code']}"
                        altering(query,session,request.form)
                        query = "SELECT * FROM tec"
                        print(request.form)
                case "new":     #adiciona um novo item à db, é necessário que sejam passados todos os parâmetros
                    if filter:
                        print("entrou")
                        for value in request.form:
                            if request.form[value] == "" and value != 'code':
                                return redirect(url_for("index"))
                        values = f"""'{request.form["damage"]}', '{request.form["name"]}', '{request.form["quantity"]}', '{request.form["value"]}'"""
                        query = f"INSERT INTO tec(damage,name,quantity,value) VALUES({values})"
                        altering(query,session,request.form)
                        query = "SELECT * FROM tec"
                case "change":  #altera os valores de um item da tabela(somente altera os atributos que o usuário preencheu os campos)
                    if filter:
                        columns = ""
                        for value in request.form:
                            if value == 'code' and request.form[value] == "":
                                return redirect(url_for("index"))
                            if request.form[value] != "" and value != 'code' and value != 'type':
                                columns += f"{value} = '{request.form[value]}', "
                        columns = columns[:-2]
                        query = f"UPDATE tec SET {columns} WHERE id = {request.form['code']}"
                        altering(query,session,request.form)
                        query = query = "SELECT * FROM tec"
            if filter == "WHERE(":
                return redirect(url_for("index"))
            return query_table_to_dict(query) #retorna o json
        case 'GET':             #redireciona para o login
            if not session.get('username'): 
                return redirect(url_for("login"))
            return render_template("index.html")
        
    


if __name__ == '__main__':
    app.debug = True
    app.run(port=5000)
