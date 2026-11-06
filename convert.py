"""
convert.py - Konversi PDF UU No. 20 Tahun 2025 (KUHAP) menjadi Markdown + JSON
menggunakan OpenDataLoader PDF.

Cara pakai (di folder yang sama dengan file PDF):
    python convert.py
"""
import re
import subprocess
import sys
import time
from pathlib import Path

PDF_FILE = "UU_Nomor_20_Tahun_2025.pdf"
OUTPUT_DIR = "output"


def cek_java():
    """Pastikan Java 11+ terpasang. Java 1.8 (Java 8) TIDAK cukup."""
    try:
        hasil = subprocess.run(
            ["java", "-version"], capture_output=True, text=True
        )
    except FileNotFoundError:
        sys.exit("[ERROR] Java tidak ditemukan. Install JDK 11+ dulu.")

    teks = hasil.stderr or hasil.stdout  # java -version menulis ke stderr
    cocok = re.search(r'version "(\d+)(?:\.(\d+))?', teks)
    if not cocok:
        print("[PERINGATAN] Versi Java tidak terbaca, lanjut saja...")
        return
    mayor = int(cocok.group(1))
    if mayor == 1:  # format lama: 1.8.0 -> Java 8
        mayor = int(cocok.group(2))
    print(f"[OK] Java terdeteksi: versi {mayor}")
    if mayor < 11:
        sys.exit(
            f"[ERROR] Java kamu versi {mayor}, butuh 11 atau lebih baru.\n"
            "Install JDK 17 lalu buka Command Prompt BARU "
            "dan cek lagi: java -version"
        )


def main():
    cek_java()

    pdf = Path(PDF_FILE)
    if not pdf.exists():
        sys.exit(
            f"[ERROR] File '{PDF_FILE}' tidak ada di folder ini: {Path.cwd()}"
        )

    try:
        import opendataloader_pdf
    except ImportError:
        sys.exit(
            "[ERROR] Library belum terpasang. Jalankan:\n"
            "    python -m pip install -U opendataloader-pdf"
        )

    print(f"[PROSES] Mengonversi {PDF_FILE} (238 halaman, bisa beberapa menit)...")
    mulai = time.time()

    opendataloader_pdf.convert(
        input_path=[PDF_FILE],
        output_dir=OUTPUT_DIR + "/",
        format="markdown,json",
    )

    print(f"[SELESAI] Waktu: {time.time() - mulai:.1f} detik")
    print(f"Hasil ada di folder: {Path(OUTPUT_DIR).resolve()}")
    print("Lanjut jalankan: python cek_hasil.py")


if __name__ == "__main__":
    main()
