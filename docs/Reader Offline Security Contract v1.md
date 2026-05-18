# Reader Offline Security Contract v1

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan kontrak keamanan untuk desktop reader berbasis **Java + JavaFX** yang beroperasi dengan mode baca **offline-only**.  
Online connection hanya digunakan untuk autentikasi/sinkron minimal dan download package.

Dokumen ini menjadi acuan implementasi untuk:
- tim backend DRM
- tim desktop reader
- tim QA security

---

## 2. Prinsip Utama

1. Reader harus dapat membaca ebook tanpa koneksi internet setelah package berhasil diunduh.
2. Reader tidak boleh pernah menerima atau menyimpan source file asli (PDF/EPUB mentah) dari backend.
3. Reader hanya membuka package yang lolos integrity verification dan license policy.
4. Semua dekripsi konten harus terjadi lokal pada device pengguna yang terotorisasi.
5. Master key server tidak boleh ditanam di reader.

---

## 3. Ruang Lingkup

### In-Scope
- autentikasi user untuk sesi download
- download `.bookpkg`
- penyimpanan package lokal
- verifikasi signature manifest offline
- validasi license binding user/device/ebook offline
- dekripsi per halaman untuk image layer dan text layer
- local persistence menggunakan SQLite

### Out-of-Scope
- anti screenshot level OS/hardware
- pencegahan kamera eksternal
- kernel-level memory protection
- DRM yang sepenuhnya anti reverse engineering

---

## 3A. Functional Capabilities Reader v1

Reader v1 wajib menyediakan kemampuan berikut:

1. Membaca ebook
2. Text selection
3. Text highlight/block
4. Page bookmark
5. Note
6. Annotation
7. Text search
8. Tampilan dua halaman berdampingan kanan-kiri (two-page spread)

Seluruh kemampuan di atas harus tetap dapat berjalan pada mode baca offline setelah package berhasil diunduh dan tervalidasi.

---

## 4. Mode Operasi

### 4.1 Online Mode (Terbatas)
Online mode hanya diperbolehkan untuk:
1. Login/authentication
2. Register/validate device
3. Verify/issue download entitlement
4. Download package ebook
5. Sync metadata kebijakan minimum (opsional)

### 4.2 Offline Read Mode (Wajib)
Setelah package tersimpan lokal:
1. Reader harus bisa membuka dan membaca tanpa network call.
2. Seluruh verifikasi dan dekripsi dilakukan lokal.
3. Jika integrity check gagal, reader harus menolak membuka buku.

---

## 5. Trust Model

### 5.1 Trusted Components
- Backend DRM service
- Signing key server (private key)
- Reader executable resmi
- Public verification key yang dibundel reader

### 5.2 Untrusted/Hostile Surface
- user filesystem
- network path
- package file saat in transit/at rest
- local memory (diasumsikan dapat dianalisis attacker advanced)

---

## 6. Key & Crypto Contract

### 6.1 Wajib
1. Manifest signature: RSA-2048 + SHA-256
2. Content encryption per halaman: AES-256-GCM
3. Nonce harus unik per-encryption operation
4. Page key harus unik per halaman

### 6.2 Larangan
1. Tidak boleh menaruh server master encryption/signing private key di reader.
2. Tidak boleh menyimpan plaintext konten halaman secara permanen di disk.
3. Tidak boleh bypass integrity verification pada mode normal.

### 6.3 Reader Key Material
Reader hanya boleh menyimpan:
- public key untuk verifikasi signature
- token/license lokal yang dibutuhkan untuk dekripsi sesuai kebijakan backend
- key material terproteksi OS-level ke device context (misal DPAPI/KeyStore wrapper)

---

## 7. Package Validation Contract

Sebelum membuka ebook, reader wajib menjalankan urutan berikut:

1. Validasi format `.bookpkg` (zip container + struktur folder wajib)
2. Baca `manifest.bin`
3. Baca `license.sig`
4. Verifikasi `license.sig` terhadap `manifest.bin` menggunakan RSA public key
5. Cocokkan metadata manifest dengan identitas ebook lokal
6. Validasi license binding:
   - user_id cocok dengan user aktif lokal
   - device_hash cocok dengan device identity lokal
   - ebook_id cocok dengan item library
