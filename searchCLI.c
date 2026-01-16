/*
 * Search Engine CLI - JSON Interface
 * Wrapper for searchEngine.c to interface with Python backend
 *
 * Usage:
 *   searchCLI index <filename>
 *   searchCLI freq <word>
 *   searchCLI search <keyword>
 *   searchCLI prefix <prefix>
 *   searchCLI index_text <name> <text_content>
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ALPHABET_SIZE 26
#define HASH_SIZE 1000
#define MAX_WORD_LEN 100
#define MAX_LINE_LEN 4096
#define MAX_TEXT_LEN 65536

/* ==================== DATA STRUCTURES ==================== */

typedef struct DocNode {
  int doc_id;
  int frequency;
  struct DocNode *next;
} DocNode;

typedef struct TrieNode {
  struct TrieNode *children[ALPHABET_SIZE];
  int is_end;
  DocNode *doc_list;
  int total_freq;
} TrieNode;

typedef struct HashEntry {
  char *word;
  TrieNode *trie_node;
  struct HashEntry *next;
} HashEntry;

typedef struct Document {
  int id;
  char *filename;
  int word_count;
  struct Document *next;
} Document;

typedef struct SearchEngine {
  TrieNode *trie_root;
  HashEntry *hash_table[HASH_SIZE];
  Document *documents;
  int doc_count;
} SearchEngine;

/* Global engine instance */
SearchEngine *g_engine = NULL;

/* ==================== UTILITY FUNCTIONS ==================== */

unsigned long hash_func(const char *str) {
  unsigned long hash = 5381;
  int c;
  while ((c = *str++))
    hash = ((hash << 5) + hash) + c;
  return hash % HASH_SIZE;
}

void normalize_word(char *word) {
  char *src = word, *dst = word;
  while (*src) {
    if (isalpha(*src))
      *dst++ = tolower(*src);
    src++;
  }
  *dst = '\0';
}

/* ==================== TRIE OPERATIONS ==================== */

TrieNode *create_trie_node() {
  TrieNode *node = (TrieNode *)calloc(1, sizeof(TrieNode));
  return node;
}

void add_doc_occurrence(TrieNode *node, int doc_id) {
  DocNode *curr = node->doc_list;
  while (curr) {
    if (curr->doc_id == doc_id) {
      curr->frequency++;
      node->total_freq++;
      return;
    }
    curr = curr->next;
  }
  DocNode *new_node = (DocNode *)malloc(sizeof(DocNode));
  new_node->doc_id = doc_id;
  new_node->frequency = 1;
  new_node->next = node->doc_list;
  node->doc_list = new_node;
  node->total_freq++;
}

TrieNode *trie_insert(TrieNode *root, const char *word, int doc_id) {
  TrieNode *curr = root;
  for (int i = 0; word[i]; i++) {
    int idx = word[i] - 'a';
    if (idx < 0 || idx >= ALPHABET_SIZE)
      continue;
    if (!curr->children[idx])
      curr->children[idx] = create_trie_node();
    curr = curr->children[idx];
  }
  curr->is_end = 1;
  add_doc_occurrence(curr, doc_id);
  return curr;
}

TrieNode *trie_search(TrieNode *root, const char *word) {
  TrieNode *curr = root;
  for (int i = 0; word[i]; i++) {
    int idx = word[i] - 'a';
    if (idx < 0 || idx >= ALPHABET_SIZE)
      return NULL;
    if (!curr->children[idx])
      return NULL;
    curr = curr->children[idx];
  }
  return curr->is_end ? curr : NULL;
}

/* ==================== HASH TABLE OPERATIONS ==================== */

