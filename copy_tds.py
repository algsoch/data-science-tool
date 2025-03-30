import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
import shutil
from datetime import datetime
import sys
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tds_app")

# Try to import the question-answering system
try:
    from vicky_server import answer_question
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    sys.exit("Error: Could not import answer_question from vicky_server. Make sure the file exists in the same directory.")

app = FastAPI(title="TDS - Tools for Data Science",
              description="Interactive assistant for data science questions")

# Create directories for templates and static files if they don't exist
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
UPLOADS_DIR = Path("uploads")

for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Create the HTML template file - same as your original implementation
# Replace your existing HTML template with this enhanced version
with open(TEMPLATES_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS - Tools for Data Science</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #4c2882;
            --primary-light: #6b3eb6;
            --secondary-color: #37bb9c;
            --dark-color: #2c2c2c;
            --light-color: #f5f5f5;
            --success-color: #4CAF50;
            --error-color: #f44336;
            --warning-color: #ff9800;
            --text-color: #333;
            --border-radius: 8px;
            --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--light-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }
        
        header::after {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            background: radial-gradient(circle at top right, rgba(255,255,255,0.2), transparent);
            pointer-events: none;
        }
        
        h1 {
            margin: 0;
            font-size: 32px;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        }
        
        .subtitle {
            font-style: italic;
            opacity: 0.9;
            margin-top: 10px;
            font-weight: 300;
        }
        
        .header-buttons {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }
        
        .header-button {
            background-color: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .header-button:hover {
            background-color: rgba(255,255,255,0.3);
        }
        
        .main-section {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .chat-container {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .chat-box {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            background-color: white;
        }
        
        .message {
            padding: 12px 18px;
            border-radius: 18px;
            margin-bottom: 15px;
            max-width: 85%;
            word-wrap: break-word;
            position: relative;
            animation: fadeIn 0.3s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            background-color: #e3f2fd;
            margin-left: auto;
            border-top-right-radius: 4px;
            text-align: right;
        }
        
        .bot-message {
            background-color: #f5f5f5;
            margin-right: auto;
            border-top-left-radius: 4px;
            white-space: pre-wrap;
        }
        
        .bot-message.loading {
            background-color: #f0f0f0;
            color: #666;
        }
        
        .bot-message.loading::after {
            content: '⏳';
            margin-left: 5px;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.5; }
            50% { opacity: 1; }
            100% { opacity: 0.5; }
        }
        
        .input-area {
            padding: 15px;
            background-color: #f9f9f9;
            border-top: 1px solid #eee;
        }
        
        .input-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .question-input {
            flex-grow: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 16px;
            background-color: white;
            transition: var(--transition);
        }
        
        .question-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(76, 40, 130, 0.1);
        }
        
        .file-attach {
            position: relative;
        }
        
        .file-attach input[type="file"] {
            position: absolute;
            width: 0.1px;
            height: 0.1px;
            opacity: 0;
            overflow: hidden;
            z-index: -1;
        }
        
        .file-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: var(--secondary-color);
            color: white;
            border-radius: 50%;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .file-button:hover {
            background-color: #2ea58a;
        }
        
        .send-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            transition: var(--transition);
        }
        
        .send-button:hover {
            background-color: var(--primary-light);
        }
        
        .sidebar {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .sidebar-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            font-weight: bold;
        }
        
        .question-categories {
            display: flex;
            border-bottom: 1px solid #eee;
        }
        
        .category-tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            transition: var(--transition);
        }
        
        .category-tab.active {
            border-bottom-color: var(--primary-color);
            color: var(--primary-color);
        }
        
        .preloaded-questions {
            flex-grow: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .question-item {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .question-item:hover {
            background-color: #f5f5f5;
        }
        
        .question-item:last-child {
            border-bottom: none;
        }
        
        .file-upload-section {
            margin-top: 20px;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        
        .file-upload-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .file-upload-content {
            padding: 20px;
        }
        
        .file-input-container {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .file-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            background-color: white;
        }
        
        .upload-button {
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: var(--transition);
        }
        
        .upload-button:hover {
            background-color: var(--primary-light);
        }
        
        .uploaded-files h4 {
            margin-top: 0;
            margin-bottom: 10px;
            color: var(--primary-color);
        }
        
        .uploaded-files ul {
            list-style: none;
            padding: 0;
        }
        
        .uploaded-files li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .uploaded-files li:last-child {
            border-bottom: none;
        }
        
        .uploaded-files a {
            color: var(--primary-color);
            text-decoration: none;
            font-size: 14px;
            margin-left: 10px;
        }
        
        .status-bar {
            background-color: var(--primary-color);
            color: white;
            padding: 8px 15px;
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            text-align: center;
            font-size: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            z-index: 1000;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success-color);
            border-radius: 50%;
        }
        
        code {
            background-color: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }
        
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #eee;
            margin: 10px 0;
        }
        
        .code-block {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            margin: 10px 0;
            position: relative;
        }
        
        .code-block::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 8px;
            background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        .copy-button {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #ddd;
            border-radius: 3px;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .copy-button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        @media (max-width: 900px) {
            .main-section {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                height: 300px;
            }
            
            .status-bar {
                flex-direction: column;
                gap: 5px;
                padding: 5px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS - Tools for Data Science</h1>
            <div class="subtitle">Full support for Graded Assignments 1 & 2 is now available!</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
                <button class="header-button" onclick="location.href='/api/docs'">
                    <i class="fas fa-code"></i> API
                </button>
            </div>
        </header>
        
        <div class="main-section">
            <!-- Chat container (left side) -->
            <div class="chat-container">
                <div class="chat-box" id="chatBox">
                    <!-- Initial welcome message -->
                    <div class="message bot-message">
                        <strong>Welcome to TDS - Tools for Data Science!</strong><br><br>
                        I can help you with various data science tasks and questions, including all assignments for GA1 and GA2. 
                        Try asking a question or select one of the preloaded examples from the sidebar.
                    </div>
                </div>
                <div class="input-area">
                    <form class="input-form" id="questionForm" enctype="multipart/form-data" onsubmit="sendQuestionWithFile(event)">
                        <div class="file-attach">
                            <input type="file" id="fileAttachment" name="file">
                            <label for="fileAttachment" class="file-button">
                                <i class="fas fa-paperclip"></i>
                            </label>
                        </div>
                        <input type="text" class="question-input" id="questionInput" placeholder="Ask me anything about data science..." autocomplete="off">
                        <button type="submit" class="send-button">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Sidebar with preloaded questions (right side) -->
            <div class="sidebar">
                <div class="sidebar-header">Graded Assignment Questions</div>
                <div class="question-categories">
                    <div class="category-tab active" data-category="GA1">GA1</div>
                    <div class="category-tab" data-category="GA2">GA2</div>
                </div>
                <div class="preloaded-questions" id="preloadedQuestions">
                    <!-- Questions will be loaded here by JavaScript -->
                </div>
            </div>
        </div>

        <!-- File upload section -->
        <div class="file-upload-section">
            <div class="file-upload-header">
                <i class="fas fa-cloud-upload-alt"></i> File Repository
            </div>
            <div class="file-upload-content">
                <form class="file-input-container" action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" class="file-input" name="file">
                    <button type="submit" class="upload-button">Upload File</button>
                </form>
                <div class="uploaded-files">
                    <h4>Uploaded Files</h4>
                    <ul id="uploadedFilesList">
                        {% if files %}
                            {% for file in files %}
                                <li>
                                    <span>{{ file }}</span>
                                    <div>
                                        <a href="/use-file/{{ file }}">Use</a>
                                        <a href="/delete-file/{{ file }}" class="delete-link">Delete</a>
                                    </div>
                                </li>
                            {% endfor %}
                        {% else %}
                            <li>No files uploaded yet</li>
                        {% endif %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        <div class="status-indicator">
            <span class="status-dot"></span>
            <span>System Online</span>
        </div>
        <div>
            <i class="fas fa-server"></i> Full support for GA1 & GA2 enabled
        </div>
        <div>
            <i class="fas fa-code"></i> API Ready
        </div>
    </div>

    <button onclick="debugForm()" style="margin-top:10px;">Debug Form Data</button>

    <script>
        // Preloaded questions data
        const preloadedQuestions = [
            // GA1 Questions
            {"id": "ga1-1", "text": "What is the output of code -s?", "category": "GA1"},
            {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
            {"id": "ga1-3", "text": "How to use npx and prettier with README.md?", "category": "GA1"},
            {"id": "ga1-4", "text": "Google Sheets formula with SEQUENCE and ARRAY_CONSTRAIN", "category": "GA1"},
            {"id": "ga1-5", "text": "Excel formula with SORTBY and TAKE", "category": "GA1"},
            {"id": "ga1-6", "text": "Find hidden input value on a webpage", "category": "GA1"},
            {"id": "ga1-7", "text": "How many Wednesdays are in a date range?", "category": "GA1"},
            {"id": "ga1-8", "text": "Extract data from CSV in a ZIP file", "category": "GA1"},
            
            // GA2 Questions
            {"id": "ga2-1", "text": "Write Python code to count pixels by brightness in an image", "category": "GA2"},
            {"id": "ga2-2", "text": "How to set up a git hook to enforce commit message format?", "category": "GA2"},
            {"id": "ga2-3", "text": "Join datasets using SQLModel in Python", "category": "GA2"},
            {"id": "ga2-4", "text": "Display a world map using Matplotlib", "category": "GA2"},
            {"id": "ga2-5", "text": "Create a MIDI file with a simple melody", "category": "GA2"},
            {"id": "ga2-6", "text": "Generate a fake dataset with scikit-learn", "category": "GA2"},
            {"id": "ga2-7", "text": "Download and visualize weather data", "category": "GA2"},
            {"id": "ga2-8", "text": "Create a simple interactive dashboard with Plotly", "category": "GA2"},
            {"id": "ga2-9", "text": "Create a FastAPI server for student data", "category": "GA2"},
            {"id": "ga2-10", "text": "Set up a Llama model with ngrok tunnel", "category": "GA2"}
        ];

        document.addEventListener('DOMContentLoaded', function() {
            const chatBox = document.getElementById('chatBox');
            const questionForm = document.getElementById('questionForm');
            const questionInput = document.getElementById('questionInput');
            const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
            const categoryTabs = document.querySelectorAll('.category-tab');
            
            // Initialize with GA1 questions
            displayPreloadedQuestions('GA1');
            
            // Handle category switching
            categoryTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    categoryTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Display questions for the selected category
                    displayPreloadedQuestions(this.dataset.category);
                });
            });
            
            // Display preloaded questions for a specific category
            function displayPreloadedQuestions(category) {
                preloadedQuestionsContainer.innerHTML = '';
                
                const filteredQuestions = preloadedQuestions.filter(q => q.category === category);
                
                filteredQuestions.forEach(question => {
                    const questionItem = document.createElement('div');
                    questionItem.className = 'question-item';
                    questionItem.textContent = question.text;
                    questionItem.addEventListener('click', () => {
                        questionInput.value = question.text;
                        // Auto-submit the question on click
                        questionForm.dispatchEvent(new Event('submit'));
                    });
                    
                    preloadedQuestionsContainer.appendChild(questionItem);
                });
            }
            
            // Handle file upload links
            document.addEventListener('click', function(e) {
                if (e.target.classList.contains('delete-link')) {
                    if (!confirm('Are you sure you want to delete this file?')) {
                        e.preventDefault();
                    }
                }
            });
            
            // Function to send questions with file
            window.sendQuestionWithFile = function(event) {
                event.preventDefault();
                const question = document.getElementById('questionInput').value.trim();
                if (!question) return;
                
                // Display user question
                addMessage(question, 'user');
                
                // Clear input
                document.getElementById('questionInput').value = '';
                
                // Display loading indicator
                const loadingId = 'loading-' + Date.now();
                addMessage('Thinking...', 'bot loading', loadingId);
                
                // Create form data
                const formData = new FormData();
                formData.append('question', question);
                
                // Add file if present
                const fileInput = document.getElementById('fileAttachment');
                if (fileInput.files.length > 0) {
                    formData.append('file', fileInput.files[0]);
                }
                
                fetch('/ask_with_file', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // Remove loading message
                    const loadingMsg = document.getElementById(loadingId);
                    if (loadingMsg) loadingMsg.remove();
                    
                    // Display answer
                    if (data.success) {
                        addMessage(data.answer || "No response received", 'bot');
                    } else {
                        addMessage("Error: " + (data.error || "Unknown error occurred"), 'bot');
                    }
                })
                .catch(error => {
                    // Remove loading message
                    const loadingMsg = document.getElementById(loadingId);
                    if (loadingMsg) loadingMsg.remove();
                    
                    console.error('Error:', error);
                    addMessage("Sorry, there was an error processing your question.", 'bot');
                });
            };
            
            // Function to add a message to the chat
            function addMessage(text, type, id = null) {
                const messageElement = document.createElement('div');
                messageElement.className = `message ${type}-message`;
                if (id) messageElement.id = id;
                
                // Process code blocks if it's a bot message
                if (type === 'bot' || type === 'bot loading') {
                    // Simple code block detection for ```code``` blocks
                    text = text.replace(/```([^`]+)```/g, function(match, codeContent) {
                        return `<div class="code-block">${codeContent}<button class="copy-button">Copy</button></div>`;
                    });
                    
                    // Inline code detection for `code`
                    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
                }
                
                messageElement.innerHTML = text;
                
                // Add copy functionality to code blocks
                if (type === 'bot') {
                    setTimeout(() => {
                        messageElement.querySelectorAll('.copy-button').forEach(button => {
                            button.addEventListener('click', function() {
                                const codeBlock = this.parentNode;
                                const code = codeBlock.textContent.replace('Copy', '').trim();
                                
                                navigator.clipboard.writeText(code).then(() => {
                                    this.textContent = 'Copied!';
                                    setTimeout(() => { this.textContent = 'Copy'; }, 2000);
                                });
                            });
                        });
                    }, 0);
                }
                
                chatBox.appendChild(messageElement);
                chatBox.scrollTop = chatBox.scrollHeight;
                return messageElement;
            }
            
            // Function to format the answer with code highlighting
            function formatAnswer(text) {
                if (!text) return "No response received";
                
                // Handle line breaks
                text = text.replace(/\\n/g, '<br>');
                
                return text;
            }
            
            // Check server status and update the status indicator
            fetch('/health')
                .then(response => {
                    if (response.ok) {
                        document.querySelector('.status-dot').style.backgroundColor = '#4CAF50'; // Green
                    } else {
                        document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
                    }
                })
                .catch(() => {
                    document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
                });
                
            // Load uploaded files list
            function loadUploadedFiles() {
                fetch('/files')
                    .then(response => response.text())
                    .then(html => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const filesList = doc.querySelector('.files-table tbody');
                        if (filesList) {
                            const uploadedFilesList = document.getElementById('uploadedFilesList');
                            uploadedFilesList.innerHTML = '';
                            
                            Array.from(filesList.querySelectorAll('tr')).forEach(row => {
                                const fileId = row.cells[0].textContent;
                                const fileName = row.cells[1].textContent;
                                
                                const li = document.createElement('li');
                                li.innerHTML = `
                                    <span>${fileName} (ID: ${fileId})</span>
                                    <div>
                                        <a href="#" class="use-file" data-id="${fileId}">Use</a>
                                        <a href="#" class="delete-file" data-id="${fileId}">Delete</a>
                                    </div>
                                `;
                                uploadedFilesList.appendChild(li);
                            });
                            
                            // Add event listeners to use/delete links
                            document.querySelectorAll('.use-file').forEach(link => {
                                link.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    const fileId = this.dataset.id;
                                    questionInput.value += ` with ID ${fileId}`;
                                    questionInput.focus();
                                });
                            });
                            
                            document.querySelectorAll('.delete-file').forEach(link => {
                                link.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    if (confirm('Are you sure you want to delete this file?')) {
                                        const fileId = this.dataset.id;
                                        fetch(`/delete-file/${fileId}`, { method: 'DELETE' })
                                            .then(response => response.json())
                                            .then(data => {
                                                if (data.success) {
                                                    loadUploadedFiles();
                                                }
                                            });
                                    }
                                });
                            });
                        }
                    });
            }
            
            // Load uploaded files on page load
            loadUploadedFiles();
        });

        function debugForm() {
            const formData = new FormData();
            formData.append('question', 'Test question');
            
            fetch('/debug-form', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Debug data:', data);
                alert('Check console for debug info');
            });
        }
    </script>
</body>
</html>
""")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Get list of uploaded files
    files = []
    if UPLOADS_DIR.exists():
        files = [f.name for f in UPLOADS_DIR.iterdir() if f.is_file()]
    
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "files": files}
    )

@app.get("/health")
async def health_check():
    """Endpoint to check if the server is running correctly"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Update the ask_question function to handle file types more generically

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    try:
        logger.info(f"Processing question: {question[:50]}...")
        
        # Check if the question references any uploaded files by ID
        file_ids = re.findall(r'\b([0-9a-f]{8})\b', question)
        
        # If we found file IDs, add their paths to the question
        if file_ids:
            for file_id in file_ids:
                if file_id in UPLOADED_FILES_REGISTRY:
                    # Add the actual file path to the question text
                    file_info = UPLOADED_FILES_REGISTRY[file_id]
                    file_ext = file_info["type"].lower()
                    
                    # Add appropriate context based on file type
                    if file_ext == ".zip":
                        question += f" The ZIP file is located at {file_info['path']}"
                    elif file_ext == ".md":
                        question += f" The README.md file is located at {file_info['path']}"
                    else:
                        # Generic handling for other file types
                        question += f" The file {file_info['original_name']} is located at {file_info['path']}"
        
        # Process the question with the augmented information
        answer = answer_question(question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing your question: {str(e)}")

# Create a global registry for uploaded files
UPLOADED_FILES_REGISTRY = {}  # Maps unique IDs to actual file paths

def register_uploaded_file(original_filename, file_path):
    """Register an uploaded file so solution functions can access it"""
    # Generate a unique ID for this file
    import uuid
    file_id = str(uuid.uuid4())[:8]
    
    # Add to registry with metadata
    UPLOADED_FILES_REGISTRY[file_id] = {
        "original_name": original_filename,
        "path": file_path,
        "uploaded_at": datetime.now().isoformat(),
        "type": os.path.splitext(original_filename)[1].lower()
    }
    
    # Return the ID that can be used in queries
    return file_id

# Update the upload file function to display file IDs better

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save uploaded file
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = UPLOADS_DIR / filename
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Register the file and get an ID
        file_id = register_uploaded_file(file.filename, str(file_path))
        
        logger.info(f"File uploaded: {filename} (ID: {file_id})")
        
        # Add a message to the chat interface about the uploaded file
        file_type = os.path.splitext(file.filename)[1].lower()
        usage_example = ""
        if file_type == ".zip":
            usage_example = f"Extract data from ZIP file with ID {file_id}"
        elif file_type == ".md":
            usage_example = f"Run npx prettier on README.md with ID {file_id}"
        
        return {
            "filename": filename,
            "file_id": file_id,
            "message": f"File uploaded successfully (ID: {file_id}). Example usage: '{usage_example}'"
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/use-file/{filename}")
async def use_file(filename: str, request: Request):
    # Redirect back to the chat interface with the filename in a query parameter
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return RedirectResponse(url=f"/?file={filename}")

# Add this function to make file IDs more accessible

@app.get("/files")
async def list_files(request: Request):
    """Show all uploaded files and their IDs"""
    files_info = []
    for file_id, info in UPLOADED_FILES_REGISTRY.items():
        files_info.append({
            "id": file_id,
            "name": info["original_name"],
            "type": info["type"],
            "uploaded_at": info["uploaded_at"]
        })
    
    return templates.TemplateResponse(
        "files.html",
        {"request": request, "files": files_info}
    )

# Create a template for the files page
with open(TEMPLATES_DIR / "files.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Uploaded Files - TDS</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #4c2882;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            margin: 0;
            font-size: 28px;
        }
        .files-table {
            width: 100%;
            background-color: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .files-table th, .files-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .files-table th {
            background-color: #4c2882;
            color: white;
        }
        .files-table tr:last-child td {
            border-bottom: none;
        }
        .files-table tr:hover {
            background-color: #f5f5f5;
        }
        .back-button {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background-color: #4c2882;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Uploaded Files</h1>
        </header>
        
        {% if files %}
        <table class="files-table">
            <thead>
                <tr>
                    <th>File ID</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Uploaded At</th>
                    <th>Usage Example</th>
                </tr>
            </thead>
            <tbody>
                {% for file in files %}
                <tr>
                    <td>{{ file.id }}</td>
                    <td>{{ file.name }}</td>
                    <td>{{ file.type }}</td>
                    <td>{{ file.uploaded_at }}</td>
                    <td>
                        {% if file.type == '.md' %}
                            Run npx prettier on README.md with ID {{ file.id }}
                        {% elif file.type == '.zip' %}
                            Extract data from ZIP file with ID {{ file.id }}
                        {% else %}
                            Process file with ID {{ file.id }}
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No files have been uploaded yet.</p>
        {% endif %}
        
        <a href="/" class="back-button">Back to Chat</a>
    </div>
</body>
</html>
""")

@app.post("/ask_with_file")
async def ask_with_file(question: str = Form(...), file: UploadFile = File(None)):
    try:
        logger.info(f"Processing question with file: {question[:50]}...")
        
        # If a file was provided, save and process it
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            logger.info(f"File uploaded with question: {filename} (ID: {file_id})")
            
            # Add file context directly to the question
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            elif file_ext == ".md":
                question += f" The README.md file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        answer = answer_question(question)
        return {"success": True, "answer": answer}
    except Exception as e:
        logger.error(f"Error processing question with file: {e}")
        return {
            "success": False, 
            "error": str(e),
            "error_type": e.__class__.__name__
        }

@app.get("/api/docs", response_class=HTMLResponse)
async def api_docs(request: Request):
    return templates.TemplateResponse(
        "api_docs.html",
        {"request": request}
    )

# Create a template for the API documentation page
with open(TEMPLATES_DIR / "api_docs.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS API Documentation</title>
    <!-- CSS styles here -->
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS API Documentation</h1>
        </header>
        
        <section>
            <h2>Asking Questions</h2>
            
            <h3>POST /api/ask_with_file</h3>
            <p>Ask a question with an optional file attachment</p>
            
            <h4>Parameters</h4>
            <ul>
                <li><strong>question</strong> (required) - The question text</li>
                <li><strong>file</strong> (optional) - A file to use with the question</li>
            </ul>
            
            <h4>Example</h4>
            <pre>
curl -X POST "http://yourdomain.com/api/ask_with_file" \
  -F "question=Extract data from this ZIP file" \
  -F "file=@/path/to/file.zip"
            </pre>
            
            <h4>Response</h4>
            <pre>
{
  "success": true,
  "answer": "The answer from extract.csv is 42",
  "question": "Extract data from this ZIP file"
}
            </pre>
        </section>
        
        <section>
    <h2>File Processing API</h2>
    
    <h3>POST /api/process</h3>
    <p>Process a question that requires a file (like README.md for Question 3 or ZIP for Question 8)</p>
    
    <h4>Parameters</h4>
    <ul>
        <li><strong>question</strong> (required) - The question text</li>
        <li><strong>file</strong> (required) - The file to process</li>
        <li><strong>question_type</strong> (optional) - Hint about question type:
            <ul>
                <li><code>npx_readme</code> - For GA1 third question (README.md with npx)</li>
                <li><code>extract_zip</code> - For GA1 eighth question (Extract from ZIP)</li>
            </ul>
        </li>
    </ul>
    
    <h4>cURL Example</h4>
    <pre>
# For README.md (Question 3)
curl -X POST "http://localhost:8000/api/process" \
  -F "question=What is the output of npx prettier on this README file?" \
  -F "file=@/path/to/README.md" \
  -F "question_type=npx_readme"

# For ZIP file (Question 8)
curl -X POST "http://localhost:8000/api/process" \
  -F "question=What is the value in the answer column?" \
  -F "file=@/path/to/q-extract-csv-zip.zip" \
  -F "question_type=extract_zip"
    </pre>
</section>
    </div>
</body>
</html>
""")

@app.post("/api/process")
async def api_process(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...),
    question_type: str = Form(None)  # Optional hint about which question it is
):
    """Process a question with an optional file through API"""
    try:
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Auto-detect the question type from file extension if not specified
            if not question_type:
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext == ".md":
                    question_type = "npx_readme"  # GA1 third question
                elif file_ext == ".zip":
                    question_type = "extract_zip"  # GA1 eighth question
            
            # Add appropriate context based on detected question type
            if question_type == "npx_readme" or (file.filename.lower() == "readme.md"):
                question += f" The README.md file is located at {file_path}"
            elif question_type == "extract_zip" or file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the enhanced question
        answer = answer_question(question)
        
        # Return a structured response for API clients
        return {
            "success": True,
            "answer": answer,
            "file_processed": bool(file and file.filename),
            "question": question
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_details": str(e.__class__.__name__)
        }

@app.get("/connection-info")
async def connection_info():
    """Get server connection details - useful for debugging remote connections"""
    import platform
    import socket
    
    # Get hostname and IP
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except:
        ip = "Unable to determine IP"
    
    # Return connection info
    return {
        "server": {
            "hostname": hostname,
            "operating_system": platform.system(),
            "ip_address": ip,
            "python_version": platform.python_version(),
        },
        "request_handling": {
            "file_upload_directory": str(UPLOADS_DIR.absolute()),
            "ngrok_support": "Supported (use 'ngrok http 8000' to expose)"
        }
    }

# Add this to the startup code of your application
@app.on_event("startup")
async def startup_event():
    """Run when the application starts"""
    # Create uploads directory if it doesn't exist
    UPLOADS_DIR.mkdir(exist_ok=True)
    logger.info(f"Uploads directory ready: {UPLOADS_DIR.absolute()}")
    
    # Load existing files into registry
    load_existing_files()

def load_existing_files():
    """Load any existing files in the uploads directory into the registry"""
    if UPLOADS_DIR.exists():
        for file_path in UPLOADS_DIR.iterdir():
            if file_path.is_file():
                # Register existing file with its original timestamp if possible
                try:
                    # Try to extract timestamp from filename (assumes format: YYYYMMDD_HHMMSS_originalname)
                    filename = file_path.name
                    parts = filename.split('_', 2)
                    if len(parts) >= 3:
                        original_name = parts[2]  # Get original filename
                        file_id = register_uploaded_file(original_name, str(file_path))
                        logger.info(f"Loaded existing file: {filename} (ID: {file_id})")
                except Exception as e:
                    logger.warning(f"Couldn't register existing file {file_path}: {e}")

@app.post("/debug-form")
async def debug_form(request: Request):
    """Debug endpoint to see what's being received in a form submission"""
    form_data = await request.form()
    return {
        "received_fields": list(form_data.keys()),
        "form_data": {k: str(v) for k, v in form_data.items()},
        "content_type": request.headers.get("content-type", "none")
    }

def start():
    """Function to start the server with proper error handling"""
    try:
        print("\n" + "=" * 50)
        print("Starting TDS - Tools for Data Science Server")
        print("=" * 50)
        print("\n* Access the web interface at: http://127.0.0.1:8000")
        print("* Press Ctrl+C to stop the server\n")
        
        # Use 127.0.0.1 instead of 0.0.0.0 for better local access
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\nError starting the server: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure port 8000 is not already in use")
        print("2. Check that you have permissions to create files/directories")
        print("3. Ensure vicky_server.py is in the same directory")
        sys.exit(1)

if __name__ == "__main__":
    start()