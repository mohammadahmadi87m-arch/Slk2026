import os
import random
import string
import psycopg2
import base64
from flask import Flask, request, render_template_string, jsonify, redirect

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
# تغییر ۱: رمز ورود مدیریت جدید
ADMIN_PASSWORD = "admiin49g" 

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
            stars INTEGER DEFAULT 3,
            cards_file_url TEXT DEFAULT ''
        )
    ''')
    
    # جدول بازیکنان تیم‌های استاندارد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standard_players (
            id SERIAL PRIMARY KEY,
            team_id INTEGER,
            player_name TEXT,
            card_url TEXT DEFAULT ''
        )
    ''')
    
    # ۵. جدول مسابقات و ثبت ترکیب‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            team_a TEXT,
            team_b TEXT,
            tournament_name TEXT,
            description TEXT,
            result TEXT DEFAULT 'برگزاری نشده',
            status TEXT DEFAULT 'فعال',
            allow_own_team INTEGER DEFAULT 1,
            team_a_lineup TEXT DEFAULT '',
            team_b_lineup TEXT DEFAULT ''
        )
    ''')
    
    # ۶. جدول تورنمنت‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id SERIAL PRIMARY KEY,
            name TEXT,
            status TEXT DEFAULT 'ثبت نام',
            table_imgs TEXT DEFAULT '',
            result_imgs TEXT DEFAULT '',
            standing_imgs TEXT DEFAULT '',
            scorer_imgs TEXT DEFAULT '',
            assist_imgs TEXT DEFAULT '',
            cleansheet_imgs TEXT DEFAULT ''
        )
    ''')
    
    # ۷. جدول ثبت‌نام تورنمنت‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_regs (
            id SERIAL PRIMARY KEY,
            tournament_id INTEGER,
            team_code TEXT,
            team_name TEXT,
            status TEXT DEFAULT 'در انتظار تایید'
        )
    ''')

    # ۸. جدول مجوزها و قفل‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_permissions (
            account_type TEXT PRIMARY KEY,
            tournament_locked INTEGER DEFAULT 0,
            league_locked INTEGER DEFAULT 0,
            shop_locked INTEGER DEFAULT 0,
            player_locked INTEGER DEFAULT 0,
            team_locked INTEGER DEFAULT 0,
            match_locked INTEGER DEFAULT 0,
            transfer_locked INTEGER DEFAULT 0,
            honors_locked INTEGER DEFAULT 0
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

    # ۱۱. جداول مربوط به بخش فروشگاه کارتی پیشرفته و محصولات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_products (
            id SERIAL PRIMARY KEY,
            name TEXT,
            sale_type TEXT, 
            price_coins INTEGER DEFAULT 0,
            price_money INTEGER DEFAULT 0,
            reward_coins INTEGER DEFAULT 0,
            reward_credit INTEGER DEFAULT 0,
            reward_transfers INTEGER DEFAULT 0,
            reward_players TEXT DEFAULT ''
        )
    ''')

    # جدول آیتم‌های شانس برای باکس‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS box_items (
            id SERIAL PRIMARY KEY,
            product_id INTEGER,
            player_name TEXT,
            chance_weight INTEGER DEFAULT 5
        )
    ''')

    # جدول کدهای پیگیری مربیان
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracking_codes (
            id SERIAL PRIMARY KEY,
            tracking_code TEXT UNIQUE,
            team_name TEXT,
            product_name TEXT,
            details TEXT
        )
    ''')
    
    # پر کردن پیش‌فرض مجوزها به صورت کاملاً باز (0)
    cursor.execute("SELECT COUNT(*) FROM account_permissions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account_permissions VALUES ('رایگان', 0, 0, 0, 0, 0, 0, 0, 0)")
        cursor.execute("INSERT INTO account_permissions VALUES ('نرمال', 0, 0, 0, 0, 0, 0, 0, 0)")
        cursor.execute("INSERT INTO account_permissions VALUES ('حرفه ای', 0, 0, 0, 0, 0, 0, 0, 0)")

    conn.commit()
    cursor.close()
    conn.close()

def generate_mixed_code():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

