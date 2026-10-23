# 🥕 Buzdolabı Asistanı

Elindeki malzemeleri gir, yapabileceğin tarifleri gör. Küçük ama işlevsel bir web uygulaması.

| Katman | Geliştirme (yerel) | Yayın (production) |
|---|---|---|
| Frontend | HTML, CSS, vanilla JS | Vercel CDN (`public/` klasörü) |
| Backend | Python, FastAPI | Vercel Function (Python runtime) |
| Veritabanı | SQLite (`local.db`) | Supabase (PostgreSQL) |
| ORM / Migration | SQLAlchemy 2.x + Alembic | aynı |

> **Neden yayında SQLite değil?** Vercel Function'ları sunucusuz (serverless) çalışır; dosya sistemi kalıcı değildir ve her istek farklı bir örnekte çalışabilir. SQLite dosyası yayında korunamaz. Bu yüzden kod baştan **veritabanından bağımsız** yazılır: yerelde SQLite, yayında Supabase Postgres kullanılır ve aradaki tek fark `DATABASE_URL` ortam değişkenidir.

---

## 1. Amaç

Kullanıcı buzdolabındaki / dolabındaki malzemeleri seçer. Uygulama veritabanındaki tarifleri bu malzemelerle karşılaştırır ve şunları gösterir:

- **Hemen yapılabilecekler:** Tüm zorunlu malzemeler mevcut.
- **Az eksikle yapılabilecekler:** 1–2 malzeme eksik, eksikler listelenir.
- Her tarif için bir **eşleşme oranı** (ör. %80).

---

## 2. Özellikler

### MVP (ilk sürüm)
- [ ] Malzeme arama (otomatik tamamlama ile)
- [ ] "Buzdolabım" listesi: malzeme ekle / çıkar (veritabanında saklanır)
- [ ] Tarif eşleştirme: eşleşme oranına göre sıralı tarif listesi
- [ ] Tarif detay sayfası: malzemeler (var / eksik işaretli), yapılış adımları, süre, porsiyon
- [ ] Tarif ekleme / düzenleme / silme
- [ ] Başlangıç için örnek tarif verisi (seed)
- [ ] Vercel + Supabase üzerinde yayında

### Sonraki adımlar (isteğe bağlı)
- [x] Son kullanma tarihi takibi ("yakında bozulacaklar" ile önce bunları kullanan tarifler)
- [ ] Favori tarifler
- [x] Eksik malzemelerden alışveriş listesi oluşturma
- [x] Kategori / etiket filtreleri (vegan, kahvaltı, 30 dk altı...)
- [x] Porsiyona göre miktar ölçekleme
- [ ] Kullanıcı hesapları (Supabase Auth ile çok kullanıcılı yapı)
- [ ] Tarif görselleri (Supabase Storage)
- [ ] Yapay zekâ ile tarif önerisi / malzeme ikamesi ("süt yoksa ne kullanabilirim?")

---

## 3. Klasör Yapısı

Yapı, Vercel'in FastAPI'yi **sıfır yapılandırmayla** algılayacağı şekilde kurulur: Vercel `app/main.py` içindeki `app` nesnesini otomatik bulur ve kök dizindeki `public/` klasörünü CDN'den sunar.

```
buzdolabi-asistani/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI uygulaması (Vercel giriş noktası)
│   ├── config.py            # Ortam değişkenleri (DATABASE_URL vb.)
│   ├── database.py          # Engine + session; SQLite / Postgres ayrımı
│   ├── models.py            # SQLAlchemy tabloları
│   ├── schemas.py           # Pydantic istek/yanıt şemaları
│   ├── routers/
│   │   ├── ingredients.py
│   │   ├── pantry.py
│   │   ├── recipes.py
│   │   ├── shopping.py
│   │   └── tags.py
│   ├── services/
│   │   └── matching.py      # Eşleştirme algoritması
│   └── utils/
│       └── text.py          # Türkçe metin normalizasyonu
├── public/                  # Frontend — Vercel CDN'den sunulur
│   ├── index.html           # Ana sayfa: buzdolabım + önerilen tarifler
│   ├── recipe.html          # Tarif detay
│   ├── recipe-form.html     # Tarif ekle / düzenle
│   ├── shopping.html        # Alışveriş listesi
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js           # Tüm fetch çağrıları tek yerde
│       ├── dom.js           # Güvenli DOM oluşturma yardımcısı (innerHTML yok)
│       ├── home.js          # Ana sayfa girişi (satır içi script yasak, bkz. bölüm 8)
│       ├── pantry.js
│       ├── recipes.js
│       ├── scale.js         # Porsiyon ölçekleme için saf yardımcılar (Node ile test edilir)
│       ├── recipe.js        # Tarif detay sayfası
│       ├── filter-bar.js    # Ana sayfadaki etiket / süre filtre çubuğu
│       ├── tags.js          # Etiket ve filtre yardımcıları (saf; Node ile test edilir)
│       ├── text.js          # fold(): sunucudaki normalize() ile aynı kural
│       └── recipe-form.js
├── migrations/              # Alembic migration dosyaları
│   ├── env.py
│   └── versions/
├── scripts/
│   └── seed.py              # Örnek verileri veritabanına yükler
├── data/
│   └── seed_recipes.json
├── tests/
│   ├── js/scale.test.mjs    # Frontend yardımcılarının Node testleri (pytest bunları da çalıştırır)
│   └── test_matching.py
├── alembic.ini
├── requirements.txt         # Yayında gereken paketler
├── requirements-dev.txt     # Test / geliştirme paketleri
├── .env.example
├── .gitignore
├── vercel.json              # Güvenlik başlıkları (CSP vb.)
├── .vercelignore
└── README.md
```

