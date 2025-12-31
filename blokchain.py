import sys
import hashlib
import json
import os
from time import time
from uuid import uuid4
from flask import Flask, request, jsonify, render_template_string
import requests
from urllib.parse import urlparse
from utils_crypto import verify_signature, generate_keypair
from utils_merkle import calculate_merkle_root

CHAIN_FILE = "chain_data.json"

class Blockchain:
    def __init__(self):
        self.nodes = set()
        self.chain = []
        self.current_transactions = []
        self.difficulty_target = "0000"
        self.difficulty_adjustment_interval = 5  # Adjust setiap 5 blocks
        self.target_block_time = 10  # Target 10 detik per block
        self.user_nonces = {}  # Track nonce per user untuk prevent replay attacks
        if os.path.exists(CHAIN_FILE):
            self.load_chain()
        else:
            genesis_hash = self.hash_block("genesis_block")
            self.append_block(
                nonce=self.proof_of_work(0, genesis_hash, []),
                hash_of_previous_block=genesis_hash
            )
            self.save_chain()

    def save_chain(self):
        with open(CHAIN_FILE, "w") as f:
            json.dump(self.chain, f, indent=4)

    def load_chain(self):
        with open(CHAIN_FILE, "r") as f:
            self.chain = json.load(f)

    def add_node(self, address):
        if not address.startswith("http://") and not address.startswith("https://"):
            address = f"http://{address}"
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        if not chain or not isinstance(chain, list):
            return False
        try:
            last_block = chain[0]
            current_index = 1
            while current_index < len(chain):
                block = chain[current_index]
                if block['hash_of_previous_block'] != self.hash_block(last_block):
                    return False
                if not self.valid_proof(
                    current_index,
                    block['hash_of_previous_block'],
                    block['transactions'],
                    block['nonce']
                ):
                    return False
                last_block = block
                current_index += 1
            return True
        except Exception as e:
            print(f"[!] Error in valid_chain: {e}")
            return False

    def update_blockchain(self):
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/blockchain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except Exception as e:
                print(f"[!] Gagal sync ke node {node}: {e}")

        if new_chain:
            self.chain = new_chain
            self.save_chain()
            return True
        return False

    def hash_block(self, block):
        block_encoded = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_encoded).hexdigest()

    def proof_of_work(self, index, hash_of_previous_block, transactions):
        nonce = 0
        while not self.valid_proof(index, hash_of_previous_block, transactions, nonce):
            nonce += 1
        return nonce

    def valid_proof(self, index, hash_of_previous_block, transactions, nonce):
        content = f'{index}{hash_of_previous_block}{transactions}{nonce}'.encode()
        content_hash = hashlib.sha256(content).hexdigest()
        return content_hash[:len(self.difficulty_target)] == self.difficulty_target

    def adjust_difficulty(self):
        """Adjust difficulty berdasarkan kecepatan mining."""
        if len(self.chain) % self.difficulty_adjustment_interval != 0:
            return
        
        if len(self.chain) < self.difficulty_adjustment_interval:
            return
        
        # Hitung waktu yang diperlukan untuk N blocks terakhir
        recent_blocks = self.chain[-self.difficulty_adjustment_interval:]
        time_taken = recent_blocks[-1]['timestamp'] - recent_blocks[0]['timestamp']
        expected_time = self.target_block_time * self.difficulty_adjustment_interval
        
        # Jika terlalu cepat, tambah difficulty
        if time_taken < expected_time * 0.5:
            self.difficulty_target += "0"  # Lebih sulit
            print(f"[+] Difficulty INCREASED to {self.difficulty_target}")
        # Jika terlalu lambat, kurangi difficulty
        elif time_taken > expected_time * 2 and len(self.difficulty_target) > 1:
            self.difficulty_target = self.difficulty_target[:-1]  # Lebih mudah
            print(f"[-] Difficulty DECREASED to {self.difficulty_target}")

    def append_block(self, nonce, hash_of_previous_block):
        merkle_root = calculate_merkle_root(self.current_transactions)
        
        block = {
            'index': len(self.chain),
            'timestamp': time(),
            'transactions': self.current_transactions,
            'nonce': nonce,
            'hash_of_previous_block': hash_of_previous_block,
            'merkle_root': merkle_root,
            'difficulty': self.difficulty_target
        }
        self.current_transactions = []
        self.chain.append(block)
        self.adjust_difficulty()
        self.save_chain()
        return block

    def get_balance_of(self, address):
        balance = 0
        for block in self.chain:
            for tx in block['transactions']:
                if tx['recipient'] == address:
                    balance += tx['amount']
                elif tx['sender'] == address:
                    balance -= tx['amount']
        return balance

    def add_transaction(self, sender, recipient, amount, signature=None, fee=0, nonce=None):
        if sender != "0":
            # Verify nonce (prevent replay attacks)
            if nonce is not None:
                current_nonce = self.user_nonces.get(sender, -1)
                if nonce <= current_nonce:
                    raise ValueError(f"Nonce invalid. Expected > {current_nonce}, got {nonce}")
                self.user_nonces[sender] = nonce
            
            message = f"{sender}:{recipient}:{amount}:{fee}:{nonce}"
            # Sender diasumsikan sebagai Public Key (PEM format) atau identifier unik
            # Verifikasi signature menggunakan sender itu sendiri (jika sender adalah pubkey)
            if not signature or not verify_signature(sender, message, signature):
                raise ValueError("Signature tidak valid atau hilang")

            total_cost = amount + fee
            if self.get_balance_of(sender) < total_cost:
                raise ValueError(f"Saldo {sender} tidak cukup. Perlu {total_cost}, ada {self.get_balance_of(sender)}")

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'fee': fee,
            'nonce': nonce,
            'currency': "DNR",
            'timestamp': time()
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

