from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import logging
import google.generativeai as genai
import json
from dotenv import load_dotenv

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API anahtarını çevre değişkeninden yükle
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")



# Gemini API yapılandırması
genai.configure(api_key=GEMINI_API_KEY)

# Kullanılabilir modelleri listele (debug için)
def list_available_models():
    try:
        models = genai.list_models()
        model_names = [model.name for model in models]
        logging.info(f"Available models: {model_names}")
        return model_names
    except Exception as e:
        logging.error(f"Error listing models: {str(e)}")
        return []

app = Flask(__name__)
CORS(app)  # Cross Origin Resource Sharing

# Chrome sürücüsü seçenekleri
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # Yeni headless mod
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

# ChromeDriver yolunu manuel olarak ayarla
CHROME_DRIVER_PATH = "chromedriver.exe"  # ChromeDriver'ın yolunu projenin kök dizinine göre ayarlayın

# URL'den video kimliğini çıkar
def extract_video_id(url):
    youtube_regex = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(youtube_regex, url)
    return match.group(1) if match else None

# Yorumları Gemini API ile analiz et
def analyze_comments_with_gemini(video_title, comments):
    try:
        logging.info(f"Analyzing {len(comments)} comments with Gemini API")
        
        # Mevcut modelleri listele
        available_models = list_available_models()
        
        # Gemini'den cevap için maksimum token sınırlaması, çok uzun yorumlar için
        MAX_COMMENT_LENGTH = 400
        # MAX_COMMENTS_TO_ANALYZE = min(len(comments), 100)  # En fazla 100 yorum analiz edilsin (KALDIRILDI)
        
        # UYARI: Çok fazla yorumda API token limiti aşılabilir!
        if len(comments) > 200:
            logging.warning("Çok fazla yorum analiz ediliyor. Gemini API token limiti aşılabilir!")
        
        # Yorumları formatlı string olarak birleştir
        formatted_comments = []
        for i, comment in enumerate(comments):  # TÜM YORUMLAR
            # Yorum metni çok uzunsa kısalt
            text = comment["textDisplay"]
            if len(text) > MAX_COMMENT_LENGTH:
                text = text[:MAX_COMMENT_LENGTH] + "..."
                
            formatted_comment = f"Yorum {i+1}: \"{text}\" - {comment['authorDisplayName']}"
            formatted_comments.append(formatted_comment)
        
        # Yorumları tek bir string'e dönüştür
        all_comments_text = "\n".join(formatted_comments)
        
        # Güncel Gemini model adını kullan - gemini-1.5-flash yeni önerilen model
        model_name = "gemini-1.5-flash"
        
        # Mevcut modeller içinde uygun bir model bul
        if available_models:
            for m in available_models:
                if "gemini-1.5" in m.lower():
                    model_name = m
                    logging.info(f"Using model: {model_name}")
                    break
        
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as model_error:
            logging.error(f"Error creating model with {model_name}: {str(model_error)}")
            # Alternatif güncel modelleri dene
            fallback_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro-latest"]
            
            model = None
            for fallback_model in fallback_models:
                try:
                    model = genai.GenerativeModel(fallback_model)
                    model_name = fallback_model
                    logging.info(f"Successfully created model with fallback: {model_name}")
                    break
                except Exception as fallback_error:
                    logging.error(f"Error creating model with {fallback_model}: {str(fallback_error)}")
            
            if not model:
                raise Exception("Hiçbir Gemini modeli oluşturulamadı. API anahtarınızı kontrol edin.")
        
        # Analiz için prompt oluştur (Türkçe)
        prompt = f"""
        Bu bir YouTube videosu analiz görevidir. Video başlığı: "{video_title}" ve videoya yapılmış toplam {len(comments)} yorumdan {len(formatted_comments)} tanesini analiz edeceksin.
        
        Yorumlar:
        {all_comments_text}
        
        Bu yorumları detaylı olarak analiz et ve şu bilgileri içeren kapsamlı bir rapor hazırla:
        
        1. Genel Duygu Analizi: Yorumların genel duygu tonu nedir (pozitif, negatif, nötr, karışık)? Yüzde olarak dağılım tahmin et.
        2. Öne Çıkan Konular: İnsanların en çok bahsettiği konular neler? Önemli konuları frekanslarına göre sırala.
        3. Video Hakkında Genel Görüş: İzleyiciler video hakkında genel olarak ne düşünüyor? Detaylı bir özet sun.
        4. Tartışmalı/İlgi Çeken Noktalar: Yorumlarda tartışma yaratan veya özellikle ilgi gören noktalar neler?
        5. Öneriler veya İstekler: Kullanıcıların videonun içeriği veya gelecek içerikler hakkında önerileri var mı?
        6. Özet: Video ve izleyici tepkileri hakkında kısa bir özet.
        
        Raporun her bölümünde yorumlarda geçen konkret örnekler ve kanıtlar kullan. 
        Analiz net, objektif ve detaylı olmalı. Lütfen sadece mevcut yorumlara dayanan bir analiz yapın, varsayımlardan kaçının.
        Cevabı JSON formatında olmalı ve aşağıdaki yapıyı takip etmelidir:

        {{
            "genel_duygu": {{
                "pozitif": "yüzde_değeri",
                "negatif": "yüzde_değeri",
                "notr": "yüzde_değeri"
            }},
            "genel_izlenim": "Genel izlenimin kısa özeti",
            "one_cikan_konular": ["Konu 1", "Konu 2", "Konu 3", ...],
            "tartismali_noktalar": ["Tartışmalı nokta 1", "Tartışmalı nokta 2", ...],
            "oneriler": ["Öneri 1", "Öneri 2", ...],
            "ozet": "Detaylı özet"
        }}

        Yukarıdaki şablonu kullanarak JSON formatında yanıt ver. Yüzde_değeri yerine "60%" gibi gerçek değerler kullan.
        """
        
        try:
            # Gemini API'ye istek gönder
            generation_config = {
                "temperature": 0.9,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 4096,  # Daha uzun yanıtlar alabilmek için arttırıldı
            }
            
            # Güncel safety settings formatını kullan
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            # Model API'sini hata yönetimi ile çağır
            response = None
            try:
                logging.info(f"Sending request to Gemini API with model {model_name}")
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            except Exception as api_error:
                logging.error(f"First attempt failed: {str(api_error)}")
                
                try:
                    # Safety settings olmadan tekrar dene
                    logging.info("Trying without safety settings")
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    logging.info("Generated content without safety settings successfully")
                except Exception as second_error:
                    logging.error(f"Second attempt failed: {str(second_error)}")
                    
                    try:
                        # Basit bir prompt ile tekrar dene
                        logging.info("Trying with simplified prompt")
                        simple_prompt = f"Aşağıdaki YouTube video yorumlarını analiz et ve duygu analizi, öne çıkan konular ve genel izlenim hakkında JSON formatında yanıt ver:\n\n{all_comments_text[:1000]}"
                        response = model.generate_content(simple_prompt)
                        logging.info("Generated content with simplified prompt successfully")
                    except Exception as third_error:
                        logging.error(f"Third attempt failed: {str(third_error)}")
                        raise third_error
            
            # Null response kontrolü
            if not response:
                raise Exception("Gemini API boş yanıt döndü")
            
            # JSON formatındaki yanıtı parse et
            try:
                # Bazen Gemini JSON içinde açıklayıcı metinler döndürebilir
                # Yanıttan sadece JSON kısmını ayıklayalım
                response_text = response.text
                
                # JSON formatındaki metni bul (ilk { ve son } arasındaki metin)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                    analysis_result = json.loads(json_str)
                else:
                    # Eğer JSON formatı bulunamazsa, tüm yanıtı döndür
                    analysis_result = {
                        "error": "JSON formatı bulunamadı",
                        "raw_response": response_text
                    }
            except json.JSONDecodeError as e:
                # JSON parse hatası durumunda ham yanıtı döndür
                logging.error(f"JSON parse error: {str(e)}")
                analysis_result = {
                    "error": f"JSON parse hatası: {str(e)}",
                    "raw_response": response.text
                }
            
            return analysis_result
        except Exception as api_error:
            logging.error(f"Gemini API request error: {str(api_error)}")
            
            # API hatası durumunda alternatif bir çözüm olarak basit bir analiz döndür
            return {
                "error": f"Gemini API isteği hatası: {str(api_error)}",
                "genel_duygu": {"pozitif": "50%", "negatif": "25%", "notr": "25%"},
                "genel_izlenim": "API hatası nedeniyle gerçek analiz yapılamadı. Basit bir değerlendirme sunuluyor.",
                "one_cikan_konular": ["Yorumlar analiz edilemedi"],
                "tartismali_noktalar": ["API hatası nedeniyle belirlenemedi"],
                "oneriler": ["Yorumları manuel olarak incelemeyi deneyin"],
                "ozet": f"API hatası nedeniyle analiz yapılamadı. Hata: {str(api_error)}"
            }
        
    except Exception as e:
        logging.error(f"Error in Gemini API analysis: {str(e)}")
        return {
            "error": f"Gemini API hatası: {str(e)}",
            "genel_duygu": {"pozitif": "0%", "negatif": "0%", "notr": "100%"},
            "genel_izlenim": "Analiz yapılamadı",
            "one_cikan_konular": ["Analiz hatası"],
            "tartismali_noktalar": [],
            "oneriler": [],
            "ozet": "Yorumlar analiz edilirken bir hata oluştu."
        }