**Önemli kurallar:**
- `public/` klasörü FastAPI içinde `app.mount()` ile **bağlanmaz**; Vercel bunu platform seviyesinde yapar. `public/index.html` → `/`, `public/recipe.html` → `/recipe.html` adresinden sunulur.
- Frontend ve API aynı alan adında çalıştığı için **CORS gerekmez**. JS tarafında her zaman göreli yollar kullanılır: `fetch("/api/recipes")`.
- Tüm API rotaları `/api` önekiyle başlar; böylece statik dosyalarla çakışmaz.

---

## 4. Veritabanı Şeması

```
ingredients                 recipes
───────────                 ───────
id          PK              id            PK
name        UNIQUE          title
normalized  UNIQUE, index   description
                            instructions  (metin, adımlar satır satır)
                            prep_minutes
                            servings
                            image_url     (opsiyonel)
                            created_at    (timezone'lu)

recipe_ingredients          pantry_items
──────────────────          ────────────
id             PK           id             PK
recipe_id      FK → recipes ingredient_id  FK → ingredients, UNIQUE
ingredient_id  FK → ingr.   quantity       (opsiyonel)
quantity       (ör. 2)      unit           (opsiyonel)
unit           (ör. "adet") expires_at     (opsiyonel; takvim günü, UTC gece yarısı olarak saklanır)
is_optional    bool         added_at

shopping_items
──────────────
id             PK
ingredient_id  FK → ingredients, UNIQUE   (bir malzeme listede en fazla bir kez bulunur)
quantity       (opsiyonel; tariften gelir, seçili porsiyona göre ölçeklenmiş)
unit           (opsiyonel)
checked        bool          (satın alındı)
added_at

tags                        recipe_tags
────                        ───────────
id          PK              recipe_id  FK → recipes  ┐ birleşik PK
name        UNIQUE (≤50)    tag_id     FK → tags     ┘ (index: tag_id)
normalized  UNIQUE, index
```

**Notlar:**
- `normalized` alanı, arama ve eşleştirmenin büyük/küçük harf ve Türkçe karakter farklarından etkilenmemesi için tutulur (bkz. bölüm 6). Bu ayrıca SQLite ile Postgres arasındaki farkı da ortadan kaldırır: SQLite'ın `LOWER()` fonksiyonu Türkçe karakterleri doğru işlemez, Python tarafında normalize edip bu sütunda aramak her iki veritabanında aynı sonucu verir.
- `is_optional`: "Üzerine maydanoz serpilebilir" gibi malzemeler eşleşme oranını düşürmez.
- Tarif silinince malzeme satırlarının da silinmesi için SQLAlchemy ilişkisinde `cascade="all, delete-orphan"` kullanılır (SQLite'ta foreign key'ler varsayılan olarak kapalı olduğundan ORM seviyesinde çözmek daha güvenli).
- Sadece iki veritabanında da çalışan tipler kullanılır (`String`, `Text`, `Integer`, `Boolean`, `DateTime(timezone=True)`); SQLite'a veya Postgres'e özel tiplerden kaçınılır.
- MVP tek kullanıcılı olduğu için `pantry_items` ve `shopping_items` tablolarında `user_id` yok. Supabase Auth eklenirse bu alan eklenir.

---

## 5. API Uç Noktaları

Tüm uç noktalar `/api` altında. Otomatik dokümantasyon: `/docs`

