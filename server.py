import os
from flask import Flask, request, jsonify
from supabase import create_client
import requests

app = Flask(__name__)

SUPABASE_URL         = 'https://dtcrxnxhpwhmlciolkrr.supabase.co'
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0Y3J4bnhocHdobWxjaW9sa3JyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAzNzc4OCwiZXhwIjoyMDg3NjEzNzg4fQ.NiHRDE6ZSoHWIiS5AKwS4Xc7LbQ8gm4ODpEaZImNY8o"
NOWPAYMENTS_API_KEY  = "RBXGV8S-CR84S1R-K1ACRHJ-R2GY2N0"
BASE_URL             = 'https://shop.hann.lol'

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

DELIVERIES = {
    'Bee swarm source':    'YOUR BEE SWARM SCRIPT OR LINK HERE',
    'Sab trade source':    'YOUR SAB TRADE SCRIPT OR LINK HERE',
    'Sailor piece source': 'YOUR SAILOR PIECE SCRIPT OR LINK HERE',
    'Adopt me source':     'YOUR ADOPT ME SCRIPT OR LINK HERE',
    'Mm2 source':          'YOUR MM2 SCRIPT OR LINK HERE',
    'Etfb source':         'YOUR ETFB SCRIPT OR LINK HERE',
    'Ps99 trade source':   'YOUR PS99 TRADE SCRIPT OR LINK HERE',
    'Ps99 mail':           'YOUR PS99 MAIL SCRIPT OR LINK HERE',
}

@app.route('/api/create-order', methods=['POST'])
def create_order():
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

@app.route('/api/webhook', methods=['POST'])
def nowpayments_webhook():
    data           = request.get_json()
    order_id       = data.get('order_id')
    payment_status = data.get('payment_status')

    if payment_status not in ('finished', 'confirmed'):
        return jsonify({'ok': True}), 200

    result = supabase.table('orders').select('*').eq('id', order_id).single().execute()
    order  = result.data

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    delivery = DELIVERIES.get(order['product_name'], 'Contact support for your delivery.')

    supabase.table('orders').update({
        'status':           'paid',
        'delivery_content': delivery
    }).eq('id', order_id).execute()

    return jsonify({'ok': True}), 200

if __name__ == '__main__':
    app.run(port=3000, debug=True)
