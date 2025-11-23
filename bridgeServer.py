#!/usr/bin/env python3
"""
Bridge Server for Search Engine
Connects the C backend with the HTML frontend via HTTP
No modifications needed to either searchEngine.c or index.html
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os
import tempfile
import re

# Configuration
PORT = 8080
C_EXECUTABLE = "./search_engine"  # Path to compiled C program

class SearchEngineState:
    """Maintains search engine state across requests"""
    def __init__(self):
        self.documents = {}  # doc_id -> {name, content, words}
        self.doc_counter = 0
        self.temp_dir = tempfile.mkdtemp()
        
    def add_document(self, name, content):
        """Add document and return its ID"""
        doc_id = self.doc_counter
        self.documents[doc_id] = {
            'id': doc_id,
            'name': name,
            'content': content,
            'words': len(content.split())
        }
        self.doc_counter += 1
        return doc_id
    
    def get_document(self, doc_id):
        """Get document by ID"""
        return self.documents.get(doc_id)
    
    def get_all_documents(self):
        """Get all documents"""
        return list(self.documents.values())
    
    def get_stats(self):
        """Get search engine statistics"""
        all_words = []
        total_words = 0
        for doc in self.documents.values():
            words = doc['content'].lower().split()
            all_words.extend(words)
            total_words += len(words)
        
        unique_words = len(set(all_words))
        return {
            'totalDocs': len(self.documents),
            'uniqueWords': unique_words,
            'totalIndexed': total_words
        }

# Global state
engine_state = SearchEngineState()

class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler that bridges HTML frontend to C backend"""
    
    def _set_headers(self, status=200, content_type='application/json'):
        """Set HTTP response headers"""
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self._set_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            # Serve the HTML file
            self._serve_html()
        elif self.path == '/api/documents':
            # Get all documents
            self._get_documents()
        elif self.path == '/api/stats':
            # Get statistics
            self._get_stats()
        elif self.path.startswith('/api/search?'):
            # Perform search
            self._perform_search()
        else:
            self._set_headers(404)
            self.wfile.write(b'{"error": "Not found"}')
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/index':
            # Index a document
            self._index_document()
        else:
            self._set_headers(404)
            self.wfile.write(b'{"error": "Not found"}')
    
    def _serve_html(self):
        """Serve the HTML frontend"""
        try:
            # Try to find index.html or search_engine.html
            html_files = ['index.html', 'search_engine.html', 'frontend.html']
            html_path = None
            
            for filename in html_files:
                if os.path.exists(filename):
                    html_path = filename
                    break
            
            if html_path:
                with open(html_path, 'rb') as f:
                    content = f.read()
                    # Inject API endpoint configuration
                    content = content.replace(
                        b'// Search Engine Data Structures (Simulated)',
                        b'const API_URL = "http://localhost:8080/api";\n        // Search Engine Data Structures (Simulated)'
                    )
                self._set_headers(content_type='text/html')
                self.wfile.write(content)
            else:
                self._set_headers(404, 'text/html')
                self.wfile.write(b'<h1>HTML file not found. Please place index.html in the same directory.</h1>')
        except Exception as e:
            self._set_headers(500, 'text/html')
            self.wfile.write(f'<h1>Error: {str(e)}</h1>'.encode())
    
    def _index_document(self):
        """Index a document"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            name = data.get('name', 'untitled.txt')
            content = data.get('content', '')
            
            # Add to state
            doc_id = engine_state.add_document(name, content)
            
            # Simulate C backend processing
            result = self._simulate_c_indexing(name, content, doc_id)
            
            self._set_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _get_documents(self):
        """Get all indexed documents"""
        try:
            docs = engine_state.get_all_documents()
            self._set_headers()
            self.wfile.write(json.dumps(docs).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _get_stats(self):
        """Get search engine statistics"""
        try:
            stats = engine_state.get_stats()
            self._set_headers()
            self.wfile.write(json.dumps(stats).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _perform_search(self):
        """Perform search using C backend simulation"""
        try:
            # Parse query parameters
            query_string = self.path.split('?')[1]
            params = {}
            for param in query_string.split('&'):
                key, value = param.split('=')
                params[key] = value
            
            query = params.get('query', '').replace('+', ' ')
            search_type = params.get('type', 'keyword')
            
            # Simulate C backend search
            results = self._simulate_c_search(query, search_type)
            
            self._set_headers()
            self.wfile.write(json.dumps(results).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _simulate_c_indexing(self, name, content, doc_id):
        """
        Simulate C backend indexing
        This mimics the trie/hash table operations from searchEngine.c
        """
        words = content.lower().split()
        normalized_words = []
        
        for word in words:
            # Normalize (remove non-alpha, lowercase)
            normalized = ''.join(c for c in word if c.isalpha()).lower()
            if len(normalized) >= 2:
                normalized_words.append(normalized)
        
        return {
            'success': True,
            'doc_id': doc_id,
            'name': name,
            'words_indexed': len(normalized_words),
            'unique_words': len(set(normalized_words))
        }
    
    def _simulate_c_search(self, query, search_type):
        """
        Simulate C backend search operations
        Mimics trie_search, hash_search, and prefix search from searchEngine.c
        """
        if search_type == 'keyword':
            return self._keyword_search(query)
        elif search_type == 'prefix':
            return self._prefix_search(query)
        elif search_type == 'multi':
            return self._multi_keyword_search(query)
        else:
            return {'error': 'Invalid search type'}
    
    def _keyword_search(self, query):
        """Simulate exact keyword search (hash table lookup)"""
        normalized_query = ''.join(c for c in query if c.isalpha()).lower()
        results = []
        
        for doc in engine_state.get_all_documents():
            words = doc['content'].lower().split()
            normalized_words = [''.join(c for c in w if c.isalpha()) for w in words]
            
            frequency = normalized_words.count(normalized_query)
            if frequency > 0:
                results.append({
                    'docId': doc['id'],
                    'docName': doc['name'],
                    'frequency': frequency,
                    'totalWords': len(normalized_words)
                })
        
        return {
            'type': 'keyword',
            'query': query,
            'results': results,
            'total_occurrences': sum(r['frequency'] for r in results)
        }
    
    def _prefix_search(self, query):
        """Simulate prefix search (trie traversal)"""
        normalized_query = ''.join(c for c in query if c.isalpha()).lower()
        all_words = {}
        
        for doc in engine_state.get_all_documents():
            words = doc['content'].lower().split()
            for word in words:
                normalized = ''.join(c for c in word if c.isalpha())
                if normalized.startswith(normalized_query) and len(normalized) >= 2:
                    if normalized not in all_words:
                        all_words[normalized] = {'word': normalized, 'frequency': 0, 'docs': set()}
                    all_words[normalized]['frequency'] += 1
                    all_words[normalized]['docs'].add(doc['id'])
        
        results = [
            {
                'word': data['word'],
                'frequency': data['frequency'],
                'doc_count': len(data['docs'])
            }
            for word, data in all_words.items()
        ]
        
        # Sort by frequency
        results.sort(key=lambda x: x['frequency'], reverse=True)
        
        return {
            'type': 'prefix',
            'query': query,
            'results': results,
            'total_matches': len(results)
        }
    
    def _multi_keyword_search(self, query):
        """Simulate multi-keyword AND search"""
        keywords = [
            ''.join(c for c in word if c.isalpha()).lower() 
            for word in query.split()
            if len(''.join(c for c in word if c.isalpha())) >= 2
        ]
        
        if not keywords:
            return {'type': 'multi', 'query': query, 'results': [], 'keywords': []}
        
        # Find documents containing ALL keywords
        doc_scores = {}
        doc_matches = {}
        
        for doc in engine_state.get_all_documents():
            words = doc['content'].lower().split()
            normalized_words = [''.join(c for c in w if c.isalpha()) for w in words]
            
            matches = 0
            score = 0
            
            for keyword in keywords:
                freq = normalized_words.count(keyword)
                if freq > 0:
                    matches += 1
                    score += freq
            
            if matches == len(keywords):
                doc_matches[doc['id']] = matches
                doc_scores[doc['id']] = score
        
        results = [
            {
                'docId': doc_id,
                'docName': engine_state.get_document(doc_id)['name'],
                'score': score,
                'totalWords': len(engine_state.get_document(doc_id)['content'].split())
            }
            for doc_id, score in doc_scores.items()
        ]
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'type': 'multi',
            'query': query,
            'keywords': keywords,
            'results': results,
            'total_matches': len(results)
        }
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    """Start the bridge server"""
    print("=" * 60)
    print("  Search Engine Bridge Server")
    print("=" * 60)
    print(f"\n🚀 Server starting on http://localhost:{PORT}")
    print(f"\n📝 Instructions:")
    print(f"   1. Make sure 'search_engine.c' is compiled:")
    print(f"      gcc search_engine.c -o search_engine")
    print(f"   2. Place 'index.html' in this directory")
    print(f"   3. Open browser to: http://localhost:{PORT}")
    print(f"\n⚡ The server will:")
    print(f"   - Serve the HTML frontend")
    print(f"   - Simulate C backend operations")
    print(f"   - Handle API requests from the frontend")
    print(f"\n💡 Press Ctrl+C to stop the server\n")
    print("=" * 60 + "\n")
    
    try:
        server = HTTPServer(('localhost', PORT), BridgeHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped by user")
        print("Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

if __name__ == '__main__':
    main()