### Malzemeler
| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/ingredients?q=dom` | Otomatik tamamlama için arama (en fazla 10 sonuç) |
| POST | `/api/ingredients` | Yeni malzeme ekle |

### Buzdolabım
| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/pantry` | Buzdolabındaki malzemeler. Her kayıtta `expires_on` ve `days_left` (0 = bugün bitiyor, negatif = süresi geçmiş; tarih yoksa `null`) bulunur |
| POST | `/api/pantry` | Malzeme ekle `{ "ingredient_id": 3, "expires_on": "2026-10-25" }` (`expires_on` isteğe bağlı, `YYYY-MM-DD`, 2000–2100 arası) |
| PATCH | `/api/pantry/{id}` | Son kullanma tarihini değiştir `{ "expires_on": "2026-10-30" }`; `null` tarihi siler. Alan zorunludur (yoksa 422) |
| DELETE | `/api/pantry/{id}` | Malzeme çıkar |
| DELETE | `/api/pantry` | Buzdolabını boşalt |

### Tarifler
| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/recipes?limit=20&offset=0&tag=kahvaltı&max_minutes=30` | Tüm tarifler (sayfalı). Yanıt: `{items, total, limit, offset}`; `limit` 1–100, `offset` ≥ 0. Filtreler için aşağıdaki "Etiketler ve filtreler" bölümüne bak |
| GET | `/api/recipes/{id}` | Tarif detayı. Her malzemede `in_pantry` alanı vardır (buzdolabında var ya da temel malzeme) |
| POST | `/api/recipes` | Tarif ekle. Malzemeler ad ile gönderilir (`{name, quantity, unit, is_optional}`); ad normalize edilip mevcut malzemeyle eşleşir, yoksa oluşturulur. En az 1 malzeme gerekir, aynı malzeme iki kez eklenemez (400). `tags`: isteğe bağlı etiket adları listesi (en çok 10, her biri en çok 50 karakter); boşlar atılır, `normalize()` ile aynı olanlar tek bırakılır, yoksa etiket oluşturulur. Yanıtta `tags` bulunur |
| PUT | `/api/recipes/{id}` | Tarif güncelle (gövde POST ile aynı; malzeme listesi tamamen değiştirilir) |
| DELETE | `/api/recipes/{id}` | Tarif sil (malzeme satırları da silinir, malzeme kataloğu korunur) |
| GET | `/api/recipes/match?max_missing=2&tag=kahvaltı&max_minutes=30` | Buzdolabındaki malzemelere göre eşleşen tarifler (filtreler isteğe bağlı) |

### Alışveriş listesi
| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/shopping` | Liste (alınmamışlar önce, sonra ekleme sırasıyla). Her kayıtta `ingredient`, `quantity`, `unit`, `checked` |
| POST | `/api/shopping/from-recipe` | `{ "recipe_id": 7, "servings": 4 }` — tarifin **zorunlu, buzdolabında olmayan** malzemelerini listeye ekler. İsteğe bağlı malzemeler ve temel malzemeler (su, tuz, karabiber) eklenmez; listede zaten olan atlanır. `servings` verilirse miktarlar tarifin porsiyonuna göre ölçeklenir. Yanıt: `{added, already_listed, nothing_missing}` |
| PATCH | `/api/shopping/{id}` | `{ "checked": true }` — satın alındı işareti (alan zorunlu) |
| POST | `/api/shopping/move-to-pantry` | İşaretli malzemeleri buzdolabına taşır (miktar/birimle) ve listeden çıkarır; zaten buzdolabında olan tekrar eklenmez. Yanıt: `{moved}` |
| DELETE | `/api/shopping/{id}` | Malzemeyi listeden sil |
| DELETE | `/api/shopping?only_checked=true` | Yalnızca işaretlileri sil; parametresiz tüm listeyi boşaltır |

İki istek aynı malzemeyi aynı anda eklemeye çalışırsa ikincisi benzersiz kısıta çarpar; işlem geri alınıp bir kez yeniden denenir (kazanan kayıt görünür ve atlanır).

### Yazma koruması (`ADMIN_KEY`)
Uygulama tek kullanıcılı olduğu için tüm **yazma** uç noktaları (`POST`/`PUT`/`PATCH`/`DELETE`: tarifler, malzeme ekleme, buzdolabı, alışveriş listesi) `X-API-Key` başlığında `ADMIN_KEY` değerini ister; yanlış veya eksikse **401** döner. Okuma uç noktaları (`GET`) herkese açıktır.

- `ADMIN_KEY` tanımsızsa: yerelde koruma kapalıdır, Vercel'de yazma istekleri **503** döner (anahtarsız yayına çıkılamaz).
- Kontrol `app/security.py` içindeki `require_api_key` bağımlılığıyla yapılır; yeni bir yazma uç noktası eklerken `dependencies=[Depends(require_api_key)]` eklenmelidir.
- Frontend anahtarı koda gömmez: sunucu 401 dönünce `api.js` bir kez sorar ve o tarayıcının `localStorage`'ında saklar. Yanlış anahtar girilirse yeniden sorulur.
- Sınırlar: tek paylaşılan anahtardır, hız sınırı yoktur; bu yüzden uzun ve rastgele olmalıdır. Hesaplı çok kullanıcılı yapı için Supabase Auth gerekir (sonraki adımlar).

