# YouTube Yorum Analiz Aracı

Bu proje, bir YouTube video linki üzerinden yorumları çeken ve bu yorumları Gemini API kullanarak analiz eden bir web uygulamasıdır. Duygu analizi, öne çıkan konular ve genel izlenim gibi metrikler sunar.

## Özellikler

*   Belirtilen YouTube video URL'sinden yorumları çeker.
*   Çekilen yorumları Google Gemini API ile analiz eder.
*   Analiz sonuçlarını kullanıcı dostu bir arayüzde gösterir:
    *   Genel duygu dağılımı (pozitif, negatif, nötr)
    *   Yorumlarda en çok bahsedilen konular
    *   Video hakkındaki genel izleyici görüşü
    *   Tartışmalı veya ilgi çeken noktalar
    *   Kullanıcıların potansiyel öneri ve istekleri
    *   Analizin kısa bir özeti
*   Çekilen yorumları listeler.
*   Video başlığını ve toplam yorum sayısını gösterir.

## Kurulum

1.  **Depoyu Klonlayın (veya İndirin):**
    ```bash
   https://github.com/OrhanAzak/Yapay-Zeka-Destekli-Youtube-Yorum-Analizi.git
    cd Klasör Adınız
    ```

2.  **Gerekli Bağımlılıkları Yükleyin:**
    Python 3.x ve pip kurulu olmalıdır.
    ```bash
    pip install -r requirements.txt
    ```

3.  **API Anahtarını Ayarlayın:**
    *   Proje kök dizininde `.env` adında bir dosya oluşturun.
    *   İçine Google Gemini API anahtarınızı aşağıdaki formatta ekleyin:
        ```
        GEMINI_API_KEY=BURAYA_API_ANAHTARINIZI_GIRIN
        ```
    *   API anahtarınızı [Google AI Studio](https://aistudio.google.com/app/apikey) adresinden alabilirsiniz.

4.  **ChromeDriver'ı Kurun:**
    *   Bu proje, yorumları çekmek için Selenium ve ChromeDriver kullanır.
    *   Sisteminizde yüklü olan Chrome tarayıcı sürümüyle uyumlu ChromeDriver'ı [buradan](https://chromedriver.chromium.org/downloads) indirin.
    *   İndirdiğiniz `chromedriver.exe` (veya Linux/macOS için `chromedriver`) dosyasını projenin ana dizinine (`server.py` ile aynı yere) kopyalayın. (Kodda `CHROME_DRIVER_PATH = "chromedriver.exe"` olarak ayarlanmıştır.)

## Kullanım

1.  **Sunucuyu Başlatın:**
    Proje kök dizininde terminali açın ve aşağıdaki komutu çalıştırın:
    ```bash
    python server.py
    ```

2.  **Uygulamayı Açın:**
    Web tarayıcınızda `http://localhost:5000` adresine gidin.

3.  **Analiz Yapın:**
    *   YouTube video linkini giriş alanına yapıştırın.
    *   "Yorumları Getir" düğmesine tıklayın.
    *   Yorumların çekilmesi ve analiz edilmesi biraz zaman alabilir. Lütfen bekleyin.

## Kullanılan Teknolojiler

*   **Backend:** Python, Flask
*   **Frontend:** HTML, CSS, JavaScript
*   **Yorum Çekme:** Selenium
*   **Yorum Analizi:** Google Gemini API
*   **Bağımlılık Yönetimi:** pip, requirements.txt
*   **API Anahtarı Yönetimi:** python-dotenv

## Güvenlik Notları

*   API anahtarınızın gizliliğini korumak için `.env` dosyası `.gitignore` ile depoya dahil edilmemiştir.
*   Flask uygulaması üretim için `debug=False` modunda çalışacak şekilde ayarlanmıştır.
*   Statik dosyalar (`index.html`, `css`, `js`) ayrı bir `static` klasöründen sunulmaktadır.

## Katkıda Bulunma

Katkılarınız her zaman kabulümdür! Lütfen bir "issue" açın veya bir "pull request" gönderin.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız. 
