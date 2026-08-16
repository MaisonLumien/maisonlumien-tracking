"""
SERVIDOR WEBHOOK PARA MAISONLUMIEN - VERSIÓN PARA RENDER
"""

import sys
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect, make_response

# Configurar logging para Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración para Render
PORT = int(os.environ.get('PORT', 5000))

# ============================================
# CONEXIÓN A BASE DE DATOS (usar variables de entorno)
# ============================================
import pyodbc

def get_db_connection():
    """Obtiene conexión a SQL Server usando variables de entorno"""
    try:
        server = os.environ.get('DB_SERVER', 'localhost')
        database = os.environ.get('DB_NAME', 'MaisonLumien_Marketing')
        username = os.environ.get('DB_USER', '')
        password = os.environ.get('DB_PASSWORD', '')
        
        if username and password:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
        
        return pyodbc.connect(conn_str)
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return None


def save_tracking_event(customer_id, campaign_id, event_type, 
                        ip_address=None, user_agent=None, link_url=None, metadata=None):
    """Guarda un evento de tracking en la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ No se pudo conectar a la BD")
            return False
        
        cursor = conn.cursor()
        event_id = str(uuid.uuid4())
        
        if not customer_id:
            logger.warning("⚠️ customer_id vacío")
            return False
        
        customer_id_str = str(customer_id)
        logger.info(f"   Guardando customer_id: {customer_id_str}")
        
        cursor.execute("""
            INSERT INTO marketing.email_events (
                id,
                customer_id_text,
                campaign_id,
                message_id,
                event_type,
                event_timestamp,
                ip_address,
                user_agent,
                link_url,
                metadata
            ) VALUES (?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?)
        """, (
            event_id,
            customer_id_str,
            campaign_id or 'campana-default',
            'tracking_propio',
            event_type,
            ip_address,
            user_agent,
            link_url,
            metadata
        ))
        conn.commit()
        conn.close()
        logger.info(f"✅ Evento guardado: {event_type} para {customer_id_str}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error guardando evento: {e}")
        return False


@app.route('/track/click', methods=['GET'])
def track_click():
    """Tracking de clics - Redirige a la tienda"""
    try:
        customer_id = request.args.get('customer_id')
        campaign_id = request.args.get('campaign_id', 'campana-default')
        url_destino = request.args.get('url', '/products/relojelegantehombre')
        
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        logger.info(f"🖱️ Tracking - Clic detectado:")
        logger.info(f"   Customer ID: {customer_id}")
        logger.info(f"   Campaign: {campaign_id}")
        
        if customer_id:
            save_tracking_event(
                customer_id=customer_id,
                campaign_id=campaign_id,
                event_type='clicked',
                ip_address=ip_address,
                user_agent=user_agent,
                link_url=url_destino,
                metadata=json.dumps({
                    'source': 'tracking_propio',
                    'url_destino': url_destino,
                    'timestamp': datetime.now().isoformat()
                })
            )
        
        # Construir URL de destino
        if url_destino.startswith('/'):
            url_destino = f"https://maisonlumien.com{url_destino}"
        elif not url_destino.startswith('http'):
            url_destino = f"https://maisonlumien.com/{url_destino}"
        
        response = make_response(redirect(url_destino, code=302))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        response = make_response(redirect("https://maisonlumien.com", code=302))
        return response


@app.route('/track/open', methods=['GET'])
def track_open():
    """Tracking de aperturas - Imagen invisible"""
    try:
        customer_id = request.args.get('customer_id')
        campaign_id = request.args.get('campaign_id', 'campana-default')
        
        if customer_id:
            save_tracking_event(
                customer_id=customer_id,
                campaign_id=campaign_id,
                event_type='opened',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                metadata=json.dumps({
                    'source': 'tracking_propio',
                    'timestamp': datetime.now().isoformat()
                })
            )
        
        # GIF transparente de 1x1 pixel
        transparent_gif = bytes([
            0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
            0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0x21,
            0xf9, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2c, 0x00, 0x00,
            0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
            0x01, 0x00, 0x3b
        ])
        
        response = app.response_class(
            response=transparent_gif,
            status=200,
            mimetype='image/gif'
        )
        return response
        
    except Exception as e:
        logger.error(f"❌ Error en tracking de apertura: {e}")
        return "", 204


@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Health check para Render"""
    return jsonify({
        'status': 'ok',
        'service': 'MaisonLumien Tracking System',
        'version': 'v1.0 - Render',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/webhook/test', methods=['GET'])
def test_webhook():
    return jsonify({
        'message': 'Webhook funcionando correctamente',
        'timestamp': datetime.now().isoformat()
    }), 200


# ============================================
# RUTA PRINCIPAL PARA RENDER
# ============================================
@app.route('/')
def home():
    return jsonify({
        'service': 'MaisonLumien Tracking System',
        'status': 'online',
        'endpoints': [
            '/track/click?customer_id=xxx&url=xxx',
            '/track/open?customer_id=xxx',
            '/webhook/health',
            '/webhook/test'
        ]
    }), 200


if __name__ == '__main__':
    print("=" * 60)
    print("  MAISONLUMIEN - TRACKING SYSTEM (Render)")
    print("=" * 60)
    print(f"\n🚀 Servidor iniciado en puerto {PORT}")
    print("\n📡 Endpoints disponibles:")
    print("   GET  /track/click     → Tracking de clics")
    print("   GET  /track/open      → Tracking de aperturas")
    print("   GET  /webhook/health  → Health check")
    print("   GET  /webhook/test    → Test")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)