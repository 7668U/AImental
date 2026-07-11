// 【最终修正】定义后端的完整基础URL
const API_BASE_URL = 'http://127.0.0.1:8000';

// --- 全局状态变量 ---
let authToken = null;
let currentCharacterId = null;

// --- DOM 元素引用 ---
const userIdInput = document.getElementById('user-id-input');
const loginBtn = document.getElementById('login-btn');
const characterListDiv = document.getElementById('character-list');
const chatTitle = document.getElementById('chat-title');
const chatWindow = document.getElementById('chat-window');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const statusLogDiv = document.getElementById('status-log');
const statusLogContentDiv = document.getElementById('status-log-content');
const closeLogBtn = document.getElementById('close-log-btn');

// --- 初始化 ---
document.addEventListener('DOMContentLoaded', () => {
    // 登录按钮事件
    loginBtn.addEventListener('click', (event) => {
        event.preventDefault();
        login();
    });

    // 在输入框按回车键登录
    userIdInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            loginBtn.click();
        }
    });

    // 关闭日志栏按钮事件
    closeLogBtn.addEventListener('click', () => {
        statusLogDiv.classList.add('hidden');
    });
});

// --- 日志函数 ---
function logStatus(message, type = 'info') {
    const colorMap = { info: 'lime', error: 'red', warn: 'yellow' };
    statusLogDiv.classList.remove('hidden'); // 显示日志栏
    statusLogContentDiv.innerHTML += `<p style="color:${colorMap[type]}; margin: 2px 0;">[${new Date().toLocaleTimeString()}] ${message}</p>`;
    statusLogContentDiv.scrollTop = statusLogContentDiv.scrollHeight;
}

// --- 核心功能函数 ---

async function login() {
    const userId = userIdInput.value.trim();
    if (!userId) {
        alert('请输入一个用户ID！');
        return;
    }
    logStatus(`正在为测试用户 '${userId}' 获取认证Token...`);
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/users/login/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`获取Token失败: ${response.status} - ${errorText}`);
        }
        const data = await response.json();
        if (!data.access_token) throw new Error('认证接口返回的数据中没有 "access_token"。');
        
        authToken = data.access_token;

        userIdInput.disabled = true;
        loginBtn.disabled = true;
        loginBtn.innerText = "已登录";
        logStatus(`用户 '${userId}' 登录成功，获取Token成功。`, 'info');

        fetchCharacters();
    } catch (error) {
        logStatus(error.message, 'error');
        alert(error.message);
    }
}

async function fetchCharacters() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/community/characters`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error(`获取角色列表失败: ${response.status}`);
        const characters = await response.json();
        characterListDiv.innerHTML = '';
        characters.forEach(char => {
            const charDiv = document.createElement('div');
            charDiv.className = 'character';
            charDiv.id = `char-${char.id}`;
            // 注意：头像的src也需要拼接
            charDiv.innerHTML = `
                <img src="${API_BASE_URL}${char.avatar_url}" alt="${char.name}" onerror="this.onerror=null;this.src='data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';">
                <span>${char.name}</span>
                <button onclick="addFriend('${char.id}')">加好友</button>
            `;
            charDiv.addEventListener('click', () => selectCharacter(char.id, char.name));
            characterListDiv.appendChild(charDiv);
        });
        logStatus('AI角色列表加载完毕。');
    } catch (error) {
        logStatus(error.message, 'error');
    }
}

async function addFriend(characterId) {
    event.stopPropagation();
    const message = prompt("请输入好友验证信息:", "你好，可以认识一下吗？");
    if (message === null) return;
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/community/friendship/request/${characterId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ verification_message: message })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail);
        alert('好友请求已发送！');
        logStatus(`已向 ${characterId} 发送好友请求。`);
    } catch (error) {
        alert(`发送失败: ${error.message}`);
        logStatus(error.message, 'error');
    }
}

async function selectCharacter(characterId, characterName) {
    if (currentCharacterId === characterId) return;
    currentCharacterId = characterId;
    chatTitle.innerText = `与 ${characterName} 的对话`;
    messageInput.disabled = false;
    sendBtn.disabled = false;
    document.querySelectorAll('.character').forEach(c => c.classList.remove('active'));
    document.getElementById(`char-${characterId}`).classList.add('active');
    logStatus(`已选择角色: ${characterName}`);
    await fetchChatHistory(characterId);
}

async function fetchChatHistory(characterId) {
    chatWindow.innerHTML = '<p>正在加载历史消息...</p>';
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/community/chats/${characterId}?limit=50`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error('获取聊天记录失败');
        const history = await response.json();
        chatWindow.innerHTML = '';
        if (history.length === 0) {
            chatWindow.innerHTML = '<p>你们还没有聊天记录，快开始对话吧！</p>';
        } else {
            history.forEach(msg => appendMessage(msg.content, msg.role));
        }
        logStatus(`已加载与 ${currentCharacterId} 的聊天记录。`);
    } catch (error) {
        logStatus(error.message, 'error');
        chatWindow.innerHTML = `<p style="color:red">${error.message}</p>`;
    }
}

async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || !currentCharacterId) return;
    appendMessage(content, 'user');
    messageInput.value = '';
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/community/chats/${currentCharacterId}/messages`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail);
        (result.ai_messages || []).forEach(msg => appendMessage(msg.content, 'ai'));
        logStatus('消息已发送，AI回复已同步返回。');
    } catch (error) {
        logStatus(error.message, 'error');
        appendMessage(`发送失败: ${error.message}`, 'error');
    }
}

function appendMessage(content, role) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message`;
    msgDiv.innerText = content;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}
