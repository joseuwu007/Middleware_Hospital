from flask import Flask, request, jsonify
import jwt
import datetime
import os

app = Flask(__name__)

# Las credenciales y la clave JWT se leen desde variables de entorno.
JWT_SECRET = os.environ.get("JWT_SECRET", "clave_temporal_solo_desarrollo")
USUARIO = os.environ.get("HOSPITAL_USER", "hospital")
PASSWORD = os.environ.get("HOSPITAL_PASSWORD", "1234")


def laboratorio(datos):
    """Simula la recepción de información en Laboratorio."""
    return {
        "sistema": "LABORATORIO",
        "estado": "RECIBIDO",
        "datos_recibidos": datos
    }


def facturacion(datos):
    """Simula la recepción de información en Facturación."""
    return {
        "sistema": "FACTURACION",
        "estado": "RECIBIDO",
        "datos_recibidos": datos
    }


def farmacia(datos):
    """Simula la recepción de información en Farmacia."""
    return {
        "sistema": "FARMACIA",
        "estado": "RECIBIDO",
        "datos_recibidos": datos
    }


def radiologia(datos):
    """Simula la recepción de información en Radiología."""
    return {
        "sistema": "RADIOLOGIA",
        "estado": "RECIBIDO",
        "datos_recibidos": datos
    }


def validar_token():
    auth = request.headers.get("Authorization")

    if not auth:
        return False, "Token no enviado"

    partes = auth.split()

    if len(partes) != 2 or partes[0].lower() != "bearer":
        return False, "Formato de autorización incorrecto"

    token = partes[1]

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )
        return True, payload

    except jwt.ExpiredSignatureError:
        return False, "Token vencido"

    except jwt.InvalidTokenError:
        return False, "Token inválido"


@app.route("/", methods=["GET"])
def inicio():
    return jsonify({
        "aplicacion": "Middleware Hospitalario V4",
        "arquitectura": "API REST + JWT",
        "estado": "ACTIVO",
        "despliegue": "Render",
        "destinos": ["LABORATORIO", "FACTURACION", "FARMACIA", "RADIOLOGIA"],
        "endpoints": {
            "login": "POST /login",
            "middleware": "POST /middleware"
        }
    })


