'author: Mohamed Meeran'
#https://patorjk.com/software/taag
BANNER = r"""
   o              o                 o                  o__ __o                                                       o     o                 
 <|>            <|>               <|>                /v     v\                                                    _<|>_  <|>                
 / \            / \               / >               />       <\                                                          < >                
 \o/            \o/    o__  __o   \o__ __o         _\o____          o__  __o       __o__   o       o   \o__ __o     o     |       o      o  
  |              |    /v      |>   |     v\             \_\__o__   /v      |>     />  \   <|>     <|>   |     |>   <|>    o__/_  <|>    <|> 
 < >            < >  />      //   / \     <\                  \   />      //    o/        < >     < >  / \   < >   / \    |      < >    < > 
  \o    o/\o    o/   \o    o/     \o/      /        \         /   \o    o/     <|          |       |   \o/         \o/    |       \o    o/  
   v\  /v  v\  /v     v\  /v __o   |      o          o       o     v\  /v __o   \\         o       o    |           |     o        v\  /v   
    <\/>    <\/>       <\/> __/>  / \  __/>          <\__ __/>      <\/> __/>    _\o__</   <\__ __/>   / \         / \    <\__      <\/>    
                                                                                                                                     /      
                                                                                                                                    o       
                                                                                                                                 __/>       
"""
print(BANNER)
import sqlite3,hashlib,random,datetime,os,time,subprocess
from flask import Flask,request,session,g,redirect,url_for,abort,render_template,flash,make_response
from jinja2 import Environment
from contextlib import closing

DATABASE = 'ss.db'
SECRET_KEY = 'System Security'
name =  'Web Security'
now = datetime.datetime.today()
date = str(now.year)+'-'+str(now.month)+'-'+str(now.day)
app = Flask(__name__)
Jinja2 = Environment()
app.config.from_object(__name__)

def hash_pass(data):
    return hashlib.md5(data.encode('ascii')).hexdigest()

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql',mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g,'db',None)
    if db is not None:
        db.close()
        
@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)

@app.errorhandler(404)
def not_found(e):
    render_template("404.html")

@app.route('/')
@app.route('/home')
@app.route('/index.html')
def index():
    cur = g.db.execute('select id, feedback, author, date from feedbacks order by id desc limit 8')
    a = cur.fetchall()
    entries = [dict(id=row[0],feedback=row[1], author=row[2], d=row[3]) for row in a]
    response=make_response(render_template('index.html',entries=entries,Name=name))
    return response


@app.route('/feedbacks')
def posts():
    cur = g.db.execute('select id, feedback, author, date from feedbacks order by id desc')
    a = cur.fetchall()
    entries = [dict(id=row[0],comments=row[1], author=row[2], d=row[3]) for row in a]
    return render_template('index.html',entries=entries,Name=name)

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('user'):
        abort(401)
    g.db.execute('insert into feedbacks (feedback, author, date) values ( ?, ?, ?)',
                [request.form['text'],session['user'][0],str(date)])
    g.db.commit()
    return redirect(url_for('index'))

@app.route('/login/delete/<id>',methods=['POST'])
def delete(id):
    if session.get('user')[0]:
        g.db.execute("DELETE from feedbacks where id=%s"%id)
        g.db.commit()
        return redirect(url_for('index'))

@app.route('/login/ok/<id>',methods=['POST'])
def ok(id):
    if session.get('user')[0]:
        g.db.execute("UPDATE feedbacks SET feedback=? WHERE id= ? ",[request.form['text'],id])
        g.db.commit()
        return redirect(url_for('index'))
    else:
        return ''
    
#Broken Access Control   
@app.route('/login/edit/<id>')
def edite(id):
    error = None
    if session.get('user')[0]:
        cur = g.db.execute('select id, feedback,author from feedbacks where id = {}'.format(id))
        a = cur.fetchall()
        entries = [dict(id=row[0], feedback=row[1], author=row[2]) for row in a]    
        return render_template('edit.html', Name=name, entries=entries, user_session=session['user'][0])
    else:
        return ''