### Etiketler ve filtreler
| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/tags` | Filtre çubuğu için: **en az bir tarifte kullanılan** etiketler ve tarif sayıları `[{name, count}]` (ada göre sıralı). Etiketler ayrı bir uç noktayla oluşturulmaz; tarif eklenirken/güncellenirken oluşur |

`GET /api/recipes` ve `GET /api/recipes/match` aynı filtreleri alır:
- `tag` (tekrarlanabilir, en çok 10): seçilen etiketlerin **hepsine** sahip tarifler (VE). Ad `normalize()` ile karşılaştırılır ("Kahvaltı" = "kahvalti"); bilinmeyen etiket sonucu boşaltır.
- `max_minutes` (0–10000): hazırlık süresi bu değerden uzun olmayanlar. Süresi girilmemiş tarifler bu filtreyle elenir. Arayüzdeki "⏱ 30 dk altı" düğmesi `max_minutes=30` gönderir; "30 dk altı" bir etiket değil, süreden türetilen filtredir.
- Filtreler eşleştirmeden **önce** uygulanır; sıralama kuralları değişmez.

Tarif silinince etiket bağlantıları silinir, etiket kaydı kalır; kullanılmayan etiket `/api/tags` listesinde görünmez. Tarifler etiketsiz olabilir.

### Sağlık kontrolü
| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/health` | Uygulama ve veritabanı bağlantısı çalışıyor mu (deploy sonrası test için) |

### Örnek eşleştirme yanıtı
```json
[
  {
    "recipe_id": 7,
    "title": "Menemen",
    "match_ratio": 0.8,
    "have": ["yumurta", "domates", "biber", "tereyağı"],
    "missing": ["soğan"],
    "expiring": ["yumurta"],
    "tags": ["kahvaltı", "vejetaryen"],
    "prep_minutes": 15
  }
]
```

---

## 6. Eşleştirme Mantığı

`app/services/matching.py` içinde:

1. Buzdolabındaki malzeme ID'lerini bir küme (`set`) olarak al.
2. Her tarif için **zorunlu** malzemelerin kümesini al (`is_optional = False`).
3. Hesapla:
   - `have = zorunlu ∩ buzdolabı`
   - `missing = zorunlu − buzdolabı`
   - `match_ratio = len(have) / len(zorunlu)`
4. `len(missing) <= max_missing` olanları filtrele.
5. Sırala: önce eksik sayısı (az → çok), sonra **kullanılan yakında-bozulacak malzeme sayısı (çok → az)**, sonra eşleşme oranı (yüksek → düşük), sonra hazırlık süresi.

**Son kullanma tarihi (`app/services/expiry.py`):** Tarih bir takvim günüdür. "Bugün" `TIMEZONE` ortam değişkenine göre hesaplanır (varsayılan `Europe/Istanbul`; Vercel UTC çalıştığı için gün gece yarısı civarında kaymasın). Bugünden itibaren **3 gün veya daha az** kalan (süresi geçmişler dahil) malzemeler "yakında bozulacak" sayılır (`EXPIRY_SOON_DAYS`; arayüzdeki sabit `public/js/pantry.js` içinde aynıdır). Bu malzemeleri kullanan tarifler aynı eksik sayısı içinde öne çıkar ve yanıtta `expiring` listesiyle işaretlenir. Eksik sayısı hâlâ önceliklidir: eksik malzemesi olan bir tarif, tam yapılabilen tarifin önüne geçmez. Saat dilimi verisi için `tzdata` paketi gerekir (`requirements.txt`).

**Performans notu:** Tarifler ve malzemeleri tek sorguda (`selectinload`) çekilir; her tarif için ayrı sorgu atılmaz. Sunucusuz ortamda her veritabanı gidiş-dönüşü Supabase'e ağ üzerinden gittiği için bu önemlidir.

**Temel malzemeler:** Tuz, su, karabiber gibi neredeyse herkeste olan malzemeler `STAPLE_INGREDIENTS` (`app/services/matching.py`, normalize edilmiş adlarla) listesinde tutulur. Eşleştirmede yok sayılırlar: ne "var" ne "eksik" listesine girerler, orana da katılmazlar; böylece "tuz eksik" diye tarif elenmez.

**Ek kurallar:** Zorunlu malzemesi olmayan tarifler ve buzdolabındaki hiçbir malzemeyi içermeyen tarifler listelenmez; buzdolabı boşsa sonuç boştur.

