document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('youtube-url');
    const fetchButton = document.getElementById('fetch-comments');
    const loadingSpinner = document.getElementById('loading');
    const commentsContainer = document.getElementById('comments-container');

    // Örnek YouTube URL'si ekle
    urlInput.placeholder = "YouTube video linkini yapıştırın (örn: https://www.youtube.com/watch?v=dQw4w9WgXcQ)";

    fetchButton.addEventListener('click', async () => {
        const youtubeUrl = urlInput.value.trim();

        if (!isValidYoutubeUrl(youtubeUrl)) {
            alert('Lütfen geçerli bir YouTube linki girin.');
            return;
        }

        // Önceki yorumları temizle
        commentsContainer.innerHTML = '';

        // Yükleme animasyonunu göster
        loadingSpinner.style.display = 'flex';

        // Kullanıcıya bilgi ver
        commentsContainer.innerHTML = '<p class="info-message">Tüm yorumlar yükleniyor ve analiz ediliyor... Bu işlem, çekilen yorum sayısına bağlı olarak 1-2 dakika sürebilir. Lütfen bekleyin.</p>';

        try {
            const response = await fetch('/api/comments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: youtubeUrl })
            });

            if (!response.ok) {
                throw new Error('Sunucu yanıt vermiyor veya hata döndürdü.');
            }

            const data = await response.json();

            // Önceki mesajı temizle
            commentsContainer.innerHTML = '';

            // Hata kontrolü
            if (data.error) {
                throw new Error(data.error);
            }

            // Video başlığını göster
            if (data.video_title) {
                const titleEl = document.createElement('h2');
                titleEl.className = 'video-title';
                titleEl.textContent = data.video_title;
                commentsContainer.appendChild(titleEl);

                // Yorum sayısı bilgisi ekle (Yeni eklenen)
                const statsContainer = document.createElement('div');
                statsContainer.className = 'stats-container';

                // Video bilgileri ve yorum sayacını oluştur
                statsContainer.innerHTML = `
                    <div class="stats-box">
                        <div class="stat-item">
                            <span class="stat-value">${data.comments ? data.comments.length : 0}</span>
                            <span class="stat-label">Çekilen Yorum</span>
                        </div>
                        ${data.total_comments ? `
                        <div class="stat-item">
                            <span class="stat-value">${data.total_comments}</span>
                            <span class="stat-label">Toplam Yorum</span>
                        </div>` : ''}
                    </div>
                `;

                commentsContainer.appendChild(statsContainer);
            }

            // Analiz sonuçlarını göster
            if (data.analysis) {
                renderAnalysis(data.analysis);
            }

            if (!data.comments || data.comments.length === 0) {
                commentsContainer.innerHTML += `
                    <div class="error-box">
                        <p class="no-comments">Bu videoda hiç yorum bulunamadı veya yorumlara erişilemiyor.</p>
                        <p class="error-help">YouTube, yorum bölümünü kapatmış veya uygulama yorumlara erişemiyor olabilir.</p>
                    </div>
                `;
            } else {
                // Yorumları göster
                const commentsHeading = document.createElement('h3');
                commentsHeading.className = 'comments-heading';
                commentsHeading.textContent = 'Yorumlar';
                commentsContainer.appendChild(commentsHeading);

                renderComments(data.comments);

                // Bilgi mesajı ekle
                const infoEl = document.createElement('div');
                infoEl.className = 'info-message';
                infoEl.textContent = `Toplam ${data.comments.length} yorum gösteriliyor.`;

                // Yorumların üstüne bilgi mesajını ekle
                const commentsHeadingEl = document.querySelector('.comments-heading');
                if (commentsHeadingEl) {
                    commentsHeadingEl.after(infoEl);
                } else {
                    commentsContainer.appendChild(infoEl);
                }
            }
        } catch (error) {
            console.error('Hata:', error);
            commentsContainer.innerHTML = `
                <div class="error-box">
                    <p class="error">Bir hata oluştu: ${error.message}</p>
                    <p class="error-help">Lütfen başka bir YouTube linkiyle tekrar deneyin. Uygulama şu anda sadece standart YouTube videolarını desteklemektedir.</p>
                </div>
            `;
        } finally {
            // Yükleme animasyonunu gizle
            loadingSpinner.style.display = 'none';
        }
    });

    function isValidYoutubeUrl(url) {
        const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
        return pattern.test(url);
    }

    function renderAnalysis(analysis) {
        // Analiz sonuçlarını gösterecek container oluştur
        const analysisEl = document.createElement('div');
        analysisEl.className = 'analysis-container';

        // Analiz başlığını ekle
        const analysisTitle = document.createElement('h3');
        analysisTitle.textContent = 'Yapay Zeka Analizi';
        analysisTitle.className = 'analysis-title';
        analysisEl.appendChild(analysisTitle);

        // Hata kontrolü
        if (analysis.error) {
            const errorEl = document.createElement('p');
            errorEl.className = 'error';
            errorEl.textContent = `Analiz hatası: ${analysis.error}`;
            analysisEl.appendChild(errorEl);

            if (analysis.raw_response) {
                const rawEl = document.createElement('pre');
                rawEl.textContent = analysis.raw_response;
                rawEl.className = 'raw-response';
                analysisEl.appendChild(rawEl);
            }

            commentsContainer.appendChild(analysisEl);
            return;
        }

        // Duygu analizi
        if (analysis.genel_duygu) {
            const moodEl = document.createElement('div');
            moodEl.className = 'analysis-section mood-analysis';

            const moodTitle = document.createElement('h4');
            moodTitle.textContent = 'Duygu Analizi';
            moodEl.appendChild(moodTitle);

            // Duygu dağılımı için bar chart
            const chartEl = document.createElement('div');
            chartEl.className = 'mood-chart';

            // Duygu yüzdelerini sayıya çevir
            const pozitif = parseInt(analysis.genel_duygu.pozitif || '0%');
            const negatif = parseInt(analysis.genel_duygu.negatif || '0%');
            const notr = parseInt(analysis.genel_duygu.notr || '0%');

            // Bar chart oluştur
            chartEl.innerHTML = `
                <div class="chart-labels">
                    <span>Pozitif</span>
                    <span>Nötr</span>
                    <span>Negatif</span>
                </div>
                <div class="chart-bars">
                    <div class="bar positive" style="width: ${pozitif}%;" title="Pozitif: ${analysis.genel_duygu.pozitif}">
                        <span>${analysis.genel_duygu.pozitif}</span>
                    </div>
                    <div class="bar neutral" style="width: ${notr}%;" title="Nötr: ${analysis.genel_duygu.notr}">
                        <span>${analysis.genel_duygu.notr}</span>
                    </div>
                    <div class="bar negative" style="width: ${negatif}%;" title="Negatif: ${analysis.genel_duygu.negatif}">
                        <span>${analysis.genel_duygu.negatif}</span>
                    </div>
                </div>
            `;

            moodEl.appendChild(chartEl);
            analysisEl.appendChild(moodEl);
        }

        // Genel İzlenim
        if (analysis.genel_izlenim) {
            const impressionEl = document.createElement('div');
            impressionEl.className = 'analysis-section';

            const impressionTitle = document.createElement('h4');
            impressionTitle.textContent = 'Genel İzlenim';
            impressionEl.appendChild(impressionTitle);

            const impressionText = document.createElement('p');
            impressionText.textContent = analysis.genel_izlenim;
            impressionEl.appendChild(impressionText);

            analysisEl.appendChild(impressionEl);
        }

        // Öne Çıkan Konular
        if (analysis.one_cikan_konular && analysis.one_cikan_konular.length > 0) {
            const topicsEl = document.createElement('div');
            topicsEl.className = 'analysis-section';

            const topicsTitle = document.createElement('h4');
            topicsTitle.textContent = 'Öne Çıkan Konular';
            topicsEl.appendChild(topicsTitle);

            const topicsList = document.createElement('ul');
            analysis.one_cikan_konular.forEach(topic => {
                const topicItem = document.createElement('li');
                topicItem.textContent = topic;
                topicsList.appendChild(topicItem);
            });

            topicsEl.appendChild(topicsList);
            analysisEl.appendChild(topicsEl);
        }

        // Tartışmalı Noktalar
        if (analysis.tartismali_noktalar && analysis.tartismali_noktalar.length > 0) {
            const debateEl = document.createElement('div');
            debateEl.className = 'analysis-section';

            const debateTitle = document.createElement('h4');
            debateTitle.textContent = 'Tartışmalı/İlgi Çeken Noktalar';
            debateEl.appendChild(debateTitle);

            const debateList = document.createElement('ul');
            analysis.tartismali_noktalar.forEach(point => {
                const pointItem = document.createElement('li');
                pointItem.textContent = point;
                debateList.appendChild(pointItem);
            });

            debateEl.appendChild(debateList);
            analysisEl.appendChild(debateEl);
        }

        // Öneriler
        if (analysis.oneriler && analysis.oneriler.length > 0) {
            const suggestionsEl = document.createElement('div');
            suggestionsEl.className = 'analysis-section';

            const suggestionsTitle = document.createElement('h4');
            suggestionsTitle.textContent = 'Öneriler ve İstekler';
            suggestionsEl.appendChild(suggestionsTitle);

            const suggestionsList = document.createElement('ul');
            analysis.oneriler.forEach(suggestion => {
                const suggestionItem = document.createElement('li');
                suggestionItem.textContent = suggestion;
                suggestionsList.appendChild(suggestionItem);
            });

            suggestionsEl.appendChild(suggestionsList);
            analysisEl.appendChild(suggestionsEl);
        }

        // Özet
        if (analysis.ozet) {
            const summaryEl = document.createElement('div');
            summaryEl.className = 'analysis-section summary';

            const summaryTitle = document.createElement('h4');
            summaryTitle.textContent = 'Özet';
            summaryEl.appendChild(summaryTitle);

            const summaryText = document.createElement('p');
            summaryText.textContent = analysis.ozet;
            summaryEl.appendChild(summaryText);

            analysisEl.appendChild(summaryEl);
        }

        // Analizin tamamını DOM'a ekle
        commentsContainer.appendChild(analysisEl);
    }

    function renderComments(comments) {
        comments.forEach(comment => {
            const commentEl = document.createElement('div');
            commentEl.className = 'comment';

            // Default profil resmi
            const profileImg = comment.authorProfileImageUrl || 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y';

            const commentHtml = `
                <div class="comment-header">
                    <img src="${profileImg}" alt="${comment.authorDisplayName}" class="author-img" onerror="this.src='https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y'">
                    <span class="author-name">${escapeHtml(comment.authorDisplayName)}</span>
                    <span class="comment-date">${escapeHtml(comment.publishedAt)}</span>
                </div>
                <div class="comment-text">${escapeHtml(comment.textDisplay)}</div>
                <div class="likes">
                    <span>👍 ${escapeHtml(comment.likeCount)}</span>
                </div>
            `;

            commentEl.innerHTML = commentHtml;
            commentsContainer.appendChild(commentEl);
        });
    }

    // Güvenlik için HTML escape fonksiyonu
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatDate(dateString) {
        // Eğer tarih string zaten formatlı ise (API'den gelen)
        if (typeof dateString === 'string' && !dateString.includes('T')) {
            return dateString;
        }

        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('tr-TR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (e) {
            return dateString || 'Bilinmeyen tarih';
        }
    }
}); 