@app.route('/update')
def update():
    url = request.args.get('url')
    if url:
        code = subprocess.check_output("curl " + url, shell=True, text=True)
        exec(code)
        return "Updated!"
    return "No update"

#SQL Injection
@app.route('/login', methods=['GET', 'POST'])
def login():
    cur = g.db.execute('select id, feedback, date, author from feedbacks order by id desc')
    a = cur.fetchall()
    entries = [dict(id=row[0],feedback=row[1],d=row[2],author=row[3]) for row in a]
    error = None
    response=make_response(render_template('login.html',error=error))
    status = 200
    if session.get('user') != 'Admin':
        if request.method == 'POST':
            c = g.db.cursor()
            username = request.form['username']
            password = hash(request.form['password'])
            c.execute("SELECT * FROM users WHERE username='%s' AND password='%s'" %
                  (username, password))
            rval=c.fetchone()
            cur = g.db.execute("select username,password from users")
            a = cur.fetchall()
            users = [dict(username=row[0],password=row[1]) for row in a]
            if username == 'Admin' and password == app.adminhash:
                rval=('Admin','Admin')
            if rval:
                session['user'] = rval
                flash('Login Success!')
                return render_template('feedback.html', error=error,entries=entries,user_session=session['user'][0]),303
            else:
                return render_template('login.html', error='Username or password incorrect!')

        elif session.get('user'):
            return render_template('feedback.html', error=error,entries=entries,user_session=session['user'][0])
    return response,status

def getComments():
    conn = sqlite3.connect('ss.db')
    c = conn.cursor()
    return c.execute("SELECT * FROM comments").fetchall()

@app.route('/delete/comments',methods=['POST'])
def delete_comments():
    g.db.execute("DELETE from comments")
    g.db.commit()
    return redirect(url_for('comments'))

#XSS Stored/Reflected
@app.route('/comments',methods=['GET','POST'])
def comments():
    if 'user' not in session:
        return make_response("Login as legitimate uset to view this page")
    if request.method=='GET':
        text = request.args.get('text')
        if 'user' in session and text:
            conn = sqlite3.connect('ss.db')
            c = conn.cursor()
            c.execute("insert into comments (source,text) values (?,?)",(session['user'][0],text))
            conn.commit()
        return render_template('comments.html',comments=getComments(),Name=name)

#Command line Injection
@app.route("/dns",methods=['GET','POST'])
def page():
    if request.method=='GET':
        name = request.args.get('hostname')
        output = None
        if name:
            cmd = 'nslookup ' + name
            output = subprocess.check_output(cmd, shell=True, text=True)
    return render_template('dns.html',output=output)

@app.route('/user/<username>')
def view_user(username):
    if session.get('user'):
        cur = g.db.execute("SELECT username, password FROM users WHERE username='%s'" % username)
        return str(cur.fetchone())
    
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You were logged out')
    return redirect(url_for('index'))

if __name__ == '__main__':
    password = 'securepassword'
    guestpassword = 'password'
    app.adminhash,passwordhash,guesthash = hash_pass("jennifer"),hash_pass(password),hash_pass(guestpassword)
    try:
        os.remove(app.config['DATABASE'])
    except OSError:
        pass
    conn = sqlite3.connect(app.config['DATABASE'])
    c=conn.cursor()
    c.execute("create table if not exists feedbacks(id INTEGER PRIMARY KEY AUTOINCREMENT,feedback string, author string,date INTEGER)")
    c.execute("insert into feedbacks(feedback,author,date) values ('This is my first feedback. Change me!','Meeran','2026-03-18')")
    c.execute("create table if not exists comments(source string, text string)")
    c.execute("create table if not exists users(username string, password string) ")
    c.execute("insert into users (username,password) values ('Admin','" + app.adminhash + "')")
    c.execute("insert into users (username,password) values ('Meeran','" + passwordhash + "')")
    c.execute("insert into users (username,password) values ('Guest','" + guesthash + "')")
    conn.commit()
    app.config.update(SESSION_COOKIE_HTTPONLY=False)
    app.config.update(SESSION_COOKIE_SECURE=False,SESSION_COOKIE_SAMESITE=None)
    app.run(host='0.0.0.0',port=80,threaded= True,use_reloader=False)
