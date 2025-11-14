# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_cors import CORS
import oracledb
import os

# --- Fechas ---
from datetime import datetime, timezone

# --- MongoDB ---
from pymongo import MongoClient

# -------------------------------
#  CONEXIÓN A MONGO (OFICIAL)
# -------------------------------
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "historial_ideam"

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
mongo_db = mongo_client[MONGO_DB]

print("Mongo conectado correctamente")

# -------------------------------
#  FUNCIÓN PARA GUARDAR HISTORIAL
# -------------------------------
def log_action(user: str, action: str, details: dict | None = None):
    try:
        doc = {
            "user": user or "anon",
            "action": action,
            "details": details or {},
            "ts": datetime.now(timezone.utc)
        }
        mongo_db.historial.insert_one(doc)
        print("✔ Historial guardado")
    except Exception as e:
        print("❌ Error guardando historial:", e)



# --- Configuración Oracle Instant Client (Thick) ---
# Ajusta la ruta según tu instalación de Instant Client en Windows
oracledb.init_oracle_client(lib_dir=r"C:\oraclexe\instantclient_23_9")

# --- Credenciales / DSN (puedes usar variables de entorno) ---
DB_USER = os.getenv('DB_USER', 'userideam')
DB_PASS = os.getenv('DB_PASS', 'userideam')
DB_DSN  = os.getenv('DB_DSN', 'localhost/XE')

# --- Flask ---
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'clave-secreta-dev')
CORS(app)  # permite peticiones desde otros orígenes (ajusta en producción)

# --- Pool de conexiones Oracle ---
pool = oracledb.create_pool(
    user=DB_USER,
    password=DB_PASS,
    dsn=DB_DSN,
    min=1,
    max=4,
    increment=1
)

# -------------------------
# RUTAS WEB (tu UI)
# -------------------------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    departamentos = [
        "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bolívar", "Boyacá", "Caldas", "Caquetá",
        "Casanare", "Cauca", "Cesar", "Chocó", "Córdoba", "Cundinamarca", "Guainía", "Guaviare",
        "Huila", "La Guajira", "Magdalena", "Meta", "Nariño", "Norte de Santander", "Putumayo",
        "Quindío", "Risaralda", "San Andrés y Providencia", "Santander", "Sucre", "Tolima",
        "Valle del Cauca", "Vaupés", "Vichada"
    ]

    if request.method == 'POST':
        nro_documento = request.form['nro_documento']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        contrasena = request.form['contrasena']
        departamento = request.form['departamento']

        try:
            with pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO usuario (nro_documento, nombre, apellido, contrasena, departamento)
                        VALUES (:1, :2, :3, :4, :5)
                    """, (nro_documento, nombre, apellido, contrasena, departamento))
                    connection.commit()

            flash("✅ Usuario registrado exitosamente")
            return redirect(url_for('register'))

        except Exception as e:
            flash(f"⚠️ Error al registrar: {str(e)}")

    return render_template('register.html', departamentos=departamentos)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nro_documento = request.form['nro_documento']
        contrasena = request.form['contrasena']

        try:
            with pool.acquire() as connection:
                with connection.cursor() as cursor:
                    p_valido = cursor.var(int)

                    cursor.callproc("SP_LOGIN_USUARIO", [nro_documento, contrasena, p_valido])

                    if p_valido.getvalue() == 1:
                        # Obtiene el nombre del usuario
                        cursor.execute("""
                            SELECT NOMBRE 
                            FROM USUARIO 
                            WHERE NRO_DOCUMENTO = :nro
                        """, {"nro": nro_documento})
                        result = cursor.fetchone()
                        nombre = result[0].lower() if result else ""

                        # Guarda la sesión
                        session['usuario'] = nro_documento
                        session['nombre'] = nombre

                        # 🔥🔥 AGREGAR ESTO: GUARDAR LOGIN EN EL HISTORIAL
                        log_action(
                            user=nro_documento,
                            action="login",
                            details={"nombre": nombre}
                        )
                        # 🔥🔥 FIN

                        # Redirección
                        if nombre == "admin":
                            return redirect(url_for('index2'))
                        else:
                            return redirect(url_for('main_index'))
                    else:
                        flash("⚠️ Credenciales incorrectas")

        except Exception as e:
            flash(f"⚠️ Error de base de datos: {str(e)}")

    return render_template('login.html')



from datetime import datetime

from datetime import date

@app.route('/index')
def main_index():
    nro_doc = session.get('usuario')

    brigada = None
    if nro_doc:
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT r.MUNICIPIO,
                           TO_CHAR(r.FECHA_INICIO, 'DD/MM/YYYY'),
                           TO_CHAR(r.FECHA_FIN, 'DD/MM/YYYY'),
                           r.LATITUD, r.LONGITUD
                    FROM reserva_evento r
                    JOIN reserva_participante p ON r.ID_RESERVA = p.ID_RESERVA
                    WHERE p.NRO_DOCUMENTO_USUARIO = :doc
                      AND TRUNC(SYSDATE) BETWEEN TRUNC(r.FECHA_INICIO) AND TRUNC(r.FECHA_FIN)
                """, {'doc': nro_doc})

                row = cursor.fetchone()

                if row:
                    brigada = {
                        'municipio': row[0],
                        'fecha_inicio': row[1],
                        'fecha_fin': row[2],
                        'latitud': row[3],
                        'longitud': row[4]
                    }

    return render_template('index.html', brigada=brigada)





