import React, { useState, useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import './ChatInterface.css';

interface Message {
    id: string;
    text: string;
    sender: 'user' | 'ai';
    timestamp: Date;
}

interface ChatSession {
    id: string;
    title: string;
    messages: Message[];
    createdAt: Date;
}

const API_BASE = 'http://localhost:8080/api';

export const ChatInterface: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [uploadedDoc, setUploadedDoc] = useState<{ name: string, content: string } | null>(null);
    const [showAnalyzeModal, setShowAnalyzeModal] = useState(false);
    const [analyzeQuery, setAnalyzeQuery] = useState('');
    const [replaceWord, setReplaceWord] = useState('');
    const [analyzeAction, setAnalyzeAction] = useState<'freq' | 'search' | 'prefix' | 'replace' | 'topk'>('freq');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Load chat sessions from localStorage on mount AND sync with splay tree
    useEffect(() => {
        const loadChats = async () => {
            // First load from localStorage for messages
            const saved = localStorage.getItem('chatSessions');
            if (saved) {
                const sessions = JSON.parse(saved).map((s: any) => ({
                    ...s,
                    createdAt: new Date(s.createdAt),
                    messages: s.messages.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) }))
                }));
                setChatSessions(sessions);
            }

            // Also try to load from splay tree (for ordering)
            try {
                const response = await fetch(`${API_BASE}/chats`);
                const data = await response.json();
                if (data.success && data.chats?.length > 0) {
                    // Merge splay tree order with localStorage messages
                    const savedData = saved ? JSON.parse(saved) : [];
                    const orderedSessions = data.chats.map((chat: any) => {
                        const localChat = savedData.find((s: any) => s.id === chat.id);
                        if (localChat) {
                            return {
                                ...localChat,
                                createdAt: new Date(chat.timestamp * 1000),
                                messages: localChat.messages.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) }))
                            };
                        }
                        return {
                            id: chat.id,
                            title: chat.title,
                            messages: [],
                            createdAt: new Date(chat.timestamp * 1000)
                        };
                    });
                    setChatSessions(orderedSessions);
                }
            } catch (e) {
                // Splay tree not available, use localStorage only
                console.log('Splay tree not available, using localStorage');
            }
        };
        loadChats();
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Save chat sessions to localStorage whenever they change
    const saveChatSessions = (sessions: ChatSession[]) => {
        setChatSessions(sessions);
        localStorage.setItem('chatSessions', JSON.stringify(sessions));
    };

    // Sync chat to splay tree backend
    const syncToSplayTree = async (chatId: string, title: string, timestamp?: number) => {
        try {
            await fetch(`${API_BASE}/chats`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: chatId,
                    title: title,
                    timestamp: timestamp || Math.floor(Date.now() / 1000)
                })
            });
        } catch (e) {
            console.log('Failed to sync to splay tree');
        }
    };

    // Notify splay tree of access (triggers splay operation) and reload list
    const accessSplayTree = async (chatId: string) => {
        try {
            await fetch(`${API_BASE}/chats/${chatId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            // Reload chat list from splay tree to get new order
            const response = await fetch(`${API_BASE}/chats`);
            const data = await response.json();
            if (data.success && data.chats?.length > 0) {
                const savedData = JSON.parse(localStorage.getItem('chatSessions') || '[]');
                const orderedSessions = data.chats.map((chat: any) => {
                    const localChat = savedData.find((s: any) => s.id === chat.id);
                    if (localChat) {
                        return {
                            ...localChat,
                            createdAt: new Date(chat.timestamp * 1000),
                            messages: localChat.messages.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) }))
                        };
                    }
                    return {
                        id: chat.id,
                        title: chat.title,
                        messages: [],
                        createdAt: new Date(chat.timestamp * 1000)
                    };
                });
                setChatSessions(orderedSessions);
            }
        } catch (e) {
            console.log('Failed to access splay tree');
        }
    };

    // Create a new chat session and return the new sessions array
    const createNewChat = (firstMessage: Message): { chatId: string, newSessions: ChatSession[] } => {
        const chatId = Date.now().toString();
        const title = firstMessage.text.length > 30
            ? firstMessage.text.substring(0, 30) + '...'
            : firstMessage.text;
        const newChat: ChatSession = {
            id: chatId,
            title,
            messages: [firstMessage],
            createdAt: new Date(),
        };
        const newSessions = [newChat, ...chatSessions].slice(0, 20); // Keep max 20 chats
        saveChatSessions(newSessions);
        setCurrentChatId(chatId);

        // Sync to splay tree
        syncToSplayTree(chatId, title);

        return { chatId, newSessions };
    };

    // Create a new chat with document name as title
    const createChatFromDocument = (docName: string, firstMessage: Message): { chatId: string, newSessions: ChatSession[] } => {
        const chatId = Date.now().toString();
        const title = docName.replace('.txt', ''); // Use document name as title
        const newChat: ChatSession = {
            id: chatId,
            title,
            messages: [firstMessage],
            createdAt: new Date(),
        };
        const newSessions = [newChat, ...chatSessions].slice(0, 20);
        saveChatSessions(newSessions);
        setCurrentChatId(chatId);
        syncToSplayTree(chatId, title);
        return { chatId, newSessions };
    };


    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            text: input,
            sender: 'user',
            timestamp: new Date(),
        };

        const newMessages = [...messages, userMessage];
        setMessages(newMessages);

        // If no current chat, create one (first message auto-creates chat)
        let chatId = currentChatId;
        let currentSessions = chatSessions;

        if (!chatId) {
            const result = createNewChat(userMessage);
            chatId = result.chatId;
            currentSessions = result.newSessions;
        } else {
            // Update existing chat with new message
            currentSessions = chatSessions.map(chat =>
                chat.id === chatId ? { ...chat, messages: newMessages } : chat
            );
            saveChatSessions(currentSessions);
        }

        const query = input;
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE}/rag`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
            });

            const data = await response.json();

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: data.answer || data.error || 'No response',
                sender: 'ai',
                timestamp: new Date(),
            };

            const finalMessages = [...newMessages, aiMessage];
            setMessages(finalMessages);

            // Update the chat session with AI response using functional update
            setChatSessions(prevSessions => {
                const updated = prevSessions.map(chat =>
                    chat.id === chatId ? { ...chat, messages: finalMessages } : chat
                );
                localStorage.setItem('chatSessions', JSON.stringify(updated));
                return updated;
            });
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: 'Failed to connect to server',
                sender: 'ai',
                timestamp: new Date(),
            };
            const finalMessages = [...newMessages, errorMessage];
            setMessages(finalMessages);

            setChatSessions(prevSessions => {
                const updated = prevSessions.map(chat =>
                    chat.id === chatId ? { ...chat, messages: finalMessages } : chat
                );
                localStorage.setItem('chatSessions', JSON.stringify(updated));
                return updated;
            });
        } finally {
            setIsLoading(false);
            inputRef.current?.focus();
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !file.name.endsWith('.txt')) {
            alert('Please upload a .txt file');
            return;
        }

        const content = await file.text();
        setUploadedDoc({ name: file.name, content });
        setShowAnalyzeModal(true);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleAnalyze = async () => {
        if (!uploadedDoc) return;

        // For topk, no query needed. For replace, need both query and replaceWord
        if (analyzeAction === 'replace' && (!analyzeQuery.trim() || !replaceWord.trim())) return;
        if (analyzeAction !== 'topk' && analyzeAction !== 'replace' && !analyzeQuery.trim()) return;

        setShowAnalyzeModal(false);

        const actionLabel = {
            freq: 'Word Frequency',
            search: 'Keyword Search',
            prefix: 'Prefix Search',
            replace: 'Replace All',
            topk: 'Top 5 Words'
        }[analyzeAction];

        const userMessage: Message = {
            id: Date.now().toString(),
            text: analyzeAction === 'topk'
                ? `📄 ${uploadedDoc.name}\n\n📊 ${actionLabel}`
                : analyzeAction === 'replace'
                    ? `📄 ${uploadedDoc.name}\n\n🔄 ${actionLabel}: "${analyzeQuery}" → "${replaceWord}"`
                    : `📄 ${uploadedDoc.name}\n\n🔍 ${actionLabel}: "${analyzeQuery}"`,
            sender: 'user',
            timestamp: new Date(),
        };

        // Create a new chat session using the document name
        if (!currentChatId) {
            createChatFromDocument(uploadedDoc.name, userMessage);
        } else {
            setMessages(prev => [...prev, userMessage]);
        }
        setIsLoading(true);

        try {
            let response;
            let data;

            if (analyzeAction === 'replace') {
                response = await fetch(`${API_BASE}/replace`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: uploadedDoc.content,
                        find: analyzeQuery,
                        replace: replaceWord,
                        filename: uploadedDoc.name
                    }),
                });
                data = await response.json();
            } else if (analyzeAction === 'topk') {
                response = await fetch(`${API_BASE}/topk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: uploadedDoc.content,
                        k: 5
                    }),
                });
                data = await response.json();
            } else {
                response = await fetch(`${API_BASE}/analyze`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: uploadedDoc.content,
                        action: analyzeAction,
                        query: analyzeQuery
                    }),
                });
                data = await response.json();
            }

            let resultText = '';
            if (data.error) {
                resultText = `Error: ${data.error}`;
            } else if (analyzeAction === 'freq') {
                if (data.found) {
                    resultText = `📊 Word Frequency for "${data.word}"\n\n`;
                    resultText += `Total occurrences: ${data.total_freq}\n\n`;
                    resultText += `Document breakdown:\n`;
                    data.documents?.forEach((doc: any) => {
                        resultText += `• ${doc.filename}: ${doc.frequency} times\n`;
                    });
                } else {
                    resultText = `Word "${data.word}" not found in the document.`;
                }
            } else if (analyzeAction === 'search') {
                if (data.found) {
                    resultText = `🔍 Keyword Search: "${data.keyword}"\n\n`;
                    resultText += `Total occurrences: ${data.total_freq}\n\n`;
                    data.results?.forEach((r: any) => {
                        resultText += `• ${r.filename}: ${r.frequency} matches\n`;
                    });
                } else {
                    resultText = `Keyword "${data.keyword}" not found.`;
                }
            } else if (analyzeAction === 'prefix') {
                if (data.found && data.words?.length > 0) {
                    resultText = `🔤 Words with prefix "${data.prefix}":\n\n`;
                    data.words.forEach((w: any) => {
                        resultText += `• ${w.word} (${w.frequency} times)\n`;
                    });
                } else {
                    resultText = `No words found with prefix "${data.prefix}"`;
                }
            } else if (analyzeAction === 'replace') {
                resultText = `🔄 Replace All: "${data.original_word}" → "${data.replacement_word}"\n\n`;
                resultText += `Occurrences replaced: ${data.occurrences_replaced}\n\n`;
                if (data.file_saved) {
                    resultText += `✅ File saved to: documents/${uploadedDoc?.name}\n\n`;
                }
                if (data.occurrences_replaced > 0 && data.modified_text) {
                    // Update the cached document content with the modified text
                    setUploadedDoc(prev => prev ? { ...prev, content: data.modified_text } : null);
                    resultText += `Modified text preview:\n${data.modified_text?.substring(0, 400)}${data.modified_text?.length > 400 ? '...' : ''}`;
                }
            } else if (analyzeAction === 'topk') {
                resultText = `📊 Top ${data.k} Most Frequent Words\n\n`;
                resultText += `Total unique words: ${data.total_unique_words}\n\n`;
                data.top_words?.forEach((w: any, i: number) => {
                    resultText += `${i + 1}. "${w.word}" - ${w.frequency} occurrences\n`;
                });
            }

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: resultText || JSON.stringify(data, null, 2),
                sender: 'ai',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: 'Failed to analyze document',
                sender: 'ai',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
            // Don't clear uploadedDoc after replace - keep the modified content for further operations
            // Only clear for non-replace operations
            if (analyzeAction !== 'replace') {
                setUploadedDoc(null);
            }
            setAnalyzeQuery('');
            setReplaceWord('');
        }
    };


    const handleSummarize = async () => {
        if (!uploadedDoc) return;

        setShowAnalyzeModal(false);

        const userMessage: Message = {
            id: Date.now().toString(),
            text: `📄 Uploaded: ${uploadedDoc.name}\n\nSummarize this document.`,
            sender: 'user',
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: uploadedDoc.content, filename: uploadedDoc.name, action: 'summarize' }),
            });

            const data = await response.json();

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: data.result || data.error || 'No response',
                sender: 'ai',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: 'Failed to process file',
                sender: 'ai',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
            setUploadedDoc(null);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const clearHistory = async () => {
        setChatSessions([]);
        setCurrentChatId(null);
        setMessages([]);
        localStorage.removeItem('chatSessions');
        // Also clear splay tree backend
        try {
            await fetch(`${API_BASE}/chats/clear`, { method: 'POST' });
        } catch (e) {
            console.log('Failed to clear splay tree');
        }
    };

    const newChat = () => {
        setCurrentChatId(null);
        setMessages([]);
    };

    const switchToChat = (chatId: string) => {
        const chat = chatSessions.find(c => c.id === chatId);
        if (chat) {
            setCurrentChatId(chatId);
            setMessages(chat.messages);
            // Trigger splay operation - recently accessed chats bubble up
            accessSplayTree(chatId);
        }
    };

    return (
        <div className="app-layout">
            {/* Analyze Modal */}
            {showAnalyzeModal && uploadedDoc && (
                <div className="modal-overlay">
                    <div className="modal">
                        <h3>📄 {uploadedDoc.name}</h3>
                        <p className="modal-subtitle">Choose an action:</p>

                        <div className="modal-options">
                            <button onClick={handleSummarize} className="modal-btn summarize">
                                ✨ Summarize (AI)
                            </button>

                            <div className="modal-divider">— or analyze with C engine —</div>

                            <div className="analyze-options">
                                <select
                                    value={analyzeAction}
                                    onChange={(e) => setAnalyzeAction(e.target.value as any)}
                                    className="analyze-select"
                                >
                                    <option value="freq">Word Frequency</option>
                                    <option value="search">Keyword Search</option>
                                    <option value="prefix">Prefix Search</option>
                                    <option value="replace">Replace All</option>
                                    <option value="topk">Top 5 Words</option>
                                </select>
                                {analyzeAction !== 'topk' && (
                                    <input
                                        type="text"
                                        value={analyzeQuery}
                                        onChange={(e) => setAnalyzeQuery(e.target.value)}
                                        placeholder={analyzeAction === 'replace' ? "Word to find..." : "Enter word to search..."}
                                        className="analyze-input"
                                    />
                                )}
                                {analyzeAction === 'replace' && (
                                    <input
                                        type="text"
                                        value={replaceWord}
                                        onChange={(e) => setReplaceWord(e.target.value)}
                                        placeholder="Replace with..."
                                        className="analyze-input"
                                    />
                                )}
                                <button
                                    onClick={handleAnalyze}
                                    disabled={
                                        analyzeAction === 'topk' ? false :
                                            analyzeAction === 'replace' ? (!analyzeQuery.trim() || !replaceWord.trim()) :
                                                !analyzeQuery.trim()
                                    }
                                    className="modal-btn analyze"
                                >
                                    {analyzeAction === 'topk' ? '📊 Get Top 5' : analyzeAction === 'replace' ? '🔄 Replace All' : '🔍 Analyze'}
                                </button>
                            </div>
                        </div>

                        <button onClick={() => setShowAnalyzeModal(false)} className="modal-close">
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Reopen sidebar button */}
            {!sidebarOpen && (
                <button onClick={() => setSidebarOpen(true)} className="sidebar-reopen-btn">
                    ☰
                </button>
            )}

            {/* Sidebar */}
            <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
                <div className="sidebar-header">
                    <h2>Mini Google</h2>
                    <button onClick={() => setSidebarOpen(!sidebarOpen)} className="toggle-btn">
                        {sidebarOpen ? '◀' : '▶'}
                    </button>
                </div>

                <button onClick={newChat} className="new-chat-btn">
                    + New Chat
                </button>

                <div className="history-section">
                    <div className="history-header">
                        <span>Recent Chats</span>
                        {chatSessions.length > 0 && (
                            <button onClick={clearHistory} className="clear-btn">Clear</button>
                        )}
                    </div>
                    <div className="history-list">
                        {chatSessions.map((chat) => (
                            <button
                                key={chat.id}
                                className={`history-item ${currentChatId === chat.id ? 'active' : ''}`}
                                onClick={() => switchToChat(chat.id)}
                            >
                                {chat.title}
                            </button>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <div className="messages-area">
                    {messages.length === 0 && (
                        <div className="welcome">
                            <div className="welcome-icon">✦</div>
                            <h1>How can I help you today?</h1>
                            <p className="welcome-hint">Upload a .txt file to analyze with C data structures</p>
                        </div>
                    )}
                    {messages.map(msg => (
                        <MessageBubble key={msg.id} message={msg} />
                    ))}
                    {isLoading && (
                        <div className="loading">
                            <div className="dots"><span></span><span></span><span></span></div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div className="input-area">
                    <div className="input-wrapper">
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="attach-btn"
                            title="Upload .txt file for analysis"
                        >
                            +
                        </button>
                        {/* Show when there's a modified document in memory */}
                        {uploadedDoc && (
                            <button
                                onClick={() => setShowAnalyzeModal(true)}
                                className="attach-btn"
                                title={`Continue with ${uploadedDoc.name}`}
                                style={{ marginLeft: '4px', backgroundColor: '#4ade80' }}
                            >
                                📄
                            </button>
                        )}
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileUpload}
                            accept=".txt"
                            hidden
                        />
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask AI or upload a document..."
                            className="chat-input"
                            disabled={isLoading}
                        />
                        <span className="model-badge">phi ▾</span>
                        <button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className="send-btn"
                        >
                            ↑
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
};