void hash_insert(SearchEngine *engine, const char *word, TrieNode *trie_node) {
  unsigned long idx = hash_func(word);
  HashEntry *curr = engine->hash_table[idx];
  while (curr) {
    if (strcmp(curr->word, word) == 0)
      return;
    curr = curr->next;
  }
  HashEntry *entry = (HashEntry *)malloc(sizeof(HashEntry));
  entry->word = strdup(word);
  entry->trie_node = trie_node;
  entry->next = engine->hash_table[idx];
  engine->hash_table[idx] = entry;
}

TrieNode *hash_search(SearchEngine *engine, const char *word) {
  unsigned long idx = hash_func(word);
  HashEntry *curr = engine->hash_table[idx];
  while (curr) {
    if (strcmp(curr->word, word) == 0)
      return curr->trie_node;
    curr = curr->next;
  }
  return NULL;
}

/* ==================== SEARCH ENGINE ==================== */

SearchEngine *create_search_engine() {
  SearchEngine *engine = (SearchEngine *)calloc(1, sizeof(SearchEngine));
  engine->trie_root = create_trie_node();
  return engine;
}

void add_document(SearchEngine *engine, const char *filename) {
  Document *doc = (Document *)malloc(sizeof(Document));
  doc->id = engine->doc_count++;
  doc->filename = strdup(filename);
  doc->word_count = 0;
  doc->next = engine->documents;
  engine->documents = doc;
}

Document *get_document(SearchEngine *engine, int doc_id) {
  Document *curr = engine->documents;
  while (curr) {
    if (curr->id == doc_id)
      return curr;
    curr = curr->next;
  }
  return NULL;
}

void index_word(SearchEngine *engine, const char *word, int doc_id) {
  char normalized[MAX_WORD_LEN];
  strncpy(normalized, word, MAX_WORD_LEN - 1);
  normalized[MAX_WORD_LEN - 1] = '\0';
  normalize_word(normalized);
  if (strlen(normalized) < 2)
    return;
  TrieNode *node = trie_insert(engine->trie_root, normalized, doc_id);
  hash_insert(engine, normalized, node);
}

int index_text(SearchEngine *engine, const char *name, const char *text) {
  add_document(engine, name);
  int doc_id = engine->doc_count - 1;

  char *text_copy = strdup(text);
  char *token = strtok(text_copy, " \t\n\r.,;:!?\"'()[]{}");
  int word_count = 0;

  while (token) {
    index_word(engine, token, doc_id);
    word_count++;
    token = strtok(NULL, " \t\n\r.,;:!?\"'()[]{}");
  }

  Document *doc = get_document(engine, doc_id);
  if (doc)
    doc->word_count = word_count;

  free(text_copy);
  return doc_id;
}

/* ==================== JSON OUTPUT FUNCTIONS ==================== */

void json_escape(const char *str, char *out, int max_len) {
  int j = 0;
  for (int i = 0; str[i] && j < max_len - 6; i++) {
    unsigned char c = (unsigned char)str[i];
    if (c == '"') {
      out[j++] = '\\';
      out[j++] = '"';
    } else if (c == '\\') {
      out[j++] = '\\';
      out[j++] = '\\';
    } else if (c == '\n') {
      out[j++] = '\\';
      out[j++] = 'n';
    } else if (c == '\r') {
      out[j++] = '\\';
      out[j++] = 'r';
    } else if (c == '\t') {
      out[j++] = '\\';
      out[j++] = 't';
    } else if (c < 32) {
      // Skip other control characters
      continue;
    } else {
      out[j++] = c;
    }
  }
  out[j] = '\0';
}

void output_index_result(SearchEngine *engine, int doc_id) {
  Document *doc = get_document(engine, doc_id);
  printf(
      "{\"success\":true,\"doc_id\":%d,\"filename\":\"%s\",\"word_count\":%d}",
      doc_id, doc ? doc->filename : "unknown", doc ? doc->word_count : 0);
}

