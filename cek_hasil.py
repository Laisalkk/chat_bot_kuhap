"""
cek_hasil.py - Cek kualitas output OpenDataLoader PDF di folder output/

Cara pakai:
    python cek_hasil.py
"""
import json
import re
import sys
from pathlib import Path

OUT = Path("output")

if not OUT.exists():
    sys.exit("Folder output/ belum ada. Jalankan convert.py dulu.")

# 1. Daftar file
print("=== FILE DI output/ ===")
for f in sorted(OUT.rglob("*")):
    if f.is_file():
        print(f"{f.name:45s} {f.stat().st_size / 1024:10.1f} KB")

# 2. Statistik Markdown
for md in OUT.rglob("*.md"):
    teks = md.read_text(encoding="utf-8", errors="replace")
    baris = teks.splitlines()
    heading = [b for b in baris if b.startswith("#")]
    tabel = [b for b in baris if b.strip().startswith("|")]
    pasal = re.findall(r"^\s*#*\s*\**Pasal\s+(\d+)", teks, flags=re.M)

    print(f"\n=== STATISTIK {md.name} ===")
    print(f"Karakter        : {len(teks):,}")
    print(f"Baris           : {len(baris):,}")
    print(f"Heading         : {len(heading)}")
    print(f"Baris tabel     : {len(tabel)}")
    print(f"Judul 'Pasal N' : {len(pasal)} (dokumen asli sekitar 360+ pasal)")

    # 3. Cek kata kunci penting (uji kasar akurasi OCR)
    print("\n=== CEK KATA KUNCI (jumlah kemunculan) ===")
    for kata in ["Pasal 78", "Pengakuan Bersalah", "keadilan restoratif",
                 "Penyidik", "Penuntut Umum", "Hakim"]:
        print(f"{kata:25s}: {len(re.findall(kata, teks, flags=re.I))}")

    # 4. Cek tanda salah-OCR yang sering muncul
    print("\n=== INDIKASI SALAH-OCR (yang seharusnya tidak ada) ===")
    for salah in ["FRESIDEN", "REPUEUK", "AC.ARA", "PRESIDEN"]:
        print(f"{salah:12s}: {len(re.findall(salah, teks))}")

    # 5. Cuplikan sekitar 'Pasal 78'
    idx = teks.find("Pasal 78")
    if idx != -1:
        print("\n=== CUPLIKAN SEKITAR 'Pasal 78' ===")
        print(teks[max(0, idx - 100): idx + 900])

    print("\n=== 40 BARIS PERTAMA ===")
    print("\n".join(baris[:40]))

# 6. Validasi JSON
for js in OUT.rglob("*.json"):
    try:
        with open(js, encoding="utf-8") as f:
            data = json.load(f)
        print(f"\n[OK] {js.name}: JSON valid (root = {type(data).__name__})")
    except Exception as e:
        print(f"\n[GAGAL] {js.name}: {e}")
