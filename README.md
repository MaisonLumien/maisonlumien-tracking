
### `/webhook/shopify/order`

Recibe notificaciones de Shopify cuando se crea un pedido. Shopify envía automáticamente los datos en formato JSON.

**Configuración en Shopify:**
- **Evento:** `Pedido creado`
- **Formato:** `JSON`
- **URL:** `https://click.maisonlumien.com/webhook/shopify/order`

### `/webhook/mailgun`

Recibe eventos de Mailgun (aperturas, clics, rebotes, etc.) cuando Mailgun los envía.

**Configuración en Mailgun:**
- **URL:** `https://click.maisonlumien.com/webhook/mailgun`
- **Eventos:** Seleccionar todos

## 🗄️ Base de datos

El sistema guarda los eventos en la tabla `marketing.email_events`.

### Estructura de la tabla

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | UNIQUEIDENTIFIER | Identificador único del evento |
| `customer_id_text` | NVARCHAR(50) | ID del cliente (texto) |
| `campaign_id` | NVARCHAR(50) | ID de la campaña |
| `message_id` | NVARCHAR(255) | ID del mensaje |
| `event_type` | NVARCHAR(50) | Tipo de evento: `opened`, `clicked`, `purchased` |
| `event_timestamp` | DATETIME2 | Fecha y hora del evento |
| `ip_address` | VARCHAR(45) | Dirección IP del usuario |
| `user_agent` | NVARCHAR(500) | Navegador/dispositivo del usuario |
| `link_url` | NVARCHAR(1000) | URL que fue clickeada |
| `metadata` | NVARCHAR(MAX) | Metadatos adicionales en JSON |

### Consultas útiles

```sql
-- Ver eventos de los últimos 7 días
SELECT 
    event_type,
    customer_id_text,
    campaign_id,
    event_timestamp,
    link_url
FROM marketing.email_events
WHERE event_timestamp > DATEADD(DAY, -7, GETDATE())
ORDER BY event_timestamp DESC;

-- Estadísticas por campaña
SELECT 
    campaign_id,
    COUNT(*) AS total_eventos,
    SUM(CASE WHEN event_type = 'clicked' THEN 1 ELSE 0 END) AS clics,
    SUM(CASE WHEN event_type = 'opened' THEN 1 ELSE 0 END) AS aperturas,
    SUM(CASE WHEN event_type = 'purchased' THEN 1 ELSE 0 END) AS compras
FROM marketing.email_events
GROUP BY campaign_id
ORDER BY total_eventos DESC;

-- Clientes más activos
SELECT 
    customer_id_text,
    COUNT(*) AS total_eventos,
    MAX(event_timestamp) AS ultima_actividad
FROM marketing.email_events
GROUP BY customer_id_text
ORDER BY total_eventos DESC;