@app.route("/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True)

    if not datos:
        return jsonify({
            "error": "Debe enviar información en formato JSON"
        }), 400

    usuario = datos.get("usuario")
    password = datos.get("password")

    if usuario != USUARIO or password != PASSWORD:
        return jsonify({
            "error": "Usuario o contraseña incorrectos"
        }), 401

    ahora = datetime.datetime.now(datetime.timezone.utc)

    token = jwt.encode(
        {
            "usuario": usuario,
            "iat": ahora,
            "exp": ahora + datetime.timedelta(minutes=30)
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return jsonify({
        "mensaje": "Autenticación correcta",
        "token": token,
        "tipo": "Bearer",
        "vigencia_minutos": 30
    }), 200


@app.route("/middleware", methods=["POST"])
def middleware():

    # 1. SEGURIDAD
    valido, resultado_token = validar_token()

    if not valido:
        return jsonify({
            "etapa": "SEGURIDAD",
            "error": resultado_token
        }), 401

    # 2. RECEPCIÓN
    datos = request.get_json(silent=True)

    if not datos:
        return jsonify({
            "etapa": "RECEPCION",
            "error": "Debe enviar información en formato JSON"
        }), 400

    # 3. VALIDACIÓN GENERAL
    if "paciente" not in datos or "destino" not in datos:
        return jsonify({
            "etapa": "VALIDACION",
            "error": "Se requieren los campos paciente y destino"
        }), 400

    # Normaliza tildes: FACTURACIÓN -> FACTURACION, RADIOLOGÍA -> RADIOLOGIA
    destino = (str(datos["destino"]).strip().upper()
               .replace("Í", "I").replace("Ó", "O"))

    # 4. LABORATORIO
    if destino == "LABORATORIO":

        if "examen" not in datos:
            return jsonify({
                "etapa": "VALIDACION",
                "error": "No se especificó el examen"
            }), 400

        # Regla de negocio sencilla
        prioridad = "URGENTE" if datos.get("urgente", False) else "NORMAL"

        # Transformación
        datos_transformados = {
            "id_paciente": datos["paciente"],
            "tipo_examen": datos["examen"],
            "prioridad": prioridad
        }

        respuesta = laboratorio(datos_transformados)

        return jsonify({
            "mensaje": "Solicitud procesada correctamente",
            "usuario_autenticado": resultado_token["usuario"],
            "destino_seleccionado": "LABORATORIO",
            "datos_originales": datos,
            "datos_transformados": datos_transformados,
            "respuesta_destino": respuesta
        }), 200

    # 5. FACTURACIÓN
    elif destino == "FACTURACION":

        if "concepto" not in datos or "valor" not in datos:
            return jsonify({
                "etapa": "VALIDACION",
                "error": "Se requieren concepto y valor"
            }), 400

        # Transformación
        datos_transformados = {
            "id_paciente": datos["paciente"],
            "concepto": datos["concepto"],
            "valor": datos["valor"]
        }

        respuesta = facturacion(datos_transformados)

        return jsonify({
            "mensaje": "Solicitud procesada correctamente",
            "usuario_autenticado": resultado_token["usuario"],
            "destino_seleccionado": "FACTURACION",
            "datos_originales": datos,
            "datos_transformados": datos_transformados,
            "respuesta_destino": respuesta
        }), 200

    # 6. FARMACIA (NUEVO)
    elif destino == "FARMACIA":

        faltantes = [c for c in ("solicitud", "cantidad") if c not in datos]
        if faltantes:
            return jsonify({
                "etapa": "VALIDACION",
                "error": "Se requieren solicitud y cantidad",
                "campos_faltantes": faltantes
            }), 400

        cantidad = datos["cantidad"]
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
            return jsonify({
                "etapa": "VALIDACION",
                "error": "La cantidad debe ser un número entero mayor que 0"
            }), 400

        # Transformación + regla de negocio (más de 30 unidades requiere autorización)
        datos_transformados = {
            "id_paciente": datos["paciente"],
            "medicamento": datos["solicitud"],
            "unidades": cantidad,
            "requiere_autorizacion": cantidad > 30
        }

        respuesta = farmacia(datos_transformados)

        return jsonify({
            "mensaje": "Solicitud procesada correctamente",
            "usuario_autenticado": resultado_token["usuario"],
            "destino_seleccionado": "FARMACIA",
            "datos_originales": datos,
            "datos_transformados": datos_transformados,
            "respuesta_destino": respuesta
        }), 200

    # 7. RADIOLOGÍA (NUEVO)
    elif destino == "RADIOLOGIA":

        faltantes = [c for c in ("solicitud", "urgente") if c not in datos]
        if faltantes:
            return jsonify({
                "etapa": "VALIDACION",
                "error": "Se requieren solicitud y urgente",
                "campos_faltantes": faltantes
            }), 400

        if not isinstance(datos["urgente"], bool):
            return jsonify({
                "etapa": "VALIDACION",
                "error": "El campo urgente debe ser true o false"
            }), 400

        # Transformación + regla de prioridad
        datos_transformados = {
            "id_paciente": datos["paciente"],
            "tipo_estudio": datos["solicitud"],
            "prioridad": "URGENTE" if datos["urgente"] else "NORMAL"
        }

        respuesta = radiologia(datos_transformados)

        return jsonify({
            "mensaje": "Solicitud procesada correctamente",
            "usuario_autenticado": resultado_token["usuario"],
            "destino_seleccionado": "RADIOLOGIA",
            "datos_originales": datos,
            "datos_transformados": datos_transformados,
            "respuesta_destino": respuesta
        }), 200

    # 8. DESTINO NO RECONOCIDO
    else:
        return jsonify({
            "etapa": "ENRUTAMIENTO",
            "error": "Destino no reconocido",
            "destinos_permitidos": ["LABORATORIO", "FACTURACION", "FARMACIA", "RADIOLOGIA"]
        }), 400


if __name__ == "__main__":
    # Útil para pruebas fuera de Render.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