7. Jika salah satu langkah gagal, ebook harus ditolak dengan status error yang jelas.

---

## 8. Decryption Contract

1. Reader melakukan dekripsi **on-demand per halaman** (lazy decrypt), bukan bulk decrypt semua halaman.
2. Plaintext image/text hanya hidup di memory untuk waktu minimum.
3. Buffer plaintext harus dibersihkan secepat mungkin setelah render selesai.
4. Cache decrypted page di disk dilarang (kecuali terenkripsi ulang dengan key lokal device dan TTL pendek, jika disetujui pada versi lanjutan).

---

## 9. Local Persistence Contract (SQLite)

SQLite digunakan untuk metadata lokal reader, bukan menyimpan source ebook mentah.

### 9.1 Tabel Minimum (konseptual)
1. `local_user_session`
2. `local_device`
3. `local_library`
4. `local_license`
5. `reading_progress`
6. `download_history`
7. `security_events`

### 9.2 Data Sensitif
Data berikut harus diproteksi:
1. local license token/material
2. device identity secret
3. session refresh artifact (jika ada)

Proteksi minimal:
- file permission ketat
- OS-protected key storage untuk secret material
- integrity hash untuk record penting

---

## 10. Offline License Policy

Karena mode baca offline:
1. License yang sudah valid saat download dianggap valid untuk sesi offline berikutnya sesuai aturan policy yang tersimpan lokal.
2. Revocation dari server tidak real-time di offline mode.
3. Revocation diterapkan saat client kembali online (sync berikutnya) atau saat user mengunduh ulang/sinkron.

---

## 11. Device Binding Policy

1. Satu license ebook terikat ke satu device hash.
2. Reader wajib menghitung/menyediakan device hash konsisten.
3. Jika hash berubah signifikan (reinstall/hardware change policy), reader harus menandai mismatch dan meminta re-authorize online.

---

## 12. Error Handling & Security Events

Reader wajib mencatat event berikut ke `security_events`:
1. signature verification failed
2. manifest malformed
3. license mismatch
4. device mismatch
5. decrypt failure (GCM tag invalid)

Setiap error harus:
1. user-facing message ringkas
2. internal log detail (tanpa membocorkan secret)

---

## 13. Minimum QA Security Checklist

1. Package tampered byte → harus gagal dibuka.
2. `license.sig` diganti → harus gagal verifikasi.
3. Package dipindah ke device lain → harus gagal policy check.
4. Offline read tanpa internet setelah download sukses → harus berhasil.
5. Corrupted nonce/tag pada page blob → dekripsi gagal terkontrol.
6. Tidak ada source PDF/EPUB asli di artefak distribusi reader.

---

## 14. Compatibility Notes dengan Backend Saat Ini

1. Backend saat ini sudah menghasilkan `.bookpkg`, `manifest.bin`, dan `license.sig`.
2. Reader membutuhkan public key yang sesuai dengan private signing key backend.
3. Kontrak key delivery per-device/per-license harus dikunci lebih detail pada dokumen turunan `Key Provisioning Spec v1` sebelum production release.

---

## 15. Open Decisions (Butuh Persetujuan)

1. Format final license offline token (claims + expiry + signature scheme)
2. Mekanisme rotasi key signing/public key pinning
3. Kebijakan masa berlaku offline (tanpa revocation realtime)
4. Pilihan proteksi secret lokal (DPAPI-only atau tambahan envelope encryption)
5. Apakah reader mengizinkan copy text penuh atau dibatasi watermark/policy

---

## 16. Kesimpulan

Kontrak ini menetapkan bahwa reader:
1. online hanya untuk autentikasi dan download
2. read path sepenuhnya offline
3. selalu melakukan integrity + license enforcement lokal
4. tidak pernah membawa master key server

Dokumen ini adalah baseline security contract untuk implementasi Reader v1.
