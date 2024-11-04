// gemini_chat.js
/*async function sendMessageTogemini(message) {
    const response = await fetch('/gemini/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ 'message': message })
    });
    const data = await response.json();
    return data.reply;
}
*/
function sendMessage() {
    const userInput = document.getElementById('user-input').value;
    const csrftoken = getCookie('csrftoken');  // 获取 CSRF token
    fetch('https://gemini-api-url', {  // 替换为实际 API URL
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userInput })
    })
    .then(response => response.json())
    .then(data => {
        const chatLog = document.getElementById('chat-log');
        chatLog.innerHTML += `<p>User: ${userInput}</p>`;
        chatLog.innerHTML += `<p>gemini: ${data.response}</p>`;
        document.getElementById('user-input').value = '';  // 清空输入框
    })
    .catch(error => console.error('Error:', error));
}

// 获取 CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
