"""
SERVIDOR WEBHOOK PARA MAISONLUMIEN - VERSIÓN SQLITE PARA RENDER
"""

import sys
import os
import json
import logging
import uuid
import sqlite3
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
# CONEXIÓN A BASE DE DATOS SQLITE
# ============================================
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tracking.db')

def get_db_connection():
    """Obtiene conexión a la base de datos SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"❌ Error de conexión a SQLite: {e}")
        return None

def init_db():
    """Crea la tabla si no existe"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ No se pudo conectar a SQLite")
            return
        
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_events (
                id TEXT PRIMARY KEY,
                customer_id_text TEXT,
                campaign_id TEXT,
                message_id TEXT,
                event_type TEXT,
                event_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                link_url TEXT,
                metadata TEXT
            )
        ''')
        
        # Crear índices para mejorar rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_id ON email_events(customer_id_text)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_id ON email_events(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON email_events(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON email_events(event_timestamp)')
        
        conn.commit()
        conn.close()
        logger.info("✅ Base de datos SQLite inicializada correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando SQLite: {e}")

# Inicializar la base de datos al arrancar
init_db()

# ============================================
# FUNCIONES DE TRACKING
# ============================================
def save_tracking_event(customer_id, campaign_id, event_type, 
                        ip_address=None, user_agent=None, link_url=None, metadata=None):
    """Guarda un evento de tracking en la base de datos SQLite"""
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
            INSERT INTO email_events (
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
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
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


# ============================================
# ENDPOINTS
# ============================================
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
        logger.error(f"❌ Error en tracking de clic: {e}")
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


@app.route('/webhook/shopify/order', methods=['POST'])
def shopify_order_webhook():
    """Webhook de Shopify - Registra compras"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        order = data
        customer_data = order.get('customer', {})
        email = customer_data.get('email', '')
        order_number = order.get('order_number')
        total_price = float(order.get('total_price', 0))
        
        logger.info(f"💰 Shopify - Pedido: #{order_number} - {email}")
        
        # Buscar o crear customer_id
        customer_id = f"shopify_{order_number}"
        
        save_tracking_event(
            customer_id=customer_id,
            campaign_id='shopify_purchase',
            event_type='purchased',
            metadata=json.dumps({
                'source': 'shopify_webhook',
                'order_number': order_number,
                'total_price': total_price,
                'email': email,
                'products': order.get('line_items', [])
            })
        )

        return jsonify({'status': 'ok', 'message': 'Compra registrada'}), 200

    except Exception as e:
        logger.error(f"❌ Error en webhook Shopify: {e}")
        return jsonify({'error': 'Error interno'}), 500


@app.route('/webhook/mailgun', methods=['POST'])
def mailgun_webhook():
    """Webhook de Mailgun"""
    try:
        data = request.form
        event_type = data.get('event')
        recipient = data.get('recipient')
        
        logger.info(f"📨 Mailgun webhook: {event_type} para {recipient}")
        
        user_vars = data.get('user-variables', {})
        if isinstance(user_vars, str):
            try:
                user_vars = json.loads(user_vars)
            except:
                user_vars = {}
        
        customer_id = user_vars.get('customer_id')
        campaign_id = user_vars.get('campaign_id')
        
        if customer_id and event_type:
            save_tracking_event(
                customer_id=customer_id,
                campaign_id=campaign_id or 'mailgun',
                event_type=event_type,
                ip_address=data.get('ip'),
                user_agent=data.get('user-agent'),
                link_url=data.get('url'),
                metadata=json.dumps(dict(data))
            )
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Mailgun: {e}")
        return "Error", 500


@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Health check para Render"""
    return jsonify({
        'status': 'ok',
        'service': 'MaisonLumien Tracking System',
        'version': 'v1.0 - SQLite',
        'database': 'SQLite',
        'db_path': DB_PATH,
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/webhook/test', methods=['GET'])
def test_webhook():
    return jsonify({
        'message': 'Webhook funcionando correctamente',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/webhook/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas de la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a la BD'}), 500
        
        cursor = conn.cursor()
        
        # Total de eventos
        cursor.execute('SELECT COUNT(*) FROM email_events')
        total = cursor.fetchone()[0]
        
        # Eventos por tipo
        cursor.execute('''
            SELECT event_type, COUNT(*) as count 
            FROM email_events 
            GROUP BY event_type
        ''')
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Eventos por campaña
        cursor.execute('''
            SELECT campaign_id, COUNT(*) as count 
            FROM email_events 
            GROUP BY campaign_id
            ORDER BY count DESC
            LIMIT 10
        ''')
        by_campaign = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify({
            'total_events': total,
            'by_type': by_type,
            'by_campaign': by_campaign,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# RUTA PRINCIPAL
# ============================================
@app.route('/')
def home():
    return jsonify({
        'service': 'MaisonLumien Tracking System',
        'status': 'online',
        'version': 'v1.0 - SQLite',
        'database': 'SQLite',
        'endpoints': {
            'track_click': '/track/click?customer_id=xxx&url=xxx',
            'track_open': '/track/open?customer_id=xxx',
            'webhook_shopify': '/webhook/shopify/order',
            'webhook_mailgun': '/webhook/mailgun',
            'health': '/webhook/health',
            'stats': '/webhook/stats',
            'test': '/webhook/test'
        }
    }), 200


if __name__ == '__main__':
    print("=" * 60)
    print("  MAISONLUMIEN - TRACKING SYSTEM (SQLite)")
    print("=" * 60)
    print(f"\n🚀 Servidor iniciado en puerto {PORT}")
    print(f"📁 Base de datos: {DB_PATH}")
    print("\n📡 Endpoints disponibles:")
    print("   GET  /track/click     → Tracking de clics")
    print("   GET  /track/open      → Tracking de aperturas")
    print("   POST /webhook/shopify → Webhook de Shopify")
    print("   POST /webhook/mailgun → Webhook de Mailgun")
    print("   GET  /webhook/health  → Health check")
    print("   GET  /webhook/stats   → Estadísticas")
    print("   GET  /webhook/test    → Test")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