# Flask App
app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', "")
blockchain = Blockchain()

@app.route('/')
def home():
    return "<h2 style='text-align:center'>🧱 DSS_Chain 2.0 Aktif</h2><p>Menu: <a href='/explorer'>/explorer</a>, <a href='/nodes'>/nodes</a>, <a href='/blockchain'>/blockchain</a></p>"

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
    pub, priv = generate_keypair()
    return jsonify({
        'private_key': priv,
        'public_key': pub,
        'message': "Simpan kunci ini! Private key tidak disimpan di server."
    })

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(k in values for k in required):
        return jsonify({'error': 'Field kurang'}), 400
    try:
        index = blockchain.add_transaction(
            values['sender'], 
            values['recipient'], 
            values['amount'], 
            values['signature'],
            fee=values.get('fee', 0),
            nonce=values.get('nonce')
        )
        return jsonify({'message': f'Transaksi akan masuk ke block {index}'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/mine', methods=['GET'])
def mine_block():
    # Allow custom miner address to receive rewards (facilitates testing)
    miner_address = request.args.get('miner_address', node_identifier)
    
    # Hitung total fees dari pending transactions
    total_fees = sum(tx.get('fee', 0) for tx in blockchain.current_transactions)
    
    # Block reward + fees
    block_reward = 1.0
    total_reward = block_reward + total_fees
    
    # Coinbase transaction (mining reward)
    blockchain.add_transaction("0", miner_address, total_reward)
    last_hash = blockchain.hash_block(blockchain.last_block)
    nonce = blockchain.proof_of_work(len(blockchain.chain), last_hash, blockchain.current_transactions)
    block = blockchain.append_block(nonce, last_hash)
    return jsonify({
        'message': 'Block ditambahkan!',
        'block': block
    })

@app.route('/blockchain', methods=['GET'])
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    })

@app.route('/nodes/add_nodes', methods=['POST'])
def add_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if not nodes:
        return "Missing nodes", 400
    for node in nodes:
        blockchain.add_node(node)
    return jsonify({'message': 'Node ditambahkan', 'nodes': list(blockchain.nodes)})

@app.route('/nodes/sync', methods=['GET'])
def sync_nodes():
    updated = blockchain.update_blockchain()
    msg = 'Blockchain diperbarui' if updated else 'Blockchain sudah up-to-date'
    return jsonify({'message': msg, 'chain': blockchain.chain})

@app.route('/nodes', methods=['GET'])
def list_nodes():
    return jsonify({'nodes': list(blockchain.nodes)})