void output_freq_result(SearchEngine *engine, const char *word) {
  char normalized[MAX_WORD_LEN];
  strncpy(normalized, word, MAX_WORD_LEN - 1);
  normalize_word(normalized);

  TrieNode *node = hash_search(engine, normalized);

  if (!node) {
    printf("{\"success\":true,\"word\":\"%s\",\"found\":false,\"total_freq\":0,"
           "\"documents\":[]}",
           normalized);
    return;
  }

  printf("{\"success\":true,\"word\":\"%s\",\"found\":true,\"total_freq\":%d,"
         "\"documents\":[",
         normalized, node->total_freq);

  DocNode *doc = node->doc_list;
  int first = 1;
  while (doc) {
    Document *doc_info = get_document(engine, doc->doc_id);
    if (!first)
      printf(",");
    printf("{\"doc_id\":%d,\"filename\":\"%s\",\"frequency\":%d}", doc->doc_id,
           doc_info ? doc_info->filename : "unknown", doc->frequency);
    first = 0;
    doc = doc->next;
  }
  printf("]}");
}

void output_search_result(SearchEngine *engine, const char *keyword) {
  char normalized[MAX_WORD_LEN];
  strncpy(normalized, keyword, MAX_WORD_LEN - 1);
  normalize_word(normalized);

  TrieNode *node = hash_search(engine, normalized);

  if (!node) {
    printf(
        "{\"success\":true,\"keyword\":\"%s\",\"found\":false,\"results\":[]}",
        normalized);
    return;
  }

  printf("{\"success\":true,\"keyword\":\"%s\",\"found\":true,\"total_freq\":%"
         "d,\"results\":[",
         normalized, node->total_freq);

  DocNode *doc = node->doc_list;
  int first = 1;
  while (doc) {
    Document *doc_info = get_document(engine, doc->doc_id);
    if (!first)
      printf(",");
    printf("{\"doc_id\":%d,\"filename\":\"%s\",\"frequency\":%d,\"word_count\":"
           "%d}",
           doc->doc_id, doc_info ? doc_info->filename : "unknown",
           doc->frequency, doc_info ? doc_info->word_count : 0);
    first = 0;
    doc = doc->next;
  }
  printf("]}");
}

/* Prefix search with JSON output */
typedef struct {
  char words[100][MAX_WORD_LEN];
  int freqs[100];
  int count;
} PrefixResults;

void collect_prefix_words(TrieNode *node, char *prefix, int len,
                          PrefixResults *results) {
  if (!node || results->count >= 100)
    return;

  if (node->is_end) {
    prefix[len] = '\0';
    strcpy(results->words[results->count], prefix);
    results->freqs[results->count] = node->total_freq;
    results->count++;
  }

  for (int i = 0; i < ALPHABET_SIZE && results->count < 100; i++) {
    if (node->children[i]) {
      prefix[len] = 'a' + i;
      collect_prefix_words(node->children[i], prefix, len + 1, results);
    }
  }
}

void output_prefix_result(SearchEngine *engine, const char *prefix) {
  char normalized[MAX_WORD_LEN];
  strncpy(normalized, prefix, MAX_WORD_LEN - 1);
  normalize_word(normalized);

  TrieNode *curr = engine->trie_root;
  for (int i = 0; normalized[i]; i++) {
    int idx = normalized[i] - 'a';
    if (idx < 0 || idx >= ALPHABET_SIZE || !curr->children[idx]) {
      printf(
          "{\"success\":true,\"prefix\":\"%s\",\"found\":false,\"words\":[]}",
          normalized);
      return;
    }
    curr = curr->children[idx];
  }

  PrefixResults results = {0};
  char buffer[MAX_WORD_LEN];
  strcpy(buffer, normalized);
  collect_prefix_words(curr, buffer, strlen(normalized), &results);

  printf("{\"success\":true,\"prefix\":\"%s\",\"found\":true,\"words\":[",
         normalized);
  for (int i = 0; i < results.count; i++) {
    if (i > 0)
      printf(",");
    printf("{\"word\":\"%s\",\"frequency\":%d}", results.words[i],
           results.freqs[i]);
  }
  printf("]}");
}

