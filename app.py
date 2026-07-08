import os
import random
import psycopg2
from flask import Flask, request, render_template_string, jsonify, redirect

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = "admin"  # رمز ورود مدیریت شما با حروف کوچک

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ۱. جدول مربیان
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coaches (
            login_code TEXT PRIMARY KEY,
            team_name TEXT,
            coins INTEGER DEFAULT 1000,
            credit INTEGER DEFAULT 10,
            transfer_cards INTEGER DEFAULT 2,
            wallet INTEGER DEFAULT 0,
            account_type TEXT DEFAULT 'رایگان',
            honors TEXT DEFAULT 'هنوز افتخاری ثبت نشده است.'
        )
    ''')
    
    # ۲. جدول بازیکنان
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            team_code TEXT,
            player_name TEXT,
            card_url TEXT DEFAULT '',
            position TEXT DEFAULT 'نیمکت'
        )
    ''')
    
    # ۳. جدول لیگ‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standard_leagues (
            id SERIAL PRIMARY KEY,
            league_name TEXT
        )
    ''')
    
    # ۴. جدول تیم‌های استاندارد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standard_teams (
            id SERIAL PRIMARY KEY,
            league_id INTEGER,
            team_name TEXT,
            credit_required INTEGER DEFAULT 0,
            player_list TEXT,
            cards_file_url TEXT DEFAULT ''
        )
    ''')
    
    # ۵. جدول مسابقات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            team_a TEXT,
            team_b TEXT,
            tournament_name TEXT,
            description TEXT,
            result TEXT DEFAULT 'برگزاری نشده',
            status TEXT DEFAULT 'فعال'
        )
    ''')
    
    # ۶. جدول تورنمنت‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id SERIAL PRIMARY KEY,
            name TEXT,
            status TEXT DEFAULT 'ثبت نام',
            stats_image TEXT DEFAULT ''
        )
    ''')
    
    # ۷. جدول ثبت‌نام تورنمنت‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_regs (
            id SERIAL PRIMARY KEY,
            tournament_id INTEGER,
            team_name TEXT
        )
    ''')

    # ۸. جدول مجوزها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_permissions (
            account_type TEXT PRIMARY KEY,
            tournament_locked INTEGER DEFAULT 0,
            league_locked INTEGER DEFAULT 0,
            shop_locked INTEGER DEFAULT 0
        )
    ''')
    
    # ۹. جدول لاگ‌ها و پیام‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id SERIAL PRIMARY KEY,
            team_name TEXT,
            log_type TEXT,
            message TEXT
        )
    ''')
    
    # پر کردن پیش‌فرض مجوزها
    cursor.execute("SELECT COUNT(*) FROM account_permissions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account_permissions VALUES ('رایگان', 0, 0, 0)")
        cursor.execute("INSERT INTO account_permissions VALUES ('نرمال', 0, 0, 0)")
        cursor.execute("INSERT INTO account_permissions VALUES ('حرفه ای', 0, 0, 0)")

    conn.commit()
    cursor.close()
    conn.close()

LUCKY_BOX_PLAYERS = [
    {"name": "امباپه", "chance": 20, "rarity": "پک ویژه (۲۰٪ شانس)"},
    {"name": "وینیسیوس", "chance": 30, "rarity": "نرمال (۳۰٪ شانس)"},
    {"name": "یک بازیکن لیگ داخلی", "chance": 50, "rarity": "معمولی (۵۰٪ شانس)"}
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سوپرلیگ کارتی v2</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 10px; text-align: center; }
        .container { max-width: 700px; margin: 0 auto; background: #1e293b; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
        h1, h2, h3 { color: #38bdf8; }
        .btn { background-color: #0284c7; color: white; border: none; padding: 8px 15px; margin: 4px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn:hover { background-color: #0369a1; }
        .grid-menu { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 15px; }
        .status-card { background: #334155; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; line-height: 1.6; text-align: right; }
        .section { display: none; margin-top: 15px; padding: 15px; background: #334155; border-radius: 8px; text-align: right; }
        .active { display: block; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
        th, td { border: 1px solid #475569; padding: 6px; text-align: center; }
        th { background-color: #0284c7; }
        input, select, textarea { padding: 8px; border-radius: 5px; border: 1px solid #475569; margin: 4px 0; width: 95%; background: #f8fafc; color: #000; }
    </style>
</head>
<body>
<div class="container">

    {% if role == "none" %}
        <h1>⚽ سوپرلیگ کارتی (نسخه وب ۲) ⚽</h1>
        <p>لطفاً کد مربیگری یا رمز عبور مدیریت را وارد کنید:</p>
        <form method="POST" action="/login">
            <input type="text" name="code" placeholder="کد مربی یا رمز ادمین" style="width: 80%; text-align:center;" required><br><br>
            <button type="submit" class="btn" style="width: 85%;">🔓 ورود به پنل</button>
        </form>
        {% if error %} <p style="color: #ef4444; font-weight: bold;">{{ error }}</p> {% endif %}

    {% elif role == "admin" %}
        <h2>👑 داشبورد ادمین سوپرلیگ</h2>
        <div style="text-align:center;">
            <button class="btn" onclick="showSec('adm-teams')">👥 تیم‌ها & داشبوردها</button>
            <button class="btn" onclick="showSec('adm-matches')">📅 بازی‌ها & نتایج</button>
            <button class="btn" onclick="showSec('adm-tournaments')">🏆 تورنمنت‌ها</button>
            <button class="btn" onclick="showSec('adm-standards')">🌍 تیم‌های استاندارد</button>
            <button class="btn" onclick="showSec('adm-locks')">🔒 دسترسی اکانت‌ها</button>
            <button class="btn" onclick="showSec('adm-transfers')">📩 پیام‌های نقل و انتقالات</button>
            <a href="/" class="btn" style="background:#ef4444;">خروج</a>
        </div>

        <div id="adm-teams" class="section active">
            <h3>➕ ایجاد تیم جدید (دریافت هزینه پی‌وی)</h3>
            <form method="POST" action="/admin/create_team">
                <input type="text" name="t_name" placeholder="نام تیم مربی خریدار" required>
                <button type="submit" class="btn">ایجاد تیم و صدور کد ۶ رقمی</button>
            </form>

            <h3>⚙️ داشبورد و ویرایش جزئیات مربیان</h3>
            <table>
                <tr>
                    <th>تیم (کد)</th>
                    <th>اکانت</th>
                    <th>سکه/اعتبار/کیف</th>
                    <th>عملیات ویرایش</th>
                </tr>
                {% for team in teams %}
                <tr>
                    <td><b>{{ team[1] }}</b><br><code>{{ team[0] }}</code></td>
                    <td>{{ team[6] }}</td>
                    <td>🪙{{ team[2] }}<br>💎{{ team[3] }}<br>💳{{ team[5] }}</td>
                    <td>
                        <form method="POST" action="/admin/update_coach" style="margin:0;">
                            <input type="hidden" name="code" value="{{ team[0] }}">
                            <select name="acc_type" style="width:70px; padding:2px;">
                                <option value="رایگان" {% if team[6]=='رایگان' %}selected{% endif %}>رایگان</option>
                                <option value="نرمال" {% if team[6]=='نرمال' %}selected{% endif %}>نرمال</option>
                                <option value="حرفه ای" {% if team[6]=='حرفه ای' %}selected{% endif %}>حرفه‌ای</option>
                            </select>
                            <input type="number" name="u_coins" value="{{ team[2] }}" style="width:45px; padding:2px;" title="سکه">
                            <input type="number" name="u_credit" value="{{ team[3] }}" style="width:45px; padding:2px;" title="اعتبار">
                            <button type="submit" style="font-size:10px; cursor:pointer;">💾 ثبت تغییرات</button>
                        </form>
                        <hr style="margin:2px; border-color:#475569;">
                        <a href="/admin/delete_team/{{ team[0] }}" onclick="return confirm('حذف تیمی؟')" style="color:#ef4444; font-size:11px;">🗑️ حذف کامل تیم</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="adm-matches" class="section">
            <h3>📅 اضافه کردن بازی آینده جدید</h3>
            <form method="POST" action="/admin/create_match">
                <input type="text" name="t_a" placeholder="تیم اول" required>
                <input type="text" name="t_b" placeholder="تیم دوم" required>
                <input type="text" name="tour_name" placeholder="نام تورنمنت مربوطه" required>
                <input type="text" name="desc" placeholder="توضیحات بازی">
                <button type="submit" class="btn">ثبت بازی فعال</button>
            </form>

            <h3>⚽ ثبت نتیجه بازی‌های انجام شده</h3>
            <table>
                <tr>
                    <th>تورنمنت</th>
                    <th>مسابقه</th>
                    <th>وضعیت/نتیجه</th>
                </tr>
                {% for m in matches %}
                <tr>
                    <td>{{ m[3] }}</td>
                    <td>{{ m[1] }} vs {{ m[2] }}</td>
                    <td>
                        <form method="POST" action="/admin/submit_result" style="margin:0;">
                            <input type="hidden" name="m_id" value="{{ m[0] }}">
                            <input type="text" name="res_text" value="{{ m[5] }}" style="width:80px; padding:2px;">
                            <button type="submit" style="font-size:10px;">ثبت</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="adm-tournaments" class="section">
            <h3>🏆 تعریف تورنمنت جدید</h3>
            <form method="POST" action="/admin/create_tournament">
                <input type="text" name="tour_name" placeholder="نام تورنمنت جدید" required>
                <button type="submit" class="btn">ایجاد و باز کردن ثبت نام</button>
            </form>
            <h3>📊 آپلود عکس جدول/گلزنان برای تورنمنت فعال</h3>
            <form method="POST" action="/admin/upload_tour_image">
                <input type="text" name="tour_name" placeholder="نام دقیق تورنمنت" required>
                <input type="text" name="img_url" placeholder="لینک عکس شیت / جدول / گلزنان" required>
                <button type="submit" class="btn">بروزرسانی مدیا شیت</button>
            </form>
        </div>

        <div id="adm-standards" class="section">
            <h3>🌍 افزودن لیگ استاندارد جدید</h3>
            <form method="POST" action="/admin/add_std_league">
                <input type="text" name="l_name" placeholder="نام لیگ" required>
                <button type="submit" class="btn">ایجاد لیگ</button>
            </form>

            <h3>🛡️ ثبت تیم استاندارد داخل لیگ</h3>
            <form method="POST" action="/admin/add_std_team">
                <input type="text" name="t_name" placeholder="نام تیم استاندارد" required>
                <input type="number" name="credit_req" placeholder="اعتبار مورد نیاز برای انتخاب" required>
                <textarea name="p_list" placeholder="لیست متنی بازیکنان تیم" rows="2"></textarea>
                <input type="text" name="cards_url" placeholder="لینک فایل عکس یا کارت‌ها">
                <button type="submit" class="btn">ثبت تیم استاندارد</button>
            </form>
        </div>

        <div id="adm-locks" class="section">
            <h3>🔒 قفل یا باز کردن دکمه‌ها</h3>
            <form method="POST" action="/admin/update_permissions">
                <select name="target_acc">
                    <option value="رایگان">اکانت رایگان</option>
                    <option value="نرمال">اکانت نرمال</option>
                    <option value="حرفه ای">اکانت حرفه‌ای</option>
                </select><br>
                <label><input type="checkbox" name="lock_tour" value="1" style="width:auto;"> قفل کردن بخش تورنمنت‌ها</label><br>
                <label><input type="checkbox" name="lock_league" value="1" style="width:auto;"> قفل کردن بخش لیگ‌های استاندارد</label><br>
                <button type="submit" class="btn">اعمال قفل / محدودیت‌ها</button>
            </form>
        </div>

        <div id="adm-transfers" class="section">
            <h3>📩 آرشیو پیام‌های توافقی نقل و انتقالات</h3>
            {% for log in logs %}
                {% if log[1] == 'نقل و انتقالات' %}
                <div style="background:#1e293b; padding:8px; margin:4px 0; border-right:4px solid #38bdf8;">
                    <b>فرستنده (تیم): {{ log[0] }}</b><br>
                    <span>شرح توافق: {{ log[2] }}</span>
                </div>
                {% endif %}
            {% endfor %}
        </div>

    {% elif role == "coach" %}
        <h2>🛡️ پنل مربیگری: {{ data[1] }}</h2>
        
        <div class="status-card">
            🪙 موجودی سکه: <b>{{ data[2] }}</b> | 💎 اعتبار: <b>{{ data[3] }}</b><br>
            🔄 کارت نقل و انتقالات: <b>{{ data[4] }}</b> | 💳 کیف پول (نمادین): <b>{{ data[5] }} تومان</b><br>
            🎖️ نوع اکانت شما: <span style="color:#38bdf8; font-weight:bold;">{{ data[6] }}</span>
        </div>

        <div class="grid-menu">
            <button class="btn" onclick="showSec('c-team')">۱. 🏃‍♂️ تیم من & کارت‌ها</button>
            <button class="btn" onclick="showSec('c-nextmatch')">۲. 📅 بازی پیش رو</button>
            <button class="btn" onclick="showSec('c-history')">۳. 📜 تاریخچه بازی‌ها</button>
            <button class="btn" onclick="showSec('c-honors')">۴. 🏆 افتخارات من</button>
            <button class="btn" onclick="showSec('c-tournaments')">۵. 🎪 تورنمنت‌ها</button>
            <button class="btn" onclick="showSec('c-standards')">۶. 🌍 تیم‌های استاندارد</button>
            <button class="btn" onclick="showSec('c-transfer')">۷. 🔄 ثبت نقل و انتقالات</button>
            <button class="btn" onclick="showSec('c-shop')">۸. 🏪 فروشگاه کارتی</button>
            <button class="btn" onclick="showSec('c-contact')">۹. 📞 ارتباط با ما</button>
        </div>
        <br><a href="/" class="btn" style="background:#ef4444; width:90px; display:inline-block;">🔒 خروج</a>

        <div id="c-team" class="section active">
            <h3>🏃‍♂️ بازیکنان تحت قرارداد شما</h3>
            <div id="coach-players-list"></div>
        </div>

        <div id="c-nextmatch" class="section">
            <h3>📅 بازی‌های آینده برنامه‌ریزی شده</h3>
            {% for m in matches %}
                {% if m[5] == 'برگزاری نشده' %}
                <div style="background:#1e293b; padding:10px; margin-bottom:8px; border-radius:6px;">
                    📌 <b>تورنمنت: {{ m[3] }}</b><br>
                    ⚔️ مسابقه: {{ m[1] }} vs {{ m[2] }}<br>
                    📝 توضیحات: {{ m[4] }}<br>
                    <button class="btn" style="font-size:11px;" onclick="alert('مکانیزم ترکیب: فرم ارسال متن یا تصویر ترکیب تیم را برای مدیر ارسال کنید.')">📋 ارسال ترکیب (حداقل ۷ بازیکن)</button>
                </div>
                {% endif %}
            {% endfor %}
        </div>

        <div id="c-history" class="section">
            <h3>📜 نتایج ثبت شده بازی‌های قبلی</h3>
            <table>
                <tr>
                    <th>تورنمنت</th>
                    <th>مسابقه</th>
                    <th>نتیجه نهایی</th>
                </tr>
                {% for m in matches %}
                {% if m[5] != 'برگزاری نشده' %}
                <tr>
                    <td>{{ m[3] }}</td>
                    <td>{{ m[1] }} vs {{ m[2] }}</td>
                    <td style="color:#38bdf8; font-weight:bold;">{{ m[5] }}</td>
                </tr>
                {% endif %}
                {% endfor %}
            </table>
        </div>

        <div id="c-honors" class="section">
            <h3>🏆 تالار افتخارات مربی</h3>
            <p style="background:#1e293b; padding:15px; border-radius:6px; font-style:italic;">" {{ data[7] }} "</p>
        </div>

        <div id="c-tournaments" class="section">
            {% if perms[0] == 1 %}
                <p style="color:#ef4444; font-weight:bold;">🔒 این بخش برای سطح اکانت شما قفل شده است.</p>
            {% else %}
                <h3>🎪 تورنمنت‌های فعال</h3>
                {% for t in tours %}
                <div style="background:#1e293b; padding:10px; margin-bottom:8px; border-radius:6px;">
                    🏆 <b>نام تورنمنت: {{ t[1] }}</b> (وضعیت: {{ t[2] }})<br>
                    {% if t[2] == 'ثبت نام' %}
                        <button class="btn" onclick="regTour('{{ t[0] }}')">📩 ارسال درخواست ثبت نام</button>
                    {% endif %}
                    {% if t[3] %}
                        <br><a href="{{ t[3] }}" target="_blank" style="color:#38bdf8;">🖼️ مشاهده عکس شیت، جدول و گلزنان</a>
                    {% endif %}
                </div>
                {% endfor %}
            {% endif %}
        </div>

        <div id="c-standards" class="section">
            {% if perms[1] == 1 %}
                <p style="color:#ef4444; font-weight:bold;">🔒 این بخش برای سطح اکانت شما قفل شده است.</p>
            {% else %}
                <h3>🌍 تیم‌های استاندارد فدراسیون</h3>
                <button class="btn" onclick="alert('لیست کامل تیم‌های استاندارد مجاز در داشبورد فعال است.')">مشاهده راهنما و لیست تیم‌ها</button>
            {% endif %}
        </div>

        <div id="c-transfer" class="section">
            <h3>🔄 فرم رسمی اعلام نقل و انتقالات</h3>
            <input type="text" id="trans-text-input" placeholder="مثال: واگذاری بازیکن X به تیم مربی Y در قبال ۲۰۰ سکه.">
            <button class="btn" onclick="submitTransfer()">📩 ارسال رسمی برای مدیر</button>
        </div>

        <div id="c-shop" class="section">
            <h3>🏪 فروشگاه رسمی سوپرلیگ</h3>
            <div style="background:#1e293b; padding:10px; margin-bottom:10px; border-radius:6px;">
                <h4>🎁 باکس شانسی هیرو</h4>
                <p>💰 هزینه هر شانس: <b>۳۵۰ سکه</b></p>
                <button class="btn" style="background:#eab308; color:#000;" onclick="buyBox()">🎰 باز کردن باکس شانسی</button>
                <div id="box-output" style="margin-top:8px; color:#eab308; font-weight:bold;"></div>
            </div>
            
            <div style="background:#1e293b; padding:10px; border-radius:6px;">
                <h4>🛒 تمدید قرارداد</h4>
                <p>کارت تمدید فوری قرارداد مربی (💰 قیمت: ۲۰۰ سکه)</p>
                <button class="btn" onclick="buyDirect('کارت تمدید قرارداد', 200)">💳 خرید مستقیم و کسر سکه</button>
            </div>
        </div>

        <div id="c-contact" class="section">
            <h3>📞 ارتباط با مدیریت</h3>
            <p style="font-size:18px; color:#38bdf8; font-weight:bold;">🆔 آیدی ادمین سوپرلیگ: @Admin_SuperLeague</p>
        </div>
    {% endif %}

</div>

<script>
    const code = "{{ code }}";
    function showSec(id) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById(id).classList.add('active');
    }
    
    if(code && "{{ role }}" === "coach") {
        fetch('/get_players?code=' + code)
            .then(res => res.json())
            .then(data => {
                const div = document.getElementById('coach-players-list');
                div.innerHTML = '';
                if(data.length === 0) div.innerHTML = '<p>هنوز بازیکنی برای تیم شما ثبت نشده است.</p>';
                data.forEach(p => {
                    let b = document.createElement('button');
                    b.className = 'btn';
                    b.style.display = 'block';
                    b.style.width = '100%';
                    b.innerText = "🏃‍♂️ " + p.name;
                    b.onclick = () => {
                        if(p.card) { alert("🖼️ لینک کارت بازیکن:\\n" + p.card); }
                        else { alert("کارت تصویری برای این بازیکن آپلود نشده است."); }
                    };
                    div.appendChild(b);
                });
            });
    }

    function buyBox() {
        fetch('/buy_lucky_box', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: code })
        }).then(res => res.json()).then(data => {
            if(data.success) {
                document.getElementById('box-output').innerHTML = "🎉 بازیکن جدید باز شد: " + data.player;
            } else { alert(data.msg); }
        });
    }

    function buyDirect(item, price) {
        fetch('/buy_direct', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: code, item: item, price: price })
        }).then(res => res.json()).then(data => { alert(data.msg); });
    }

    function submitTransfer() {
        let txt = document.getElementById('trans-text-input').value;
        if(!txt) return;
        fetch('/submit_transfer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: code, msg: txt })
        }).then(res => res.json()).then(data => {
            alert(data.msg);
            document.getElementById('trans-text-input').value = '';
        });
    }

    function regTour(tId) {
        fetch('/reg_tournament', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: code, tour_id: tId })
        }).then(res => res.json()).then(data => { alert(data.msg); });
    }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, role="none", error=None)

@app.route('/login', methods=['POST'])
def login():
    try:
        init_db()  # دیتابیس را مجبور می‌کند قبل از ورود حتما جدول‌ها را بسازد
    except Exception as e:
        pass
        
    code = request.form.get('code', '').strip()
    if code == ADMIN_PASSWORD:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coaches")
        teams = cursor.fetchall()
        cursor.execute("SELECT team_name, log_type, message FROM admin_logs ORDER BY id DESC")
        logs = cursor.fetchall()
        cursor.execute("SELECT * FROM matches")
        matches = cursor.fetchall()
        cursor.execute("SELECT * FROM tournaments")
        tours = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template_string(HTML_TEMPLATE, role="admin", teams=teams, logs=logs, matches=matches, tours=tours)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coaches WHERE login_code = %s", (code,))
    coach = cursor.fetchone()
    
    if coach:
        cursor.execute("SELECT tournament_locked, league_locked FROM account_permissions WHERE account_type = %s", (coach[6],))
        perms = cursor.fetchone() or (0, 0)
        cursor.execute("SELECT * FROM matches")
        matches = cursor.fetchall()
        cursor.execute("SELECT * FROM tournaments")
        tours = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template_string(HTML_TEMPLATE, role="coach", data=coach, code=code, perms=perms, matches=matches, tours=tours)
    
    cursor.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, role="none", error="❌ کد ورود یا رمز عبور نامعتبر است.")

@app.route('/admin/create_team', methods=['POST'])
def admin_create_team():
    t_name = request.form.get('t_name', '').strip()
    code = str(random.randint(100000, 999999))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO coaches (login_code, team_name) VALUES (%s, %s)", (code, t_name))
    conn.commit()
    cursor.close()
    conn.close()
    return f"<h3>تیم ساخته شد! کد ۶ رقمی مربی: <b style='color:cyan;'>{code}</b></h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/update_coach', methods=['POST'])
def admin_update_coach():
    code = request.form.get('code')
    acc_type = request.form.get('acc_type')
    coins = int(request.form.get('u_coins'))
    credit = int(request.form.get('u_credit'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE coaches SET account_type=%s, coins=%s, credit=%s WHERE login_code=%s", (acc_type, coins, credit, code))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>داشبورد مربی بروزرسانی شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/delete_team/<code>')
def admin_delete_team(code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM coaches WHERE login_code = %s", (code,))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>تیم حذف شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/get_players')
def get_players():
    code = request.args.get('code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT player_name, card_url FROM players WHERE team_code=%s", (code,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{"name": r[0], "card": r[1]} for r in rows])

@app.route('/buy_lucky_box', methods=['POST'])
def buy_lucky_box():
    code = request.json.get('code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coins, team_name FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    if not coach or coach[0] < 350:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "msg": "سکه کافی نیست!"})
    
    win = random.choice(LUCKY_BOX_PLAYERS)
    new_coins = coach[0] - 350
    cursor.execute("UPDATE coaches SET coins=%s WHERE login_code=%s", (new_coins, code))
    cursor.execute("INSERT INTO players (team_code, player_name) VALUES (%s, %s)", (code, win["name"]))
    cursor.execute("INSERT INTO admin_logs (team_name, log_type, message) VALUES (%s, 'باکس شانسی', %s)", (coach[1], f"باز کردن باکس و دریافت بازیکن {win['name']}"))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "player": win["name"]})

@app.route('/buy_direct', methods=['POST'])
def buy_direct():
    data = request.json
    code, item, price = data.get('code'), data.get('item'), int(data.get('price'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coins, team_name FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    if coach and coach[0] >= price:
        cursor.execute("UPDATE coaches SET coins=%s WHERE login_code=%s", (coach[0]-price, code))
        cursor.execute("INSERT INTO admin_logs (team_name, log_type, message) VALUES (%s, 'خرید مستقیم', %s)", (coach[1], f"خرید مستقیم {item}"))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"msg": "✅ خرید موفقیت‌آمیز بود."})
    cursor.close()
    conn.close()
    return jsonify({"msg": "❌ موجودی سکه کافی نیست."})

@app.route('/submit_transfer', methods=['POST'])
def submit_transfer():
    data = request.json
    code, msg = data.get('code'), data.get('msg')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    if coach:
        cursor.execute("INSERT INTO admin_logs (team_name, log_type, message) VALUES (%s, %s, %s)", (coach[1], 'نقل و انتقالات', msg))
        conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"msg": "📩 درخواست با موفقیت برای مدیر ارسال شد."})

@app.route('/admin/create_match', methods=['POST'])
def create_match():
    t_a = request.form.get('t_a')
    t_b = request.form.get('t_b')
    t_name = request.form.get('tour_name')
    desc = request.form.get('desc')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO matches (team_a, team_b, tournament_name, description) VALUES (%s, %s, %s, %s)", (t_a, t_b, t_name, desc))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>مسابقه جدید ثبت شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/submit_result', methods=['POST'])
def submit_result():
    m_id = request.form.get('m_id')
    res = request.form.get('res_text')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET result=%s WHERE id=%s", (res, m_id))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>نتیجه ثبت شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/create_tournament', methods=['POST'])
def create_tournament():
    name = request.form.get('tour_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tournaments (name) VALUES (%s)", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>تورنمنت ایجاد شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/upload_tour_image', methods=['POST'])
def upload_tour_image():
    name = request.form.get('tour_name')
    url = request.form.get('img_url')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournaments SET stats_image=%s, status='در حال برگزاری' WHERE name=%s", (url, name))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>مدیا شیت آپدیت شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/update_permissions', methods=['POST'])
def update_permissions():
    target = request.form.get('target_acc')
    lock_tour = 1 if request.form.get('lock_tour') else 0
    lock_league = 1 if request.form.get('lock_league') else 0
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE account_permissions SET tournament_locked=%s, league_locked=%s WHERE account_type=%s", (lock_tour, lock_league, target))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>قفل‌ها با موفقیت اعمال شدند.</h3><br><a href='/'>بازگشت</a>"

@app.route('/reg_tournament', methods=['POST'])
def reg_tournament():
    data = request.json
    code, t_id = data.get('code'), data.get('tour_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    if coach:
        cursor.execute("INSERT INTO tournament_regs (tournament_id, team_name) VALUES (%s, %s)", (t_id, coach[0]))
        conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"msg": "✅ درخواست ثبت نام در تورنمنت ارسال گردید."})

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        pass
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