@app.route('/balance/<address>', methods=['GET'])
def check_balance(address):
    balance = blockchain.get_balance_of(address)
    return jsonify({'address': address, 'balance': balance, 'currency': 'DNR'})

    return jsonify({'total_supply': total, 'currency': 'DNR'})

@app.route('/transactions/pending', methods=['GET'])
def pending_tx():
    return jsonify(blockchain.current_transactions)

@app.route('/history', methods=['POST'])
def history():
    """
    Cari history transaksi berdasarkan address (public key atau identifier).
    Menggunakan POST karena Public Key terlalu panjang untuk URL.
    """
    values = request.get_json()
    address = values.get('address')
    if not address:
        return jsonify({'error': 'Missing address'}), 400
        
    user_txs = []
    # Scan chain
    for block in blockchain.chain:
        for tx in block['transactions']:
            if tx['sender'] == address or tx['recipient'] == address:
                # Tambahkan info block index biar informatif
                tx_copy = tx.copy()
                tx_copy['block_index'] = block['index']
                tx_copy['timestamp'] = block['timestamp']
                user_txs.append(tx_copy)
    
    # Scan pending (mempool)
    for tx in blockchain.current_transactions:
        if tx['sender'] == address or tx['recipient'] == address:
            tx_copy = tx.copy()
            tx_copy['status'] = 'pending'
            user_txs.append(tx_copy)

    return jsonify({'address': address, 'transactions': user_txs})

@app.route('/explorer', methods=['GET'])
def explorer():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DSS_Chain Explorer</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
            h1 { text-align: center; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .stats { background: rgba(255,255,255,0.95); padding: 15px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .block { background: rgba(255,255,255,0.95); border-left: 5px solid #667eea; padding: 15px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .block-header { font-weight: bold; color: #667eea; margin-bottom: 10px; font-size: 1.2em; }
            .tx { background: #f7f7f7; padding: 10px; margin: 5px 0; border-radius: 5px; font-family: monospace; font-size: 0.9em; }
            .fee { color: #e67e22; font-weight: bold; }
            .reward { color: #27ae60; font-weight: bold; }
            .hash { color: #666; font-size: 0.85em; word-break: break-all; }
        </style>
    </head>
    <body>
        <h1>🧱 DSS_Chain Advanced Explorer</h1>
        <div class="stats">
            <strong>Chain Stats:</strong> 
            Total Blocks: {{ chain|length }} | 
            Current Difficulty: <span style="color: #e74c3c; font-weight: bold;">{{ difficulty }}</span> |
            Pending TX: {{ pending_count }}
        </div>
        {% for block in chain %}
        <div class="block">
            <div class="block-header">Block #{{ block.index }}</div>
            <div><strong>Timestamp:</strong> {{ block.timestamp }}</div>
            <div><strong>Difficulty:</strong> {{ block.get('difficulty', 'N/A') }}</div>
            <div><strong>Nonce:</strong> {{ block.nonce }}</div>
            <div class="hash"><strong>Previous Hash:</strong> {{ block.hash_of_previous_block }}</div>
            <div class="hash"><strong>Merkle Root:</strong> {{ block.get('merkle_root', 'N/A') }}</div>
            <div style="margin-top: 10px;"><strong>Transactions ({{ block.transactions|length }}):</strong></div>
            {% for tx in block.transactions %}
                <div class="tx">
                    {% if tx.sender == "0" %}
                        <span class="reward">⛏ MINING REWARD</span> → {{ tx.recipient[:30] }}... : {{ tx.amount }} {{ tx.currency }}
                    {% else %}
                        {{ tx.sender[:20] }}... ➜ {{ tx.recipient[:20] }}... : {{ tx.amount }} {{ tx.currency }}
                        {% if tx.get('fee', 0) > 0 %}
                            <span class="fee">(Fee: {{ tx.fee }})</span>
                        {% endif %}
                    {% endif %}
                </div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html, 
                                   chain=blockchain.chain, 
                                   difficulty=blockchain.difficulty_target,
                                   pending_count=len(blockchain.current_transactions))

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(host='0.0.0.0', port=port)