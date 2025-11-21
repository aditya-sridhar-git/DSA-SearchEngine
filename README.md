# MiniSearchEngine
A simple project that implements a mini search engine in C using linked lists, hash table and tries. It indexes words from a set of documents, implements word frequency count and keyword search. 

Linked Lists are used in two places: storing document occurrences for each word (which document contains it and how many times), and chaining in the hash table to handle collisions.

Trie provides efficient prefix-based searching and autocomplete functionality. Each path from root to a node marked as is_end represents an indexed word, and each end node stores a linked list of documents containing that word.

Hash Table enables O(1) average-case lookup for exact keyword searches. It maps words directly to their trie nodes, bypassing the need to traverse the trie for known words.

Key Features
The engine supports document indexing where you can index text from files or strings, with automatic word normalization (lowercase, alphabetic only). Word frequency counting tracks how many times each word appears in each document and calculates term frequency (TF). Keyword search uses the hash table for fast exact matches and displays all documents containing the word with frequency counts. Prefix search uses the trie to find all words starting with a given prefix, which is useful for autocomplete. Multi-keyword search finds documents containing all specified keywords and ranks them by combined frequency score.

How to Use
Compile with gcc search_engine.c -o search_engine and run with ./search_engine. The demo indexes three sample texts and demonstrates all search features.
To index your own files, use index_document(engine, "path/to/file.txt") instead of index_text().

Possible Extensions
You could add an interactive command-line interface with a menu system, implement TF-IDF scoring for better relevance ranking, add phrase searching with quotes, support Boolean operators like OR and NOT, or build a file crawler to index entire directories.
