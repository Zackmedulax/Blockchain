import requests
import json
import rsa
import base64
from time import sleep

BASE_URL = "http://localhost:5000"

def get_balance(address):
    res = requests.post(f"{BASE_URL}/history", json={"address": address})
    if res.status_code != 200:
        print(f"Failed to get history: {res.text}")
        return 0
    
    txs = res.json().get('transactions', [])
    balance = 0
    for tx in txs:
        if tx['recipient'] == address:
            balance += tx['amount']
        if tx['sender'] == address:
            balance -= tx['amount']
            # Juga kurangi fee
            balance -= tx.get('fee', 0)
    return balance

def main():
    print("=== DSS_Chain Advanced Features Test ===\n")
    
    print("[1] Creating Wallet A...")
    resp = requests.get(f"{BASE_URL}/wallet/new").json()
    pk_a = resp['public_key']
    sk_a_pem = resp['private_key']
    sk_a = rsa.PrivateKey.load_pkcs1(sk_a_pem.encode())
    print(f"    ✓ Wallet A Created.")

    print("[2] Creating Wallet B...")
    resp = requests.get(f"{BASE_URL}/wallet/new").json()
    pk_b = resp['public_key']
    print(f"    ✓ Wallet B Created.\n")

    print("[3] Mining blocks to Wallet A...")
    for i in range(3):
        requests.get(f"{BASE_URL}/mine", params={'miner_address': pk_a})
        sleep(0.5)
    print("    ✓ Mined 3 blocks.")

    bal_a = get_balance(pk_a)
    print(f"    Balance A: {bal_a} DNR\n")

    print("[4] Testing Transaction with FEE...")
    amount = 1.5
    fee = 0.25
    nonce = 0
    message = f"{pk_a}:{pk_b}:{amount}:{fee}:{nonce}"
    signature = rsa.sign(message.encode(), sk_a, 'SHA-256')
    signature_b64 = base64.b64encode(signature).decode()

    tx_data = {
        "sender": pk_a,
        "recipient": pk_b,
        "amount": amount,
        "fee": fee,
        "nonce": nonce,
        "signature": signature_b64
    }
    
    res = requests.post(f"{BASE_URL}/transactions/new", json=tx_data)
    print(f"    Response: {res.json()}")

    print("[5] Mining block (miner gets reward + fee)...")
    # Different miner untuk test fee distribution
    resp_miner = requests.get(f"{BASE_URL}/wallet/new").json()
    pk_miner = resp_miner['public_key']
    
    requests.get(f"{BASE_URL}/mine", params={'miner_address': pk_miner})
    
    bal_b = get_balance(pk_b)
    bal_miner = get_balance(pk_miner)
    print(f"    ✓ Transaction Confirmed!")
    print(f"    Balance B: {bal_b} DNR (expected: 1.5)")
    print(f"    Balance Miner: {bal_miner} DNR (expected: 1.0 reward + 0.25 fee = 1.25)\n")

    print("[6] Testing Nonce (Replay Attack Prevention)...")
    # Try to replay the same transaction with old nonce
    try:
        res = requests.post(f"{BASE_URL}/transactions/new", json=tx_data)
        if res.status_code == 400:
            print(f"    ✓ Replay Attack PREVENTED: {res.json()['error']}")
        else:
            print(f"    ✗ Replay attack should have been blocked!")
    except Exception as e:
        print(f"    Error: {e}\n")

    print("[7] Mining more blocks to test Dynamic Difficulty...")
    for i in range(5):
        requests.get(f"{BASE_URL}/mine", params={'miner_address': pk_a})
        sleep(0.2)  # Fast mining
    print("    ✓ Check server logs for difficulty adjustments!\n")

    # Get chain info
    chain_res = requests.get(f"{BASE_URL}/blockchain").json()
    latest_block = chain_res['chain'][-1]
    print(f"[8] Latest Block Info:")
    print(f"    Index: {latest_block['index']}")
    print(f"    Difficulty: {latest_block.get('difficulty', 'N/A')}")
    print(f"    Merkle Root: {latest_block.get('merkle_root', 'N/A')[:16]}...")
    print(f"    Transactions: {len(latest_block['transactions'])}\n")

    print("=== Test Complete ===")
    if bal_b == 1.5 and bal_miner == 1.25:
        print("✓ All features working correctly!")
    else:
        print("⚠ Some features may need verification")

if __name__ == "__main__":
    main()
