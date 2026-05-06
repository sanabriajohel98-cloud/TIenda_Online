from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bookglace_pro")

# 📦 DB - PostgreSQL en producción, SQLite en local
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # Render/Heroku usa postgres://, convertir a postgresql:// para SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bookglace.db"

app.config["UPLOAD_FOLDER"] = "static/images"

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 📁 Servir imágenes
@app.route('/static/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

# 👤 USUARIOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

# 📦 PRODUCTOS
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50))
    nombre = db.Column(db.String(100))
    precio = db.Column(db.Float)
    stock = db.Column(db.Integer)
    imagen = db.Column(db.String(200))

# 📊 VENTAS
class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    producto = db.Column(db.String(100))
    cantidad = db.Column(db.Integer, default=1)
    total = db.Column(db.Float)
    cliente = db.Column(db.String(100))

# 🧾 TICKETS
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    items = db.Column(db.Text)  # JSON con los items
    total = db.Column(db.Float)
    cliente = db.Column(db.String(100))

# 🔧 DIAGNÓSTICO
@app.route("/debug")
def debug():
    try:
        db.create_all()
        return f"✅ DB OK. Tablas: {[t.__tablename__ for t in db.metadata.tables.values()]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"



# 🔐 LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["pass"]

        # ADMIN
        if user == "admin" and password == "1234":
            session["role"] = "admin"
            return redirect("/admin")

        # CLIENTE
        u = Usuario.query.filter_by(nombre=user, password=password).first()
        if u:
            session["role"] = "cliente"
            session["user"] = user
            return redirect("/tienda")

        return "❌ Error login"

    return render_template("login.html")

# 📝 REGISTRO
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["user"]
        password = request.form["pass"]

        nuevo = Usuario(nombre=nombre, password=password)
        db.session.add(nuevo)
        db.session.commit()

        return redirect("/")

    return render_template("registro.html")