def generate_tracking_code():
    return 'TRK-' + ''.join(random.choice(string.digits + string.ascii_uppercase) for _ in range(8))


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مدیریت تیم سوپرلیگ کارتی فقط</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 10px; text-align: center; }
        .container { max-width: 850px; margin: 0 auto; background: #1e293b; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
        h1, h2, h3 { color: #38bdf8; }
        .btn { background-color: #0284c7; color: white; border: none; padding: 8px 15px; margin: 4px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn:hover { background-color: #0369a1; }
        .grid-menu { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 15px; }
        .status-card { background: #334155; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; line-height: 1.6; text-align: right; }
        .section { display: none; margin-top: 15px; padding: 15px; background: #334155; border-radius: 8px; text-align: right; }
        .active { display: block; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
        th, td { border: 1px solid #475569; padding: 6px; text-align: center; }
        th { background-color: #0284c7; }
        input, select, textarea { padding: 8px; border-radius: 5px; border: 1px solid #475569; margin: 4px 0; width: 95%; background: #f8fafc; color: #000; }
        .player-card-preview { max-width: 100px; max-height: 130px; display: block; margin: 5px auto; border-radius: 4px; }
        .box-product { border: 1px dashed #38bdf8; padding: 10px; margin: 10px 0; border-radius: 6px; background: #1e293b; }
    </style>
</head>
<body>
<div class="container">

    {% if role == "none" %}
        <h1>⚽ مدیریت تیم سوپرلیگ کارتی فقط ⚽</h1>
        <p>لطفاً کد مربیگری یا رمز عبور مدیریت را وارد کنید:</p>
        <form method="POST" action="/login">
            <input type="text" name="code" placeholder="کد مربی یا رمز ادمین" style="width: 80%; text-align:center;" required><br><br>
            <button type="submit" class="btn" style="width: 85%;">🔓 ورود به پنل</button>
        </form>
        {% if error %} <p style="color: #ef4444; font-weight: bold;">{{ error }}</p> {% endif %}

    {% elif role == "admin" %}
        <h2>👑 داشبورد ادمین سوپرلیگ</h2>
        <div style="text-align:center;">
            <button class="btn" onclick="showSec('adm-teams')">👥 تیم‌ها & مربیان</button>
            <button class="btn" onclick="showSec('adm-matches')">📅 بازی‌ها & نتایج</button>
            <button class="btn" onclick="showSec('adm-tournaments')">🏆 تورنمنت‌ها</button>
            <button class="btn" onclick="showSec('adm-standards')">🌍 تیم‌های استاندارد</button>
            <button class="btn" onclick="showSec('adm-locks')">🔒 دسترسی اکانت‌ها</button>
            <button class="btn" onclick="showSec('adm-transfers')">📩 پیام‌های نقل و انتقالات</button>
            <button class="btn" onclick="showSec('adm-shop')">🏪 مدیریت فروشگاه</button>
            <button class="btn" onclick="showSec('adm-tracking')">🔍 پیگیری کدهای خرید</button>
            <a href="/" class="btn" style="background:#ef4444;">خروج</a>
        </div>

        <div id="adm-teams" class="section active">
            <h3>➕ ایجاد تیم جدید (کد ۶ رقمی ترکیبی)</h3>
            <form method="POST" action="/admin/create_team">
                <input type="text" name="t_name" placeholder="نام تیم مربی خریدار" required>
                <button type="submit" class="btn">ایجاد تیم و صدور کد ترکیبی</button>
            </form>

            <h3>⚙️ داشبورد و ویرایش جزئیات مربیان</h3>
            <table>
                <tr>
                    <th>تیم (کد)</th>
                    <th>اکانت</th>
                    <th>سکه/اعتبار/کیف/کارت</th>
                    <th>عملیات ویرایش اطلاعات & بازیکنان</th>
                </tr>
                {% for team in teams %}
                <tr>
                    <td><b>{{ team[1] }}</b><br><code>{{ team[0] }}</code></td>
                    <td>{{ team[6] }}</td>
                    <td>🪙{{ team[2] }}<br>💎{{ team[3] }}<br>💳 کیف پول: {{ team[5] }} تومان<br>🔄 کارت نقل و انتقال: {{ team[4] }}</td>
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
                            <input type="number" name="u_wallet" value="{{ team[5] }}" style="width:55px; padding:2px;" title="کیف پول">
                            <input type="number" name="u_trans" value="{{ team[4] }}" style="width:40px; padding:2px;" title="کارت نقل و انتقال">
                            <button type="submit" style="font-size:10px; cursor:pointer; background:#22c55e; color:white; border:none; padding:3px; border-radius:3px;">💾 ثبت</button>
                        </form>
                        
                        <hr style="margin:5px 0;">
                        <form method="POST" action="/admin/update_honors" style="margin:0;">
                            <input type="hidden" name="code" value="{{ team[0] }}">
                            <input type="text" name="t_honors" value="{{ team[7] }}" placeholder="متن افتخارات تیم" style="width:130px; font-size:10px; padding:2px;">
                            <button type="submit" style="font-size:10px; background:#eab308; border:none; padding:3px;">🏆 ثبت افتخار</button>
                        </form>

                        <hr style="margin:5px 0;">
                        <div style="background:#1e293b; padding:5px; text-align:right; border-radius:4px; margin-top:5px;">
                            <span style="font-size:11px; color:#38bdf8;">🏃‍♂️ مدیریت بازیکنان تیم:</span>
                            <a href="/admin/manage_players/{{ team[0] }}" class="btn" style="padding:2px 5px; font-size:10px; background:#a855f7;">✏️ ویرایش و افزودن بازیکنان</a>
                        </div>

                        <hr style="margin:5px 0;">
                        <a href="/admin/delete_team/{{ team[0] }}" onclick="return confirm('حذف کامل تیمی؟')" style="color:#ef4444; font-size:11px; font-weight:bold;">🗑️ حذف کامل تیم</a>
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
                <label><input type="checkbox" name="allow_own" value="1" checked style="width:auto;"> مربیان مجاز به بازی با تیم خود (اصلی) هستند؟</label><br><br>
                <button type="submit" class="btn">ثبت بازی فعال</button>
            </form>

            <h3>⚽ ثبت نتیجه بازی‌های انجام شده</h3>
            <table>
                <tr>
                    <th>تورنمنت</th>
                    <th>مسابقه</th>
                    <th>ترکیب تیم‌ها</th>
                    <th>وضعیت/نتیجه نهایی</th>
                </tr>
                {% for m in matches %}
                <tr>
                    <td>{{ m[3] }}</td>
                    <td>{{ m[1] }} vs {{ m[2] }}</td>
                    <td style="font-size:10px; text-align:right; background:#1e293b; color:#cbd5e1;">
                        <b>ترکیب A:</b> {{ m[8] or 'ثبت نشده' }}<br>
                        <b>ترکیب B:</b> {{ m[9] or 'ثبت نشده' }}
                    </td>
                    <td>
                        <form method="POST" action="/admin/submit_result" style="margin:0;">
                            <input type="hidden" name="m_id" value="{{ m[0] }}">
                            <input type="text" name="res_text" value="{{ m[5] }}" style="width:100px; padding:2px;" placeholder="مثلا ۲-۱ به نفع A">
                            <button type="submit" style="font-size:10px; background:#22c55e; color:white; border:none; padding:3px 6px;">ثبت نتیجه</button>
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
            
            <h3>📋 مدیریت درخواست‌ها و تیم‌های ثبت‌نام شده هر تورنمنت</h3>
            {% for t in tours %}
                <div style="background:#1e293b; padding:10px; margin-bottom:10px; border-radius:6px; border:1px solid #475569;">
                    <h4>🏆 {{ t[1] }} (وضعیت: {{ t[2] }})</h4>
                    
                    {% if t[2] == 'ثبت نام' %}
                        <p style="font-size:11px; color:#38bdf8;">⏳ تیم‌های متقاضی ثبت‌نام:</p>
                        <table style="margin-bottom:8px;">
                            <tr>
                                <th>نام تیم</th>
                                <th>وضعیت</th>
                                <th>عملیات</th>
                            </tr>
                            {% for reg in regs %}
                                {% if reg[1] == t[0] %}
                                <tr>
                                    <td>{{ reg[3] }}</td>
                                    <td>{{ reg[4] }}</td>
                                    <td>
                                        {% if reg[4] == 'در انتظار تایید' %}
                                            <a href="/admin/approve_reg/{{ reg[0] }}" class="btn" style="background:#22c55e; padding:2px 5px; font-size:10px;">✅ تایید</a>
                                            <a href="/admin/reject_reg/{{ reg[0] }}" class="btn" style="background:#ef4444; padding:2px 5px; font-size:10px;">❌ رد</a>
                                        {% else %}
                                            تکمیل شده
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endif %}
                            {% endfor %}
                        </table>
                        <a href="/admin/start_tournament/{{ t[0] }}" class="btn" style="background:#eab308; color:black;">🚀 تکمیل ظرفیت و شروع تورنمنت</a>
                    {% else %}
                        <p style="font-size:11px; color:#22c55e;">🛠️ داشبورد مدیریت چندرسانه‌ای تورنمنت (آپلود مستقیم فایل):</p>
                        <form method="POST" action="/admin/upload_tour_media" enctype="multipart/form-data">
                            <input type="hidden" name="t_id" value="{{ t[0] }}">
                            <select name="media_type" style="width:100px; font-size:11px; padding:3px;">
                                <option value="table">جدول بازی‌ها</option>
                                <option value="result">نتایج</option>
                                <option value="standing">جدول رده‌بندی</option>
                                option value="scorer">جدول گلزنان</option>
                                <option value="assist">جدول پاس گل‌ها</option>
                                <option value="cleansheet">جدول کلین شیت‌ها</option>
                            </select>
                            <input type="file" name="media_files" multiple accept="image/*" style="width:60%; font-size:11px;" required><br>
                            <button type="submit" class="btn" style="padding:4px 8px; font-size:11px; background:#a855f7;">📤 آپلود مستقیم تصاویر شاخص</button>
                        </form>
                    {% endif %}
                </div>
            {% endfor %}
        </div>

        <div id="adm-standards" class="section">
            <h3>🌍 افزودن لیگ استاندارد جدید</h3>
            <form method="POST" action="/admin/add_std_league">
                <input type="text" name="l_name" placeholder="نام لیگ" required>
                <button type="submit" class="btn">ایجاد لیگ</button>
            </form>

            <h3>🛡️ ثبت تیم استاندارد داخل لیگ</h3>
            <form method="POST" action="/admin/add_std_team">
                <select name="l_id" required>
                    {% for l in std_leagues %}
                        <option value="{{ l[0] }}">{{ l[1] }}</option>
                    {% endfor %}
                </select>
                <input type="text" name="t_name" placeholder="نام تیم استاندارد" required>
                <input type="number" name="credit_req" placeholder="اعتبار مورد نیاز برای انتخاب تیم" required>
                <input type="number" name="stars" placeholder="تعداد ستاره‌های تیم (۱ تا ۵)" min="1" max="5" required>
                <button type="submit" class="btn">ثبت تیم استاندارد</button>
            </form>

            <h3>🏃‍♂️ مدیریت بازیکنان تیم‌های استاندارد</h3>
            <table>
                <tr>
                    <th>تیم استاندارد</th>
                    <th>ستاره / اعتبار</th>
                    <th>عملیات مدیریت بازیکنان</th>
                </tr>
                {% for st in std_teams %}
                <tr>
                    <td>{{ st[2] }}</td>
                    <td>⭐{{ st[4] }} / 💎{{ st[3] }}</td>
                    <td>
                        <a href="/admin/manage_std_players/{{ st[0] }}" class="btn" style="font-size:10px; background:#a855f7; padding:3px 6px;">👥 افزودن / ویرایش بازیکنان</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="adm-locks" class="section">
            <h3>🔒 قفل یا باز کردن دکمه‌ها و تمام بخش‌ها</h3>
            <form method="POST" action="/admin/update_permissions">
                <select name="target_acc">
                    <option value="رایگان">اکانت رایگان</option>
                    <option value="نرمال">اکانت نرمال</option>
                    <option value="حرفه ای">اکانت حرفه‌ای</option>
                </select><br><br>
                <div style="text-align:right; display:grid; grid-template-columns: 1fr 1fr; gap:10px; font-size:12px;">
                    <label><input type="checkbox" name="lock_tour" value="1" style="width:auto;"> قفل تورنمنت‌ها</label>
                    <label><input type="checkbox" name="lock_league" value="1" style="width:auto;"> قفل لیگ‌های استاندارد</label>
                    <label><input type="checkbox" name="lock_shop" value="1" style="width:auto;"> قفل فروشگاه کارتی</label>
                    <label><input type="checkbox" name="lock_player" value="1" style="width:auto;"> قفل بازیکنان من</label>
                    <label><input type="checkbox" name="lock_team" value="1" style="width:auto;"> قفل تیم من</label>
                    <label><input type="checkbox" name="lock_match" value="1" style="width:auto;"> قفل بازی‌های پیش رو</label>
                    <label><input type="checkbox" name="lock_transfer" value="1" style="width:auto;"> قفل نقل و انتقالات</label>
                    <label><input type="checkbox" name="lock_honors" value="1" style="width:auto;"> قفل افتخارات</label>
                </div><br>
                <button type="submit" class="btn">اعمال قفل / محدودیت‌های سراسری</button>
            </form>
        </div>

        <div id="adm-transfers" class="section">
            <h3>📩 آرشیو پیام‌های توافقی نقل و انتقالات مربیان</h3>
            {% if logs|length == 0 %}
                <p>هیچ پیامی در سیستم ثبت نشده است.</p>
            {% endif %}
            {% for log in logs %}
                {% if log[1] == 'نقل و انتقالات' %}
                <div style="background:#1e293b; padding:10px; margin:6px 0; border-right:4px solid #38bdf8; border-radius:4px;">
                    <b>فرستنده (تیم مربی): {{ log[0] }}</b><br>
                    <span style="color:#cbd5e1;">شرح توافق: {{ log[2] }}</span>
                </div>
                {% endif %}
            {% endfor %}
        </div>

        <div id="adm-shop" class="section">
            <h3>🏪 پنل مدیریت فروشگاه کارتی</h3>
            <div style="background:#1e293b; padding:10px; border-radius:6px; margin-bottom:15px;">
                <h4>➕ افزودن محصول جدید به فروشگاه</h4>
                <form method="POST" action="/admin/add_product">
                    <input type="text" name="p_name" placeholder="نام محصول (مثلا: پک طلایی آلمان)" required>
                    <select name="s_type" id="s_type_select" onchange="toggleShopFields()" required>
                        <option value="1">نوع ۱: فروش قطعی با سکه (پک ها)</option>
                        <option value="2">نوع ۲: خرید قطعی پولی (کیف پول / مستقیم)</option>
                        <option value="3">نوع ۳: خرید شانسی (باکس‌های گردونه شانس)</option>
                    </select>
                    
                    <div id="div_coin_price"><input type="number" name="price_coins" placeholder="قیمت محصول به سکه"></div>
                    <div id="div_money_price" style="display:none;"><input type="number" name="price_money" placeholder="قیمت محصول به تومان"></div>
                    
                    <div id="div_rewards">
                        <p style="font-size:11px; color:#38bdf8; margin:2px 0;">🎁 محتویات پاداش خرید قطعی (با ویرگول جدا کنید):</p>
                        <input type="number" name="r_coins" placeholder="تعداد سکه جایزه">
                        <input type="number" name="r_credit" placeholder="تعداد اعتبار جایزه">
                        <input type="number" name="r_transfers" placeholder="تعداد کارت نقل و انتقال جایزه">
                        <input type="text" name="r_players" placeholder="نام بازیکنان دریافتی پک (مثال: رونالدو,مسی)">
                    </div>
                    
                    <div id="div_chance_items" style="display:none;">
                        <p style="font-size:11px; color:#eab308;">🎰 برای افزودن بازیکنان و شانس گردونه باکس، ابتدا محصول را بسازید و سپس از بخش مدیریت شانس‌ها استفاده کنید.</p>
                    </div>
                    
                    <button type="submit" class="btn" style="background:#22c55e;">💾 ذخیره و انتشار محصول</button>
                </form>
            </div>

            <h3>📦 لیست محصولات فعال فروشگاه</h3>
            <table>
                <tr>
                    <th>نام محصول</th>
                    <th>نوع فروش</th>
                    <th>قیمت</th>
                    <th>عملیات</th>
                </tr>
                {% for p in products %}
                <tr>
                    <td><b>{{ p[1] }}</b></td>
                    <td>
                        {% if p[2] == '1' %} فروش قطعی با سکه 
                        {% elif p[2] == '2' %} خرید قطعی پولی 
                        {% else %} گردونه شانس باکس
                        {% endif %}
                    </td>
                    <td>
                        {% if p[2] == '1' or p[2] == '3' %} 🪙{{ p[3] }} سکه
                        {% else %} 💳 {{ p[4] }} تومان
                        {% endif %}
                    </td>
                    <td>
                        {% if p[2] == '3' %}
                            <a href="/admin/manage_box/{{ p[0] }}" class="btn" style="font-size:10px; background:#eab308; color:black; padding:2px 4px;">🎰 شانس‌ها</a>
                        {% endif %}
                        <a href="/admin/delete_product/{{ p[0] }}" class="btn" style="font-size:10px; background:#ef4444; padding:2px 4px;" onclick="return confirm('حذف محصول؟')">🗑️ حذف</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="adm-tracking" class="section">
            <h3>🔍 بخش پیگیری کدهای خرید و تراکنش مربیان</h3>
            <form method="POST" action="/admin/search_tracking">
                <input type="text" name="track_code" placeholder="کد پیگیری را وارد کنید" required>
                <button type="submit" class="btn">🔎 جستجو در دیتابیس</button>
            </form>
            {% if track_res %}
                <div style="background:#1e293b; padding:10px; border-radius:6px; margin-top:10px; text-align:right; border-left:4px solid #22c55e;">
                    <h4>نتیجه تراکنش پیگیری شده:</h4>
                    <p><b>تیم مربی:</b> {{ track_res[2] }}</p>
                    <p><b>محصول خریداری شده:</b> {{ track_res[3] }}</p>
                    <p><b>شرح جزییات و پاداش اعمال شده:</b> {{ track_res[4] }}</p>
                </div>
            {% endif %}
        </div>

        <script>
            function toggleShopFields() {
                var t = document.getElementById('s_type_select').value;
                if(t === '1') {
                    document.getElementById('div_coin_price').style.display = 'block';
                    document.getElementById('div_money_price').style.display = 'none';
                    document.getElementById('div_rewards').style.display = 'block';
                    document.getElementById('div_chance_items').style.display = 'none';
                } else if(t === '2') {
                    document.getElementById('div_coin_price').style.display = 'none';
                    document.getElementById('div_money_price').style.display = 'block';
                    document.getElementById('div_rewards').style.display = 'block';
                    document.getElementById('div_chance_items').style.display = 'none';
                } else if(t === '3') {
                    document.getElementById('div_coin_price').style.display = 'block';
                    document.getElementById('div_money_price').style.display = 'none';
                    document.getElementById('div_rewards').style.display = 'none';
                    document.getElementById('div_chance_items').style.display = 'block';
                }
            }
        </script>

    {% elif role == "coach" %}
        <h2>🛡️ پنل مربیگری: {{ data[1] }}</h2>
        
        <div class="status-card">
            🪙 موجودی سکه: <b>{{ data[2] }}</b> | 💎 اعتبار: <b>{{ data[3] }}</b><br>
            🔄 کارت نقل و انتقالات: <b>{{ data[4] }}</b> | 💳 کیف پول: <b>{{ data[5] }} تومان</b><br>
            🎖️ نوع اکانت شما: <span style="color:#38bdf8; font-weight:bold;">{{ data[6] }}</span>
        </div>

        <div class="grid-menu">
            {% if perms[4] == 0 %}<button class="btn" onclick="showSec('c-team')">۱. 🏃‍♂️ تیم من & کارت‌ها</button>{% endif %}
            {% if perms[5] == 0 %}<button class="btn" onclick="showSec('c-nextmatch')">۲. 📅 بازی پیش رو</button>{% endif %}
            <button class="btn" onclick="showSec('c-history')">۳. 📜 تاریخچه بازی‌ها</button>
            {% if perms[7] == 0 %}<button class="btn" onclick="showSec('c-honors')">۴. 🏆 افتخارات من</button>{% endif %}
            {% if perms[0] == 0 %}<button class="btn" onclick="showSec('c-tournaments')">۵. 🎪 تورنمنت‌ها</button>{% endif %}
            {% if perms[1] == 0 %}<button class="btn" onclick="showSec('c-standards')">۶. 🌍 تیم‌های استاندارد</button>{% endif %}
            {% if perms[6] == 0 %}<button class="btn" onclick="showSec('c-transfer')">۷. 🔄 ثبت نقل و انتقالات</button>{% endif %}
            {% if perms[2] == 0 %}<button class="btn" onclick="showSec('c-shop')">۸. 🏪 فروشگاه کارتی</button>{% endif %}
            <button class="btn" onclick="showSec('c-contact')">۹. 📞 ارتباط با ما</button>
        </div>
        <br><a href="/" class="btn" style="background:#ef4444; width:90px; display:inline-block;">🔒 خروج</a>

        <div id="c-team" class="section active">
            <h3>🏃‍♂️ بازیکنان تحت قرارداد شما</h3>
            <div id="coach-players-list"></div>
        </div>

        <div id="c-nextmatch" class="section">
            <h3>📅 بازی‌های آینده برنامه‌ریزی شده و ثبت ترکیب پیشرفته</h3>
            {% for m in matches %}
                {% if m[5] == 'برگزاری نشده' %}
                <div style="background:#1e293b; padding:10px; margin-bottom:12px; border-radius:6px; border-left:4px solid #38bdf8;">
                    📌 <b>تورنمنت: {{ m[3] }}</b><br>
                    ⚔️ مسابقه: {{ m[1] }} vs {{ m[2] }}<br>
                    📝 توضیحات بازی: {{ m[4] }}<br>
                    
                    <div style="background:#334155; padding:8px; border-radius:4px; margin-top:8px;">
                        <p style="font-size:11px; color:#eab308; margin:2px 0;">📋 انتخاب و ارسال رسمی ترکیب ۷ نفره:</p>
                        
                        <form method="POST" action="/coach/submit_lineup">
                            <input type="hidden" name="match_id" value="{{ m[0] }}">
                            <input type="hidden" name="code" value="{{ code }}">
                            
                            <select name="lineup_source" id="lineup_src_{{ m[0] }}" onchange="loadLineupPlayers('{{ m[0] }}', '{{ code }}')" required>
                                <option value="">-- انتخاب منبع بازیکنان --</option>
                                {% if m[7] == 1 %}
                                    <option value="own">۱- بازی با بازیکنان تیم خودم</option>
                                {% endif %}
                                <option value="std">۲- بازی با بازیکنان تیم‌های استاندارد</option>
                            </select>
                            
                            <div id="lineup_players_container_{{ m[0] }}" style="margin-top:5px; max-height:150px; overflow-y:auto; font-size:11px; text-align:right;"></div>
                            
                            <button type="submit" class="btn" style="font-size:11px; background:#22c55e; width:100%;">💾 ثبت و قفل ترکیب این مسابقه</button>
                        </form>
                    </div>
                </div>
                {% endif %}
            {% endfor %}
        </div>

        <div id="c-history" class="section">
            <h3>📜 نتایج و تاریخچه رسمی بازی‌ها</h3>
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
            <p style="background:#1e293b; padding:15px; border-radius:6px; font-style:italic; color:#eab308; font-size:14px; line-height:1.6;">" {{ data[7] }} "</p>
        </div>

        <div id="c-tournaments" class="section">
            <h3>🎪 تورنمنت‌های فدراسیون و بخش مدیا شیت‌ها</h3>
            {% for t in tours %}
            <div style="background:#1e293b; padding:10px; margin-bottom:12px; border-radius:6px; border:1px solid #475569;">
                🏆 <b>نام تورنمنت: {{ t[1] }}</b> (وضعیت: {{ t[2] }})<br>
                
                {% if t[2] == 'ثبت نام' %}
                    <button class="btn" onclick="regTour('{{ t[0] }}')">📩 ارسال درخواست ثبت نام به مدیر</button>
                {% else %}
                    <div style="margin-top:10px; background:#334155; padding:5px; border-radius:4px; text-align:right;">
                        <span style="font-size:11px; color:#38bdf8; font-weight:bold;">🖼️ مشاهده مستقیم مدارک و جداول مسابقات:</span><br>
                        
                        {% if t[3] %}<p><b>📊 جدول بازی‌ها:</b><br>{% for img in t[3].split(',') %}<img src="{{img}}" class="player-card-preview" style="max-width:90%; max-height:none;">{% endfor %}</p>{% endif %}
                        {% if t[4] %}<p><b>⚽ نتایج:</b><br>{% for img in t[4].split(',') %}<img src="{{img}}" class="player-card-preview" style="max-width:90%; max-height:none;">{% endfor %}</p>{% endif %}
                        {% if t[5] %}<p><b>📈 جدول رده‌بندی:</b><br>{% for img in t[5].split(',') %}<img src="{{img}}" class="player-card-preview" style="max-width:90%; max-height:none;">{% endfor %}</p>{% endif %}
                        {% if t[6] %}<p><b>🔥 جدول گلزنان:</b><br>{% for img in t[6].split(',') %}<img src="{{img}}" class="player-card-preview" style="max-width:90%; max-height:none;">{% endfor %}</p>{% endif %}
                        {% if t[7] %}<p><b>🎯 جدول پاس گل‌ها:</b><br>{% for img in t[7].split(',') %}<img src="{{img}}" class="player-card-preview" style="max-width:90%; max-height:none;">{% endfor %}</p>{% endif %}
                        {% if t[8] %}<p><b>🧤 جدول کلین شیت‌ها:</b><br>{% for img in t[8].split(',') %}<img src="{{img}}" class="player-card-preview" style="max-width:90%; max-height:none;">{% endfor %}</p>{% endif %}
                    </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <div id="c-standards" class="section">
            <h3>🌍 تیم‌های استاندارد و بازیکنان فعال فدراسیون</h3>
            {% for st in std_teams %}
                <div style="background:#1e293b; padding:10px; margin-bottom:8px; border-radius:6px; text-align:right;">
                    <b>🛡️ تیم: {{ st[2] }}</b> | ⭐ درجه: {{ st[4] }} ستاره | 💎 هزینه اعتبار در هر مسابقه: {{ st[3] }} اعتبار<br>
                    <button class="btn" style="font-size:11px; padding:2px 6px;" onclick="loadStdPlayersList('{{ st[0] }}')">🏃‍♂️ مشاهده بازیکنان و دانلود کارت‌ها</button>
                    <div id="std_p_list_{{ st[0] }}" style="margin-top:5px; background:#334155; padding:5px; border-radius:4px; font-size:11px; display:none;"></div>
                </div>
            {% endfor %}
        </div>

        <div id="c-transfer" class="section">
            <h3>🔄 فرم رسمی اعلام نقل و انتقالات به مدیریت</h3>
            <input type="text" id="trans-text-input" placeholder="مثال: واگذاری بازیکن X به تیم مربی Y در قبال ۲۰۰ سکه.">
            <button class="btn" onclick="submitTransfer()">📩 ارسال رسمی به مدیریت</button>
        </div>

        <div id="c-shop" class="section">
            <h3>🏪 فروشگاه رسمی و بزرگ سوپرلیگ</h3>
            <p style="font-size:11px; color:#cbd5e1;">محصول مورد نظر خود را خریداری کرده و در صورت نیاز کد پیگیری دریافت کنید.</p>
            
            {% for p in products %}
                <div class="box-product">
                    <h4>📦 {{ p[1] }}</h4>
                    <p style="font-size:11px; color:#cbd5e1;">
                        نوع فروش: 
                        {% if p[2] == '1' %} خرید قطعی پکیج با سکه
                        {% elif p[2] == '2' %} خرید قطعی پولی شاپ
                        {% else %} باکس شانسی گردونه فدراسیون
                        {% endif %}
                    </p>
                    
                    <p style="font-weight:bold; color:#eab308;">
                        قیمت: 
                        {% if p[2] == '1' or p[2] == '3' %} 🪙 {{ p[3] }} سکه
                        {% else %} 💳 {{ p[4] }} تومان
                        {% endif %}
                    </p>
                    
                    <button class="btn" onclick="buyProductAction('{{ p[0] }}', '{{ p[2] }}')">💳 اقدام به سفارش و خرید</button>
                    <div id="shop_output_{{ p[0] }}" style="margin-top:5px; font-weight:bold; color:#22c55e; font-size:12px;"></div>
                </div>
            {% endfor %}
        </div>

        <div id="c-contact" class="section">
            <h3>📞 ارتباط با ما</h3>
            <p style="font-size:16px; color:#38bdf8; font-weight:bold; background:#1e293b; padding:15px; border-radius:6px;">
                🆔 آیدی پشتیبانی و مدیریت در تلگرام:<br><br>
                <span style="color:#22c55e; font-size:20px;">@Mamad13287</span><br><br>
                (حتماً برای خرید مستقیم، واریز وجه یا ارسال کدهای پیگیری به این آیدی تلگرامی پیام دهید.)
            </p>
        </div>
    {% endif %}

</div>

<script>
    // تغییر ۲: ایمن‌سازی مقادیر برای جلوگیری از کرش جاوااسکریپت در زمان ورود ادمین
    const code = "{{ code or '' }}";
    const role = "{{ role }}";

    function showSec(id) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        const targetSec = document.getElementById(id);
        if(targetSec) {
            targetSec.classList.add('active');
        }
    }
    
    // واکشی بازیکنان تیم مربی همراه با لینک دانلود کارت
    if(code && role === "coach") {
        const playerListDiv = document.getElementById('coach-players-list');
        if(playerListDiv) {
            fetch('/get_players?code=' + code)
                .then(res => res.json())
                .then(data => {
                    playerListDiv.innerHTML = '';
                    if(data.length === 0) playerListDiv.innerHTML = '<p>هنوز بازیکنی برای تیم شما ثبت نشده است.</p>';
                    data.forEach(p => {
                        let itemDiv = document.createElement('div');
                        itemDiv.style.background = '#334155';
                        itemDiv.style.padding = '8px';
                        itemDiv.style.margin = '5px 0';
                        itemDiv.style.borderRadius = '5px';
                        itemDiv.style.textAlign = 'right';
                        
                        let html = "<b>🏃‍♂️ نام بازیکن: " + p.name + "</b>";
                        if(p.card) {
                            html += " | <a href='" + p.card + "' target='_blank' style='color:#38bdf8; font-weight:bold;'>📥 دانلود کارت بازیکن</a>";
                        } else {
                            html += " | <span style='color:#94a3b8;'>کارت تصویری ندارد</span>";
                        }
                        itemDiv.innerHTML = html;
                        playerListDiv.appendChild(itemDiv);
                    });
                }).catch(err => console.log("Error fetching players:", err));
        }
    }

    // لود چک باکس بازیکنان برای ثبت ترکیب مسابقه
    function loadLineupPlayers(matchId, coachCode) {
        var src = document.getElementById('lineup_src_' + matchId).value;
        var container = document.getElementById('lineup_players_container_' + matchId);
        container.innerHTML = 'در حال بارگذاری لیست بازیکنان...';
        if(!src) { container.innerHTML = ''; return; }
        
        fetch('/get_lineup_players?src=' + src + '&code=' + coachCode)
            .then(res => res.json())
            .then(data => {
                container.innerHTML = '';
                if(data.length === 0) { container.innerHTML = 'هیچ بازیکنی یافت نشد.'; return; }
                data.forEach(p => {
                    let lbl = document.createElement('label');
                    lbl.style.display = 'block';
                    lbl.style.margin = '4px 0';
                    lbl.innerHTML = "<input type='checkbox' name='selected_players' value='" + p.name + "' style='width:auto;'> " + p.name;
                    container.appendChild(lbl);
                });
            });
    }

    // لود بازیکنان تیم‌های استاندارد
    function loadStdPlayersList(teamId) {
        var div = document.getElementById('std_p_list_' + teamId);
        if(div.style.display === 'block') { div.style.display = 'none'; return; }
        div.innerHTML = 'در حال بارگذاری...';
        div.style.display = 'block';
        
        fetch('/get_std_players?team_id=' + teamId)
            .then(res => res.json())
            .then(data => {
                div.innerHTML = '';
                if(data.length === 0) { div.innerHTML = 'هیچ بازیکنی برای این تیم استاندارد ثبت نشده است.'; return; }
                data.forEach(p => {
                    let pLine = document.createElement('div');
                    pLine.style.borderBottom = '1px solid #475569';
                    pLine.style.padding = '4px 0';
                    let h = "<span>🏃‍♂️ " + p.name + "</span>";
                    if(p.card) {
                        h += " | <a href='" + p.card + "' target='_blank' style='color:#38bdf8;'>📥 دانلود کارت</a>";
                    }
                    pLine.innerHTML = h;
                    div.appendChild(pLine);
                });
            });
    }

    // عملیات خرید هوشمند فروشگاه همراه با صدور کد پیگیری
    function buyProductAction(productId, saleType) {
        var out = document.getElementById('shop_output_' + productId);
        out.innerHTML = '';
        
        if(saleType === '2') {
            var method = prompt("نوع پرداخت را انتخاب کنید:\n1- پرداخت مستقیم از تلگرام\n2- پرداخت از موجودی کیف پول فدراسیون\n(عدد 1 یا 2 را وارد کنید)");
            if(method === '1') {
                alert("آیدی تلگرام من برای خرید مستقیم و پرداخت هزینه: @Mamad13287\nلطفا پیام دهید تا محصول فعال گردد.");
                return;
            } else if(method !== '2') {
                return;
            }
        }
        
        fetch('/execute_purchase', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: code, product_id: productId })
        }).then(res => res.json()).then(data => {
            if(data.success) {
                out.style.color = '#22c55e';
                out.innerHTML = "🎉 خرید موفقیت‌آمیز بود!<br>کد پیگیری تراکنش شما: <span style='color:cyan;'>" + data.track_code + "</span><br>جزییات: " + data.msg;
            } else {
                out.style.color = '#ef4444';
                out.innerHTML = "❌ خطای خرید: " + data.msg;
            }
        });
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

# صفحه ورود و روت اصلی
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, role="none", error=None)

@app.route('/login', methods=['POST'])
def login():
    try:
        init_db()
    except Exception as e:
        pass
        
    code = request.form.get('code', '').strip()
    if code == ADMIN_PASSWORD:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coaches ORDER BY team_name ASC")
        teams = cursor.fetchall()
        cursor.execute("SELECT team_name, log_type, message FROM admin_logs ORDER BY id DESC")
        logs = cursor.fetchall()
        cursor.execute("SELECT * FROM matches ORDER BY id DESC")
        matches = cursor.fetchall()
        cursor.execute("SELECT * FROM tournaments ORDER BY id DESC")
        tours = cursor.fetchall()
        cursor.execute("SELECT * FROM tournament_regs ORDER BY id DESC")
        regs = cursor.fetchall()
        cursor.execute("SELECT * FROM standard_leagues ORDER BY id DESC")
        std_leagues = cursor.fetchall()
        cursor.execute("SELECT * FROM standard_teams ORDER BY id DESC")
        std_teams = cursor.fetchall()
        cursor.execute("SELECT * FROM shop_products ORDER BY id DESC")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template_string(HTML_TEMPLATE, role="admin", teams=teams, logs=logs, matches=matches, tours=tours, regs=regs, std_leagues=std_leagues, std_teams=std_teams, products=products, track_res=None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coaches WHERE login_code = %s", (code,))
    coach = cursor.fetchone()
    
    if coach:
        cursor.execute("SELECT * FROM account_permissions WHERE account_type = %s", (coach[6],))
        perms = cursor.fetchone() or (0, 0, 0, 0, 0, 0, 0, 0, 0)
        cursor.execute("SELECT * FROM matches ORDER BY id DESC")
        matches = cursor.fetchall()
        cursor.execute("SELECT * FROM tournaments ORDER BY id DESC")
        tours = cursor.fetchall()
        cursor.execute("SELECT * FROM standard_teams ORDER BY id DESC")
        std_teams = cursor.fetchall()
        cursor.execute("SELECT * FROM shop_products ORDER BY id DESC")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template_string(HTML_TEMPLATE, role="coach", data=coach, code=code, perms=perms, matches=matches, tours=tours, std_teams=std_teams, products=products)
    
    cursor.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, role="none", error="❌ کد ورود یا رمز عبور نامعتبر است.")

@app.route('/admin/create_team', methods=['POST'])
def admin_create_team():
    t_name = request.form.get('t_name', '').strip()
    code = generate_mixed_code()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO coaches (login_code, team_name) VALUES (%s, %s)", (code, t_name))
    conn.commit()
    cursor.close()
    conn.close()
    return f"<h3>تیم ساخته شد! کد ۶ رقمی ترکیبی مربی: <b style='color:cyan;'>{code}</b></h3><br><a href='/'>بازگشت به پنل مدیریت</a>"

@app.route('/admin/update_coach', methods=['POST'])
def admin_update_coach():
    code = request.form.get('code')
    acc_type = request.form.get('acc_type')
    coins = int(request.form.get('u_coins'))
    credit = int(request.form.get('u_credit'))
    wallet = int(request.form.get('u_wallet'))
    transfers = int(request.form.get('u_trans'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE coaches SET account_type=%s, coins=%s, credit=%s, wallet=%s, transfer_cards=%s WHERE login_code=%s", (acc_type, coins, credit, wallet, transfers, code))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>داشبورد مربی با موفقیت بروزرسانی شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/update_honors', methods=['POST'])
def admin_update_honors():
    code = request.form.get('code')
    honors_text = request.form.get('t_honors', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE coaches SET honors=%s WHERE login_code=%s", (honors_text, code))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>افتخارات مربی بروزرسانی شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/manage_players/<code>')
def admin_manage_players(code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    c_name = cursor.fetchone()[0]
    cursor.execute("SELECT id, player_name, card_url FROM players WHERE team_code=%s", (code,))
    players = cursor.fetchall()
    cursor.close()
    conn.close()
    
    html = f"""
    <html lang="fa" dir="rtl">
    <body style="font-family:Tahoma; background:#0f172a; color:white; padding:20px; text-align:right;">
        <h2>🏃‍♂️ مدیریت بازیکنان تیم {c_name}</h2>
        <a href="/" style="color:cyan;">🔙 بازگشت به پنل</a><hr>
        <h3>➕ افزودن بازیکن جدید</h3>
        <form method="POST" action="/admin/add_player_to_team">
            <input type="hidden" name="code" value="{code}">
            <input type="text" name="p_name" placeholder="نام بازیکن جدید" required><br>
            <input type="text" name="card_url" placeholder="لینک دانلود کارت بازیکن"><br><br>
            <button type="submit" style="background:#22c55e; color:white; padding:5px 10px;">افزودن</button>
        </form>
        <hr>
        <h3>لیست بازیکنان تحت قرارداد:</h3>
        <table>
            <tr style="background:#0284c7;"><th>نام بازیکن</th><th>لینک دانلود کارت</th><th>عملیات</th></tr>
    """
    for p in players:
        html += f"""
        <tr>
            <form method="POST" action="/admin/edit_player_in_team">
                <input type="hidden" name="p_id" value="{p[0]}">
                <td><input type="text" name="p_name" value="{p[1]}" style="width:120px;"></td>
                <td><input type="text" name="card_url" value="{p[2]}" style="width:200px;"></td>
                <td>
                    <button type="submit" style="background:#eab308;">💾 ثبت ویرایش</button>
                    <a href="/admin/remove_player_from_team/{p[0]}/{code}" style="color:#ef4444; margin-right:10px;">🗑️ حذف بازیکن</a>
                </td>
            </form>
        </tr>
        """
    html += "</table></body></html>"
    return html

@app.route('/admin/add_player_to_team', methods=['POST'])
def add_player_to_team():
    code = request.form.get('code')
    p_name = request.form.get('p_name').strip()
    card_url = request.form.get('card_url').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO players (team_code, player_name, card_url) VALUES (%s, %s, %s)", (code, p_name, card_url))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(f"/admin/manage_players/{code}")

@app.route('/admin/edit_player_in_team', methods=['POST'])
def edit_player_in_team():
    p_id = request.form.get('p_id')
    p_name = request.form.get('p_name').strip()
    card_url = request.form.get('card_url').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET player_name=%s, card_url=%s WHERE id=%s", (p_name, card_url, p_id))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>بازیکن ویرایش شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/remove_player_from_team/<p_id>/<code>')
def remove_player_from_team(p_id, code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id=%s", (p_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(f"/admin/manage_players/{code}")

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

@app.route('/get_lineup_players')
def get_lineup_players():
    src = request.args.get('src')
    code = request.args.get('code')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if src == 'own':
        cursor.execute("SELECT player_name FROM players WHERE team_code=%s", (code,))
        rows = cursor.fetchall()
        res = [{"name": r[0]} for r in rows]
    else:
        cursor.execute("SELECT player_name FROM standard_players")
        rows = cursor.fetchall()
        res = [{"name": r[0]} for r in rows]
        
    cursor.close()
    conn.close()
    return jsonify(res)

@app.route('/coach/submit_lineup', methods=['POST'])
def coach_submit_lineup():
    match_id = request.form.get('match_id')
    code = request.form.get('code')
    selected_players = request.form.getlist('selected_players')
    
    if len(selected_players) != 7:
        return "<h3>خطا: شما باید دقیقاً ۷ بازیکن برای فیکس کردن ترکیب انتخاب کنید!</h3><br><a href='/'>بازگشت و تلاش مجدد</a>"
    
    lineup_txt = ", ".join(selected_players)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    coach_name = cursor.fetchone()[0]
    
    cursor.execute("SELECT team_a, team_b FROM matches WHERE id=%s", (match_id,))
    match = cursor.fetchone()
    
    if match[0] == coach_name:
        cursor.execute("UPDATE matches SET team_a_lineup=%s WHERE id=%s", (lineup_txt, match_id))
    elif match[1] == coach_name:
        cursor.execute("UPDATE matches SET team_b_lineup=%s WHERE id=%s", (lineup_txt, match_id))
    else:
        cursor.execute("UPDATE matches SET team_a_lineup=%s WHERE id=%s", (f"{coach_name} ({lineup_txt})", match_id))
        
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>✅ ترکیب ۷ نفره شما با موفقیت ثبت شد و در اختیار داور/مدیر قرار گرفت.</h3><br><a href='/'>بازگشت</a>"

@app.route('/submit_transfer', methods=['POST'])
def submit_transfer():
    data = request.json
    code, msg = data.get('code'), data.get('msg')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    if coach:
        cursor.execute("INSERT INTO admin_logs (team_name, log_type, message) VALUES (%s, %s, %s)", (coach[0], 'نقل و انتقالات', msg))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"msg": "📩 درخواست با موفقیت به بخش نقل و انتقالات مدیر ارسال شد."})
    cursor.close()
    conn.close()
    return jsonify({"msg": "❌ مربی یافت نشد."})

@app.route('/admin/create_match', methods=['POST'])
def create_match():
    t_a = request.form.get('t_a').strip()
    t_b = request.form.get('t_b').strip()
    t_name = request.form.get('tour_name').strip()
    desc = request.form.get('desc').strip()
    allow_own = 1 if request.form.get('allow_own') else 0
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO matches (team_a, team_b, tournament_name, description, allow_own_team) VALUES (%s, %s, %s, %s, %s)", (t_a, t_b, t_name, desc, allow_own))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>مسابقه جدید ثبت شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/submit_result', methods=['POST'])
def submit_result():
    m_id = request.form.get('m_id')
    res = request.form.get('res_text').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET result=%s WHERE id=%s", (res, m_id))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>نتیجه بازی با موفقیت ثبت و وارد تاریخچه شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/create_tournament', methods=['POST'])
def create_tournament():
    name = request.form.get('tour_name').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tournaments (name) VALUES (%s)", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>تورنمنت ایجاد و بخش ثبت نام باز شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/reg_tournament', methods=['POST'])
def reg_tournament():
    data = request.json
    code, t_id = data.get('code'), data.get('tour_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    if coach:
        cursor.execute("INSERT INTO tournament_regs (tournament_id, team_code, team_name) VALUES (%s, %s, %s)", (t_id, code, coach[0]))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"msg": "✅ درخواست ثبت نام ارسال شد و منتظر تایید مدیر است."})
    cursor.close()
    conn.close()
    return jsonify({"msg": "خطا در ثبت نام."})

@app.route('/admin/approve_reg/<reg_id>')
def admin_approve_reg(reg_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_regs SET status='تایید شده' WHERE id=%s", (reg_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/admin/reject_reg/<reg_id>')
def admin_reject_reg(reg_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_regs SET status='رد شده' WHERE id=%s", (reg_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/admin/start_tournament/<t_id>')
def admin_start_tournament(t_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournaments SET status='در حال برگزاری' WHERE id=%s", (t_id,))
    cursor.execute("DELETE FROM tournament_regs WHERE tournament_id=%s AND status!='تایید شده'", (t_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>تورنمنت با موفقیت آغاز شد و ثبت نام های غیرمجاز حذف شدند.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/upload_tour_media', methods=['POST'])
def admin_upload_tour_media():
    t_id = request.form.get('t_id')
    media_type = request.form.get('media_type')
    files = request.files.getlist('media_files')
    
    encoded_strings = []
    for f in files:
        if f.filename != '':
            f_bytes = f.read()
            b64_str = "data:" + f.content_type + ";base64," + base64.b64encode(f_bytes).decode('utf-8')
            encoded_strings.append(b64_str)
            
    if not encoded_strings:
        return "فایلی آپلود نشد."
        
    media_data = ",".join(encoded_strings)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if media_type == 'table':
        cursor.execute("UPDATE tournaments SET table_imgs=%s WHERE id=%s", (media_data, t_id))
    elif media_type == 'result':
        cursor.execute("UPDATE tournaments SET result_imgs=%s WHERE id=%s", (media_data, t_id))
    elif media_type == 'standing':
        cursor.execute("UPDATE tournaments SET standing_imgs=%s WHERE id=%s", (media_data, t_id))
    elif media_type == 'scorer':
        cursor.execute("UPDATE tournaments SET scorer_imgs=%s WHERE id=%s", (media_data, t_id))
    elif media_type == 'assist':
        cursor.execute("UPDATE tournaments SET assist_imgs=%s WHERE id=%s", (media_data, t_id))
    elif media_type == 'cleansheet':
        cursor.execute("UPDATE tournaments SET cleansheet_imgs=%s WHERE id=%s", (media_data, t_id))
        
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>تصاویر بخش مربوطه با موفقیت به صورت مستقیم آپلود و ذخیره شدند.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/add_std_league', methods=['POST'])
def add_std_league():
    name = request.form.get('l_name').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO standard_leagues (league_name) VALUES (%s)", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>لیگ استاندارد جدید ساخته شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/add_std_team', methods=['POST'])
def add_std_team():
    l_id = int(request.form.get('l_id'))
    t_name = request.form.get('t_name').strip()
    credit_req = int(request.form.get('credit_req'))
    stars = int(request.form.get('stars'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO standard_teams (league_id, team_name, credit_required, stars) VALUES (%s, %s, %s, %s)", (l_id, t_name, credit_req, stars))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>تیم استاندارد با موفقیت ثبت شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/manage_std_players/<team_id>')
def admin_manage_std_players(team_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM standard_teams WHERE id=%s", (team_id,))
    t_name = cursor.fetchone()[0]
    cursor.execute("SELECT id, player_name, card_url FROM standard_players WHERE team_id=%s", (team_id,))
    players = cursor.fetchall()
    cursor.close()
    conn.close()
    
    html = f"""
    <html lang="fa" dir="rtl">
    <body style="font-family:Tahoma; background:#0f172a; color:white; padding:20px; text-align:right;">
        <h2>👥 بخش مدیریت بازیکنان تیم استاندارد: {t_name}</h2>
        <a href="/" style="color:cyan;">🔙 بازگشت به پنل اصلی ادمین</a><hr>
        <h3>➕ ایجاد و افزودن بازیکن جدید</h3>
        <form method="POST" action="/admin/add_std_player_action">
            <input type="hidden" name="team_id" value="{team_id}">
            <input type="text" name="p_name" placeholder="نام بازیکن" required><br>
            <input type="text" name="card_url" placeholder="لینک دانلود کارت بازیکن"><br><br>
            <button type="submit" style="background:#22c55e; color:white; padding:6px 12px;">انجام و ثبت بازیکن</button>
        </form>
        <hr>
        <h3>لیست بازیکنان ایجاد شده فعلی:</h3>
        <ul>
    """
    for p in players:
        html += f"<li><b>{p[1]}</b> - کارت: <code>{p[2] or 'ندارد'}</code> | <a href='/admin/delete_std_player/{p[0]}/{team_id}' style='color:#ef4444;'>حذف بازیکن</a></li>"
    html += "</ul></body></html>"
    return html

@app.route('/admin/add_std_player_action', methods=['POST'])
def add_std_player_action():
    t_id = request.form.get('team_id')
    p_name = request.form.get('p_name').strip()
    card_url = request.form.get('card_url').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO standard_players (team_id, player_name, card_url) VALUES (%s, %s, %s)", (t_id, p_name, card_url))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(f"/admin/manage_std_players/{t_id}")

@app.route('/admin/delete_std_player/<p_id>/<t_id>')
def delete_std_player(p_id, t_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM standard_players WHERE id=%s", (p_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(f"/admin/manage_std_players/{t_id}")

@app.route('/get_std_players')
def get_std_players():
    t_id = request.args.get('team_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT player_name, card_url FROM standard_players WHERE team_id=%s", (t_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{"name": r[0], "card": r[1]} for r in rows])

@app.route('/admin/update_permissions', methods=['POST'])
def update_permissions():
    target = request.form.get('target_acc')
    lock_tour = 1 if request.form.get('lock_tour') else 0
    lock_league = 1 if request.form.get('lock_league') else 0
    lock_shop = 1 if request.form.get('lock_shop') else 0
    lock_player = 1 if request.form.get('lock_player') else 0
    lock_team = 1 if request.form.get('lock_team') else 0
    lock_match = 1 if request.form.get('lock_match') else 0
    lock_transfer = 1 if request.form.get('lock_transfer') else 0
    lock_honors = 1 if request.form.get('lock_honors') else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE account_permissions SET 
        tournament_locked=%s, league_locked=%s, shop_locked=%s, 
        player_locked=%s, team_locked=%s, match_locked=%s, 
        transfer_locked=%s, honors_locked=%s WHERE account_type=%s
    ''', (lock_tour, lock_league, lock_shop, lock_player, lock_team, lock_match, lock_transfer, lock_honors, target))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>قفل‌های سراسری با موفقیت بر روی تمام سطوح اکانت اعمال شدند.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/add_product', methods=['POST'])
def admin_add_product():
    name = request.form.get('p_name').strip()
    s_type = request.form.get('s_type')
    price_coins = int(request.form.get('price_coins') or 0)
    price_money = int(request.form.get('price_money') or 0)
    
    r_coins = int(request.form.get('r_coins') or 0)
    r_credit = int(request.form.get('r_credit') or 0)
    r_transfers = int(request.form.get('r_transfers') or 0)
    r_players = request.form.get('r_players', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO shop_products (name, sale_type, price_coins, price_money, reward_coins, reward_credit, reward_transfers, reward_players)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (name, s_type, price_coins, price_money, r_coins, r_credit, r_transfers, r_players))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>محصول جدید با موفقیت ایجاد و روانه فروشگاه شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/manage_box/<p_id>')
def admin_manage_box(p_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM shop_products WHERE id=%s", (p_id,))
    p_name = cursor.fetchone()[0]
    cursor.execute("SELECT id, player_name, chance_weight FROM box_items WHERE product_id=%s", (p_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    
    html = f"""
    <html lang="fa" dir="rtl">
    <body style="font-family:Tahoma; background:#0f172a; color:white; padding:20px; text-align:right;">
        <h2>🎰 تنظیم شانس‌های باکس: {p_name}</h2>
        <form method="POST" action="/admin/add_box_item">
            <input type="hidden" name="p_id" value="{p_id}">
            <input type="text" name="p_name" placeholder="نام بازیکن باکس" required>
            <input type="number" name="weight" placeholder="میزان شانس خروج (۱ تا ۱۰)" min="1" max="10" required><br><br>
            <button type="submit">➕ ثبت بازیکن در باکس</button>
        </form>
        <hr><h3>آیتم‌های گردونه:</h3><ul>
    """
    for i in items:
        html += f"<li>{i[1]} (وزن شانس: {i[2]}/10) | <a href='/admin/delete_box_item/{i[0]}/{p_id}' style='color:red;'>حذف</a></li>"
    html += "</ul><br><a href='/'>بازگشت</a></body></html>"
    return html

@app.route('/admin/add_box_item', methods=['POST'])
def add_box_item():
    p_id = request.form.get('p_id')
    p_name = request.form.get('p_name').strip()
    weight = int(request.form.get('weight'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO box_items (product_id, player_name, chance_weight) VALUES (%s, %s, %s)", (p_id, p_name, weight))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(f"/admin/manage_box/{p_id}")

@app.route('/admin/delete_box_item/<i_id>/<p_id>')
def delete_box_item(i_id, p_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM box_items WHERE id=%s", (i_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(f"/admin/manage_box/{p_id}")

@app.route('/admin/delete_product/<p_id>')
def admin_delete_product(p_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop_products WHERE id=%s", (p_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/execute_purchase', methods=['POST'])
def execute_purchase():
    data = request.json
    code = data.get('code')
    product_id = int(data.get('product_id'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM coaches WHERE login_code=%s", (code,))
    coach = cursor.fetchone()
    cursor.execute("SELECT * FROM shop_products WHERE id=%s", (product_id,))
    prod = cursor.fetchall()
    
    if not coach or not prod:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "msg": "اطلاعات نامعتبر است."})
        
    p = prod[0]
    p_id, p_name, s_type, p_coins, p_money, r_coins, r_credit, r_transfers, r_players = p
    
    track_code = generate_tracking_code()
    details = ""
    
    if s_type == '1':
        if coach[2] < p_coins:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "سکه شما کافی نیست!"})
        
        new_coins = coach[2] - p_coins + r_coins
        new_credit = coach[3] + r_credit
        new_transfers = coach[4] + r_transfers
        
        cursor.execute("UPDATE coaches SET coins=%s, credit=%s, transfer_cards=%s WHERE login_code=%s", (new_coins, new_credit, new_transfers, code))
        
        if r_players:
            for pl in r_players.split(','):
                if pl.strip():
                    cursor.execute("INSERT INTO players (team_code, player_name) VALUES (%s, %s)", (code, pl.strip()))
                    
        details = f"خرید قطعی پک با کسر {p_coins} سکه. هدایا: سکه+{r_coins}، اعتبار+{r_credit}، کارت نقل و انتقال+{r_transfers}"

    elif s_type == '2':
        if coach[5] < p_money:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "موجودی کیف پول شما کافی نیست!"})
            
        new_wallet = coach[5] - p_money
        new_coins = coach[2] + r_coins
        new_credit = coach[3] + r_credit
        new_transfers = coach[4] + r_transfers
        
        cursor.execute("UPDATE coaches SET wallet=%s, coins=%s, credit=%s, transfer_cards=%s WHERE login_code=%s", (new_wallet, new_coins, new_credit, new_transfers, code))
        
        if r_players:
            for pl in r_players.split(','):
                if pl.strip():
                    cursor.execute("INSERT INTO players (team_code, player_name) VALUES (%s, %s)", (code, pl.strip()))
                    
        details = f"خرید پولی با کسر {p_money} تومان. هدایا: سکه+{r_coins}، اعتبار+{r_credit}"

    elif s_type == '3':
        if coach[2] < p_coins:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "سکه شما کافی نیست!"})
            
        cursor.execute("SELECT player_name, chance_weight FROM box_items WHERE product_id=%s", (p_id,))
        box_items = cursor.fetchall()
        if not box_items:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "این باکس خالی است!"})
            
        pool = []
        for item in box_items:
            name, weight = item[0], item[1]
            for _ in range(weight):
                pool.append(name)
                
        winner_player = random.choice(pool)
        
        new_coins = coach[2] - p_coins
        cursor.execute("UPDATE coaches SET coins=%s WHERE login_code=%s", (new_coins, code))
        cursor.execute("INSERT INTO players (team_code, player_name) VALUES (%s, %s)", (code, winner_player))
        
        details = f"باکس شانسی با هزینه {p_coins} سکه. برنده: {winner_player}"
        
    cursor.execute("INSERT INTO tracking_codes (tracking_code, team_name, product_name, details) VALUES (%s, %s, %s, %s)", (track_code, coach[1], p_name, details))
    cursor.execute("INSERT INTO admin_logs (team_name, log_type, message) VALUES (%s, 'فروشگاه', %s)", (coach[1], f"کد تراکنش {track_code}: {details}"))
    
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "track_code": track_code, "msg": details})

@app.route('/admin/search_tracking', methods=['POST'])
def admin_search_tracking():
    t_code = request.form.get('track_code').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracking_codes WHERE tracking_code=%s", (t_code,))
    res = cursor.fetchone()
    
    cursor.execute("SELECT * FROM coaches ORDER BY team_name ASC")
    teams = cursor.fetchall()
    cursor.execute("SELECT team_name, log_type, message FROM admin_logs ORDER BY id DESC")
    logs = cursor.fetchall()
    cursor.execute("SELECT * FROM matches ORDER BY id DESC")
    matches = cursor.fetchall()
    cursor.execute("SELECT * FROM tournaments ORDER BY id DESC")
    tours = cursor.fetchall()
    cursor.execute("SELECT * FROM tournament_regs ORDER BY id DESC")
    regs = cursor.fetchall()
    cursor.execute("SELECT * FROM standard_leagues ORDER BY id DESC")
    std_leagues = cursor.fetchall()
    cursor.execute("SELECT * FROM standard_teams ORDER BY id DESC")
    std_teams = cursor.fetchall()
    cursor.execute("SELECT * FROM shop_products ORDER BY id DESC")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, role="admin", teams=teams, logs=logs, matches=matches, tours=tours, regs=regs, std_leagues=std_leagues, std_teams=std_teams, products=products, track_res=res)


if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        pass
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
