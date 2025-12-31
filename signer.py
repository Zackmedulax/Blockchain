import rsa
import base64
import json
import argparse
import requests

# Load private key
with open("private.pem", "rb") as f:
    privkey = rsa.PrivateKey.load_pkcs1(f.read())

# Argparse for CLI
parser = argparse.ArgumentParser(description="Sign and send DinarChain transaction")
parser.add_argument("--sender", required=True, help="Alamat pengirim")
parser.add_argument("--recipient", required=True, help="Alamat penerima")
parser.add_argument("--amount", type=int, required=True, help="Jumlah DNR")
parser.add_argument("--node", default="http://127.0.0.1:5000", help="Alamat node target")
args = parser.parse_args()

# Prepare data to sign
message = f"{args.sender}:{args.recipient}:{args.amount}"
signature = rsa.sign(message.encode(), privkey, "SHA-256")
signature_b64 = base64.b64encode(signature).decode()

# Prepare payload
tx_payload = {
    "sender": args.sender,
    "recipient": args.recipient,
    "amount": args.amount,
    "signature": signature_b64
}

# Send to blockchain node
res = requests.post(f"{args.node}/transactions/new", json=tx_payload)

# Output result
print("Transaksi dikirim ke node:")
print(f" {args.node}/transactions/new")
print("Payload:")
print(json.dumps(tx_payload, indent=2))
print("Response:")
print(res.status_code, res.json())