# ⚙️ ADMIN
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("role") != "admin":
        return redirect("/")

    if request.method == "POST":
        codigo = request.form.get("codigo", "")
        nombre = request.form["nombre"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        imagen = request.files["imagen"]

        ruta = os.path.join(app.config["UPLOAD_FOLDER"], imagen.filename)
        imagen.save(ruta)

        p = Producto(
            codigo=codigo,
            nombre=nombre,
            precio=float(precio),
            stock=int(stock),
            imagen=imagen.filename
        )

        db.session.add(p)
        db.session.commit()

    productos = Producto.query.all()
    return render_template("admin.html", productos=productos)

# ✏️ EDITAR PRODUCTO
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    p = Producto.query.get(id)
    
    if request.method == "POST":
        p.codigo = request.form.get("codigo", "")
        p.nombre = request.form["nombre"]
        p.precio = float(request.form["precio"])
        p.stock = int(request.form["stock"])
        
        if request.files["imagen"].filename:
            imagen = request.files["imagen"]
            ruta = os.path.join(app.config["UPLOAD_FOLDER"], imagen.filename)
            imagen.save(ruta)
            p.imagen = imagen.filename
        
        db.session.commit()
        return redirect("/admin")
    
    return render_template("editar.html", producto=p)

# 🗑️ ELIMINAR PRODUCTO
@app.route("/eliminar/<int:id>")
def eliminar(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    p = Producto.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
    
    return redirect("/admin")

# 🏪 TIENDA
@app.route("/tienda")
def tienda():
    productos = Producto.query.all()
    return render_template("tienda.html", productos=productos)

# 🔍 BUSCAR PRODUCTOS (para caja)
@app.route("/buscar")
def buscar():
    q = request.args.get("q", "")
    if q:
        productos = Producto.query.filter(
            (Producto.nombre.ilike(f"%{q}%")) | 
            (Producto.codigo.ilike(f"%{q}%"))
        ).all()
    else:
        productos = Producto.query.all()
    return render_template("caja.html", caja=session.get("caja", []), total=sum(p["precio"] for p in session.get("caja", [])), productos=productos)

# 🛒 CAJA
@app.route("/caja")
def caja():
    if session.get("role") != "admin":
        return redirect("/")

    caja = session.get("caja", [])
    total = sum(p["precio"] for p in caja)

    productos = Producto.query.all()

    return render_template("caja.html", caja=caja, total=total, productos=productos)

# ➕ AGREGAR A CAJA
@app.route("/agregar/<int:id>")
def agregar(id):
    p = Producto.query.get(id)

    caja = session.get("caja", [])
    
    # Buscar si el producto ya existe
    encontrado = False
    for item in caja:
        if item["nombre"] == p.nombre:
            item["cantidad"] = item.get("cantidad", 1) + 1
            item["precio"] = float(p.precio) * item["cantidad"]
            encontrado = True
            break
    
    if not encontrado:
        caja.append({
            "nombre": p.nombre,
            "precio": float(p.precio),
            "cantidad": 1,
            "precio_unitario": float(p.precio)
        })

    session["caja"] = caja
    session.modified = True

    return redirect("/caja")

# ✏️ ACTUALIZAR CANTIDAD
@app.route("/actualizar_cantidad/<int:index>", methods=["POST"])
def actualizar_cantidad(index):
    cantidad = int(request.form.get("cantidad", 1))
    caja = session.get("caja", [])
    
    if 0 <= index < len(caja):
        if cantidad > 0:
            caja[index]["cantidad"] = cantidad
            caja[index]["precio"] = caja[index].get("precio_unitario", caja[index]["precio"] / caja[index].get("cantidad", 1)) * cantidad
        else:
            caja.pop(index)
    
    session["caja"] = caja
    session.modified = True
    
    return redirect("/caja")

# ❌ QUITAR DE CAJA
@app.route("/quitar/<int:index>")
def quitar(index):
    caja = session.get("caja", [])
    
    if 0 <= index < len(caja):
        caja.pop(index)
        session["caja"] = caja
        session.modified = True
    
    return redirect("/caja")

# 🗑️ LIMPIAR CAJA
@app.route("/limpiar")
def limpiar():
    session["caja"] = []
    return redirect("/caja")

# 💰 COBRAR
@app.route("/cobrar", methods=["GET", "POST"])
def cobrar():
    caja = session.get("caja", [])
    total = sum(p["precio"] for p in caja)
    
    if request.method == "POST":
        cliente = request.form.get("cliente", "")
    else:
        cliente = ""

    for item in caja:
        # Registrar venta
        v = Venta(producto=item["nombre"], total=item["precio"], cantidad=item.get("cantidad", 1), cliente=cliente)
        db.session.add(v)
        
        # Descontar stock
        producto = Producto.query.filter_by(nombre=item["nombre"]).first()
        if producto and producto.stock > 0:
            producto.stock -= 1

    # Guardar ticket en la base de datos
    ticket = Ticket(
        fecha=datetime.now(),
        items=json.dumps(caja),
        total=total,
        cliente=cliente
    )
    db.session.add(ticket)
    db.session.commit()

    session["ticket"] = caja
    session["ticket_total"] = total
    session["ticket_cliente"] = cliente
    session["caja"] = []

    return redirect("/ticket")

# 🧾 VER ÚLTIMO TICKET
@app.route("/ticket")
def ver_ultimo_ticket():
    if session.get("role") != "admin":
        return redirect("/")
    
    items = session.get("ticket", [])
    total = session.get("ticket_total", 0)
    cliente = session.get("ticket_cliente", "")
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    return render_template("ticket.html", items=items, total=total, fecha=fecha, cliente=cliente)

# 📋 LISTA DE TICKETS
@app.route("/tickets")
def tickets():
    if session.get("role") != "admin":
        return redirect("/")
    
    tickets = Ticket.query.order_by(Ticket.fecha.desc()).all()
    return render_template("tickets.html", tickets=tickets)

# 🧾 VER TICKET
@app.route("/ticket/<int:id>")
def ver_ticket(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    ticket = Ticket.query.get(id)
    if ticket:
        items = json.loads(ticket.items)
        return render_template("ticket.html", items=items, total=ticket.total, fecha=ticket.fecha.strftime("%d/%m/%Y %H:%M:%S"), cliente=ticket.cliente if hasattr(ticket, 'cliente') else "")
    return redirect("/tickets")

# ✏️ EDITAR TICKET
@app.route("/editar_ticket/<int:id>", methods=["GET", "POST"])
def editar_ticket(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    ticket = Ticket.query.get(id)
    
    if request.method == "POST":
        ticket.total = float(request.form["total"])
        db.session.commit()
        return redirect("/tickets")
    
    return render_template("editar_ticket.html", ticket=ticket)

# 🗑️ ELIMINAR TICKET
@app.route("/eliminar_ticket/<int:id>")
def eliminar_ticket(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    ticket = Ticket.query.get(id)
    if ticket:
        db.session.delete(ticket)
        db.session.commit()
    
    return redirect("/tickets")

# 📊 VENTAS
@app.route("/ventas")
def ventas():
    if session.get("role") != "admin":
        return redirect("/")

    ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    
    # Agrupar por día
    ventas_por_dia = {}
    for v in ventas:
        dia = v.fecha.strftime("%Y-%m-%d")
        if dia not in ventas_por_dia:
            ventas_por_dia[dia] = []
        ventas_por_dia[dia].append(v)
    
    return render_template("ventas.html", ventas=ventas, ventas_por_dia=ventas_por_dia)

# ✏️ EDITAR VENTA
@app.route("/editar_venta/<int:id>", methods=["GET", "POST"])
def editar_venta(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    venta = Venta.query.get(id)
    
    if request.method == "POST":
        venta.producto = request.form["producto"]
        venta.cantidad = int(request.form["cantidad"])
        venta.total = float(request.form["total"])
        venta.cliente = request.form.get("cliente", "")
        db.session.commit()
        return redirect("/ventas")
    
    return render_template("editar_venta.html", venta=venta)

# 🗑️ ELIMINAR VENTA
@app.route("/eliminar_venta/<int:id>")
def eliminar_venta(id):
    if session.get("role") != "admin":
        return redirect("/")
    
    venta = Venta.query.get(id)
    if venta:
        db.session.delete(venta)
        db.session.commit()
    
    return redirect("/ventas")

# 🚪 LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
    # =========================
# 🚀 RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)