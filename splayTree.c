/*
 * Splay Tree Implementation for Chat History Management
 * Data Structure: Self-balancing BST with splay operation
 * Features: Add, access, delete, list chat sessions
 * Persistence: JSON file storage
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_ID_LEN 64
#define MAX_TITLE_LEN 256
#define MAX_CHATS 100
#define HISTORY_FILE "chat_history.json"

/* ==================== DATA STRUCTURES ==================== */

// Splay Tree Node for Chat History
typedef struct ChatNode {
    char chat_id[MAX_ID_LEN];
    char title[MAX_TITLE_LEN];
    long timestamp;
    struct ChatNode *left;
    struct ChatNode *right;
    struct ChatNode *parent;
} ChatNode;

// Splay Tree
typedef struct SplayTree {
    ChatNode *root;
    int size;
} SplayTree;

/* ==================== SPLAY TREE OPERATIONS ==================== */

// Create new chat node
ChatNode* create_node(const char *id, const char *title, long timestamp) {
    ChatNode *node = (ChatNode*)calloc(1, sizeof(ChatNode));
    strncpy(node->chat_id, id, MAX_ID_LEN - 1);
    strncpy(node->title, title, MAX_TITLE_LEN - 1);
    node->timestamp = timestamp;
    node->left = node->right = node->parent = NULL;
    return node;
}

// Create splay tree
SplayTree* create_splay_tree() {
    SplayTree *tree = (SplayTree*)calloc(1, sizeof(SplayTree));
    return tree;
}

// Right rotation (zig)
void rotate_right(SplayTree *tree, ChatNode *x) {
    ChatNode *y = x->left;
    if (!y) return;
    
    x->left = y->right;
    if (y->right) y->right->parent = x;
    
    y->parent = x->parent;
    if (!x->parent) {
        tree->root = y;
    } else if (x == x->parent->left) {
        x->parent->left = y;
    } else {
        x->parent->right = y;
    }
    
    y->right = x;
    x->parent = y;
}

// Left rotation (zag)
void rotate_left(SplayTree *tree, ChatNode *x) {
    ChatNode *y = x->right;
    if (!y) return;
    
    x->right = y->left;
    if (y->left) y->left->parent = x;
    
    y->parent = x->parent;
    if (!x->parent) {
        tree->root = y;
    } else if (x == x->parent->left) {
        x->parent->left = y;
    } else {
        x->parent->right = y;
    }
    
    y->left = x;
    x->parent = y;
}

// Splay operation - moves node to root
void splay(SplayTree *tree, ChatNode *x) {
    if (!x) return;
    
    while (x->parent) {
        ChatNode *p = x->parent;
        ChatNode *g = p->parent;
        
        if (!g) {
            // Zig step (parent is root)
            if (x == p->left) {
                rotate_right(tree, p);
            } else {
                rotate_left(tree, p);
            }
        } else if (x == p->left && p == g->left) {
            // Zig-zig (left-left)
            rotate_right(tree, g);
            rotate_right(tree, p);
        } else if (x == p->right && p == g->right) {
            // Zig-zig (right-right)
            rotate_left(tree, g);
            rotate_left(tree, p);
        } else if (x == p->right && p == g->left) {
            // Zig-zag (left-right)
            rotate_left(tree, p);
            rotate_right(tree, g);
        } else {
            // Zig-zag (right-left)
            rotate_right(tree, p);
            rotate_left(tree, g);
        }
    }
}

// Find node by chat_id
ChatNode* find_node(SplayTree *tree, const char *chat_id) {
    ChatNode *curr = tree->root;
    while (curr) {
        int cmp = strcmp(chat_id, curr->chat_id);
        if (cmp == 0) return curr;
        else if (cmp < 0) curr = curr->left;
        else curr = curr->right;
    }
    return NULL;
}

// Insert new chat (sorted by chat_id for BST property)
ChatNode* insert_chat(SplayTree *tree, const char *id, const char *title, long timestamp) {
    ChatNode *new_node = create_node(id, title, timestamp);
    
    if (!tree->root) {
        tree->root = new_node;
        tree->size = 1;
        return new_node;
    }
    
    ChatNode *curr = tree->root;
    ChatNode *parent = NULL;
    
    while (curr) {
        parent = curr;
        int cmp = strcmp(id, curr->chat_id);
        if (cmp == 0) {
            // Update existing
            strncpy(curr->title, title, MAX_TITLE_LEN - 1);
            curr->timestamp = timestamp;
            free(new_node);
            splay(tree, curr);
            return curr;
        } else if (cmp < 0) {
            curr = curr->left;
        } else {
            curr = curr->right;
        }
    }
    
    new_node->parent = parent;
    if (strcmp(id, parent->chat_id) < 0) {
        parent->left = new_node;
    } else {
        parent->right = new_node;
    }
    
    tree->size++;
    splay(tree, new_node);
    return new_node;
}

