import hashlib
import json

def hash_data(data):
    """Hash data menggunakan SHA256."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def calculate_merkle_root(transactions):
    """
    Menghitung Merkle Root dari list transaksi.
    Merkle Tree memungkinkan verifikasi efisien bahwa transaksi ada dalam block.
    """
    if not transactions:
        return hash_data("empty")
    
    # Hash semua transaksi
    current_level = [hash_data(tx) for tx in transactions]
    
    # Jika hanya ada 1 transaksi, itu adalah root
    if len(current_level) == 1:
        return current_level[0]
    
    # Build tree dari bottom-up
    while len(current_level) > 1:
        next_level = []
        
        # Pair up hashes dan hash mereka bersama
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                # Ada pair
                combined = current_level[i] + current_level[i+1]
            else:
                # Ganjil, duplicate yang terakhir
                combined = current_level[i] + current_level[i]
            
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        
        current_level = next_level
    
    return current_level[0]
