# CLAUDE.md — Buzdolabı Asistanı

Kullanıcının elindeki malzemelere göre yapabileceği tarifleri öneren küçük bir web uygulaması.
Ayrıntılı plan, şema, API listesi ve yol haritası için `README.md` dosyasına bak. Bu dosya kod yazarken uyulacak kuralları içerir.

## Teknoloji

- **Backend:** Python, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- **Frontend:** HTML, CSS, vanilla JavaScript (framework yok, build adımı yok)
- **Veritabanı:** Yerelde SQLite, yayında Supabase Postgres (fark sadece `DATABASE_URL`)
- **Yayın:** Vercel (FastAPI tek bir Vercel Function olarak çalışır, `public/` CDN'den sunulur)

## Komutlar

```bash
source .venv/bin/activate                         # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head                              # şemayı uygula
alembic revision --autogenerate -m "aciklama"     # model değişince yeni migration
python scripts/seed.py                            # örnek verileri yükle
uvicorn app.main:app --reload                     # sadece API → http://localhost:8000/docs
vercel dev                                        # frontend + API → http://localhost:3000
pytest                                            # testler (SQLite)
TEST_DATABASE_URL=postgresql://... pytest         # aynı testler Postgres'te, geçici şemada
node --test tests/js/                             # frontend'in saf JS yardımcıları (pytest de çalıştırır; Node yoksa atlanır)
```

## Klasör yapısı (özet)

```
app/main.py            FastAPI uygulaması — Vercel giriş noktası, adı ve yeri değişmez
app/database.py        engine + session, SQLite/Postgres ayrımı burada
app/models.py          SQLAlchemy modelleri
app/schemas.py         Pydantic şemaları
app/routers/           ingredients.py, pantry.py, recipes.py, shopping.py
app/services/matching.py   eşleştirme algoritması
app/utils/text.py      Türkçe normalize()
public/                frontend (index.html, recipe.html, recipe-form.html, shopping.html, css/, js/)
migrations/            Alembic
scripts/seed.py        seed yükleyici, veriyi data/seed_recipes.json'dan okur
tests/
```

## Kesin kurallar

### Vercel
- `app/main.py` içindeki nesnenin adı `app` olmalı; Vercel onu otomatik bulur.
- `public/` klasörünü **asla** `app.mount()` veya `StaticFiles` ile bağlama. Vercel bunu kendisi sunar.
- Tüm API rotaları `/api` önekiyle başlar (`APIRouter(prefix="/api/...")`).
- Üst seviye middleware ekleme (CORS dahil). Frontend ve API aynı alan adında; CORS gerekmez.
- Dosya sistemine yazma. Yayında dosya sistemi kalıcı değildir; tüm kalıcı veri veritabanına gider.

### Veritabanı
- Uygulama açılışında `Base.metadata.create_all()` **çağırma**. Şema sadece Alembic ile yönetilir.
- Model değişikliği = yeni Alembic migration. Migration'ı oluşturduktan sonra dosyayı oku ve kontrol et.
- `migrations/env.py` içinde `render_as_batch=True` açık kalmalı (SQLite uyumluluğu).
- Sadece iki veritabanında da çalışan tipler: `String`, `Text`, `Integer`, `Boolean`, `Float`, `DateTime(timezone=True)`. Postgres'e veya SQLite'a özel tip/fonksiyon kullanma.
- Postgres bağlantısında `poolclass=NullPool` ve `connect_args={"prepare_threshold": None}` korunmalı (Supabase transaction pooler).
- `postgres://` / `postgresql://` ile başlayan URL'ler `postgresql+psycopg://` olarak çevrilir; bu mantık `database.py` içinde kalır.
- Yeni tablo eklenirse, migration'a o tablo için `ENABLE ROW LEVEL SECURITY` ekle (sadece Postgres dialect'inde çalıştır, SQLite'ta atla). Policy ekleme.
- İlişkili verileri tek sorguda çek (`selectinload`). Döngü içinde sorgu atma (N+1 yok).
- Tarif → malzeme ilişkisinde `cascade="all, delete-orphan"` kullan.

### Türkçe metin
- Malzeme adları kaydedilirken ve aranırken her zaman `app/utils/text.py` içindeki `normalize()` kullanılır; arama `normalized` sütununda yapılır.
- Python'ın `.lower()` / `.casefold()` fonksiyonunu tek başına veya SQL `LOWER()`/`ILIKE` kullanma; Türkçe `İ`/`I` harflerini yanlış işler.
- `normalize()` `İ`/`I`/`ı` harflerini `i`'ye katlar (İngilizce klavyeyle yazılan "ispanak" da "Ispanak"ı bulsun diye). Fonksiyon değişirse `normalized` sütununu yeniden hesaplayan bir veri migration'ı gerekir.
- Yol/sorgu parametresi olan her `id` ve `offset` `1..MAX_ID` (`app/schemas.py`) ile sınırlanır; daha büyük değer veritabanında 500 hatasına yol açar.

### Güvenlik ve gizli bilgiler
- Şifre, bağlantı dizesi veya anahtarı koda, migration'a, teste ya da commit'e yazma. Her şey ortam değişkeninden okunur (`.env` yerelde, Vercel panelinde yayında).
- `.env` ve `*.db` dosyaları Git'e girmez.
- Her yazma uç noktası (`POST`/`PUT`/`DELETE`) `dependencies=[Depends(require_api_key)]` ile korunur (`app/security.py`). `ADMIN_KEY` ortam değişkenidir; koda yazılmaz, frontend'e gömülmez.
- Tüm SQL, SQLAlchemy üzerinden parametreli çalışır; string birleştirerek sorgu kurma.
- Kullanıcıdan gelen metni frontend'de `innerHTML` ile basma; `textContent` veya güvenli DOM oluşturma kullan.
- `vercel.json` CSP uygular (`script-src 'self'; style-src 'self'`): HTML'e satır içi `<script>`/`<style>`, `style=` ve `on…=` öznitelikleri koyma, `setAttribute("style")` kullanma; dinamik stil için `el.style.x = …`. Betikler `public/js/` altında ayrı dosyadır. Dışarıdan kaynak (CDN, harici görsel) eklemek CSP'yi de değiştirmeyi gerektirir. Değişiklikten sonra `tests/test_frontend_csp.py` geçmeli.

## Kod stili

### Python
- Tip ipuçları her yerde. SQLAlchemy 2.0 stili: `Mapped[...]`, `mapped_column()`, `select()`. Eski `Query` API'si kullanma.
- Pydantic v2: ORM'den okunan şemalarda `model_config = ConfigDict(from_attributes=True)`.
- Veritabanı session'ı bağımlılık olarak gelir: `db: Session = Depends(get_db)`.
- Bulunamayan kayıt → `HTTPException(404)`, geçersiz istek → 422 (Pydantic) veya 400.
- İş mantığı (özellikle eşleştirme) router'da değil `services/` içinde, saf ve test edilebilir fonksiyonlar olarak durur.

### Frontend
- ES modülleri (`<script type="module">`). Kütüphane veya CDN bağımlılığı ekleme.
- Tüm `fetch` çağrıları sadece `public/js/api.js` içinde; diğer dosyalar bu fonksiyonları kullanır.
- Hesaplama/biçimlendirme gibi saf mantık DOM'dan ayrı, test edilebilir modüllerde durur (örn. `scale.js`) ve `tests/js/` altında Node testi olur. Sunucudaki bir sınırı yansıtan sabitler (örn. `MAX_SERVINGS`) için `tests/test_js_scale.py`'deki gibi eşitlik testi eklenir.
- Her zaman göreli yol: `fetch("/api/recipes")`. Tam URL veya `localhost` yazma.
- Her API çağrısında yükleniyor durumu ve hata mesajı göster (soğuk başlatma gecikebilir).
- Renkler ve aralıklar `:root` içinde CSS değişkenleri; açık/koyu mod `prefers-color-scheme` ile. Mobil öncelikli.

### Dil
- Kod, değişken, fonksiyon, tablo ve sütun adları **İngilizce**.
- Arayüz metinleri, hata mesajları (kullanıcıya gösterilenler) ve seed verisi **Türkçe**.

## Çalışma şekli

- `README.md` bölüm 9'daki yol haritasını sırayla takip et; bir aşama bitmeden sonrakine geçme.
- Her aşama sonunda: `pytest` çalıştır, gerekiyorsa `uvicorn` ile `/docs` üzerinden uç noktaları dene.
- Eşleştirme mantığına dokunan her değişiklikte `tests/test_matching.py` güncellenir.
- README'deki şema veya API listesi değişirse README'yi de güncelle.
- Supabase veya Vercel üzerinde geri alınamayan bir işlem (proje silme, veri silme, yayın ortamında migration) yapmadan önce kullanıcıya sor.