// Access chat by ID (splays to root)
ChatNode* access_chat(SplayTree *tree, const char *chat_id) {
    ChatNode *node = find_node(tree, chat_id);
    if (node) {
        splay(tree, node);
    }
    return node;
}

// Find minimum node in subtree
ChatNode* find_min(ChatNode *node) {
    while (node && node->left) {
        node = node->left;
    }
    return node;
}

// Delete chat by ID
int delete_chat(SplayTree *tree, const char *chat_id) {
    ChatNode *node = find_node(tree, chat_id);
    if (!node) return 0;
    
    splay(tree, node);
    
    if (!node->left) {
        tree->root = node->right;
        if (tree->root) tree->root->parent = NULL;
    } else if (!node->right) {
        tree->root = node->left;
        if (tree->root) tree->root->parent = NULL;
    } else {
        ChatNode *left_subtree = node->left;
        left_subtree->parent = NULL;
        
        ChatNode *right_subtree = node->right;
        right_subtree->parent = NULL;
        
        // Find max in left subtree
        ChatNode *max_left = left_subtree;
        while (max_left->right) {
            max_left = max_left->right;
        }
        
        tree->root = left_subtree;
        splay(tree, max_left);
        
        tree->root->right = right_subtree;
        right_subtree->parent = tree->root;
    }
    
    free(node);
    tree->size--;
    return 1;
}

// Clear all chats
void clear_tree(ChatNode *node) {
    if (!node) return;
    clear_tree(node->left);
    clear_tree(node->right);
    free(node);
}

void clear_all(SplayTree *tree) {
    clear_tree(tree->root);
    tree->root = NULL;
    tree->size = 0;
}

/* ==================== TRAVERSAL & COLLECTION ==================== */

typedef struct {
    ChatNode *nodes[MAX_CHATS];
    int count;
} ChatList;

// Collect all nodes via inorder traversal
void collect_inorder(ChatNode *node, ChatList *list) {
    if (!node || list->count >= MAX_CHATS) return;
    collect_inorder(node->left, list);
    if (list->count < MAX_CHATS) {
        list->nodes[list->count++] = node;
    }
    collect_inorder(node->right, list);
}

// Compare function for sorting by timestamp (descending - newest first)
int compare_by_timestamp(const void *a, const void *b) {
    ChatNode *na = *(ChatNode**)a;
    ChatNode *nb = *(ChatNode**)b;
    if (nb->timestamp > na->timestamp) return 1;
    if (nb->timestamp < na->timestamp) return -1;
    return 0;
}

/* ==================== JSON PERSISTENCE ==================== */

// Escape string for JSON
void json_escape(const char *str, char *out, int max_len) {
    int j = 0;
    for (int i = 0; str[i] && j < max_len - 2; i++) {
        if (str[i] == '"' || str[i] == '\\') {
            out[j++] = '\\';
        }
        if (str[i] == '\n') {
            out[j++] = '\\';
            out[j++] = 'n';
        } else if (str[i] == '\r') {
            // skip
        } else {
            out[j++] = str[i];
        }
    }
    out[j] = '\0';
}

// Save tree to JSON file
void save_to_file(SplayTree *tree) {
    FILE *f = fopen(HISTORY_FILE, "w");
    if (!f) return;
    
    ChatList list = {0};
    collect_inorder(tree->root, &list);
    
    fprintf(f, "{\"chats\":[");
    for (int i = 0; i < list.count; i++) {
        char escaped_title[MAX_TITLE_LEN * 2];
        json_escape(list.nodes[i]->title, escaped_title, sizeof(escaped_title));
        
        if (i > 0) fprintf(f, ",");
        fprintf(f, "{\"id\":\"%s\",\"title\":\"%s\",\"timestamp\":%ld}",
                list.nodes[i]->chat_id, escaped_title, list.nodes[i]->timestamp);
    }
    fprintf(f, "]}");
    fclose(f);
}

