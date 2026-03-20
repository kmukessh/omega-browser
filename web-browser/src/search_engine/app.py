from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse
import threading
import time
import re
from wikipedia import wikipedia, exceptions
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

app = Flask(__name__)

SEARCH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Omega Search - {{query}}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
        }
        .search-results {
            max-width: 800px;
            margin: 0 auto;
        }
        .result-item {
            display: flex;
            align-items: start;
            gap: 15px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            margin: 10px 0;
            border-radius: 10px;
            transition: transform 0.2s;
        }
        .result-item:hover {
            transform: translateY(-2px);
        }
        .result-title {
            color: #4a90e2;
            text-decoration: none;
            font-size: 18px;
        }
        .result-url {
            color: #66b1ff;
            font-size: 14px;
            margin: 5px 0;
        }
        .result-snippet {
            color: #ccc;
            font-size: 14px;
        }
        .search-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .omega-logo {
            font-size: 36px;
            margin-bottom: 10px;
        }
        .loading {
            text-align: center;
            padding: 20px;
            font-size: 18px;
        }
        .search-box-container {
            position: relative;
            max-width: 600px;
            margin: 20px auto;
        }
        .search-input {
            width: 100%;
            padding: 12px 40px 12px 15px;
            border-radius: 20px;
            border: 2px solid #4a90e2;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 16px;
        }
        .search-input::placeholder {
            color: rgba(255, 255, 255, 0.6);
        }
        .search-button {
            position: absolute;
            right: 5px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: #4a90e2;
            font-size: 20px;
            cursor: pointer;
            padding: 10px;
        }
        .search-button:hover {
            color: #66b1ff;
        }
        .result-favicon {
            width: 32px;
            height: 32px;
            border-radius: 6px;
        }
        .result-content {
            flex: 1;
        }
        .result-meta {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 5px;
        }
        .result-type {
            background: rgba(74, 144, 226, 0.2);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            color: #66b1ff;
        }
        .suggestions {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(26, 26, 46, 0.95);
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            display: none;
            z-index: 1000;
        }
        .suggestion-item {
            padding: 10px 15px;
            cursor: pointer;
        }
        .suggestion-item:hover {
            background: rgba(74, 144, 226, 0.1);
        }
        .suggestion-content {
            flex: 1;
        }
        .suggestion-description {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
            opacity: 0.8;
        }
        .suggestion-text {
            font-weight: 500;
        }
        .suggestion-item {
            padding: 12px 20px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }
        .suggestion-icon {
            font-size: 16px;
            min-width: 24px;
            text-align: center;
        }
    </style>
    <script>
        function submitSearch() {
            var query = document.getElementById('search-input').value;
            if (query.trim()) {
                window.location.href = '/search?q=' + encodeURIComponent(query);
            }
        }
        
        let typingTimer;
        
        function handleInput(input) {
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => getSuggestions(input.value), 300);
        }

        async function getSuggestions(query) {
            if (!query) return;
            try {
                const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                showSuggestions(data.suggestions);
            } catch (e) {
                console.error('Error fetching suggestions:', e);
            }
        }

        async function showSuggestions(suggestions) {
            currentSuggestions = suggestions;
            const container = document.querySelector('.suggestions');
            
            if (!suggestions || suggestions.length === 0) {
                hideSuggestions();
                return;
            }

            const html = suggestions.map((suggestion, index) => `
                <div class="suggestion-item" 
                     onclick="selectSuggestion(${index})"
                     onmouseover="selectedIndex = ${index}">
                    <span class="suggestion-icon">${getIconForType(suggestion.type)}</span>
                    <div class="suggestion-content">
                        <div class="suggestion-text">${suggestion.text}</div>
                        ${suggestion.description ? 
                          `<div class="suggestion-description">${suggestion.description}</div>` : 
                          ''}
                    </div>
                </div>
            `).join('');

            container.innerHTML = html;
            container.style.display = 'block';
        }

        function getIconForType(type) {
            const icons = {
                'direct': '🔍',
                'related': '📌',
                'definition': '📖',
                'examples': '💡',
                'how-to': '❓'
            };
            return icons[type] || '🔍';
        }

        function selectSuggestion(suggestion) {
            document.getElementById('search-input').value = suggestion;
            submitSearch();
        }
    </script>
</head>
<body>
    <div class="search-header">
        <div class="omega-logo">Ω</div>
        <div class="search-box-container">
            <input type="text" 
                   id="search-input"
                   class="search-input" 
                   value="{{query}}"
                   placeholder="Search the web with Omega..."
                   onkeypress="if(event.key === 'Enter') submitSearch()" oninput="handleInput(this)">
            <button class="search-button" onclick="submitSearch()">🔍</button>
            <div class="suggestions"></div>
        </div>
    </div>
    <div class="search-results">
        {% if error %}
            <div class="result-item">
                <p>{{error}}</p>
            </div>
        {% else %}
            {% for result in results %}
                <div class="result-item">
                    <img class="result-favicon" src="{{result.favicon}}" alt="">
                    <div class="result-content">
                        <a href="{{result.url}}" class="result-title">{{result.title}}</a>
                        <div class="result-meta">
                            <span class="result-url">{{result.domain}}</span>
                            <span class="result-type">{{result.type}}</span>
                        </div>
                        {% if result.snippet %}
                            <div class="result-snippet">{{result.snippet}}</div>
                        {% endif %}
                    </div>
                </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
