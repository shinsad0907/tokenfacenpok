from flask import Flask, request, render_template_string, jsonify
import sys
import os
import json

# Import FacebookGetToken
try:
    from facebook_login import FacebookGetToken
except ImportError:
    from .facebook_login import FacebookGetToken

app = Flask(__name__)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook Login Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }
        h1 i { color: #1877f2; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
            font-size: 14px;
        }
        input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
            outline: none;
        }
        input:focus {
            border-color: #1877f2;
        }
        .hint {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #1877f2;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s, transform 0.2s;
        }
        button:hover {
            background: #166fe5;
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            background: #999;
            cursor: not-allowed;
            transform: none;
        }
        #result {
            margin-top: 25px;
            padding: 20px;
            border-radius: 10px;
            display: none;
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1877f2;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .result-details {
            margin-top: 15px;
        }
        .result-item {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            font-size: 14px;
        }
        .result-item strong {
            color: #333;
        }
        .result-item .value {
            color: #1877f2;
            word-break: break-all;
        }
        .page-list {
            margin-top: 15px;
        }
        .page-item {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 14px;
        }
        .page-item .page-name {
            font-weight: 600;
            color: #333;
        }
        .page-item .page-detail {
            color: #666;
            font-size: 12px;
            margin-top: 4px;
        }
        .token-display {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
            margin-top: 8px;
            max-height: 100px;
            overflow-y: auto;
        }
        .toggle-btn {
            background: none;
            border: none;
            color: #1877f2;
            cursor: pointer;
            font-size: 13px;
            padding: 5px;
            width: auto;
            margin-top: 5px;
        }
        .toggle-btn:hover {
            text-decoration: underline;
            background: none;
            transform: none;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><i>📘</i> Facebook Login</h1>
        <form id="loginForm">
            <div class="form-group">
                <label for="uid">Email hoặc UID</label>
                <input type="text" id="uid" name="uid" placeholder="Nhập email hoặc UID" required>
            </div>
            <div class="form-group">
                <label for="password">Mật khẩu</label>
                <input type="password" id="password" name="password" placeholder="Nhập mật khẩu" required>
            </div>
            <div class="form-group">
                <label for="auth">2FA Secret Key (nếu có)</label>
                <input type="text" id="auth" name="auth" placeholder="Mã secret (VD: 557CXEC4BLSX4KD4...)" style="text-transform: uppercase;">
                <div class="hint">Nếu không có 2FA, để trống</div>
            </div>
            <button type="submit" id="submitBtn">🔑 Đăng nhập</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 10px; color: #666;">Đang đăng nhập...</p>
        </div>
        
        <div id="result"></div>
        <div class="footer">Made with ❤️</div>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const btn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const resultDiv = document.getElementById('result');
            
            btn.disabled = true;
            loading.style.display = 'block';
            resultDiv.style.display = 'none';
            
            const data = {
                uid: document.getElementById('uid').value.trim(),
                password: document.getElementById('password').value.trim(),
                auth: document.getElementById('auth').value.trim().toUpperCase()
            };
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                loading.style.display = 'none';
                btn.disabled = false;
                resultDiv.style.display = 'block';
                
                if (result.ok) {
                    resultDiv.className = 'success';
                    let html = '<h3>✅ Đăng nhập thành công!</h3><div class="result-details>';
                    html += `<div class="result-item"><strong>UID:</strong> <span class="value">${result.uid || 'N/A'}</span></div>`;
                    html += `<div class="result-item"><strong>Tên:</strong> <span class="value">${result.name || 'N/A'}</span></div>`;
                    
                    html += `<div class="result-item"><strong>Token:</strong>`;
                    html += `<div class="token-display">${result.token || 'N/A'}</div>`;
                    html += `<button class="toggle-btn" onclick="copyText('${result.token || ''}')">📋 Sao chép token</button>`;
                    html += `</div>`;
                    
                    if (result.cookie) {
                        html += `<div class="result-item"><strong>Cookie:</strong>`;
                        html += `<div class="token-display">${result.cookie}</div>`;
                        html += `<button class="toggle-btn" onclick="copyText('${result.cookie || ''}')">📋 Sao chép cookie</button>`;
                        html += `</div>`;
                    }
                    
                    if (result.avatar) {
                        html += `<div class="result-item"><strong>Avatar:</strong><br>`;
                        html += `<img src="${result.avatar}" style="width:80px;height:80px;border-radius:50%;margin-top:8px;">`;
                        html += `</div>`;
                    }
                    
                    if (result.pages && result.pages.length > 0) {
                        html += `<div class="result-item"><strong>📄 Pages (${result.pages.length}):</strong>`;
                        html += `<div class="page-list">`;
                        result.pages.forEach(page => {
                            html += `<div class="page-item">`;
                            html += `<div class="page-name">📌 ${page.name || 'Unnamed'}</div>`;
                            html += `<div class="page-detail">ID: ${page.uid || page.page_id_graph || 'N/A'}`;
                            if (page.fans) html += ` | Fans: ${page.fans}`;
                            html += `</div>`;
                            if (page.token) {
                                html += `<div class="token-display" style="font-size:11px;max-height:60px;">${page.token}</div>`;
                            }
                            html += `</div>`;
                        });
                        html += `</div></div>`;
                    }
                    
                    html += '</div>';
                    resultDiv.innerHTML = html;
                } else {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `<h3>❌ Lỗi</h3><p>${result.msg || 'Đăng nhập thất bại'}</p>`;
                }
            } catch (error) {
                loading.style.display = 'none';
                btn.disabled = false;
                resultDiv.style.display = 'block';
                resultDiv.className = 'error';
                resultDiv.innerHTML = `<h3>❌ Lỗi kết nối</h3><p>${error.message}</p>`;
            }
        });
        
        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('Đã sao chép!');
            }).catch(() => {
                const input = document.createElement('input');
                input.value = text;
                document.body.appendChild(input);
                input.select();
                document.execCommand('copy');
                document.body.removeChild(input);
                alert('Đã sao chép!');
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': 'Invalid request'})
            
        uid = data.get('uid', '').strip()
        password = data.get('password', '').strip()
        auth = data.get('auth', '').strip()
        
        if not uid or not password:
            return jsonify({'ok': False, 'msg': 'Vui lòng nhập đầy đủ thông tin'})
        
        fb = FacebookGetToken(uid, password, auth)
        result = fb.login()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)})

# Vercel entry point
if __name__ == '__main__':
    app.run()
