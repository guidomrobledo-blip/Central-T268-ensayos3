import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logic_clientes, logic_domicilios, logic_informe, logic_seguridad
import os
import json
import hashlib
import base64
import time

# =====================================================
# CONFIGURACION GLOBAL E INMUNE
# =====================================================
st.set_page_config(
    page_title="Panel Operaciones Online Carrefour",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicialización de Estados en Session State
if "pedidos_manual" not in st.session_state:
    st.session_state.pedidos_manual = []
if "pedido_a_mover" not in st.session_state:
    st.session_state.pedido_a_mover = None
if "df_clean" not in st.session_state:
    st.session_state.df_clean = None
if "fecha_tit" not in st.session_state:
    st.session_state.fecha_tit = None

# =====================================================
# FUNCIONES DE UTILIDAD Y PERSISTENCIA
# =====================================================
def cargar_css(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass

def get_image_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

def cargar_datos_mensuales():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                datos = json.load(f)
            mes_guardado = datos.get("mes", "")
            mes_actual = hoy_ar.strftime("%Y-%m")
            if mes_guardado != mes_actual:
                return {"mes": mes_actual, "pedidos_por_dia": {}, "archivos_procesados": [], "modalidades": {"DOMICILIOS": 0, "DRIVE": 0, "SUCURSAL": 0}}
            return datos
        else:
            return {"mes": hoy_ar.strftime("%Y-%m"), "pedidos_por_dia": {}, "archivos_procesados": [], "modalidades": {"DOMICILIOS": 0, "DRIVE": 0, "SUCURSAL": 0}}
    except Exception:
        return {"mes": hoy_ar.strftime("%Y-%m"), "pedidos_por_dia": {}, "archivos_procesados": [], "modalidades": {"DOMICILIOS": 0, "DRIVE": 0, "SUCURSAL": 0}}

def guardar_datos_mensuales(datos):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(datos, f)
    except Exception:
        pass

def obtener_hash_archivo(archivo_bytes):
    return hashlib.md5(archivo_bytes).hexdigest()

def extraer_fecha_entrega(df):
    col_fecha = None
    for col in df.columns:
        if "FECHA" in str(col).upper() and "ENTREGA" in str(col).upper():
            col_fecha = col
            break
    if col_fecha is None:
        return None
    try:
        fecha_val = df[col_fecha].dropna().iloc[0]
        fecha_str = str(fecha_val).strip()
        fecha = pd.to_datetime(fecha_str, dayfirst=True, errors='coerce')
        if pd.isna(fecha):
            return None
        return fecha.date()
    except Exception:
        return None

def contar_modalidades(df):
    modalidades_conteo = {"DOMICILIOS": 0, "DRIVE": 0, "SUCURSAL": 0}
    col_modalidad = None
    for col in df.columns:
        col_upper = str(col).upper().strip()
        if "MODALIDAD" in col_upper and "ENTREGA" in col_upper:
            col_modalidad = col
            break
    if col_modalidad is None:
        for col in df.columns:
            col_upper = str(col).upper().strip()
            if "MODALIDAD" in col_upper and "FECHA" not in col_upper:
                col_modalidad = col
                break
    if col_modalidad is not None:
        for valor in df[col_modalidad].dropna():
            valor_upper = str(valor).upper().strip()
            if "DOMICILIO" in valor_upper or "A DOMICILIO" in valor_upper:
                modalidades_conteo["DOMICILIOS"] += 1
            elif "DRIVE" in valor_upper:
                modalidades_conteo["DRIVE"] += 1
            elif "SUCURSAL" in valor_upper or "RETIRO" in valor_upper or "PICK" in valor_upper or "TIENDA" in valor_upper:
                modalidades_conteo["SUCURSAL"] += 1
    return modalidades_conteo

def registrar_pedidos_cdp(archivo_bytes, df):
    datos = cargar_datos_mensuales()
    archivo_hash = obtener_hash_archivo(archivo_bytes)
    if archivo_hash in datos["archivos_procesados"]:
        return datos, False
    fecha_entrega = extraer_fecha_entrega(df)
    if fecha_entrega is None:
        return datos, False
    if fecha_entrega.strftime("%Y-%m") != datos["mes"]:
        return datos, False
    fecha_str = fecha_entrega.strftime("%Y-%m-%d")
    cantidad_pedidos = len(df)
    datos["pedidos_por_dia"][fecha_str] = cantidad_pedidos
    datos["archivos_procesados"].append(archivo_hash)
    modalidades_archivo = contar_modalidades(df)
    if "modalidades" not in datos:
        datos["modalidades"] = {"DOMICILIOS": 0, "DRIVE": 0, "SUCURSAL": 0}
    datos["modalidades"]["DOMICILIOS"] += modalidades_archivo["DOMICILIOS"]
    datos["modalidades"]["DRIVE"] += modalidades_archivo["DRIVE"]
    datos["modalidades"]["SUCURSAL"] += modalidades_archivo["SUCURSAL"]
    guardar_datos_mensuales(datos)
    return datos, True

# Carga de Tiempos y Parámetros Iniciales
fecha_ar_ahora = datetime.utcnow() - timedelta(hours=3)
hoy_ar = fecha_ar_ahora.date()
DATA_FILE = "datos_mensuales.json"

# Inyección de estilos CSS Corporativos Avanzados
cargar_css("styles_corporativo.css")

# =====================================================
# LOADING SCREEN
# =====================================================
loading_logo_base64 = get_image_base64("logo.png.webp")
if loading_logo_base64:
    st.markdown(f"""
        <div class="loading-screen" id="loadingScreen">
            <img src="data:image/webp;base64,{loading_logo_base64}" class="loading-logo" style="max-width: 200px; height: auto;" alt="Carrefour">
        </div>
    """, unsafe_allow_html=True)

# =====================================================
# BLOQUE 1 - HEADER OPERATIVO FIJO (5% Alto)
# =====================================================
logo_base64 = get_image_base64("carrefour+logo.png")
logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="header-logo" alt="Carrefour">' if logo_base64 else '<span style="color:#eef2f6;font-weight:700;">Carrefour</span>'

st.markdown(f"""
    <div class="bloque-header">
        <div class="header-container">
            <div class="header-left">{logo_html}</div>
            <div class="header-right">
                <h1 class="title-main">PANEL DE OPERACIONES CARREFOUR ONLINE</h1>
                <p class="subtitle-main">Tienda 268 - Rosario&nbsp;&nbsp;|&nbsp;&nbsp;{hoy_ar.strftime("%d/%m/%Y")}</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# =====================================================
# BLOQUE 2 - BARRA DE ACCIONES Y DESCARGAS RESERVADAS (5% Alto)
# =====================================================
# Envolvemos toda la estructura en un div de clase control-bar-wrapper para congelar su geometría
st.markdown('<div class="bloque-menu">', unsafe_allow_html=True)
cols_menu = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 3.0]) # El último bloque estirado contiene la ZONA RESERVADA DE DESCARGAS

with cols_menu[0]:
    archivo_cdp = st.file_uploader("Upload (cargar)", type=["xlsx"], key="uploader_cdp", label_visibility="collapsed")
with cols_menu[1]:
    btn_1 = st.button("PLANILLA CLIENTES", key="top_1", use_container_width=True)
with cols_menu[2]:
    btn_seguridad = st.button("PLANILLA SEGURIDAD", key="top_seg", use_container_width=True)
with cols_menu[3]:
    btn_3 = st.button("PLANILLA LOGISTICA", key="top_3", use_container_width=True)
with cols_menu[4]:
    st.link_button("PLANILLA MEC", "https://docs.google.com/spreadsheets/d/1v0Rls8fg_uIGfhA1t3CzINq3VfAUvPY3DY8_m_ZSmM8/edit#gid=0", use_container_width=True)

# LÓGICA DE PROCESAMIENTO LOGÍSTICO
if archivo_cdp:
    archivo_cdp_bytes = archivo_cdp.read()
    archivo_cdp.seek(0)
    if st.session_state.df_clean is None:
        with st.spinner("Procesando archivo..."):
            df_raw = pd.read_excel(archivo_cdp)
            columnas_janis = ["displayId", "shippingType", "dropoffStreet", "dropoffNumber", "scheduleStart", "scheduleEnd", "receiverFullname", "receiverPhone"]
            if all(col in df_raw.columns for col in columnas_janis):
                df_janis = pd.DataFrame()
                df_janis["NUMERO PEDIDO"] = df_raw["orderCommerceIds"].astype(str).str.split("-").str[0]
                df_janis["MODALIDAD DE ENTREGA"] = df_raw["carrierName"].replace({
                    "Envío a Domicilio 0268 - Hiper Rosario Pueyrredón": "Domicilio",
                    "Drive 0268 - Hiper Rosario Pueyrredón": "Drive",
                    "Retiro en Tienda 0268 - Hiper Rosario Pueyrredón": "Sucursal"
                })
                df_janis["CALLE"] = df_raw["dropoffStreet"]
                df_janis["NUMERO"] = df_raw["dropoffNumber"]
                df_janis["DEPTO"] = df_raw["dropoffComplement"]
                df_janis["FECHA ENTREGA"] = pd.to_datetime(df_raw["scheduleStart"], errors="coerce")
                hora_inicio = pd.to_datetime(df_raw["scheduleStart"], errors="coerce").dt.strftime("%H:%M")
                hora_fin = pd.to_datetime(df_raw["scheduleEnd"], errors="coerce").dt.strftime("%H:%M")
                df_janis["BANDA HORARIA"] = hora_inicio + " a " + hora_fin
                df_janis["NOMBRE CLIENTE"] = df_raw["receiverFullname"].fillna("").astype(str).str.strip()
                df_janis["TELEFONO CLIENTE"] = df_raw["receiverPhone"]
                df_janis["TEL. PARTICULAR"] = df_raw["receiverPhone"]
                df_raw = df_janis.copy()

            df_raw['FECHA ENTREGA'] = pd.to_datetime(df_raw['FECHA ENTREGA'], dayfirst=True, errors='coerce')
            st.session_state.df_clean, st.session_state.fecha_tit = logic_clientes.motor_limpieza(df_raw)
            registrar_pedidos_cdp(archivo_cdp_bytes, st.session_state.df_clean)
            st.toast(f"Janis.xlsx CARGADO: {st.session_state.fecha_tit}", icon="✅")

df_clean = st.session_state.df_clean
fecha_tit = st.session_state.fecha_tit

# ZONA RESERVADA DE DESCARGAS (Columna Extremo Derecho - Inmóvil)
with cols_menu[5]:
    st.markdown('<div class="zona-reservada-descargas">', unsafe_allow_html=True)
    if df_clean is not None:
        sub_descargas = st.columns(3)
        with sub_descargas[0]:
            if btn_1:
                pdf1 = logic_clientes.generar_pdf_clientes(df_clean)
                st.download_button("DESCARGAR CLIENTES", bytes(pdf1), f"Clientes_{fecha_tit}.pdf", key="dl_c")
        with sub_descargas[1]:
            if btn_seguridad:
                pdf2 = logic_seguridad.generar_pdf_seguridad(df_clean, fecha_tit)
                st.download_button("DESCARGAR SEGURIDAD", bytes(pdf2), f"Seguridad_{fecha_tit}.pdf", key="dl_s")
        with sub_descargas[2]:
            if btn_3:
                pdf3 = logic_domicilios.generar_pdf_domicilios(df_clean, fecha_tit)
                st.download_button("DESCARGAR LOGISTICA", bytes(pdf3), f"Domicilios_{fecha_tit}.pdf", key="dl_l")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# BLOQUE 3 - CAPTURA MANUAL Y ZONA DE ALERTAS MICRO (7% Alto)
# =====================================================
st.markdown('<div class="bloque-captura">', unsafe_allow_html=True)
cols_captura = st.columns([2.5, 1.0, 1.0, 1.2, 1.0, 2.3])

with cols_captura[0]:
    dir_manual = st.text_input("Dirección", key="in_dir", label_visibility="collapsed", placeholder="Dirección...")
with cols_captura[1]:
    nro_manual = st.text_input("Nro Pedido", key="in_nro", label_visibility="collapsed", placeholder="Pedido...")
with cols_captura[2]:
    tipo_manual = st.selectbox("Tipo", ["Caja", "Reclamo", "Reprogramado", "NonFood", "Transferencia"], key="in_tipo", label_visibility="collapsed")
with cols_captura[3]:
    banda_manual = st.selectbox("Banda horaria", ["10:00 a 14:00", "14:00 a 18:00", "18:00 a 21:00"], key="in_banda", label_visibility="collapsed")
with cols_captura[4]:
    btn_agregar_manual = st.button("AGREGAR", key="btn_add", use_container_width=True, type="primary")

# LÓGICA DE PROCESAMIENTO MANUAL / INTERCAMBIO
with cols_captura[5]:
    st.markdown('<div class="zona-reservada-alertas">', unsafe_allow_html=True)
    if btn_agregar_manual:
        prefijos = {"Caja": "LC-", "Reclamo": "R-", "Reprogramado": "RP-", "NonFood": "NF-", "Transferencia": "TR-"}
        pedido_final = f"{prefijos[tipo_manual]}{nro_manual}"
        pedido_existente = next((p for p in st.session_state.pedidos_manual if p["pedido"] == pedido_final), None)

        if pedido_existente:
            st.session_state.pedido_a_mover = {
                "pedido": pedido_final, "direccion": dir_manual, "tipo": tipo_manual,
                "banda_actual": pedido_existente["banda"], "banda_nueva": banda_manual
            }
        else:
            st.session_state.pedidos_manual.append({
                "direccion": dir_manual, "pedido": pedido_final, "tipo": tipo_manual, "banda": banda_manual, "estado": "Pendiente"
            })
            st.toast(f"Pedido {pedido_final} agregado", icon="✅")
            time.sleep(0.3)
            st.rerun()

    if st.session_state.pedido_a_mover:
        datos = st.session_state.pedido_a_mover
        if datos["banda_actual"] == datos["banda_nueva"]:
            st.markdown('<span class="micro-txt-warning">⚠️ Ya existe en esta banda.</span>', unsafe_allow_html=True)
            if st.button("OK", key="ok_misma"):
                st.session_state.pedido_a_mover = None
                st.rerun()
        else:
            st.markdown(f'<span class="micro-txt-warning">⚠️ Existe en banda {datos["banda_actual"].split(":")[0]}</span>', unsafe_allow_html=True)
            sub_col_alertas = st.columns(2)
            with sub_col_alertas[0]:
                if st.button("MOVER", key="mv_ok", use_container_width=True):
                    st.session_state.pedidos_manual = [p for p in st.session_state.pedidos_manual if p["pedido"] != datos["pedido"]]
                    st.session_state.pedidos_manual.append({
                        "direccion": datos["direccion"], "pedido": datos["pedido"], "tipo": datos["tipo"], "banda": datos["banda_nueva"], "estado": "Pendiente"
                    })
                    st.toast(f"Pedido movido", icon="🚚")
                    st.session_state.pedido_a_mover = None
                    st.rerun()
            with sub_col_alertas[1]:
                if st.button("X", key="mv_cancel", use_container_width=True):
                    st.session_state.pedido_a_mover = None
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# BLOQUE 4 - PANEL DE PEDIDOS DE ALTA DENSIDAD (78% Alto)
# =====================================================
st.markdown('<div class="bloque-tablero">', unsafe_allow_html=True)

BANDAS_FIJAS = [
    ("10 a 14 hs", ["10:00 a 14:00"]),
    ("14 a 18 hs", ["14:00 a 18:00"]),
    ("18 a 21 hs", ["18:00 a 21:00"]),
]

def construir_tabla_banda(claves_banda):
    filas = []
    if df_clean is not None:
        df_rutas = df_clean[df_clean["MODALIDAD DE ENTREGA"].str.contains("Domicilio", case=False, na=False)].copy()
        df_banda = df_rutas[df_rutas["BANDA HORARIA"].isin(claves_banda)]
        for _, r in df_banda.iterrows():
            filas.append({"ORDEN": "-", "DIRECCIÓN": r.get("DIRECCIÓN", ""), "PEDIDO": r.get("NUMERO PEDIDO", ""), "TIPO": "Ecommerce", "ESTADO": "Pendiente"})
    ecommerce = len(filas)
    
    manuales = 0
    for pedido in st.session_state.pedidos_manual:
        if pedido["banda"] in claves_banda:
            manuales += 1
            filas.append({"ORDEN": "-", "DIRECCIÓN": pedido["direccion"], "PEDIDO": pedido["pedido"], "TIPO": pedido["tipo"], "ESTADO": pedido["estado"]})
    return pd.DataFrame(filas), ecommerce, manuales

cols_bandas = st.columns(3, gap="small")

for col, (label, claves) in zip(cols_bandas, BANDAS_FIJAS):
    with col:
        tabla, ecommerce, manuales = construir_tabla_banda(claves)
        conteo = f"{ecommerce} ecomm" + (f" · {manuales} manual" if manuales > 0 else "")
        
        st.markdown(f'<div class="banda-header">{label}<span class="conteo">{conteo}</span></div>', unsafe_allow_html=True)
        
        if not tabla.empty:
            st.dataframe(tabla, use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="banda-vacia">Sin pedidos cargados</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# BLOQUE 5 - FOOTER FIJO (5% Alto)
# =====================================================
st.markdown('<div class="bloque-footer">CENTRAL DE ARMADO T268 | CARREFOUR ONLINE | ROSARIO</div>', unsafe_allow_html=True)
