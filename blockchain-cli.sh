# CONFIG
PORT=5000
HOST="127.0.0.1"
URL="http://$HOST:$PORT"

echo "=== 🧱 Blockchain CLI ==="

while true; do
    echo ""
    echo "1️⃣  Jalankan Server"
    echo "2️⃣  Tambah Transaksi"
    echo "3️⃣  Mine Block"
    echo "4️⃣  Lihat Blockchain"
    echo "5️⃣  Tambah Node"
    echo "6️⃣  Sync dari Node"
    echo "7️⃣  Lihat Daftar Node"
    echo "0️⃣  Exit"
    echo "=========================="
    read -p "Pilih menu > " pilihan

    case $pilihan in
        1)
            echo "[✔] Menjalankan server di port $PORT..."
            nohup python blokchain.py $PORT > output.log 2>&1 &
            echo "[✔] Server dijalankan di background! Cek: http://$HOST:$PORT"
            ;;
        2)
            read -p "Sender     : " sender
            read -p "Recipient  : " recipient
            read -p "Amount     : " amount
            curl -X POST "$URL/transactions/new" \
                -H "Content-Type: application/json" \
                -d "{\"sender\":\"$sender\",\"recipient\":\"$recipient\",\"amount\":$amount}"
            ;;
        3)
            echo "[⛏] Mining blok baru..."
            curl "$URL/mine"
            ;;
        4)
            echo "[📜] Blockchain:"
            curl "$URL/blockchain"
            ;;
        5)
            read -p "Masukkan alamat node (contoh 192.168.1.5:5000): " node
            curl -X POST "$URL/nodes/add_nodes" \
                -H "Content-Type: application/json" \
                -d "{\"nodes\": [\"$node\"]}"
            ;;
        6)
            echo "[🔁] Sync blockchain..."
            curl "$URL/nodes/sync"
            ;;
        7)
            echo "[🌐] Node terdaftar:"
            curl "$URL/nodes"
            ;;
        0)
            echo "Keluar..."
            break
            ;;
        *)
            echo "[!] Pilihan tidak valid"
            ;;
    esac
done
