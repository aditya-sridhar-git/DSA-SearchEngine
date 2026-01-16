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
import urllib.request
import urllib.error

# Configuration
PORT = 8080
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:2b"  # Better quality model
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

def load_documents_from_folder():
    """Load all .txt files from documents folder on startup"""
    docs_dir = "documents"
    if not os.path.exists(docs_dir):
        print(f"⚠️  Documents folder not found at '{docs_dir}'")
        return
    
    txt_files = [f for f in os.listdir(docs_dir) if f.endswith('.txt')]
    
    if not txt_files:
        print(f"⚠️  No .txt files found in '{docs_dir}'")
        return
    
    print(f"\n📚 Loading documents from '{docs_dir}' folder...")
    
    for filename in txt_files:
        filepath = os.path.join(docs_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                doc_id = engine_state.add_document(filename, content)
                print(f"  ✓ Indexed: {filename} (ID: {doc_id})")
        except Exception as e:
            print(f"  ✗ Error loading {filename}: {e}")
    
    print(f"\n✅ Loaded {len(engine_state.documents)} documents\n")

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
        elif self.path.startswith('/api/autocomplete?'):
            # Autocomplete suggestions
            self._handle_autocomplete()
        elif self.path == '/api/chats':
            # Get all chat sessions (splay tree)
            self._get_chats()
        else:
            self._set_headers(404)
            self.wfile.write(b'{"error": "Not found"}')
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/index':
            # Index a document
            self._index_document()
        elif self.path == '/api/rag':
            # Query Ollama directly
            self._handle_rag_request()
        elif self.path == '/api/upload':
            # Handle file upload for summarization
            self._handle_upload()
        elif self.path == '/api/analyze':
            # Analyze document using C search engine
            self._handle_analyze()
        elif self.path == '/api/replace':
            # Replace all occurrences using C engine
            self._handle_replace()
        elif self.path == '/api/topk':
            # Get top K words using C engine
            self._handle_topk()
        elif self.path == '/api/chats':
            # Add chat session (splay tree)
            self._add_chat()
        elif self.path == '/api/chats/clear':
            # Clear all chats (splay tree)
            self._clear_chats()
        elif self.path.startswith('/api/chats/'):
            # Update chat session (splay tree access)
            self._access_chat()
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
    
    def _handle_autocomplete(self):
        """Handle autocomplete requests using prefix search"""
        try:
            query_string = self.path.split('?')[1]
            params = {}
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=')
                    params[key] = value
            
            query = params.get('q', '').replace('+', ' ').strip()
            
            if len(query) < 2:
                self._set_headers()
                self.wfile.write(json.dumps({'suggestions': []}).encode())
                return
            
            # Use prefix search to find matching words
            normalized_query = ''.join(c for c in query if c.isalpha()).lower()
            all_words = set()
            
            for doc in engine_state.get_all_documents():
                words = doc['content'].lower().split()
                for word in words:
                    normalized = ''.join(c for c in word if c.isalpha())
                    if normalized.startswith(normalized_query) and len(normalized) >= 2:
                        all_words.add(normalized)
            
            suggestions = sorted(list(all_words))[:10]  # Top 10
            
            self._set_headers()
            self.wfile.write(json.dumps({'suggestions': suggestions}).encode())
            
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
    
    
    def _handle_rag_request(self):
        """Handle RAG search request - simplified to direct Ollama query"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            query = data.get('query', '')
            if not query:
                raise ValueError("Query is required")
            
            # Just send the query directly to Ollama
            answer = self._call_ollama(query)
            
            self._set_headers()
            self.wfile.write(json.dumps({'answer': answer}).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _handle_upload(self):
        """Handle file upload for text extraction and summarization"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            content = data.get('content', '')
            filename = data.get('filename', 'document.txt')
            action = data.get('action', 'summarize')  # 'summarize' or 'extract'
            
            if not content:
                raise ValueError("File content is required")
            
            if action == 'extract':
                # Just return the text content
                self._set_headers()
                self.wfile.write(json.dumps({
                    'result': content,
                    'filename': filename,
                    'wordCount': len(content.split())
                }).encode())
            else:
                # Summarize using Ollama
                prompt = f"Summarize the following text in 2-3 sentences:\n\n{content}"
                summary = self._call_ollama(prompt)
                
                self._set_headers()
                self.wfile.write(json.dumps({
                    'result': summary,
                    'filename': filename,
                    'originalWordCount': len(content.split())
                }).encode())
                
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_analyze(self):
        """Analyze document using C search engine (trie, hash table, linked list)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            content = data.get('content', '')
            action = data.get('action', 'freq')  # 'freq', 'search', or 'prefix'
            query = data.get('query', '')
            
            if not content:
                raise ValueError("Document content is required")
            if not query:
                raise ValueError("Query word is required")
            
            # Path to compiled C executable
            cli_path = os.path.join(os.path.dirname(__file__), 'searchCLI.exe')
            
            if not os.path.exists(cli_path):
                raise ValueError("C search engine not compiled. Run: gcc searchCLI.c -o searchCLI.exe")
            
            # Call C executable with action and query, pass content via stdin
            result = subprocess.run(
                [cli_path, action, query],
                input=content,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise ValueError(f"C engine error: {result.stderr}")
            
            # Parse JSON output from C
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except json.JSONDecodeError as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': f'Invalid C output: {str(e)}'}).encode())
        except subprocess.TimeoutExpired:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': 'Analysis timed out'}).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_replace(self):
        """Handle replace all request using C engine (display only, no file save)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            content = data.get('content', '')
            find_word = data.get('find', '')
            replace_word = data.get('replace', '')
            
            if not content:
                raise ValueError("Document content is required")
            if not find_word:
                raise ValueError("Find word is required")
            if not replace_word:
                raise ValueError("Replace word is required")
            
            cli_path = os.path.join(os.path.dirname(__file__), 'searchCLI.exe')
            
            if not os.path.exists(cli_path):
                raise ValueError("C search engine not compiled")
            
            result = subprocess.run(
                [cli_path, 'replace', find_word, replace_word],
                input=content,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_topk(self):
        """Handle top K words request using C engine"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            content = data.get('content', '')
            k = data.get('k', 5)
            
            if not content:
                raise ValueError("Document content is required")
            
            cli_path = os.path.join(os.path.dirname(__file__), 'searchCLI.exe')
            
            if not os.path.exists(cli_path):
                raise ValueError("C search engine not compiled")
            
            result = subprocess.run(
                [cli_path, 'topk', str(k)],
                input=content,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _get_chats(self):
        """Get all chat sessions from splay tree"""
        try:
            splay_path = os.path.join(os.path.dirname(__file__), 'splayTree.exe')
            
            if not os.path.exists(splay_path):
                # Return empty list if splay tree not compiled
                self._set_headers()
                self.wfile.write(json.dumps({'success': True, 'count': 0, 'chats': []}).encode())
                return
            
            result = subprocess.run(
                [splay_path, 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _add_chat(self):
        """Add chat session to splay tree"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            chat_id = data.get('id', '')
            title = data.get('title', '')
            timestamp = data.get('timestamp', '')
            
            if not chat_id or not title:
                raise ValueError("Chat ID and title are required")
            
            splay_path = os.path.join(os.path.dirname(__file__), 'splayTree.exe')
            
            if not os.path.exists(splay_path):
                raise ValueError("Splay tree not compiled")
            
            args = [splay_path, 'add', chat_id, title]
            if timestamp:
                args.append(str(timestamp))
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _access_chat(self):
        """Access chat session (triggers splay) or delete chat"""
        try:
            # Extract chat_id from path: /api/chats/<chat_id>
            chat_id = self.path.split('/api/chats/')[-1]
            
            splay_path = os.path.join(os.path.dirname(__file__), 'splayTree.exe')
            
            if not os.path.exists(splay_path):
                raise ValueError("Splay tree not compiled")
            
            result = subprocess.run(
                [splay_path, 'access', chat_id],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _clear_chats(self):
        """Clear all chat sessions from splay tree"""
        try:
            splay_path = os.path.join(os.path.dirname(__file__), 'splayTree.exe')
            
            if not os.path.exists(splay_path):
                self._set_headers()
                self.wfile.write(json.dumps({'success': True, 'message': 'No splay tree to clear'}).encode())
                return
            
            result = subprocess.run(
                [splay_path, 'clear'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            c_result = json.loads(result.stdout)
            
            self._set_headers()
            self.wfile.write(json.dumps(c_result).encode())
            
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())


    def _call_ollama(self, prompt):
        """Call local Ollama API"""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            
            req = urllib.request.Request(
                OLLAMA_API_URL, 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', 'No response from Ollama')
                
        except urllib.error.URLError as e:
            return f"Error connecting to Ollama: {e}. Is Ollama running?"
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    """Start the bridge server"""
    print("=" * 60)
    print("  Mini Google - RAG Search Engine")
    print("=" * 60)
    print(f"\n🚀 Server starting on http://localhost:{PORT}")
    
    # Load documents from folder
    load_documents_from_folder()
    
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