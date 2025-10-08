# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_cors import CORS
from datetime import datetime
import oracledb
import os

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
                    # Llama al procedimiento almacenado SP_LOGIN_USUARIO
                    cursor.callproc("SP_LOGIN_USUARIO", [nro_documento, contrasena, p_valido])

                    if p_valido.getvalue() == 1:
                        # Credenciales correctas -> obtener nombre para decidir ruta
                        cursor.execute("""
                            SELECT NOMBRE 
                            FROM USUARIO 
                            WHERE NRO_DOCUMENTO = :nro
                        """, {"nro": nro_documento})
                        result = cursor.fetchone()
                        nombre = result[0].lower() if result else ""

                        # Guardar sesión mínima
                        session['usuario'] = nro_documento
                        session['nombre'] = nombre

                        #flash("✅ Inicio de sesión exitoso")

                        if nombre == "admin":
                            return redirect(url_for('index2'))
                        else:
                            return redirect(url_for('main_index'))
                    else:
                        flash("⚠️ Credenciales incorrectas")

        except Exception as e:
            flash(f"⚠️ Error de base de datos: {str(e)}")

    return render_template('login.html')


@app.route('/index')
def main_index():
    nro_doc = session.get('usuario')

    brigada = None
    if nro_doc:
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT r.MUNICIPIO, TO_CHAR(r.FECHA_INICIO, 'DD/MM/YYYY'),
                           TO_CHAR(r.FECHA_FIN, 'DD/MM/YYYY'),
                           r.LATITUD, r.LONGITUD
                    FROM reserva_evento r
                    JOIN reserva_participante p ON r.ID_RESERVA = p.ID_RESERVA
                    WHERE p.NRO_DOCUMENTO_USUARIO = :doc
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
@app.route('/registro-arbol')
def registro_arbol():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('RegistroArbol.html')

@app.route('/registro-plantas')
def registro_plantas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('RegistroPlantas.html')

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


# ---------------------------
# EJECUCIÓN LOCAL
# ---------------------------
if __name__ == '__main__':
    # Nota: en producción usa un WSGI server (gunicorn/uwsgi)
    app.run(debug=True, host='0.0.0.0', port=5000)
