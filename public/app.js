document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('searchBtn');
    const keywordInput = document.getElementById('keywordInput');
    const searchIcon = document.getElementById('searchIcon');
    const spinnerIcon = document.getElementById('spinnerIcon');
    const btnText = document.getElementById('btnText');
    
    const resultsContainer = document.getElementById('resultsContainer');
    const tableBody = document.getElementById('tableBody');
    const resultCount = document.getElementById('resultCount');
    const downloadBtn = document.getElementById('downloadBtn');
    
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');

    let currentData = [];

    searchBtn.addEventListener('click', async () => {
        const keyword = keywordInput.value.trim();
        if (!keyword) return;

        setLoading(true);
        hideError();
        resultsContainer.classList.add('hidden');
        downloadBtn.classList.add('hidden');

        try {
            const response = await fetch(`/api/scrape?keyword=${encodeURIComponent(keyword)}`);
            
            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.detail || `HTTP Error ${response.status}`);
            }

            const data = await response.json();
            currentData = data;

            renderTable(data);
            
            resultCount.textContent = `${data.length}件`;
            resultsContainer.classList.remove('hidden');
            
            if (data.length > 0) {
                downloadBtn.classList.remove('hidden');
            }

        } catch (error) {
            console.error('Scraping Error:', error);
            showError(`データ取得に失敗しました: ${error.message}`);
        } finally {
            setLoading(false);
        }
    });

    downloadBtn.addEventListener('click', () => {
        if (currentData.length === 0) return;
        downloadCSV(currentData, `leads_${keywordInput.value.trim()}_${new Date().getTime()}.csv`);
    });

    function setLoading(isLoading) {
        if (isLoading) {
            searchBtn.disabled = true;
            btnText.textContent = '抽出中...';
            searchIcon.classList.add('hidden');
            spinnerIcon.classList.remove('hidden');
        } else {
            searchBtn.disabled = false;
            btnText.textContent = '検索実行';
            searchIcon.classList.remove('hidden');
            spinnerIcon.classList.add('hidden');
        }
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorMessage.classList.remove('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    function renderTable(data) {
        tableBody.innerHTML = '';
        
        if (data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-500">データが見つかりませんでした</td></tr>`;
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition-colors';
            
            tr.innerHTML = `
                <td class="px-6 py-4 font-medium text-slate-900">${escapeHTML(item.company_name)}</td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center gap-1 bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md text-xs font-medium">
                        <i class="fa-solid fa-location-dot"></i> ${escapeHTML(item.location)}
                    </span>
                </td>
                <td class="px-6 py-4 text-slate-600">${escapeHTML(item.job_title)}</td>
                <td class="px-6 py-4 text-slate-400 text-sm whitespace-nowrap">${escapeHTML(item.posted_date)}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    function escapeHTML(str) {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g, tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag));
    }

    function downloadCSV(data, filename) {
        const headers = ['企業名', '所在地', '求人職種', '掲載日', '求人ID'];
        const csvRows = [];
        
        // Header
        csvRows.push(headers.join(','));
        
        // Data Rows
        for (const row of data) {
            const values = [
                row.company_name,
                row.location,
                row.job_title,
                row.posted_date,
                row.job_id
            ].map(value => {
                const escapedValue = String(value || '').replace(/"/g, '""');
                return `"${escapedValue}"`;
            });
            csvRows.push(values.join(','));
        }
        
        // Add BOM for Excel Windows compatibility
        const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
        const blob = new Blob([bom, csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        
        const link = document.createElement("a");
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
});