@app.route('/index2')
def index2():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('index2.html')


# Rutas de ejemplo que tenías
from flask import session as flask_session  # usado sólo para comprobar existencia
@app.route('/registrar_arbol', methods=['GET', 'POST'])
def registrar_arbol():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    nro_documento = session['usuario']

    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            # Buscar reserva asociada al usuario
            cursor.execute("""
                SELECT re.ID_RESERVA, re.MUNICIPIO, re.LATITUD, re.LONGITUD
                FROM RESERVA_PARTICIPANTE rp
                JOIN RESERVA_EVENTO re ON rp.ID_RESERVA = re.ID_RESERVA
                WHERE rp.NRO_DOCUMENTO_USUARIO = :nro_documento
            """, {'nro_documento': nro_documento})
            reserva = cursor.fetchone()

            if not reserva:
                return render_template(
                    'registro_arbol.html',
                    advertencia="⚠ No tienes ninguna reserva asignada.",
                    subparcelas=[],
                    mensaje=None
                )

            # Subparcelas predefinidas
            subparcelas = [
                {'id': 1, 'direccion': 'Norte', 'distancia': 80},
                {'id': 2, 'direccion': 'Sur', 'distancia': 80},
                {'id': 3, 'direccion': 'Este', 'distancia': 80},
                {'id': 4, 'direccion': 'Oeste', 'distancia': 80},
            ]

            mensaje = None
            advertencia = None

            if request.method == 'POST':
                altura = request.form['altura']
                dano = request.form['dano']
                diametro = request.form['diametro']
                formafuste = request.form['formafuste']
                observaciones = request.form['observaciones']
                nsubparcela = request.form['nsubparcela']
                id_reserva = reserva[0]

                try:
                    cursor.execute("""
                        INSERT INTO ARBOL (ALTURA, DANO, DIAMETRO, FORMAFUSTE, OBSERVACIONES,
                                           NSUBPARCELA, NRO_DOCUMENTO, ID_RESERVA)
                        VALUES (:altura, :dano, :diametro, :formafuste, :observaciones,
                                :nsubparcela, :nro_doc, :id_reserva)
                    """, {
                        'altura': altura,
                        'dano': dano,
                        'diametro': diametro,
                        'formafuste': formafuste,
                        'observaciones': observaciones,
                        'nsubparcela': nsubparcela,
                        'nro_doc': nro_documento,
                        'id_reserva': id_reserva
                    })
                    connection.commit()
                    mensaje = "✅ Árbol registrado exitosamente."
                except Exception as e:
                    connection.rollback()
                    import traceback
                    print("❌ Error al registrar el árbol:", traceback.format_exc())
                    advertencia = f"❌ Error al registrar el árbol: {str(e)}"

    # Renderizar la misma página sin redirección
    return render_template(
        'registro_arbol.html',
        reserva=reserva,
        subparcelas=subparcelas,
        mensaje=mensaje,
        advertencia=advertencia
    )






