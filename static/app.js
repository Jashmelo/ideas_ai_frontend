document.addEventListener('DOMContentLoaded', function() {
    const chatList = document.getElementById('chat-list');
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const fileInput = document.getElementById('file-input');

    let currentChatId = null;

    // Load chats
    loadChats();

    // Event listeners
    newChatBtn.addEventListener('click', createNewChat);
    sendBtn.addEventListener('click', sendMessage);
    logoutBtn.addEventListener('click', () => window.location.href = '/logout');
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    function loadChats() {
        fetch('/api/chats')
            .then(response => response.json())
            .then(chats => {
                chatList.innerHTML = '';
                chats.forEach(chat => {
                    const li = document.createElement('li');
                    li.textContent = chat.title;
                    li.addEventListener('click', () => loadChat(chat.id));
                    chatList.appendChild(li);
                });
                if (chats.length > 0 && !currentChatId) {
                    loadChat(chats[0].id);
                }
            });
    }

    function createNewChat() {
        fetch('/api/chats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Chat' })
        })
            .then(response => response.json())
            .then(chat => {
                loadChats();
                loadChat(chat.id);
            });
    }

    function loadChat(chatId) {
        currentChatId = chatId;
        fetch(`/api/chats/${chatId}/messages`)
            .then(response => response.json())
            .then(messages => {
                chatMessages.innerHTML = '';
                messages.forEach(msg => {
                    displayMessage(msg.role, msg.content);
                });
            });
    }

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || !currentChatId) return;

        // Handle file upload if present
        const file = fileInput.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    const messageWithFile = `${message}\n[Uploaded file: ${data.filename}]`;
                    sendChatMessage(messageWithFile);
                });
        } else {
            sendChatMessage(message);
        }

        messageInput.value = '';
        fileInput.value = '';
    }

    function sendChatMessage(message) {
        displayMessage('user', message);

        fetch(`/api/chats/${currentChatId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        })
            .then(response => response.json())
            .then(data => {
                displayMessage('assistant', data.response);
            });
    }

    function displayMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.textContent = content;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});