# Video başlığını getir
def get_video_title(driver):
    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title.style-scope.ytd-video-primary-info-renderer"))
        )
        return title_element.text.strip()
    except:
        try:
            # Alternatif başlık selektörleri
            title_selectors = [
                "h1.title", 
                "h1#title", 
                "yt-formatted-string.ytd-video-primary-info-renderer", 
                "#container h1"
            ]
            
            for selector in title_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return elements[0].text.strip()
        except:
            pass
        
        return "YouTube Video"

# Toplam yorum sayısını getir
def get_total_comment_count(driver):
    try:
        # YouTube'da yorum sayısı genellikle "... Comments" şeklindeki bir metin içinde yer alır
        comment_count_selectors = [
            "h2#count yt-formatted-string span:first-child", 
            "h2#count span:first-child",
            "h2.ytd-comments-header-renderer span:first-child",
            "#count > yt-formatted-string"
        ]
        
        for selector in comment_count_selectors:
            try:
                count_element = driver.find_element(By.CSS_SELECTOR, selector)
                count_text = count_element.text.strip()
                
                # Sayıyı metinden ayıkla ("123,456 Comments" -> "123,456")
                if count_text:
                    # Virgüllü veya noktalarla ayrılmış rakamları ayıklama
                    count_text = ''.join(c for c in count_text if c.isdigit() or c in [',', '.'])
                    # Sayısal olmayan diğer karakterleri temizle
                    count_text = re.sub(r'[^\d]', '', count_text)
                    
                    if count_text.isdigit():
                        return int(count_text)
            except Exception as e:
                logging.debug(f"Selector {selector} failed: {str(e)}")
                continue
        
        # Alternatif deneme: HTML içinde geçen yorum sayısını ara
        try:
            html = driver.page_source
            comment_count_patterns = [
                r"(\d{1,3}(?:,\d{3})*)\s*yorum",  # Türkçe: "1,234 yorum"
                r"(\d{1,3}(?:,\d{3})*)\s*comments",  # İngilizce: "1,234 comments"
                r"Comments\s*\((\d{1,3}(?:,\d{3})*)\)",  # "Comments (1,234)"
                r"yorumlar\s*\((\d{1,3}(?:,\d{3})*)\)"   # "yorumlar (1,234)"
            ]
            
            for pattern in comment_count_patterns:
                matches = re.search(pattern, html, re.IGNORECASE)
                if matches:
                    count_text = matches.group(1)
                    # Virgül ve nokta gibi ayırıcıları temizle
                    count_text = re.sub(r'[^\d]', '', count_text)
                    return int(count_text)
        except Exception as e:
            logging.debug(f"Regex extraction failed: {str(e)}")
        
        return None
    except Exception as e:
        logging.warning(f"Could not get total comment count: {str(e)}")
        return None