'''

# Create thread pool for parallel searches
executor = ThreadPoolExecutor(max_workers=4)

@lru_cache(maxsize=1000)
def get_cached_search_results(query):
    """Cache search results for frequently searched terms"""
    return get_search_results(query)

def get_search_results(query, max_results=10):
    """Parallel search implementation"""
    try:
        # Run searches in parallel
        url_future = executor.submit(search_urls, query)
        wiki_future = executor.submit(search_wikipedia, query)
        google_future = executor.submit(search_google, query)
        
        # Combine results
        results = []
        results.extend(url_future.result() or [])
        results.extend(wiki_future.result() or [])
        results.extend(google_future.result() or [])
        
        return results[:max_results]
    except Exception as e:
        print(f"Search error: {e}")
        return None

def search_urls(query):
    url_pattern = re.compile(r'^(https?:\/\/)?\w+\.\w+')
    if url_pattern.match(query):
        url = query if query.startswith(('http://', 'https://')) else f'http://{query}'
        return [{
            'title': f'Go to {query}',
            'url': url,
            'domain': urlparse(url).netloc,
            'favicon': f"https://www.google.com/s2/favicons?domain={query}&sz=32",
            'snippet': f'Direct link to {query}',
            'type': 'website'
        }]
    return []

def search_wikipedia(query):
    try:
        results = []
        for term in wikipedia.search(query, results=5):
            summary = wikipedia.summary(term, sentences=1)
            results.append({
                'title': term,
                'url': f'https://en.wikipedia.org/wiki/{quote(term)}',
                'domain': 'wikipedia.org',
                'favicon': 'https://en.wikipedia.org/static/favicon/wikipedia.ico',
                'snippet': summary,
                'type': 'wiki'
            })
        return results
    except:
        return []

def search_google(query):
    try:
        results = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(
            f'https://www.google.com/search?q={quote(query)}',
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for div in soup.find_all('div', class_='g')[:10]:
            try:
                title_elem = div.find('h3')
                link_elem = div.find('a')
                snippet_elem = div.find('div', class_='VwiC3b')
                
                if title_elem and link_elem:
                    url = link_elem['href']
                    domain = urlparse(url).netloc
                    favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
                    
                    result = {
                        'title': title_elem.text,
                        'url': url,
                        'domain': domain,
                        'favicon': favicon_url,
                        'snippet': snippet_elem.text if snippet_elem else '',
                        'type': 'website'
                    }
                    
                    # Add result type based on URL pattern
                    if 'youtube.com' in domain:
                        result['type'] = 'video'
                    elif 'wikipedia.org' in domain:
                        result['type'] = 'wiki'
                    elif any(s in domain for s in ['news', 'bbc', 'cnn', 'reuters']):
                        result['type'] = 'news'
                    
                    results.append(result)
            except Exception as e:
                continue
                
        return results
    except requests.RequestException as e:
        return None

def get_quick_summary(query):
    try:
        # Try to get a Wikipedia summary
        return wikipedia.summary(query, sentences=2)
    except:
        return None

def get_related_terms(query):
    try:
        # Get related Wikipedia search results
        return wikipedia.search(query, results=5)
    except:
        return []

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return render_template_string(
            SEARCH_TEMPLATE,
            query='',
            error='Please enter a search query.',
            results=[]
        )

    results = get_search_results(query)
    if results is None:
        return render_template_string(
            SEARCH_TEMPLATE,
            query=query,
            error='Sorry, there was an error processing your search. Please try again.',
            results=[]
        )

    return render_template_string(
        SEARCH_TEMPLATE,
        query=query,
        results=results,
        error=None
    )

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Query is required'})

    results = get_search_results(query)
    if results is None:
        return jsonify({'error': 'Search failed'})

    return jsonify({'results': results})

@app.route('/api/suggestions')
def get_suggestions():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'suggestions': []})
    
    # Use cached results for better performance
    return jsonify({
        'suggestions': get_cached_suggestions(query),
        'summary': get_cached_summary(query)
    })

@lru_cache(maxsize=1000)
def get_cached_suggestions(query):
    """Cache suggestions for better performance"""
    try:
        return generate_suggestions(query)
    except Exception:
        return []

@lru_cache(maxsize=100)
def get_cached_summary(query):
    """Cache summaries for better performance"""
    try:
        return wikipedia.summary(query, sentences=2)
    except Exception:
        return None

def generate_suggestions(query):
    try:
        # Get related terms
        related = get_related_terms(query)
        
        # Get quick summary
        summary = get_quick_summary(query)
        
        # Generate contextual suggestions
        suggestions = [
            {'text': query, 'type': 'direct', 'description': summary},
            *[{'text': term, 'type': 'related'} for term in related],
            {'text': f"{query} definition", 'type': 'definition'},
            {'text': f"{query} examples", 'type': 'examples'},
            {'text': f"how does {query} work", 'type': 'how-to'}
        ]
        
        return suggestions
    except Exception as e:
        return []

if __name__ == '__main__':
    app.run(port=5000, debug=True)