/* ==================== REPLACE ALL FEATURE ==================== */

// Replace all occurrences of a word in text
void output_replace_result(const char *text, const char *find_word,
                           const char *replace_word) {
  char normalized_find[MAX_WORD_LEN];
  strncpy(normalized_find, find_word, MAX_WORD_LEN - 1);
  normalized_find[MAX_WORD_LEN - 1] = '\0';
  normalize_word(normalized_find);

  if (strlen(normalized_find) < 2) {
    printf("{\"success\":false,\"error\":\"Search word too short\"}");
    return;
  }

  // Count occurrences and build modified text
  char modified_text[MAX_TEXT_LEN] = "";
  char *text_copy = strdup(text);
  char *current = text_copy;
  char word_buffer[MAX_WORD_LEN];
  int occurrences = 0;
  int mod_pos = 0;

  while (*current && mod_pos < MAX_TEXT_LEN - MAX_WORD_LEN) {
    // Check if we're at a word boundary
    if (isalpha(*current)) {
      // Extract word
      int word_len = 0;
      char *word_start = current;
      while (isalpha(*current) && word_len < MAX_WORD_LEN - 1) {
        word_buffer[word_len++] = *current++;
      }
      word_buffer[word_len] = '\0';

      // Normalize and compare
      char normalized_word[MAX_WORD_LEN];
      strncpy(normalized_word, word_buffer, MAX_WORD_LEN);
      normalize_word(normalized_word);

      if (strcmp(normalized_word, normalized_find) == 0) {
        // Replace with new word
        occurrences++;
        int replace_len = strlen(replace_word);
        if (mod_pos + replace_len < MAX_TEXT_LEN) {
          strcpy(modified_text + mod_pos, replace_word);
          mod_pos += replace_len;
        }
      } else {
        // Keep original word
        if (mod_pos + word_len < MAX_TEXT_LEN) {
          strncpy(modified_text + mod_pos, word_start, word_len);
          mod_pos += word_len;
        }
      }
    } else {
      // Copy non-alpha characters as-is
      modified_text[mod_pos++] = *current++;
    }
  }
  modified_text[mod_pos] = '\0';

  free(text_copy);

  // Escape the modified text for JSON
  char escaped_text[MAX_TEXT_LEN * 2];
  json_escape(modified_text, escaped_text, sizeof(escaped_text));

  printf("{\"success\":true,\"original_word\":\"%s\",\"replacement_word\":\"%s"
         "\",\"occurrences_replaced\":%d,\"modified_text\":\"%s\"}",
         normalized_find, replace_word, occurrences, escaped_text);
}

/* ==================== TOP K WORDS FEATURE ==================== */

typedef struct {
  char word[MAX_WORD_LEN];
  int frequency;
} WordFreq;

// Collect word frequencies from hash table
void collect_word_frequencies(SearchEngine *engine, WordFreq *words, int *count,
                              int max_words) {
  *count = 0;
  for (int i = 0; i < HASH_SIZE && *count < max_words; i++) {
    HashEntry *curr = engine->hash_table[i];
    while (curr && *count < max_words) {
      strncpy(words[*count].word, curr->word, MAX_WORD_LEN - 1);
      words[*count].frequency = curr->trie_node->total_freq;
      (*count)++;
      curr = curr->next;
    }
  }
}

// Compare function for sorting (descending by frequency)
int compare_word_freq(const void *a, const void *b) {
  const WordFreq *wa = (const WordFreq *)a;
  const WordFreq *wb = (const WordFreq *)b;
  return wb->frequency - wa->frequency;
}

