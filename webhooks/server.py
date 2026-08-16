"""
SERVIDOR WEBHOOK PARA MAISONLUMIEN - VERSIÓN COMPLETA CON CONSULTAS
"""

import sys
import os
import json
import logging
import uuid
import sqlite3
from datetime import datetime, timedelta
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
# ENDPOINTS DE TRACKING
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


# ============================================
# ENDPOINTS DE CONSULTA (PARA VER LOS DATOS)
# ============================================
@app.route('/webhook/events', methods=['GET'])
def get_events():
    """Obtiene los últimos 50 eventos con todos los detalles"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a la BD'}), 500
        
        # Obtener parámetros de filtro
        customer_id = request.args.get('customer_id')
        campaign_id = request.args.get('campaign_id')
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', 50))
        
        cursor = conn.cursor()
        
        # Construir consulta con filtros
        query = '''
            SELECT 
                id,
                customer_id_text,
                campaign_id,
                event_type,
                event_timestamp,
                ip_address,
                user_agent,
                link_url,
                metadata
            FROM email_events
            WHERE 1=1
        '''
        params = []
        
        if customer_id:
            query += ' AND customer_id_text = ?'
            params.append(customer_id)
        if campaign_id:
            query += ' AND campaign_id = ?'
            params.append(campaign_id)
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        query += ' ORDER BY event_timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'customer_id': row[1],
                'campaign': row[2],
                'event_type': row[3],
                'timestamp': row[4],
                'ip': row[5],
                'user_agent': row[6][:100] + '...' if row[6] and len(row[6]) > 100 else row[6],
                'link_url': row[7],
                'metadata': json.loads(row[8]) if row[8] else None
            })
        
        conn.close()
        return jsonify({
            'total': len(events),
            'filters': {
                'customer_id': customer_id,
                'campaign_id': campaign_id,
                'event_type': event_type,
                'limit': limit
            },
            'events': events
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo eventos: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas completas"""
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
        ''')
        by_campaign = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Eventos por día (últimos 7 días)
        cursor.execute('''
            SELECT 
                DATE(event_timestamp) as date,
                COUNT(*) as count
            FROM email_events
            WHERE event_timestamp >= DATE('now', '-7 days')
            GROUP BY DATE(event_timestamp)
            ORDER BY date DESC
        ''')
        by_day = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Clientes más activos
        cursor.execute('''
            SELECT 
                customer_id_text,
                COUNT(*) as count
            FROM email_events
            WHERE customer_id_text IS NOT NULL
            GROUP BY customer_id_text
            ORDER BY count DESC
            LIMIT 10
        ''')
        top_customers = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify({
            'total_events': total,
            'by_type': by_type,
            'by_campaign': by_campaign,
            'by_day': by_day,
            'top_customers': top_customers,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/customer/<customer_id>', methods=['GET'])
def get_customer_events(customer_id):
    """Obtiene todos los eventos de un cliente específico"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a la BD'}), 500
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                id,
                campaign_id,
                event_type,
                event_timestamp,
                ip_address,
                link_url
            FROM email_events
            WHERE customer_id_text = ?
            ORDER BY event_timestamp DESC
        ''', (customer_id,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'campaign': row[1],
                'event_type': row[2],
                'timestamp': row[3],
                'ip': row[4],
                'link_url': row[5]
            })
        
        conn.close()
        return jsonify({
            'customer_id': customer_id,
            'total': len(events),
            'events': events
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo eventos del cliente: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/campaign/<campaign_id>', methods=['GET'])
def get_campaign_stats(campaign_id):
    """Obtiene estadísticas de una campaña específica"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a la BD'}), 500
        
        cursor = conn.cursor()
        
        # Total por tipo
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM email_events
            WHERE campaign_id = ?
            GROUP BY event_type
        ''', (campaign_id,))
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total general
        cursor.execute('SELECT COUNT(*) FROM email_events WHERE campaign_id = ?', (campaign_id,))
        total = cursor.fetchone()[0]
        
        # Clientes únicos
        cursor.execute('''
            SELECT COUNT(DISTINCT customer_id_text)
            FROM email_events
            WHERE campaign_id = ? AND customer_id_text IS NOT NULL
        ''', (campaign_id,))
        unique_customers = cursor.fetchone()[0]
        
        # Últimos eventos
        cursor.execute('''
            SELECT 
                customer_id_text,
                event_type,
                event_timestamp
            FROM email_events
            WHERE campaign_id = ?
            ORDER BY event_timestamp DESC
            LIMIT 10
        ''', (campaign_id,))
        recent = []
        for row in cursor.fetchall():
            recent.append({
                'customer_id': row[0],
                'event_type': row[1],
                'timestamp': row[2]
            })
        
        conn.close()
        
        return jsonify({
            'campaign_id': campaign_id,
            'total_events': total,
            'unique_customers': unique_customers,
            'by_type': by_type,
            'recent_events': recent
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas de campaña: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# WEBHOOKS EXTERNOS
# ============================================
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


# ============================================
# ENDPOINTS DE SALUD Y TEST
# ============================================
@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Health check para Render"""
    return jsonify({
        'status': 'ok',
        'service': 'MaisonLumien Tracking System',
        'version': 'v2.0 - Completo',
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


# ============================================
# RUTA PRINCIPAL
# ============================================
@app.route('/')
def home():
    return jsonify({
        'service': 'MaisonLumien Tracking System',
        'status': 'online',
        'version': 'v2.0 - Completo',
        'database': 'SQLite',
        'endpoints': {
            'tracking': {
                'click': '/track/click?customer_id=xxx&url=xxx',
                'open': '/track/open?customer_id=xxx'
            },
            'consultas': {
                'eventos': '/webhook/events?customer_id=xxx&limit=50',
                'estadisticas': '/webhook/stats',
                'cliente': '/webhook/customer/[customer_id]',
                'campaña': '/webhook/campaign/[campaign_id]'
            },
            'webhooks': {
                'shopify': '/webhook/shopify/order (POST)',
                'mailgun': '/webhook/mailgun (POST)'
            },
            'salud': {
                'health': '/webhook/health',
                'test': '/webhook/test'
            }
        }
    }), 200


if __name__ == '__main__':
    print("=" * 60)
    print("  MAISONLUMIEN - TRACKING SYSTEM (v2.0 - Completo)")
    print("=" * 60)
    print(f"\n🚀 Servidor iniciado en puerto {PORT}")
    print(f"📁 Base de datos: {DB_PATH}")
    print("\n📡 Endpoints disponibles:")
    print("   TRACKING:")
    print("   GET  /track/click     → Tracking de clics")
    print("   GET  /track/open      → Tracking de aperturas")
    print("   CONSULTAS:")
    print("   GET  /webhook/events  → Ver eventos (filtros)")
    print("   GET  /webhook/stats   → Estadísticas completas")
    print("   GET  /webhook/customer/[id] → Eventos por cliente")
    print("   GET  /webhook/campaign/[id] → Estadísticas por campaña")
    print("   WEBHOOKS:")
    print("   POST /webhook/shopify → Webhook de Shopify")
    print("   POST /webhook/mailgun → Webhook de Mailgun")
    print("   SALUD:")
    print("   GET  /webhook/health  → Health check")
    print("   GET  /webhook/test    → Test")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