**Türkçe normalizasyon (`app/utils/text.py`):**
Python'da `"İ".lower()` sonucu `"i̇"` (noktalı birleşik karakter) olur ve aramaları bozar. Ayrıca kullanıcılar İngilizce klavyeyle sık sık "ispanak" yazar, kayıt ise "Ispanak"tır. Bu yüzden `normalized` bir **karşılaştırma anahtarıdır**: `İ`, `I` ve `ı` harflerinin hepsi `i`'ye katlanır, sonra küçük harfe çevrilir ve boşluklar temizlenir. Görünen ad ayrıca `name` sütununda olduğu gibi kalır:

```python
def normalize(text: str) -> str:
    text = text.strip().replace("İ", "i").replace("I", "i").replace("ı", "i")
    return " ".join(text.lower().split())
```

Bu anahtar değişirse `normalized` sütunu yeniden hesaplanmalıdır (veri migration'ı); aksi hâlde eski kayıtlar aranamaz.

**Arama sıralaması:** `GET /api/ingredients?q=` önce tam eşleşmeyi, sonra öneki, sonra içerenleri döndürür (en fazla 10), böylece tam eşleşme kısa sorgularda listenin dışında kalmaz.

---

## 7. Veritabanı Bağlantısı (SQLite ↔ Supabase)

`app/database.py` tek bir `DATABASE_URL` ile iki ortamı da yönetir:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")

# Supabase "postgres://" veya "postgresql://" verir; SQLAlchemy'ye psycopg 3 sürücüsünü söyle
if DATABASE_URL.startswith(("postgres://", "postgresql://")):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.split("://", 1)[1]

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,                       # bağlantı havuzunu Supabase pooler yönetir
        connect_args={"prepare_threshold": None}, # transaction mode prepared statement desteklemez
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False)
```

**Hangi Supabase bağlantı dizesi nerede kullanılır?** (Supabase panelinde **Connect** butonu)

| Kullanım | Bağlantı türü | Port |
|---|---|---|
| Vercel'deki uygulama | **Transaction pooler** | 6543 |
| Alembic migration'ları ve seed (kendi bilgisayarından) | **Session pooler** | 5432 |

- Sunucusuz fonksiyonlar her seferinde yeni bağlantı açabildiği için uygulama **transaction pooler** kullanır ve SQLAlchemy'de `NullPool` ayarlanır.
- Direkt bağlantı (`db.<proje>.supabase.co`) IPv6 üzerinden çalışır; ev/okul ağı IPv4 ise session pooler kullan.
- Tablolar uygulama açılışında `create_all()` ile **oluşturulmaz**; bu iş Alembic migration'larına bırakılır (her soğuk başlatmada şema kontrolü yapmak gereksiz yavaşlık yaratır).

### Supabase güvenlik notu (RLS)
Supabase, `public` şemasındaki tabloları otomatik bir REST API (Data API) ile dışarı açar. Bu projede veritabanına sadece FastAPI erişeceği için, ilk migration'da tüm tablolarda **Row Level Security açılır ve hiç policy tanımlanmaz**. Böylece anonim anahtarla dışarıdan erişim kapanır; tabloların sahibi olan `postgres` rolüyle bağlanan backend ise etkilenmez. (Bu SQL sadece Postgres'te çalıştırılır, SQLite'ta atlanır.)

```sql
ALTER TABLE ingredients        ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE pantry_items       ENABLE ROW LEVEL SECURITY;
ALTER TABLE alembic_version    ENABLE ROW LEVEL SECURITY;  -- Alembic'in kendi tablosu da public şemasında
```

### Alembic ipucu
SQLite `ALTER TABLE` desteği sınırlı olduğu için `migrations/env.py` içinde `context.configure(..., render_as_batch=True)` ayarlanır. Böylece aynı migration'lar hem SQLite'ta hem Postgres'te çalışır.

---

## 8. Frontend Sayfaları

### `index.html` – Ana sayfa
- Üstte malzeme arama kutusu (yazdıkça `/api/ingredients?q=` çağrılır, 250 ms debounce)
- Arama kutusunun altında isteğe bağlı "Son kullanma tarihi" alanı: önce tarih seçilirse sonraki eklenen malzemeye uygulanır
- Seçilen malzemeler "etiket" (chip) olarak görünür, × ile silinir. Tarihi olanlar önce, en yakın bitenden başlayarak sıralanır; rozet "yarın bitiyor", "2 gün kaldı", "1 gün önce bitti" gibi gösterir (≤3 gün turuncu, geçmiş kırmızı). Rozete tıklayınca tarih düzenlenir; alanı boşaltmak tarihi siler
- **Görünüm anahtarı**: "Buzdolabıma göre" (öneriler, varsayılan) ve **"Tüm tarifler"** (buzdolabından bağımsız, her seferinde 12 tarif; "Daha fazla göster" ile sürer, "12 / 18 tarif" sayacı vardır). Seçim adrese `view=all` olarak yazılır. Tüm tarifler görünümünde "Sadece hemen yapılabilenler" kutusu gizlenir; etiket ve süre filtreleri iki görünümde de çalışır
- **Filtre çubuğu** (öneri listesinin üstünde): "⏱ 30 dk altı" ve her etiket için sayılı düğme (`kahvaltı (2)`); birden çok etiket seçilirse hepsine sahip tarifler gösterilir. Seçim sayfa adresine yazılır (`/?tag=kahvaltı&max_minutes=30`, tüm tarifler için `&view=all`), bağlantı paylaşılabilir; adresteki listede olmayan etiket de görünür ve kaldırılabilir. "Filtreleri temizle" bağlantısı vardır
- Altta önerilen tarif kartları: başlık, süre, etiketler, eşleşme oranı çubuğu, eksik malzemeler; yakında bozulacak malzeme kullanılıyorsa "⏰ Yakında bozulacak: …" satırı ve vurgulu kenarlık
- "Sadece hemen yapılabilenler" anahtarı (`max_missing=0`)

### `recipe.html?id=7` – Tarif detay
- Malzeme listesi: ✅ var / ❌ eksik işaretli
- **Porsiyon seçici** (−/+ düğmeleri ve sayı alanı, 1–1000): miktarlar seçilen porsiyona göre orantılı hesaplanır (`yeni = miktar × seçilen ÷ tarifin porsiyonu`), Türkçe biçimde en çok 2 ondalıkla gösterilir ("1,5 su bardağı"). Tarifin kayıtlı porsiyonu yoksa seçici görünmez ve miktarlar değişmez; miktarı olmayan malzemeler ölçeklenmez. Yapılış adımlarının metni ölçeklenmez; porsiyon değişince bunu belirten bir not gösterilir. Seçim kaydedilmez (sayfa yenilenince tarifin porsiyonuna döner). Hesaplama `public/js/scale.js` içindedir
- **"🛒 Eksik malzemeleri alışveriş listesine ekle"** düğmesi (eksik zorunlu malzeme varsa görünür): seçili porsiyona göre ölçeklenmiş miktarlarla ekler; sonucu "4 malzeme listeye eklendi" / "hepsi zaten listede" şeklinde bildirir
- Numaralı yapılış adımları
- Düzenle / Sil butonları

### `shopping.html` – Alışveriş listesi
- Her satırda onay kutusu (alındı işareti; işaretliler üstü çizili olarak alta iner) ve × ile silme
- "Alınanları buzdolabına taşı", "Alınanları listeden sil", "Listeyi boşalt" (onay sorar) düğmeleri
- Boş listede açıklama ve ana sayfaya bağlantı. Ana sayfa ve tarif sayfasında bu sayfaya bağlantı vardır

### `recipe-form.html` – Tarif ekle / düzenle
- Başlık, açıklama, **etiketler** (virgülle ayrılmış metin alanı; altında mevcut etiketler tek tıkla ekleyip çıkarmak için düğmeler), süre, porsiyon
- Dinamik malzeme satırları (malzeme + miktar + birim + opsiyonel kutusu)
- Adımlar için metin alanı

### Güvenlik başlıkları ve CSP (`vercel.json`)
Tüm yollara `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` ve `Permissions-Policy` eklenir. HTML/JS/CSS yanıtlarına ayrıca şu CSP uygulanır (`/api/*`, `/docs`, `/redoc`, `/openapi.json` hariç, çünkü Swagger arayüzü CDN ve satır içi betik kullanır):

```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;
object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

Bu yüzden frontend'de **satır içi `<script>`, `<style>`, `style=` / `on…=` öznitelikleri ve `setAttribute("style", …)` kullanılmaz**; genişlik gibi dinamik stiller `el.style.width = …` ile (CSSOM) verilir. `tests/test_frontend_csp.py` bunları denetler. Dışarıdan görsel (`image_url`) gösterilecekse `img-src`'ye ilgili alan adı eklenmelidir. HSTS'yi Vercel kendisi ekler.

**Tasarım:** Mobil öncelikli, CSS değişkenleriyle tema renkleri, açık/koyu mod desteği.
**Kullanıcı deneyimi:** Sunucusuz fonksiyonlarda ilk istek (soğuk başlatma) biraz gecikebilir; bu yüzden listelerde yükleniyor göstergesi (skeleton) kullanılır.

---

## 9. Geliştirme Yol Haritası

| Aşama | İş | Çıktı |
|---|---|---|
| 1 | Proje iskeleti, sanal ortam, `/api/health` | Sunucu ayağa kalkıyor |
| 2 | Modeller + Alembic ilk migration + `seed.py` | Örnek tarifler yerel SQLite'ta |
| 3 | Malzeme ve buzdolabı API'leri | `/docs` üzerinden test edilebilir |
| 4 | Eşleştirme servisi + `/api/recipes/match` | Doğru sıralı sonuçlar |
| 5 | Ana sayfa (arama + buzdolabı + öneriler) | Uygulama kullanılabilir hâlde |
| 6 | Tarif detay sayfası | |
| 7 | Tarif ekle / düzenle / sil | MVP yerelde tamamlandı 🎉 |
| 8 | Testler (pytest + FastAPI `TestClient`) | Eşleştirme mantığı test edildi |
| 9 | **Supabase:** proje oluştur, migration'ları çalıştır, RLS'i aç, seed yükle | Yayın veritabanı hazır |
| 10 | Yerel uygulamayı Supabase'e bağlayıp dene | SQLite/Postgres farkları yakalandı |
| 11 | **Vercel:** projeyi GitHub'dan bağla, `DATABASE_URL` ekle, deploy et | Uygulama yayında 🚀 |
| 12 | Deploy sonrası kontroller (bölüm 11) | |
| 13 | Sonraki sürüm özellikleri | |

---

## 10. Kurulum ve Yerel Çalıştırma

```bash
cd buzdolabi-asistani

# Sanal ortam
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Paketler
pip install -r requirements.txt -r requirements-dev.txt

# Ortam değişkenleri (yerelde boş bırakılırsa SQLite kullanılır)
cp .env.example .env

# Veritabanı tablolarını oluştur ve örnek verileri yükle
alembic upgrade head
python scripts/seed.py
```

**Sadece API'yi çalıştırmak (hızlı geliştirme, `/docs` testleri):**
```bash
uvicorn app.main:app --reload
# http://localhost:8000/docs
```

**Frontend + API birlikte (Vercel'deki ortamın aynısı):**
```bash
npm i -g vercel        # Vercel CLI (Node.js gerekir)
vercel link            # İlk seferde projeyi Vercel hesabına bağlar
vercel dev
# http://localhost:3000
```

### Testler
```bash
pytest                                  # hızlı: her test kendi bellek içi SQLite'ında
TEST_DATABASE_URL=postgresql://... pytest   # aynı testler Postgres'te (yavaş, ağ üzerinden)
```
`TEST_DATABASE_URL` verilirse testler veritabanında geçici bir `pytest_tmp` şemasında çalışır (`public`'e dokunmaz, oturum sonunda şema silinir); her testten önce tablolar `TRUNCATE` edilir. DDL ve çok sayıda sorgu için **session pooler (5432)** dizesini kullan. Yayın veritabanında çalıştırmadan önce şemayı silme yetkisi olan bir hesap kullandığından emin ol.

### SQLite ↔ Postgres farkları (Aşama 10'da yakalananlar)
- **Sıralama:** `ORDER BY name` SQLite'ta ikili (Ç, İ, Ş en sonda), Postgres'te veritabanının locale'ine göre (Ç, C'nin yanında) çalışır. Kodda alfabetik sıraya bağımlı mantık yoktur; kullanıcıya görünen sıra iki ortamda biraz farklı olabilir.
- **Eşzamanlılık:** Aynı yeni malzemeyi içeren iki tarif aynı anda eklenirse ikincisi `ingredients` benzersiz kısıtına çarpar (SQLite'ta tek yazıcı olduğu için görülmez). `create_recipe`/`update_recipe` çakışmada işlemi geri alıp bir kez yeniden dener (`_commit_retrying_on_conflict`); 8 eşzamanlı istekle denendi, hepsi 201 döndü.
- **Saat dilimi:** `DateTime(timezone=True)` Postgres'te `+00:00` ile döner; SQLite'ta saat dilimi bilgisi kaybolur.
- **Transaction pooler (6543):** `NullPool` ve `prepare_threshold=None` ile 16 iş parçacığıyla 120 karışık istek hatasız çalıştı ("prepared statement" hatası yok).

### `requirements.txt`
Yayında kurulan paketler **tam sürüm numarasıyla sabittir** (`fastapi==0.157.0` gibi); böylece Vercel'in kuracağı sürümler yerelde test edilenlerle aynıdır. Güncellemek için sürümü değiştir, `pytest` (ve gerekirse `TEST_DATABASE_URL` ile Postgres'te) çalıştır. Python sürümü `.python-version` dosyasıyla (3.12) sabitlenir.

### `requirements-dev.txt`
```
pytest
httpx
```

### `.env.example`
```
# Boş bırakılırsa yerel SQLite kullanılır
DATABASE_URL=

# Yayın (Vercel) için Supabase transaction pooler, port 6543:
# DATABASE_URL=postgresql://postgres.<proje-ref>:<şifre>@aws-0-<bölge>.pooler.supabase.com:6543/postgres
```

### `.gitignore` / `.vercelignore`
```
.venv/
__pycache__/
*.db
.env
```
> `.env` ve şifre içeren hiçbir dosya Git'e gönderilmez. Yayındaki `DATABASE_URL`, Vercel panelinde **Settings → Environment Variables** altına eklenir.

---

## 11. Yayına Alma (Vercel + Supabase)

### Supabase
1. Yeni proje oluştur (bölge olarak Avrupa, ör. Frankfurt — Vercel fonksiyonunun bölgesiyle yakın olsun).
2. **Connect** → *Session pooler* dizesini al, yerel `.env`'e geçici olarak yaz.
3. `alembic upgrade head` → tablolar ve RLS Supabase'te oluşur.
4. `python scripts/seed.py` → örnek tarifler yüklenir.
5. **Connect** → *Transaction pooler* dizesini al (Vercel için).

### Vercel
1. Projeyi GitHub'a gönder. **Depo herkese açıksa** içinde şifre, bağlantı dizesi veya anahtar olmadığından emin ol (`.env` git'te değildir; `.env.example` yalnızca şablon içerir).
2. Vercel'de **Add New → Project** ile repoyu içe aktar; FastAPI `app/main.py` içinden otomatik algılanır. `public/` klasörü CDN'den sunulur, `vercel.json` başlıkları ve fonksiyon bölgesini (`dub1`, Supabase `eu-west-1` ile aynı bölge) belirler.
3. **İlk deploy'dan önce**, içe aktarma ekranındaki **Environment Variables** bölümüne (şifreler sohbete/koda yazılmadan, doğrudan panele) ekle:
   - `DATABASE_URL` = Supabase **transaction pooler** dizesi (port 6543)
   - `ADMIN_KEY` = uzun rastgele anahtar (bkz. `.env.example`); **Production ve Preview** ortamlarının ikisine de, yoksa o ortamda yazma istekleri 503 verir
4. Deploy. Sonraki her `git push` otomatik yeni sürüm yayınlar.

### Yeni migration içeren sürümler
Vercel her `git push`'ta otomatik deploy eder; kod yeni bir tabloya erişiyorsa ve tablo henüz yoksa o uç noktalar 500 verir. Bu yüzden sıra şöyledir: (1) yerelde `pytest` ve gerekirse `TEST_DATABASE_URL` ile Postgres testleri, (2) **yayın veritabanında `alembic upgrade head`** (session pooler, `.env`'deki `DATABASE_URL` ile; geri alınamaz işlem olduğundan önce onay), (3) Supabase'te RLS ve Advisors kontrolü, (4) `git push`. Eski kod yeni tabloyu kullanmadığından migration'ı önce uygulamak güvenlidir. Sürüm yeni seed verisi getiriyorsa (örn. etiketler) `python scripts/seed.py` yayın veritabanında da çalıştırılır: var olan tarif ve malzemeleri değiştirmez, yalnızca hiç etiketi olmayan seed tariflerine etiket ekler (kullanıcının verdiği etiketlere dokunmaz). Kendi eklediğin tariflere etiketi tarif formundan verirsin.

### Deploy sonrası kontrol listesi
- [ ] `https://<proje>.vercel.app/api/health` → veritabanı bağlantısı OK
- [ ] Ana sayfa açılıyor, CSS/JS yükleniyor (CDN)
- [ ] Malzeme arama Türkçe karakterlerle çalışıyor ("ıspanak", "ispanak" ve "İrmik" aynı sonucu bulmalı)
- [ ] Tarif ekle → sayfayı yenile → tarif hâlâ orada (veri Supabase'e yazılıyor)
- [ ] Vercel loglarında "prepared statement" veya bağlantı hatası yok
- [ ] Yanıt başlıkları: ana sayfada `Content-Security-Policy` var, `/api/health` yanıtında CSP yok; tarayıcı konsolunda CSP ihlali yok (`vercel.json` kuralı Vercel'de de aynı çalışıyor mu)
- [ ] Supabase panelinde **Advisors** uyarısı yok (RLS kontrolü)

---

## 12. Örnek Seed Verisi (`data/seed_recipes.json`)

```json
[
  {
    "title": "Menemen",
    "description": "Klasik Türk kahvaltısı.",
    "prep_minutes": 15,
    "servings": 2,
    "tags": ["kahvaltı", "vejetaryen"],
    "ingredients": [
      { "name": "Yumurta", "quantity": 3, "unit": "adet" },
      { "name": "Domates", "quantity": 2, "unit": "adet" },
      { "name": "Sivri biber", "quantity": 2, "unit": "adet" },
      { "name": "Tereyağı", "quantity": 1, "unit": "yemek kaşığı" },
      { "name": "Soğan", "quantity": 1, "unit": "adet", "is_optional": true }
    ],
    "instructions": "Biberleri tereyağında kavur.\nDomatesleri ekleyip suyunu çekene kadar pişir.\nYumurtaları kırıp karıştır, tuzunu ekle."
  }
]
```