void output_topk_result(SearchEngine *engine, int k) {
  WordFreq words[1000];
  int count = 0;

  collect_word_frequencies(engine, words, &count, 1000);

  // Sort by frequency descending
  qsort(words, count, sizeof(WordFreq), compare_word_freq);

  // Output top K
  int output_count = (k < count) ? k : count;

  printf("{\"success\":true,\"k\":%d,\"total_unique_words\":%d,\"top_words\":[",
         k, count);

  for (int i = 0; i < output_count; i++) {
    if (i > 0)
      printf(",");
    printf("{\"word\":\"%s\",\"frequency\":%d}", words[i].word,
           words[i].frequency);
  }
  printf("]}");
}

/* ==================== MAIN ==================== */

int main(int argc, char *argv[]) {
  if (argc < 2) {
    printf(
        "{\"success\":false,\"error\":\"Usage: searchCLI <command> <args>\"}");
    return 1;
  }

  g_engine = create_search_engine();

  const char *cmd = argv[1];

  if (strcmp(cmd, "index_text") == 0 && argc >= 4) {
    // index_text <name> <text_content>
    const char *name = argv[2];

    // Combine remaining args as text (handles spaces)
    char text[MAX_TEXT_LEN] = "";
    for (int i = 3; i < argc; i++) {
      if (i > 3)
        strcat(text, " ");
      strncat(text, argv[i], MAX_TEXT_LEN - strlen(text) - 1);
    }

    int doc_id = index_text(g_engine, name, text);
    output_index_result(g_engine, doc_id);
  } else if (strcmp(cmd, "freq") == 0 && argc >= 3) {
    // First we need content to index, read from stdin
    char line[MAX_LINE_LEN];
    char all_text[MAX_TEXT_LEN] = "";
    while (fgets(line, MAX_LINE_LEN, stdin)) {
      strncat(all_text, line, MAX_TEXT_LEN - strlen(all_text) - 1);
    }
    index_text(g_engine, "uploaded_doc", all_text);
    output_freq_result(g_engine, argv[2]);
  } else if (strcmp(cmd, "search") == 0 && argc >= 3) {
    char line[MAX_LINE_LEN];
    char all_text[MAX_TEXT_LEN] = "";
    while (fgets(line, MAX_LINE_LEN, stdin)) {
      strncat(all_text, line, MAX_TEXT_LEN - strlen(all_text) - 1);
    }
    index_text(g_engine, "uploaded_doc", all_text);
    output_search_result(g_engine, argv[2]);
  } else if (strcmp(cmd, "prefix") == 0 && argc >= 3) {
    char line[MAX_LINE_LEN];
    char all_text[MAX_TEXT_LEN] = "";
    while (fgets(line, MAX_LINE_LEN, stdin)) {
      strncat(all_text, line, MAX_TEXT_LEN - strlen(all_text) - 1);
    }
    index_text(g_engine, "uploaded_doc", all_text);
    output_prefix_result(g_engine, argv[2]);
  } else if (strcmp(cmd, "replace") == 0 && argc >= 4) {
    // replace <find_word> <replace_word>
    char line[MAX_LINE_LEN];
    char all_text[MAX_TEXT_LEN] = "";
    while (fgets(line, MAX_LINE_LEN, stdin)) {
      strncat(all_text, line, MAX_TEXT_LEN - strlen(all_text) - 1);
    }
    output_replace_result(all_text, argv[2], argv[3]);
  } else if (strcmp(cmd, "topk") == 0 && argc >= 3) {
    // topk <k>
    char line[MAX_LINE_LEN];
    char all_text[MAX_TEXT_LEN] = "";
    while (fgets(line, MAX_LINE_LEN, stdin)) {
      strncat(all_text, line, MAX_TEXT_LEN - strlen(all_text) - 1);
    }
    int k = atoi(argv[2]);
    if (k <= 0)
      k = 5;
    index_text(g_engine, "uploaded_doc", all_text);
    output_topk_result(g_engine, k);
  } else {
    printf("{\"success\":false,\"error\":\"Unknown command: %s\"}", cmd);
    return 1;
  }

  return 0;
}