@app.route('/registrar_planta', methods=['GET', 'POST'])
def registrar_planta():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    nro_documento = session['usuario']

    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            # 🔹 Buscar SOLO la reserva vigente del usuario
            cursor.execute("""
                SELECT re.ID_RESERVA, re.MUNICIPIO, re.LATITUD, re.LONGITUD,
                       re.FECHA_INICIO, re.FECHA_FIN
                FROM RESERVA_PARTICIPANTE rp
                JOIN RESERVA_EVENTO re ON rp.ID_RESERVA = re.ID_RESERVA
                WHERE rp.NRO_DOCUMENTO_USUARIO = :nro_documento
                ORDER BY re.FECHA_INICIO DESC
            """, {'nro_documento': nro_documento})

            reservas = cursor.fetchall()

            if not reservas:
                return render_template(
                    'registroplantas.html',
                    advertencia="⚠ No tienes ninguna reserva asignada.",
                    subparcelas=[]
                )

            # 🔹 Buscar la reserva activa (entre fecha_inicio y fecha_fin)
            fecha_actual = datetime.now().date()
            reserva_activa = None

            for r in reservas:
                fecha_inicio = r[4]
                fecha_fin = r[5]

                # Convertir a date si son datetime
                if isinstance(fecha_inicio, datetime):
                    fecha_inicio = fecha_inicio.date()
                if isinstance(fecha_fin, datetime):
                    fecha_fin = fecha_fin.date()

                if fecha_inicio <= fecha_actual <= fecha_fin:
                    reserva_activa = r
                    break

            if not reserva_activa:
                return render_template(
                    'registroplantas.html',
                    advertencia="⚠ No tienes ninguna reserva activa en este momento.",
                    subparcelas=[]
                )

            # 🔹 Subparcelas predefinidas
            subparcelas = [
                {'id': 1, 'direccion': 'Norte', 'distancia': 80},
                {'id': 2, 'direccion': 'Sur', 'distancia': 80},
                {'id': 3, 'direccion': 'Este', 'distancia': 80},
                {'id': 4, 'direccion': 'Oeste', 'distancia': 80},
            ]

            # 🔹 Procesar formulario si es método POST
            if request.method == 'POST':
                tamano = request.form['tamano']
                nombre_comun = request.form['nombre_comun']
                observaciones = request.form['observaciones']
                nsubparcela = request.form['nsubparcela']
                id_reserva = reserva_activa[0]
                id_brigada = 1  # Temporal

                try:
                    cursor.execute("""
                        INSERT INTO PLANTA (TAMANO, NOMBRE_COMUN, OBSERVACIONES,
                                            NSUBPARCELA, ID_RESERVA, NRO_DOCUMENTO_USUARIO, ID_BRIGADA)
                        VALUES (:tamano, :nombre_comun, :observaciones,
                                :nsubparcela, :id_reserva, :nro_doc, :id_brigada)
                    """, {
                        'tamano': tamano,
                        'nombre_comun': nombre_comun,
                        'observaciones': observaciones,
                        'nsubparcela': nsubparcela,
                        'id_reserva': id_reserva,
                        'nro_doc': nro_documento,
                        'id_brigada': id_brigada
                    })
                    connection.commit()
                    flash("✅ Planta registrada exitosamente.")
                except Exception as e:
                    connection.rollback()
                    import traceback
                    print("❌ Error al registrar la planta:", traceback.format_exc())
                    flash(f"❌ Error al registrar la planta: {str(e)}")

    return render_template(
        'registroplantas.html',
        reserva=reserva_activa,
        subparcelas=subparcelas,
        advertencia=None
    )