# YouTube yorumlarını çek
def fetch_youtube_comments(url):
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Geçersiz YouTube URL'si"}
    
    # YouTube yorum sayfasına git
    comments_url = f"https://www.youtube.com/watch?v={video_id}"
    
    driver = None
    try:
        # ChromeDriver kurulumu
        service = Service(executable_path=CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logging.info(f"Fetching video: {video_id}")
        driver.get(comments_url)
        
        # Video başlığını al
        video_title = get_video_title(driver)
        logging.info(f"Video title: {video_title}")
        
        # Sayfanın temel yüklenmesi için bekle
        time.sleep(5)
        
        # Çerezleri kabul et (varsa)
        try:
            cookie_buttons = driver.find_elements(By.XPATH, 
                "//button[contains(@aria-label, 'Accept') or contains(@aria-label, 'Kabul') or contains(text(), 'Accept') or contains(text(), 'Kabul') or contains(text(), 'I agree')]")
            if cookie_buttons:
                cookie_buttons[0].click()
                time.sleep(2)
                logging.info("Cookie consent clicked")
        except Exception as e:
            logging.info(f"Cookie consent handling: {str(e)}")
        
        # Sayfa yüklenmesi için scroll yapalım
        logging.info("Scrolling to load comments")
        
        # Sayfa sonuna kadar kaydır ve bekle
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(3)
        
        # Sayfa boyunca ilerleyerek yorum bölümüne ulaş
        for i in range(10):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.5)
        
        # 2023-2025 için YouTube yorum bölümü Xpath'i
        comments_section_xpath = "//ytd-comments[@id='comments']"
        try:
            # Yorum bölümünü bul
            comments_section = driver.find_element(By.XPATH, comments_section_xpath)
            driver.execute_script("arguments[0].scrollIntoView(true);", comments_section)
            logging.info("Found comments section")
            time.sleep(2)
            
            # Yorumları yüklemek için tekrar kaydırma yapalım
            for i in range(5):
                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(1)
        except Exception as e:
            logging.warning(f"Could not find comments section: {e}")
        
        # Modern YouTube (2023-2025) yorum selektörleri
        comment_thread_xpath = "//ytd-comment-thread-renderer"
        try:
            # Yorum thread'lerini bekleyip bul
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, comment_thread_xpath))
            )
            
            # Yorumları yüklemek için daha fazla scroll et
            MAX_COMMENTS = 200  # Maksimum 200 yorum çek
            previous_comment_count = 0
            scroll_count = 0
            max_scroll_attempts = 30
            
            comment_threads = driver.find_elements(By.XPATH, comment_thread_xpath)
            current_comment_count = len(comment_threads)
            
            # Daha fazla yorum yüklemek için scroll
            while current_comment_count < MAX_COMMENTS and current_comment_count > previous_comment_count and scroll_count < max_scroll_attempts:
                previous_comment_count = current_comment_count
                
                # Sayfanın sonuna doğru kaydır
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                
                # Yeni yorum count'u al
                comment_threads = driver.find_elements(By.XPATH, comment_thread_xpath)
                current_comment_count = len(comment_threads)
                
                logging.info(f"Loaded {current_comment_count} comments after scroll {scroll_count + 1}")
                scroll_count += 1
                
                # Verimi arttırmak ve sıkışma durumlarını önlemek için
                if scroll_count % 5 == 0:
                    # Sayfanın başına dön ve tekrar aşağı kaydır (bazen bu yeni yorumların yüklenmesine yardımcı olur)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                    time.sleep(2)
            
            # Tüm yorumların parçalarını çıkar
            logging.info(f"Found {len(comment_threads)} total comment threads")
            results = []
            for thread in comment_threads:  # Tüm yorumları al
                try:
                    # Yazar adı - birkaç farklı olası xpath
                    author_name = "Anonim Kullanıcı"
                    try:
                        author_el = thread.find_element(By.XPATH, ".//a[@id='author-text'] | .//span[contains(@class, 'ytd-comment-renderer')]")
                        author_name = author_el.text.strip()
                    except:
                        pass
                    
                    # Profil resmi
                    author_img = None
                    try:
                        img_el = thread.find_element(By.XPATH, ".//img[@id='img'] | .//yt-img-shadow/img")
                        author_img = img_el.get_attribute("src")
                    except:
                        pass
                    
                    # Yorum metni
                    comment_text = ""
                    try:
                        content_el = thread.find_element(By.XPATH, ".//yt-formatted-string[@id='content-text'] | .//div[@id='content-text']")
                        comment_text = content_el.text.strip()
                    except:
                        # Başka bir yöntemle dene
                        try:
                            content_el = thread.find_element(By.XPATH, ".//*[contains(@id, 'content-text')]")
                            comment_text = content_el.text.strip() 
                        except:
                            pass
                    
                    # Yorum tarihi
                    published_at = "Tarih alınamadı"
                    try:
                        date_el = thread.find_element(By.XPATH, ".//yt-formatted-string[@class='published-time-text'] | .//span[contains(@class, 'published-time-text')]")
                        published_at = date_el.text.strip()
                    except:
                        pass
                    
                    # Beğeni sayısı
                    like_count = "0"
                    try:
                        like_el = thread.find_element(By.XPATH, ".//*[@id='vote-count-middle'] | .//*[contains(@class, 'vote-count-middle')]")
                        like_count = like_el.text.strip()
                        if not like_count:
                            like_count = "0"
                    except:
                        pass
                    
                    # Yorumu sonuçlara ekle
                    if comment_text:  # Sadece yorum metni varsa ekle
                        results.append({
                            "authorDisplayName": author_name,
                            "authorProfileImageUrl": author_img,
                            "textDisplay": comment_text,
                            "publishedAt": published_at,
                            "likeCount": like_count
                        })
                except Exception as e:
                    logging.error(f"Error parsing comment: {str(e)}")
                    continue
            
            # Eğer yorum varsa analiz et ve döndür
            if results:
                # Gemini API ile analiz et
                analysis = analyze_comments_with_gemini(video_title, results)
                
                # Toplam yorum sayısını al
                total_comments = get_total_comment_count(driver)
                
                return {
                    "comments": results,
                    "analysis": analysis,
                    "video_title": video_title,
                    "total_comments": total_comments
                }
            
            # Yorum thread'leri bulunamadıysa
            logging.info("No comments found in thread view, trying renderer view")
        except Exception as e:
            logging.warning(f"Failed to extract comment threads: {str(e)}")
        
        # İkinci yöntem: Doğrudan yorum rendererları bul
        comment_renderer_xpath = "//ytd-comment-renderer"
        try:
            comment_renderers = driver.find_elements(By.XPATH, comment_renderer_xpath)
            logging.info(f"Found {len(comment_renderers)} comment renderers")
            
            # Daha fazla yorum yüklemek için scroll et
            MAX_COMMENTS = 200  # Maksimum 200 yorum çek
            previous_comment_count = 0
            scroll_count = 0
            max_scroll_attempts = 30
            
            current_comment_count = len(comment_renderers)
            
            # Daha fazla yorum yüklemek için scroll
            while current_comment_count < MAX_COMMENTS and current_comment_count > previous_comment_count and scroll_count < max_scroll_attempts:
                previous_comment_count = current_comment_count
                
                # Sayfanın sonuna doğru kaydır
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                
                # Yeni yorum count'u al
                comment_renderers = driver.find_elements(By.XPATH, comment_renderer_xpath)
                current_comment_count = len(comment_renderers)
                
                logging.info(f"Loaded {current_comment_count} renderer comments after scroll {scroll_count + 1}")
                scroll_count += 1
            
            # Yorum parçalarını çıkar
            results = []
            for comment in comment_renderers:  # Tüm yorumları al
                try:
                    # Yorum metnini doğrudan al
                    comment_text = ""
                    try:
                        content_el = comment.find_element(By.XPATH, ".//yt-formatted-string[@id='content-text']")
                        comment_text = content_el.text.strip()
                    except:
                        pass
                    
                    # Eğer yorum metni bulunduysa diğer bilgileri ekstra
                    if comment_text:
                        # Yazar adı
                        author_name = "Anonim Kullanıcı"
                        try:
                            author_el = comment.find_element(By.XPATH, ".//a[@id='author-text']")
                            author_name = author_el.text.strip()
                        except:
                            pass
                        
                        # Diğer bilgiler
                        results.append({
                            "authorDisplayName": author_name,
                            "authorProfileImageUrl": None,
                            "textDisplay": comment_text,
                            "publishedAt": "Tarih alınamadı",
                            "likeCount": "0"
                        })
                except Exception as e:
                    logging.error(f"Error parsing renderer comment: {str(e)}")
                    continue
            
            # Eğer yorum varsa analiz et ve döndür
            if results:
                # Gemini API ile analiz et
                analysis = analyze_comments_with_gemini(video_title, results)
                
                # Toplam yorum sayısını al
                total_comments = get_total_comment_count(driver)
                
                return {
                    "comments": results,
                    "analysis": analysis,
                    "video_title": video_title,
                    "total_comments": total_comments
                }
        except Exception as e:
            logging.warning(f"Failed to extract comment renderers: {str(e)}")
        
        # Son çare: Sayfada XPATH ile içerik-metin alanlarını ara
        content_text_xpath = "//*[contains(@id, 'content-text')]"
        try:
            content_texts = driver.find_elements(By.XPATH, content_text_xpath)
            logging.info(f"Found {len(content_texts)} content text elements")
            
            # Daha fazla yorum yüklemek için scroll et
            MAX_COMMENTS = 200
            previous_content_count = 0
            scroll_count = 0
            max_scroll_attempts = 20
            
            current_content_count = len(content_texts)
            
            # Daha fazla içerik yüklemek için scroll
            while current_content_count < MAX_COMMENTS and current_content_count > previous_content_count and scroll_count < max_scroll_attempts:
                previous_content_count = current_content_count
                
                # Sayfanın sonuna doğru kaydır
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                
                # Yeni içerik count'u al
                content_texts = driver.find_elements(By.XPATH, content_text_xpath)
                current_content_count = len(content_texts)
                
                logging.info(f"Loaded {current_content_count} content elements after scroll {scroll_count + 1}")
                scroll_count += 1
            
            # Yeterince uzun metinleri yorum olarak al
            results = []
            for i, element in enumerate(content_texts):  # Tüm içerikleri al
                try:
                    text = element.text.strip()
                    if text and len(text) > 20:  # Muhtemelen yorumdur
                        results.append({
                            "authorDisplayName": f"YouTube Kullanıcı {i+1}",
                            "authorProfileImageUrl": None,
                            "textDisplay": text,
                            "publishedAt": "Tarih alınamadı",
                            "likeCount": "0"
                        })
                except Exception as e:
                    logging.error(f"Error parsing text element: {str(e)}")
                    continue
            
            # Eğer yorum varsa analiz et ve döndür
            if results:
                # Gemini API ile analiz et
                analysis = analyze_comments_with_gemini(video_title, results)
                
                # Toplam yorum sayısını al
                total_comments = get_total_comment_count(driver)
                
                return {
                    "comments": results,
                    "analysis": analysis,
                    "video_title": video_title,
                    "total_comments": total_comments
                }
        except Exception as e:
            logging.warning(f"Failed to extract content text elements: {str(e)}")
        
        # Yorumlar bulunamadıysa
        # Sayfadaki durum kontrolü (yorumlar kapatılmış mı?)
        page_source = driver.page_source
        if "Bu videoda yorumlar kapatıldı" in page_source or "Comments are turned off" in page_source:
            return {
                "comments": [], 
                "error": "Bu videoda yorumlar kapatılmış", 
                "video_title": video_title,
                "total_comments": 0
            }
        
        # Ekran görüntüsü al (debug için)
        try:
            screenshot_path = "debug_screenshot.png"
            driver.save_screenshot(screenshot_path)
            logging.info(f"Saved debug screenshot to {screenshot_path}")
        except Exception as e:
            logging.error(f"Failed to save screenshot: {str(e)}")
        
        # Son çare olarak sayfadaki tüm metin içeren elementleri al
        try:
            text_elements = driver.find_elements(By.XPATH, "//div[string-length(text()) > 20]")
            if text_elements and len(text_elements) > 0:
                results = []
                for i, el in enumerate(text_elements[:10]):
                    text = el.text.strip()
                    if text:
                        results.append({
                            "authorDisplayName": "Bilinmeyen Kullanıcı",
                            "authorProfileImageUrl": None,
                            "textDisplay": text,
                            "publishedAt": "Tarih alınamadı",
                            "likeCount": "0"
                        })
                
                if results:
                    # Gemini API ile analiz et
                    analysis = analyze_comments_with_gemini(video_title, results)
                    
                    # Toplam yorum sayısını al
                    total_comments = get_total_comment_count(driver)
                    
                    return {
                        "comments": results, 
                        "warning": "Yorumlar tam olarak çıkarılamadı, sadece metin içeriği gösteriliyor",
                        "analysis": analysis,
                        "video_title": video_title,
                        "total_comments": total_comments
                    }
        except Exception as e:
            logging.error(f"Last resort text extraction failed: {str(e)}")
        
        # Toplam yorum sayısını al
        total_comments = get_total_comment_count(driver)

        return {
            "comments": [], 
            "error": "Yorumlar bulunamadı veya yüklenemedi", 
            "video_title": video_title, 
            "total_comments": total_comments
        }
    
    except Exception as e:
        logging.error(f"Error fetching comments: {str(e)}")
        return {"error": str(e), "comments": [], "video_title": "Bilinmeyen Video", "total_comments": None}
    
    finally:
        if driver:
            driver.quit()

# Statik dosyaları servis et (güvenli hale getirildi)
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('static', path)

# API endpoint for fetching comments
@app.route('/api/comments', methods=['POST'])
def get_comments():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL gerekli"}), 400
    
    result = fetch_youtube_comments(url)
    return jsonify(result)

if __name__ == '__main__':
    # Üretim ortamında debug=False olmalı!
    # Geliştirme için True bırakılabilir, ancak canlıya alırken mutlaka False yapın.
    app.run(host='0.0.0.0', port=5000, debug=False) # DEBUG MODU KAPATILDI (Üretim için) 