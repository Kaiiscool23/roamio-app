const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function addMessage(content, sender) {
    const message = document.createElement("div");
    message.classList.add("message", sender);
    message.innerText = content;
    chatWindow.appendChild(message);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function handleUserInput() {
    const text = userInput.value.trim();
    if (text === "") return;

    addMessage(text, "user");
    userInput.value = "";

    fetch("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        addMessage(data.response, "bot");
    })
    .catch(error => {
        console.error("Error:", error);
    });
}

sendBtn.addEventListener("click", handleUserInput);
userInput.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        handleUserInput();
    }
});

function handleQuickOption(userMessage, botResponse) {
    addMessage(userMessage, "user");
    setTimeout(() => addMessage(botResponse, "bot"), 500);
}