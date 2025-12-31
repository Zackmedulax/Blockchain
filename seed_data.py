import requests
import rsa
import base64
from time import sleep

BASE_URL = "http://localhost:5000"

def create_wallet():
    """Buat wallet baru."""
    resp = requests.get(f"{BASE_URL}/wallet/new").json()
    pk = resp['public_key']
    sk_pem = resp['private_key']
    sk = rsa.PrivateKey.load_pkcs1(sk_pem.encode())
    return pk, sk

def send_transaction(sender_pk, sender_sk, recipient_pk, amount, fee, nonce):
    """Kirim transaksi."""
    message = f"{sender_pk}:{recipient_pk}:{amount}:{fee}:{nonce}"
    signature = rsa.sign(message.encode(), sender_sk, 'SHA-256')
    signature_b64 = base64.b64encode(signature).decode()
    
    tx_data = {
        "sender": sender_pk,
        "recipient": recipient_pk,
        "amount": amount,
        "fee": fee,
        "nonce": nonce,
        "signature": signature_b64
    }
    
    res = requests.post(f"{BASE_URL}/transactions/new", json=tx_data)
    return res.json()

def mine_block(miner_address=None):
    """Mine block."""
    params = {'miner_address': miner_address} if miner_address else {}
    res = requests.get(f"{BASE_URL}/mine", params=params)
    return res.json()

print("🌱 Seeding DSS_Chain dengan data sample...")
print("=" * 50)

# Buat 3 wallets
print("\n[1] Membuat Wallets...")
alice_pk, alice_sk = create_wallet()
print("    ✓ Alice wallet created")

bob_pk, bob_sk = create_wallet()
print("    ✓ Bob wallet created")

charlie_pk, charlie_sk = create_wallet()
print("    ✓ Charlie wallet created")

# Mine beberapa blocks untuk Alice (untuk dapat dana awal)
print("\n[2] Mining blocks untuk Alice (mendapatkan dana awal)...")
for i in range(3):
    mine_block(alice_pk)
    sleep(0.3)
print(f"    ✓ Mined 3 blocks (Alice balance: 3.0 DNR)")

# Alice kirim ke Bob
print("\n[3] Alice → Bob: 1.2 DNR (fee: 0.05)")
send_transaction(alice_pk, alice_sk, bob_pk, 1.2, 0.05, 0)

# Alice kirim ke Charlie
print("    Alice → Charlie: 0.8 DNR (fee: 0.03)")
send_transaction(alice_pk, alice_sk, charlie_pk, 0.8, 0.03, 1)

# Mine block (miner menerima reward + fees)
print("\n[4] Mining block untuk confirm transaksi...")
mine_block(charlie_pk)  # Charlie jadi miner
sleep(0.5)

# Bob kirim ke Charlie
print("\n[5] Bob → Charlie: 0.5 DNR (fee: 0.02)")
send_transaction(bob_pk, bob_sk, charlie_pk, 0.5, 0.02, 0)

# Charlie kirim ke Alice
print("    Charlie → Alice: 0.3 DNR (fee: 0.01)")
send_transaction(charlie_pk, charlie_sk, alice_pk, 0.3, 0.01, 0)

# Mine 2 blocks lagi
print("\n[6] Mining 2 blocks tambahan...")
mine_block(bob_pk)
sleep(0.3)
mine_block(alice_pk)

print("\n" + "=" * 50)
print("✅ Seeding complete!")
print(f"\n🌐 Lihat hasilnya di: {BASE_URL}/explorer")
print(f"📊 Chain info: {BASE_URL}/blockchain")