// Simple JSON parser for loading
void load_from_file(SplayTree *tree) {
    FILE *f = fopen(HISTORY_FILE, "r");
    if (!f) return;
    
    char buffer[65536];
    size_t len = fread(buffer, 1, sizeof(buffer) - 1, f);
    buffer[len] = '\0';
    fclose(f);
    
    // Simple parsing - find each chat object
    char *ptr = buffer;
    while ((ptr = strstr(ptr, "\"id\":\"")) != NULL) {
        ptr += 6;
        
        char id[MAX_ID_LEN] = {0};
        int i = 0;
        while (*ptr && *ptr != '"' && i < MAX_ID_LEN - 1) {
            id[i++] = *ptr++;
        }
        
        char *title_ptr = strstr(ptr, "\"title\":\"");
        if (!title_ptr) break;
        title_ptr += 9;
        
        char title[MAX_TITLE_LEN] = {0};
        i = 0;
        while (*title_ptr && i < MAX_TITLE_LEN - 1) {
            if (*title_ptr == '\\' && *(title_ptr + 1) == '"') {
                title[i++] = '"';
                title_ptr += 2;
            } else if (*title_ptr == '\\' && *(title_ptr + 1) == 'n') {
                title[i++] = '\n';
                title_ptr += 2;
            } else if (*title_ptr == '"') {
                break;
            } else {
                title[i++] = *title_ptr++;
            }
        }
        
        char *ts_ptr = strstr(ptr, "\"timestamp\":");
        if (!ts_ptr) break;
        ts_ptr += 12;
        long timestamp = atol(ts_ptr);
        
        insert_chat(tree, id, title, timestamp);
        ptr = ts_ptr;
    }
}

/* ==================== JSON OUTPUT ==================== */

void output_list(SplayTree *tree) {
    ChatList list = {0};
    collect_inorder(tree->root, &list);
    
    // Sort by timestamp descending
    qsort(list.nodes, list.count, sizeof(ChatNode*), compare_by_timestamp);
    
    printf("{\"success\":true,\"count\":%d,\"chats\":[", list.count);
    for (int i = 0; i < list.count; i++) {
        char escaped_title[MAX_TITLE_LEN * 2];
        json_escape(list.nodes[i]->title, escaped_title, sizeof(escaped_title));
        
        if (i > 0) printf(",");
        printf("{\"id\":\"%s\",\"title\":\"%s\",\"timestamp\":%ld}",
               list.nodes[i]->chat_id, escaped_title, list.nodes[i]->timestamp);
    }
    printf("]}");
}

void output_chat(ChatNode *node) {
    if (!node) {
        printf("{\"success\":false,\"error\":\"Chat not found\"}");
        return;
    }
    char escaped_title[MAX_TITLE_LEN * 2];
    json_escape(node->title, escaped_title, sizeof(escaped_title));
    printf("{\"success\":true,\"chat\":{\"id\":\"%s\",\"title\":\"%s\",\"timestamp\":%ld}}",
           node->chat_id, escaped_title, node->timestamp);
}

void output_success(const char *message) {
    printf("{\"success\":true,\"message\":\"%s\"}", message);
}

void output_error(const char *error) {
    printf("{\"success\":false,\"error\":\"%s\"}", error);
}

/* ==================== MAIN ==================== */

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("{\"success\":false,\"error\":\"Usage: splayTree <command> [args]\"}");
        return 1;
    }
    
    SplayTree *tree = create_splay_tree();
    load_from_file(tree);
    
    const char *cmd = argv[1];
    
    if (strcmp(cmd, "add") == 0 && argc >= 4) {
        // add <chat_id> <title> [timestamp]
        const char *id = argv[2];
        const char *title = argv[3];
        long timestamp = (argc >= 5) ? atol(argv[4]) : time(NULL);
        
        ChatNode *node = insert_chat(tree, id, title, timestamp);
        save_to_file(tree);
        output_chat(node);
        
    } else if (strcmp(cmd, "access") == 0 && argc >= 3) {
        // access <chat_id>
        ChatNode *node = access_chat(tree, argv[2]);
        save_to_file(tree);
        output_chat(node);
        
    } else if (strcmp(cmd, "list") == 0) {
        // list
        output_list(tree);
        
    } else if (strcmp(cmd, "delete") == 0 && argc >= 3) {
        // delete <chat_id>
        if (delete_chat(tree, argv[2])) {
            save_to_file(tree);
            output_success("Chat deleted");
        } else {
            output_error("Chat not found");
        }
        
    } else if (strcmp(cmd, "clear") == 0) {
        // clear
        clear_all(tree);
        save_to_file(tree);
        output_success("All chats cleared");
        
    } else {
        output_error("Unknown command or missing arguments");
    }
    
    // Cleanup
    clear_all(tree);
    free(tree);
    
    return 0;
}
