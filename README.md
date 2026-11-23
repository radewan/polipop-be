# Polipop API

REST API untuk Polipop, dibangun dengan FastAPI, SQLAlchemy (async), Alembic, dan MySQL. Struktur project berbasis domain.

## Tech Stack

- Python 3.13
- FastAPI
- SQLAlchemy 2.0 (async, driver `aiomysql`)
- Alembic (migrasi database)
- MySQL 8.x (terpasang di komputer)
- uv (package manager)

## Persiapan

Pastikan sudah terpasang dan berjalan:

- [uv](https://docs.astral.sh/uv/)
- MySQL Server 8.x (atau MariaDB)

Cek MySQL sudah aktif:

```bash
mysql --version
sudo systemctl status mysql     # Linux (nama service bisa mysqld / mariadb)
```

## Setup Database

Masuk ke MySQL sebagai root:

```bash
sudo mysql
# atau: mysql -u root -p
```

Lalu jalankan:

```sql
CREATE DATABASE polipop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'polipop'@'localhost' IDENTIFIED BY 'secret';
GRANT ALL PRIVILEGES ON polipop.* TO 'polipop'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Ganti `secret` dengan password Anda sendiri, dan samakan dengan isi `DATABASE_URL` di `.env`.

## Instalasi

```bash
# 1. Clone repo
git clone <url-repo-ini>
cd polipop-be

# 2. Install dependency
uv sync

# 3. Salin file environment lalu sesuaikan isinya
cp .env.example .env

# 4. Siapkan database (lihat bagian "Setup Database" di atas)

# 5. Jalankan migrasi
uv run alembic upgrade head

# 6. (Opsional) Isi data awal
uv run python -m src.seeders.run

# 7. Jalankan server
uv run fastapi dev src/main.py
```

Setelah server berjalan:

- API: http://localhost:8000
- Dokumentasi Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Konfigurasi (.env)

```env
DATABASE_URL=mysql+aiomysql://polipop:secret@localhost:3306/polipop
ENVIRONMENT=development
SEED_ADMIN_PASSWORD=admin12345
COOKIE_SECURE=false
```

| Variabel              | Keterangan                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`        | URL koneksi MySQL (driver `aiomysql`). Format: `mysql+aiomysql://user:password@host:port/nama_database` |
| `ENVIRONMENT`         | `development` atau `production`. Seeder tidak jalan di `production`                                     |
| `SEED_ADMIN_PASSWORD` | Password akun `admin` yang dibuat seeder                                                                |
| `COOKIE_SECURE`       | Isi `true` di production (wajib HTTPS)                                                                  |

Jika password database mengandung karakter khusus (`@`, `:`, `/`, `#`), ubah menjadi bentuk URL-encoded, misalnya `@` menjadi `%40`.

## Perintah Sehari-hari

### Server

```bash
# Development (auto-reload)
uv run fastapi dev src/main.py

# Production
uv run fastapi run src/main.py
```

### Migrasi database (Alembic)

```bash
# Buat file migrasi baru dari perubahan model
uv run alembic revision --autogenerate -m "deskripsi perubahan"

# Terapkan semua migrasi
uv run alembic upgrade head

# Batalkan 1 migrasi terakhir
uv run alembic downgrade -1

# Batalkan semua migrasi
uv run alembic downgrade base

# Lihat versi migrasi saat ini
uv run alembic current

# Lihat riwayat migrasi
uv run alembic history
```

Catatan:

- Selalu periksa file di `alembic/versions/` sebelum menjalankan `upgrade`.
- Model baru harus di-import di `alembic/env.py` supaya terdeteksi autogenerate.

### Seeder

```bash
# Jalankan semua seeder
uv run python -m src.seeders.run
```

- Aman dijalankan berulang kali. Data yang sudah ada dilewati.
- Tidak berjalan jika `ENVIRONMENT=production`.
- Jalankan migrasi (`alembic upgrade head`) lebih dulu.

Akun yang dibuat seeder:

| Username | Password                    |
| -------- | --------------------------- |
| `admin`  | nilai `SEED_ADMIN_PASSWORD` |
| `budi`   | `password123`               |
| `siti`   | `password123`               |

### Reset database

Untuk mengosongkan dan membuat ulang semua tabel (hanya untuk development, semua data akan hilang):

```bash
uv run alembic downgrade base
uv run alembic upgrade head
uv run python -m src.seeders.run
```

### Lint dan test

```bash
uv run ruff check .           # cek lint
uv run ruff format .          # format kode
uv run pytest                 # jalankan test
```

## Struktur Project

```
polipop-be/
├── alembic/                  # konfigurasi & riwayat migrasi
│   └── versions/
├── src/
│   ├── main.py               # entry point FastAPI
│   ├── config.py             # settings dari .env
│   ├── database.py           # engine, session, Base
│   ├── schemas.py            # format response (data / errors)
│   ├── exceptions.py         # exception kustom
│   ├── error_handlers.py     # handler error global
│   ├── seeders/              # data awal
│   │   ├── run.py
│   │   └── users.py
│   └── users/                # domain users
│       ├── models.py
│       ├── schemas.py
│       ├── service.py
│       ├── router.py
│       ├── dependencies.py
│       └── security.py
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## Format Response

Sukses:

```json
{ "data": { "id": "...", "username": "admin" } }
```

Error:

```json
{ "errors": [{ "field": "username", "message": "Pesan error" }] }
```

## Endpoint Users

| Method | Path               | Keterangan                         |
| ------ | ------------------ | ---------------------------------- |
| POST   | `/v1/users/login`  | Login (set cookie `session_token`) |
| POST   | `/v1/users/logout` | Logout dan hapus sesi              |
| GET    | `/v1/users/me`     | Data user yang sedang login        |

Body login:

```json
{ "username": "admin", "password": "admin12345", "remember_me": true }
```

## Menambah Domain Baru

1. Buat folder `src/<domain>/` berisi `models.py`, `schemas.py`, `service.py`, `router.py`.
2. Import `models.py`-nya di `alembic/env.py`.
3. Daftarkan router di `src/main.py`.
4. Buat dan terapkan migrasi:
   ```bash
   uv run alembic revision --autogenerate -m "add <domain>"
   uv run alembic upgrade head
   ```
5. (Opsional) Tambah seeder di `src/seeders/<domain>.py` dan panggil di `src/seeders/run.py`.

## Troubleshooting

| Masalah                                  | Solusi                                                                                                                |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `No module named 'greenlet'`             | `uv add "sqlalchemy[asyncio]"`                                                                                        |
| `ModuleNotFoundError: src` saat seeder   | Jalankan dengan `python -m src.seeders.run` dari root project                                                         |
| `Table ... doesn't exist`                | Jalankan `uv run alembic upgrade head`                                                                                |
| Autogenerate menghasilkan migrasi kosong | Pastikan `models.py` sudah di-import di `alembic/env.py`                                                              |
| `Can't connect to MySQL server`          | Pastikan service MySQL aktif (`sudo systemctl start mysql`) dan host/port di `DATABASE_URL` benar                     |
| `Access denied for user`                 | Periksa user dan password di `DATABASE_URL`, lalu cek user sudah dibuat dan diberi hak akses (lihat "Setup Database") |
| `Unknown database 'polipop'`             | Buat database-nya dulu (lihat "Setup Database")                                                                       |
