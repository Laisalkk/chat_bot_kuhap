"""
chatbot.py - Chatbot sederhana (retrieval-based) untuk UU No. 20 Tahun 2025 (KUHAP)

Cara kerja:
  1. Membaca hasil OpenDataLoader: output/UU_Nomor_20_Tahun_2025.md
  2. Membersihkan sebagian "noise" (nomor halaman, header, gambar)
  3. Memecah dokumen per Pasal (chunking)
  4. Mencari pasal paling relevan dengan algoritma BM25
  5. Menampilkan bunyi pasal di jendela chat (GUI Tkinter)

Tidak butuh library tambahan. Jalankan:
    python chatbot.py
atau dengan file lain:
    python chatbot.py "C:\\path\\ke\\file.md"
"""
import math
import re
import sys
import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import messagebox, scrolledtext

MD_PATH = Path(__file__).parent / "output" / "UU_Nomor_20_Tahun_2025.md"
TOP_K = 3          # jumlah pasal yang ditampilkan
MAX_CHARS = 1500   # batas teks per pasal yang ditampilkan

STOPWORDS = set(
    "yang dan atau di ke dari untuk dengan pada dalam adalah itu ini apa apakah "
    "bagaimana siapa kapan berapa saja dapat akan oleh sebagai tentang jika maka "
    "tersebut juga ada saya kah lah".split()
)

QUICK_QUESTIONS = [
    "Apa syarat pengakuan bersalah?",
    "Kapan penyidikan dihentikan?",
    "Apa hak tersangka?",
    "Bagaimana keadilan restoratif diatur?",
    "Pasal 78",
]


# --------------------------------------------------------------------------
# 1. PEMBERSIHAN & CHUNKING
# --------------------------------------------------------------------------
RE_IMAGE = re.compile(r"^!\[.*\]\(.*\)$")
RE_PAGENUM = re.compile(r"^-\s*\d+\s*-$")                       # -42-
RE_HEADER = re.compile(r"^(PRESIDEN|FRESIDEN)\s+\w+\s+INDONESIA$", re.I)
RE_SKNO = re.compile(r"^SK No\b", re.I)
RE_CONTINUE = re.compile(r"\.\s?\.\s?\.\s*$")                   # "(3) Dalam . . ."
RE_PASAL = re.compile(r"^Pasal\s+(\d+[A-Z]?)$")


def clean_lines(raw_lines):
    """Buang gambar, nomor halaman, header halaman, dan penanda lanjutan."""
    hasil = []
    for ln in raw_lines:
        s = re.sub(r"^#+\s*", "", ln.strip())
        if not s:
            continue
        if RE_IMAGE.match(s) or RE_PAGENUM.match(s) or RE_HEADER.match(s):
            continue
        if RE_SKNO.match(s):
            continue
        if len(s) < 40 and RE_CONTINUE.search(s):
            continue
        hasil.append(s)
    return hasil


def load_chunks(path):
    """Pecah dokumen per Pasal. Mengembalikan list of dict(label, nomor, teks)."""
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = clean_lines(raw)

    chunks = []
    nomor, buf, penjelasan = None, [], False

    def simpan():
        if nomor is not None and buf:
            label = f"Pasal {nomor}" + (" (Penjelasan)" if penjelasan else "")
            chunks.append(
                {"label": label, "nomor": nomor, "penjelasan": penjelasan,
                 "teks": "\n".join(buf)}
            )

    for s in lines:
        if s.isupper() and re.match(r"^PENJELASAN\b", s):
            simpan()
            nomor, buf, penjelasan = None, [], True
            continue
        m = RE_PASAL.match(s)
        if m:
            simpan()
            nomor, buf = m.group(1), []
        elif nomor is not None:
            buf.append(s)
    simpan()
    return chunks


# --------------------------------------------------------------------------
# 2. PENCARIAN (BM25)
# --------------------------------------------------------------------------
def stem(w):
    """Stemmer sangat sederhana (hanya akhiran), cukup untuk menaikkan recall."""
    for suf in ("nya", "kan", "lah", "kah", "an"):
        if w.endswith(suf) and len(w) > len(suf) + 3:
            return w[: -len(suf)]
    return w


def tokenize(teks):
    return [
        stem(w)
        for w in re.findall(r"[a-z0-9]+", teks.lower())
        if w not in STOPWORDS and len(w) > 1
    ]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.dl = [len(d) for d in docs]
        self.avg = sum(self.dl) / max(1, len(docs))
        n_docs = len(docs)
        df = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {
            w: math.log(1 + (n_docs - n + 0.5) / (n + 0.5)) for w, n in df.items()
        }

    def search(self, query_tokens, k):
        skor = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in query_tokens:
                if w in tf:
                    f = tf[w]
                    norm = 1 - self.b + self.b * self.dl[i] / (self.avg or 1)
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * norm)
            if s > 0:
                skor.append((s, i))
        skor.sort(reverse=True)
        return skor[:k]