@app.route('/registro_brigada')
def registro_brigada():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('registro_brigadas.html')


# ---------------------------
# API para frontend (HTML)
# ---------------------------

@app.route('/api/usuarios', methods=['GET'])
def api_usuarios():
    """
    Devuelve la lista de usuarios en formato JSON.
    Si se pasa ?departamento=<nombre> devuelve sólo los usuarios de ese departamento.
    """
    departamento = request.args.get('departamento', None)
    try:
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                if departamento:
                    # Buscar case-insensitive
                    cursor.execute("""
                        SELECT NRO_DOCUMENTO, NOMBRE, APELLIDO, DEPARTAMENTO
                        FROM USUARIO
                        WHERE UPPER(DEPARTAMENTO) = UPPER(:dep)
                        ORDER BY NOMBRE, APELLIDO
                    """, {"dep": departamento})
                else:
                    cursor.execute("""
                        SELECT NRO_DOCUMENTO, NOMBRE, APELLIDO, DEPARTAMENTO
                        FROM USUARIO
                        ORDER BY DEPARTAMENTO, NOMBRE, APELLIDO
                    """)
                usuarios = []
                for nro, nombre, apellido, departamento_row in cursor:
                    usuarios.append({
                        "NRO_DOCUMENTO": str(nro),
                        "NOMBRE": nombre,
                        "APELLIDO": apellido,
                        "DEPARTAMENTO": departamento_row
                    })
        return jsonify(usuarios), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/municipios', methods=['GET'])
def api_municipios():
    """
    Devuelve la lista de departamentos para que aparezcan en el select.
    """
    departamentos = [
        "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bolívar", "Boyacá", "Caldas", "Caquetá",
        "Casanare", "Cauca", "Cesar", "Chocó", "Córdoba", "Cundinamarca", "Guainía", "Guaviare",
        "Huila", "La Guajira", "Magdalena", "Meta", "Nariño", "Norte de Santander", "Putumayo",
        "Quindío", "Risaralda", "San Andrés y Providencia", "Santander", "Sucre", "Tolima",
        "Valle del Cauca", "Vaupés", "Vichada"
    ]
    # Devolver en formato { "id": <index>, "nombre": <departamento> } por compatibilidad con frontend
    out = [{"id": i+1, "nombre": d} for i, d in enumerate(departamentos)]
    return jsonify(out), 200


