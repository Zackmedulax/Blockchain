import rsa
import base64

def generate_keypair():
    """Menghasilkan pasangan kunci privat dan publik baru."""
    public_key, private_key = rsa.newkeys(1024)
    pub_pem = public_key.save_pkcs1().decode('utf-8')
    priv_pem = private_key.save_pkcs1().decode('utf-8')
    return pub_pem, priv_pem

def load_public_key(key_source):
    """
    Memuat public key dari path file atau string PEM langsung.
    """
    try:
        # Coba baca sebagai file
        if key_source.endswith('.pem'):
            with open(key_source, 'rb') as f:
                content = f.read()
        else:
            # Asumsikan string PEM
            content = key_source.encode('utf-8')
        
        return rsa.PublicKey.load_pkcs1(content)
    except Exception as e:
        print(f"[!] Gagal memuat public key: {e}")
        return None

def verify_signature(sender_pubkey, data, signature_b64):
    """
    Verifikasi signature menggunakan sender_pubkey (bisa path atau string PEM).
    """
    try:
        public_key = load_public_key(sender_pubkey)
        if not public_key:
            return False
            
        signature = base64.b64decode(signature_b64)
        rsa.verify(data.encode(), signature, public_key)
        return True
    except Exception as e:
        print(f"[!] Signature verification failed: {e}")
        return False