class Retriever:
    def __init__(self, chunks):
        self.chunks = chunks
        # label ikut diindeks agar pertanyaan bernomor pasal lebih mudah cocok
        self.bm25 = BM25([tokenize(c["teks"]) for c in chunks])

    def jawab(self, pertanyaan, k=TOP_K):
        # Kasus 1: pengguna menyebut nomor pasal secara langsung
        m = re.search(r"pasal\s+(\d+[a-z]?)", pertanyaan.lower())
        if m:
            nomor = m.group(1).upper()
            cocok = [c for c in self.chunks if c["nomor"] == nomor]
            cocok.sort(key=lambda c: (c["penjelasan"], -len(c["teks"])))
            if cocok:
                return [(None, c) for c in cocok[:k]]

        # Kasus 2: pencarian kata kunci
        q = tokenize(pertanyaan)
        if not q:
            return []
        return [(s, self.chunks[i]) for s, i in self.bm25.search(q, k)]


# --------------------------------------------------------------------------
# 3. GUI
# --------------------------------------------------------------------------
class ChatApp:
    def __init__(self, root, retriever, sumber):
        self.root = root
        self.retriever = retriever
        root.title("Chatbot KUHAP - UU No. 20 Tahun 2025")
        root.geometry("920x680")
        root.minsize(600, 450)

        tk.Label(
            root,
            text="Chatbot KUHAP (UU No. 20 Tahun 2025)",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(10, 0))
        tk.Label(
            root,
            text=f"{len(retriever.chunks)} pasal dimuat dari {sumber}",
            font=("Segoe UI", 9), fg="gray",
        ).pack()

        self.chat = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Segoe UI", 10), state=tk.DISABLED,
            padx=10, pady=10,
        )
        self.chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.chat.tag_config("user", foreground="#0b57d0",
                             font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("title", foreground="#1b5e20",
                             font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("note", foreground="gray",
                             font=("Segoe UI", 9, "italic"))

        quick = tk.Frame(root)
        quick.pack(fill=tk.X, padx=10)
        for q in QUICK_QUESTIONS:
            tk.Button(quick, text=q, font=("Segoe UI", 8),
                      command=lambda t=q: self.kirim(t)).pack(side=tk.LEFT, padx=2)

        bar = tk.Frame(root)
        bar.pack(fill=tk.X, padx=10, pady=10)
        self.entry = tk.Entry(bar, font=("Segoe UI", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.entry.bind("<Return>", lambda e: self.kirim())
        self.entry.focus()
        tk.Button(bar, text="Kirim", font=("Segoe UI", 10, "bold"), width=10,
                  command=self.kirim).pack(side=tk.LEFT, padx=(8, 0))

        self.tulis("Bot: ", "title")
        self.tulis(
            "Halo! Tanyakan sesuatu tentang KUHAP baru, misalnya "
            "\"Apa syarat pengakuan bersalah?\" atau ketik nomor pasal "
            "seperti \"Pasal 78\".\n"
            "Catatan: bot ini hanya menampilkan bunyi pasal yang paling relevan "
            "(bukan nasihat hukum). Teks berasal dari PDF hasil scan, jadi bisa "
            "memuat salah baca OCR.\n\n", "note",
        )

    def tulis(self, teks, tag=None):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, teks, tag)
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def kirim(self, teks=None):
        pertanyaan = (teks or self.entry.get()).strip()
        if not pertanyaan:
            return
        self.entry.delete(0, tk.END)
        self.tulis("Kamu: ", "user")
        self.tulis(pertanyaan + "\n\n")

        hasil = self.retriever.jawab(pertanyaan)
        self.tulis("Bot: ", "title")
        if not hasil:
            self.tulis(
                "Maaf, tidak ada pasal yang cocok. Coba kata kunci lain "
                "(misalnya: penyidik, tersangka, penahanan, saksi).\n\n"
            )
            return

        self.tulis(f"Ditemukan {len(hasil)} pasal yang relevan:\n\n", "note")
        for n, (skor, c) in enumerate(hasil, 1):
            info = "cocok nomor pasal" if skor is None else f"skor {skor:.1f}"
            self.tulis(f"[{n}] {c['label']}  ", "title")
            self.tulis(f"({info})\n", "note")
            isi = c["teks"]
            if len(isi) > MAX_CHARS:
                isi = isi[:MAX_CHARS].rstrip() + " ... [dipotong]"
            self.tulis(isi + "\n\n")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else MD_PATH
    if not path.exists():
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(
            "File tidak ditemukan",
            f"Tidak menemukan:\n{path}\n\nJalankan convert.py dulu atau beri "
            "path file .md sebagai argumen.",
        )
        sys.exit(1)

    chunks = load_chunks(path)
    if not chunks:
        sys.exit("Tidak ada pasal terdeteksi di file Markdown.")

    root = tk.Tk()
    ChatApp(root, Retriever(chunks), path.name)
    root.mainloop()


if __name__ == "__main__":
    main()
