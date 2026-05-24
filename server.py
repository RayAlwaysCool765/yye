import os
from flask import Flask, request, jsonify, session
from supabase import create_client
import requests

app = Flask(__name__)
app.secret_key = 'hann_super_secret_key'

SUPABASE_URL         = 'https://dtcrxnxhpwhmlciolkrr.supabase.co'
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0Y3J4bnhocHdobWxjaW9sa3JyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAzNzc4OCwiZXhwIjoyMDg3NjEzNzg4fQ.NiHRDE6ZSoHWIiS5AKwS4Xc7LbQ8gm4ODpEaZImNY8o"
NOWPAYMENTS_API_KEY  = "RBXGV8S-CR84S1R-K1ACRHJ-R2GY2N0"
BASE_URL             = 'https://shop.hann.lol'
ADMIN_PASSWORD       = 'HannScriptsOnTop'

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/')
def index():
    return 'hann api running'

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'ok': True})

@app.route('/admin/check', methods=['GET'])
def admin_check():
    if session.get('admin'):
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401

@app.route('/api/create-order', methods=['POST', 'OPTIONS'])
def create_order():
    if request.method == 'OPTIONS':
        return '', 204

    body           = request.get_json()
    product_name   = body.get('product_name')
    price          = body.get('price')
    payment_method = body.get('payment_method')

    currency_map = {
        'Bitcoin (BTC)':  'btc',
        'Litecoin (LTC)': 'ltc',
        'Solana (SOL)':   'sol',
        'Ethereum (ETH)': 'eth',
        'USDT (Tether)':  'usdttrc20',
    }
    pay_currency = currency_map.get(payment_method, 'btc')

    result = supabase.table('orders').insert({
        'product_name':     product_name,
        'price':            price,
        'payment_method':   payment_method,
        'status':           'pending',
        'delivery_content': None
    }).execute()

    order_id = result.data[0]['id']

    invoice_res = requests.post(
        'https://api.nowpayments.io/v1/invoice',
        headers={
            'x-api-key':    NOWPAYMENTS_API_KEY,
            'Content-Type': 'application/json'
        },
        json={
            'price_amount':      price,
            'price_currency':    'usd',
            'pay_currency':      pay_currency,
            'order_id':          order_id,
            'order_description': product_name,
            'success_url':       f'{BASE_URL}/claim/{order_id}',
            'cancel_url':        BASE_URL,
            'ipn_callback_url':  f'{BASE_URL}/api/webhook'
        }
    )

    invoice = invoice_res.json()

    if 'invoice_url' not in invoice:
        return jsonify({'error': 'Failed to create invoice'}), 500

    return jsonify({
        'order_id':    order_id,
        'invoice_url': invoice['invoice_url']
    })

@app.route('/api/webhook', methods=['POST', 'OPTIONS'])
def nowpayments_webhook():
    if request.method == 'OPTIONS':
        return '', 204

    data           = request.get_json()
    order_id       = data.get('order_id')
    payment_status = data.get('payment_status')

    if payment_status not in ('finished', 'confirmed'):
        return jsonify({'ok': True}), 200

    # Get order
    order_result = supabase.table('orders').select('*').eq('id', order_id).single().execute()
    order        = order_result.data

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Get delivery from products table dynamically
    product_result = supabase.table('products').select('delivery_content').eq('name', order['product_name']).single().execute()
    product        = product_result.data
    delivery       = product.get('delivery_content') if product else 'Contact support for your delivery.'

    supabase.table('orders').update({
        'status':           'paid',
        'delivery_content': delivery
    }).eq('id', order_id).execute()

    return jsonify({'ok': True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