@app.route('/api/crear_reserva', methods=['POST'])
def api_crear_reserva():
    """
    Recibe JSON con:
    {
      "fechainicio":"YYYY-MM-DD",
      "fechafin":"YYYY-MM-DD",
      "municipio":"Nombre",
      "lat":"4.123456",
      "lng":"-74.123456",
      "participantes":["111","222","333","444"]
    }
    Valida y crea una reserva + registros de participantes.
    """
    try:
        data = request.get_json(force=True)
        fechainicio = data.get('fechainicio')
        fechafin = data.get('fechafin')
        participantes = data.get('participantes', [])
        municipio = data.get('municipio')
        lat = data.get('lat')
        lng = data.get('lng')

        # Campos obligatorios
        if not (fechainicio and fechafin and municipio and lat and lng):
            return jsonify({"error":"Faltan campos obligatorios"}), 400

        # Parsear fechas
        try:
            dt_inicio = datetime.strptime(fechainicio, "%Y-%m-%d")
            dt_fin = datetime.strptime(fechafin, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error":"Formato de fecha inválido (usar YYYY-MM-DD)"}), 400

        if dt_fin < dt_inicio:
            return jsonify({"error":"La fecha fin no puede ser anterior a la fecha inicio"}), 400

        # Validar exactamente 4 participantes
        if not isinstance(participantes, list) or len(participantes) != 4:
            return jsonify({"error":"Debe seleccionar exactamente 4 participantes"}), 400

        # Validar que cada participante exista en la tabla USUARIO
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                for nro in participantes:
                    cursor.execute("SELECT COUNT(1) FROM USUARIO WHERE NRO_DOCUMENTO = :nro", {"nro": nro})
                    count = cursor.fetchone()[0]
                    if count == 0:
                        return jsonify({"error": f"El participante {nro} no existe en USUARIO"}), 400

                # Obtener un nuevo ID usando la secuencia SEQ_RESERVA_ID
                cursor.execute("SELECT SEQ_RESERVA_ID.NEXTVAL FROM DUAL")
                id_reserva = cursor.fetchone()[0]

                # Insertar en RESERVA_EVENTO
                cursor.execute("""
                    INSERT INTO RESERVA_EVENTO (
                        ID_RESERVA, FECHA_INICIO, FECHA_FIN, MUNICIPIO, LATITUD, LONGITUD, CREADO_EN
                    ) VALUES (
                        :idr, TO_DATE(:fi,'YYYY-MM-DD'), TO_DATE(:ff,'YYYY-MM-DD'), :mun, :lat, :lng, SYSDATE
                    )
                """, {
                    "idr": id_reserva,
                    "fi": fechainicio,
                    "ff": fechafin,
                    "mun": municipio,
                    "lat": lat,
                    "lng": lng
                })

                # Insertar participantes en RESERVA_PARTICIPANTE
                for nro in participantes:
                    cursor.execute("""
                        INSERT INTO RESERVA_PARTICIPANTE (ID_RESERVA, NRO_DOCUMENTO_USUARIO)
                        VALUES (:idr, :nro)
                    """, {"idr": id_reserva, "nro": nro})

                connection.commit()

        return jsonify({"ok":True, "id_reserva": int(id_reserva)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/api/reportes", methods=["GET"])
def api_reportes():
    tipo = request.args.get("tipo")
    fecha_inicio = request.args.get("fechaInicio")
    fecha_fin = request.args.get("fechaFin")

    if tipo != "Arbol":
        return jsonify({"error": "Tipo de reporte no soportado"}), 400

    query = """
        SELECT 
            ID_ARBOL,
            NOMBRE_CIENTIFICO,
            NOMBRE_COMUN,
            ALTURA,
            DIAMETRO,
            DANO,
            FORMAFUSTE,
            OBSERVACIONES,
            NSUBPARCELA,
            NRO_DOCUMENTO,
            ID_RESERVA,
            FECHA_REGISTRO
        FROM arbol
        WHERE (:ini IS NULL OR FECHA_REGISTRO >= TO_DATE(:ini, 'YYYY-MM-DD'))
          AND (:fin IS NULL OR FECHA_REGISTRO <= TO_DATE(:fin, 'YYYY-MM-DD'))
        ORDER BY FECHA_REGISTRO DESC
    """

    with pool.acquire() as conn:
        cur = conn.cursor()

        cur.execute(
            query,
            {
                "ini": fecha_inicio,
                "fin": fecha_fin
            }
        )

        columnas = [col[0] for col in cur.description]
        rows = cur.fetchall()

        data = [dict(zip(columnas, fila)) for fila in rows]

    return jsonify({
        "tabla": data
    })



@app.route("/reportes")
def reportes():
    return render_template("reportes.html")

# ---------------------------
# EJECUCIÓN LOCAL
# ---------------------------
if __name__ == '__main__':
    # Nota: en producción usa un WSGI server (gunicorn/uwsgi)
    app.run(debug=True, host='0.0.0.0', port=5000)
