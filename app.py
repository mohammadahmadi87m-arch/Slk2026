import os
import random
import string
import psycopg2
from flask import Flask, request, render_template_string, jsonify, redirect

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = "admiin49g"  # ۱- تغییر کد ورود مدیر

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ۱- جدول مربیان
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
    
    # ۲- جدول بازیکنان همراه با لینک دانلود کارت (مورد ۴)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            team_code TEXT,
            player_name TEXT,
            card_url TEXT DEFAULT '',
            position TEXT DEFAULT 'نیمکت',
            download_url TEXT DEFAULT ''
        )
    ''')
    
    # ۳- جدول لیگ‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standard_leagues (
            id SERIAL PRIMARY KEY,
            league_name TEXT
        )
    ''')
    
    # ۴- جدول تیم‌های استاندارد (مورد ۹)
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
    
    # ۵- جدول بازیکنان استاندارد (مورد ۹)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standard_players (
            id SERIAL PRIMARY KEY,
            team_id INTEGER,
            player_name TEXT,
            download_url TEXT DEFAULT ''
        )
    ''')
    
    # ۶- جدول مسابقات (مورد ۵)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            team_a TEXT,
            team_b TEXT,
            tournament_name TEXT,
            description TEXT,
            result TEXT DEFAULT 'برگزاری نشده',
            status TEXT DEFAULT 'فعال',
            allow_own_team INTEGER DEFAULT 1
        )
    ''')
    
    # ۷- جدول تورنمنت‌ها (مورد ۸)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id SERIAL PRIMARY KEY,
            name TEXT,
            status TEXT DEFAULT 'ثبت نام',
            stats_images TEXT DEFAULT '',
            results_images TEXT DEFAULT '',
            standings_images TEXT DEFAULT '',
            scorers_images TEXT DEFAULT '',
            assists_images TEXT DEFAULT '',
            cleansheets_images TEXT DEFAULT ''
        )
    ''')
    
    # ۸- جدول ثبت نام و تایید مربیان (مورد ۸)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_regs (
            id SERIAL PRIMARY KEY,
            tournament_id INTEGER,
            team_name TEXT,
            status TEXT DEFAULT 'انتظار تایید'
        )
    ''')

    # ۹- جدول مجوزها و قفل‌های پیشرفته (مورد ۱۴)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_permissions (
            account_type TEXT PRIMARY KEY,
            player_locked INTEGER DEFAULT 0,
            team_locked INTEGER DEFAULT 0,
            league_locked INTEGER DEFAULT 0,
            tournament_locked INTEGER DEFAULT 0,
            shop_locked INTEGER DEFAULT 0,
            transfer_locked INTEGER DEFAULT 0,
            history_locked INTEGER DEFAULT 0,
            honors_locked INTEGER DEFAULT 0,
            contact_locked INTEGER DEFAULT 0,
            gift_locked INTEGER DEFAULT 0
        )
    ''')
    
    # ۱۰- جدول لاگ‌ها و پیام‌های نقل و انتقالات (مورد ۱۰)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id SERIAL PRIMARY KEY,
            team_name TEXT,
            log_type TEXT,
            message TEXT
        )
    ''')

    # ۱۱- جدول محصولات فروشگاه (مورد ۱۱)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_products (
            id SERIAL PRIMARY KEY,
            name TEXT,
            type TEXT,
            price_type TEXT,
            price_value INTEGER,
            content_type TEXT DEFAULT '',
            content_value TEXT DEFAULT ''
        )
    ''')

    # ۱۲- جدول آیتم‌های باکس شانسی (مورد ۱۱)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS box_items (
            id SERIAL PRIMARY KEY,
            product_id INTEGER,
            player_name TEXT,
            chance INTEGER
        )
    ''')

    # ۱۳- جدول کدهای پیگیری فروشگاه (مورد ۱۱)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_orders (
            id SERIAL PRIMARY KEY,
            track_code TEXT,
            team_name TEXT,
            product_name TEXT,
            details TEXT
        )
    ''')

    # ۱۴- جدول ترکیب تیم‌ها (مورد ۵)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_lineups (
            id SERIAL PRIMARY KEY,
            match_id INTEGER,
            team_code TEXT,
            team_type TEXT,
            players_list TEXT
        )
    ''')

    # ۱۵- جدول کدهای هدیه (مورد ۱۸)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gift_codes (
            code TEXT PRIMARY KEY,
            reward_type TEXT,
            reward_value TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM account_permissions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account_permissions VALUES ('رایگان', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)")
        cursor.execute("INSERT INTO account_permissions VALUES ('نرمال', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)")
        cursor.execute("INSERT INTO account_permissions VALUES ('حرفه ای', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)")

    conn.commit()
    cursor.close()
    conn.close()

def generate_mix_code():
    # ۲- تولید کد ۶ رقمی ترکیبی عدد و حروف انگلیسی بزرگ و کوچک
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مدیریت تیم سوپرلیگ کارتی</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 10px; text-align: center; }
        .container { max-width: 850px; margin: 0 auto; background: #1e293b; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
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
        .badge { background: #eab308; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    </style>
</head>
<body>
<div class="container">

    {% if role == "none" %}
        <h1>⚽ مدیریت تیم سوپرلیگ کارتی ⚽</h1>
        <p>لطفاً کد مربیگری یا رمز عبور مدیریت را وارد کنید:</p>
        <form method="POST" action="/login">
            <input type="text" name="code" placeholder="کد مربی یا رمز ادمین" style="width: 80%; text-align:center;" required><br><br>
            <button type="submit" class="btn" style="width: 85%;">🔓 ورود به پنل</button>
        </form>
        {% if error %} <p style="color: #ef4444; font-weight: bold;">{{ error }}</p> {% endif %}

    {% elif role == "admin" %}
        <h2>👑 داشبورد ادمین سوپرلیگ</h2>
        <div style="text-align:center;">
            <button class="btn" onclick="showSec('adm-teams')">👥 مربیان & تیم‌ها</button>
            <button class="btn" onclick="showSec('adm-players-edit')">🏃‍♂️ مدیریت بازیکنان تیم‌ها</button>
            <button class="btn" onclick="showSec('adm-matches')">📅 بازی‌ها & ترکیب‌ها</button>
            <button class="btn" onclick="showSec('adm-tournaments')">🏆 تورنمنت‌ها</button>
            <button class="btn" onclick="showSec('adm-standards')">🌍 تیم‌های استاندارد</button>
            <button class="btn" onclick="showSec('adm-shop')">🏪 مدیریت فروشگاه</button>
            <button class="btn" onclick="showSec('adm-gifts')">🎁 کدهای هدیه</button>
            <button class="btn" onclick="showSec('adm-locks')">🔒 دسترسی اکانت‌ها</button>
            <button class="btn" onclick="showSec('adm-transfers')">📩 نقل و انتقالات</button>
            <a href="/" class="btn" style="background:#ef4444;">خروج</a>
        </div>

        <div id="adm-teams" class="section active">
            <h3>➕ ایجاد تیم جدید</h3>
            <form method="POST" action="/admin/create_team">
                <input type="text" name="t_name" placeholder="نام تیم مربی" required>
                <button type="submit" class="btn">ایجاد تیم و صدور کد ترکیبی رقمی</button>
            </form>

            <h3>⚙️ ویرایش مشخصات مربیان</h3>
            <table>
                <tr>
                    <th>تیم (کد)</th>
                    <th>اکانت</th>
                    <th>سکه / اعتبار</th>
                    <th>کارت نقل و انتقال / کیف پول</th>
                    <th>عملیات</th>
                </tr>
                {% for team in teams %}
                <tr>
                    <td><b>{{ team[1] }}</b><br><code>{{ team[0] }}</code></td>
                    <td>{{ team[6] }}</td>
                    <td>🪙{{ team[2] }}<br>💎{{ team[3] }}</td>
                    <td>🔄{{ team[4] }}<br>💳{{ team[5] }} تومان</td>
                    <td>
                        <form method="POST" action="/admin/update_coach" style="margin:0;">
                            <input type="hidden" name="code" value="{{ team[0] }}">
                            <select name="acc_type" style="width:70px; padding:2px;">
                                <option value="رایگان" {% if team[6]=='رایگان' %}selected{% endif %}>رایگان</option>
                                <option value="نرمال" {% if team[6]=='نرمال' %}selected{% endif %}>نرمال</option>
                                <option value="حرفه ای" {% if team[6]=='حرفه ای' %}selected{% endif %}>حرفه‌ای</option>
                            </select><br>
                            🪙<input type="number" name="u_coins" value="{{ team[2] }}" style="width:45px; padding:2px;">
                            💎<input type="number" name="u_credit" value="{{ team[3] }}" style="width:45px; padding:2px;"><br>
                            🔄<input type="number" name="u_trans_cards" value="{{ team[4] }}" style="width:45px; padding:2px;">
                            💳<input type="number" name="u_wallet" value="{{ team[5] }}" style="width:55px; padding:2px;"><br>
                            <button type="submit" style="font-size:10px; margin-top:3px;">💾 ذخیره</button>
                        </form>
                        <hr style="margin:2px;">
                        <form method="POST" action="/admin/add_honors" style="margin:0;">
                            <input type="hidden" name="code" value="{{ team[0] }}">
                            <input type="text" name="honors_text" value="{{ team[7] }}" style="width:80px; font-size:10px; padding:2px;">
                            <button type="submit" style="font-size:10px;">🏆 ثبت افتخار</button>
                        </form>
                        <hr style="margin:2px;">
                        <a href="/admin/delete_team/{{ team[0] }}" onclick="return confirm('حذف کامل؟')" style="color:#ef4444; font-size:10px;">🗑️ حذف کامل تیم</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="adm-players-edit" class="section">
            <h3>🏃‍♂️ مدیریت بازیکنان تحت قرارداد کل تیم‌ها</h3>
            <form method="POST" action="/admin/add_player_to_team">
                <input type="text" name="p_name" placeholder="نام بازیکن جدید" required>
                <input type="text" name="dl_url" placeholder="لینک دانلود کارت بازیکن">
                <select name="t_code">
                    {% for team in teams %}
                        <option value="{{ team[0] }}">{{ team[1] }} ({{ team[0] }})</option>
                    {% endfor %}
                </select>
                <button type="submit" class="btn">➕ افزودن بازیکن به تیم</button>
            </form>

            <table>
                <tr>
                    <th>تیم</th>
                    <th>نام بازیکن</th>
                    <th>لینک کارت</th>
                    <th>عملیات ویرایش</th>
                </tr>
                {% for p in all_players %}
                <tr>
                    <td>{{ p[1] }}</td>
                    <td>{{ p[2] }}</td>
                    <td>{% if p[5] %}<a href="{{ p[5] }}" target="_blank">🔗 لینک کارت</a>{% else %}ندارد{% endif %}</td>
                    <td>
                        <form method="POST" action="/admin/edit_player_details" style="margin:0; display:inline-block;">
                            <input type="hidden" name="p_id" value="{{ p[0] }}">
                            <input type="text" name="new_name" value="{{ p[2] }}" style="width:90px; padding:2px;" placeholder="نام">
                            <input type="text" name="new_dl" value="{{ p[5] }}" style="width:90px; padding:2px;" placeholder="لینک کارت">
                            <button type="submit" style="font-size:10px;">💾 ثبت</button>
                        </form>
                        <a href="/admin/delete_player/{{ p[0] }}" onclick="return confirm('حذف بازیکن؟')" style="color:#ef4444; margin-left:10px; font-size:11px;">🗑️ حذف</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="adm-matches" class="section">
            <h3>📅 ایجاد بازی جدید</h3>
            <form method="POST" action="/admin/create_match">
                <input type="text" name="t_a" placeholder="تیم اول" required>
                <input type="text" name="t_b" placeholder="تیم دوم" required>
                <input type="text" name="tour_name" placeholder="نام تورنمنت" required>
                <input type="text" name="desc" placeholder="توضیحات">
                <label><input type="checkbox" name="allow_own" value="1" checked style="width:auto;"> امکان بازی با تیم خود مربی فراهم باشد</label><br>
                <button type="submit" class="btn">ثبت بازی فعال</button>
            </form>

            <h3>⚽ ثبت نتایج بازی‌ها و مشاهده ترکیب‌های ارسالی</h3>
            <table>
                <tr>
                    <th>بازی</th>
                    <th>وضعیت مجاز</th>
                    <th>ترکیب‌های ثبت شده</th>
                    <th>ثبت نتیجه (مورد ۶)</th>
                </tr>
                {% for m in matches %}
                <tr>
                    <td><b>{{ m[3] }}</b><br>{{ m[1] }} vs {{ m[2] }}</td>
                    <td>{% if m[7] == 1 %}تیم خود مربی{% else %}فقط استاندارد{% endif %}</td>
                    <td style="text-align:right; font-size:11px;">
                        {% for line in lineups %}
                            {% if line[1] == m[0] %}
                                🔹 <b>کد مربی {{ line[2] }} ({{ line[3] }}):</b> {{ line[4] }}<br>
                            {% endif %}
                        {% endfor %}
                    </td>
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
                <input type="text" name="tour_name" placeholder="نام تورنمنت" required>
                <button type="submit" class="btn">ایجاد تورنمنت</button>
            </form>

            <h3>👥 مدیریت ثبت‌نام‌ها و آپلود عکس پیشرفته (مورد ۸)</h3>
            {% for t in tours %}
            <div style="background:#1e293b; padding:10px; margin-bottom:10px; border-radius:6px; text-align:right;">
                <h4>🏆 تورنمنت: {{ t[1] }} (وضعیت: {{ t[2] }})</h4>
                
                {% if t[2] == 'ثبت نام' %}
                    <p><b>درخواست‌های ثبت‌نام مربیان:</b></p>
                    {% for reg in regs %}
                        {% if reg[1] == t[0] %}
                            <div style="margin-bottom:5px;">
                                👤 تیم: {{ reg[2] }} [{{ reg[3] }}]
                                <a href="/admin/approve_reg/{{ reg[0] }}" class="btn" style="background:green; padding:2px 6px; font-size:11px;">✔️ تایید</a>
                                <a href="/admin/reject_reg/{{ reg[0] }}" class="btn" style="background:red; padding:2px 6px; font-size:11px;">❌ رد</a>
                            </div>
                        {% endif %}
                    {% endfor %}
                    <br>
                    <a href="/admin/start_tournament/{{ t[0] }}" class="btn" style="background:#eab308; color:#000;">🚀 شروع تورنمنت و بستن ثبت نام</a>
                {% else %}
                    <form method="POST" action="/admin/upload_tour_media">
                        <input type="hidden" name="t_id" value="{{ t[0] }}">
                        <p><b>لینک‌های مدیا (عکس‌ها را با ویرگول <code>,</code> جدا کنید):</b></p>
                        جدول بازی‌ها: <input type="text" name="img_stats" value="{{ t[3] }}"><br>
                        نتایج: <input type="text" name="img_results" value="{{ t[4] }}"><br>
                        رده‌بندی: <input type="text" name="img_standings" value="{{ t[5] }}"><br>
                        گلزنان: <input type="text" name="img_scorers" value="{{ t[6] }}"><br>
                        پاس گل‌ها: <input type="text" name="img_assists" value="{{ t[7] }}"><br>
                        کلین‌شیت‌ها: <input type="text" name="img_cleansheets" value="{{ t[8] }}"><br>
                        <button type="submit" class="btn" style="background:green;">💾 بروزرسانی عکس‌های تورنمنت</button>
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

            <h3>🛡️ ثبت تیم استاندارد داخل لیگ (مورد ۹)</h3>
            <form method="POST" action="/admin/add_std_team">
                <select name="l_id">
                    {% for l in std_leagues %}
                        <option value="{{ l[0] }}">{{ l[1] }}</option>
                    {% endfor %}
                </select>
                <input type="text" name="t_name" placeholder="نام تیم استاندارد" required>
                <input type="number" name="credit_req" placeholder="اعتبار مورد نیاز برای استفاده در بازی" required>
                <input type="number" name="stars" placeholder="تعداد ستاره تیم" default="3" required>
                <button type="submit" class="btn">ثبت تیم استاندارد</button>
            </form>

            <h3>🏃‍♂️ افزودن بازیکن به تیم استاندارد</h3>
            <form method="POST" action="/admin/add_std_player">
                <select name="std_t_id">
                    {% for st in std_teams %}
                        <option value="{{ st[0] }}">{{ st[2] }}</option>
                    {% endfor %}
                </select>
                <input type="text" name="p_name" placeholder="نام بازیکن" required>
                <input type="text" name="dl_url" placeholder="لینک دانلود کارت بازیکن">
                <button type="submit" class="btn">ثبت بازیکن استاندارد</button>
            </form>
        </div>

        <div id="adm-shop" class="section">
            <h3>🏪 افزودن محصول جدید به فروشگاه (مورد ۱۱)</h3>
            <form method="POST" action="/admin/add_product">
                <input type="text" name="p_name" placeholder="نام محصول" required>
                
                <select name="p_type" id="p_type_select" onchange="toggleShopFields()">
                    <option value="قطعی_سکه">فروش قطعی با سکه (پک ها)</option>
                    <option value="قطعی_پولی">خرید قطعی پولی</option>
                    <option value="شانسی">خرید شانسی (باکس ها)</option>
                </select>
                
                <input type="number" name="price" placeholder="قیمت (سکه یا تومان)" required>
                
                <div id="shop_content_div">
                    <p><b>محتویات پک / محصول قطعی:</b></p>
                    <input type="text" name="c_player" placeholder="نام بازیکن دریافتی (اگر دارد)"><br>
                    لینک کارت بازیکن: <input type="text" name="c_player_dl"><br>
                    <input type="number" name="c_credit" placeholder="مقدار اضافه شدن اعتبار مربی (عدد)"><br>
                    <input type="number" name="c_trans" placeholder="مقدار اضافه شدن کارت نقل و انتقال (عدد)">
                </div>

                <div id="shop_box_div" style="display:none;">
                    <p><b>اضافه کردن یک آیتم برای باکس شانسی (بعد از ساخت محصول نیز می‌توانید باز اضافه کنید):</b></p>
                    <input type="text" name="b_player" placeholder="نام بازیکن باکس"><br>
                    شانس خروج (۱ تا ۱۰): <input type="number" name="b_chance" min="1" max="10" placeholder="۱۰ بیشترین شانس">
                </div>

                <button type="submit" class="btn">ثبت محصول در فروشگاه</button>
            </form>

            <h3>📦 لیست محصولات فعال و کدهای پیگیری</h3>
            <table>
                <tr>
                    <th>نام محصول</th>
                    <th>نوع فروش</th>
                    <th>قیمت</th>
                    <th>عملیات</th>
                </tr>
                {% for prod in products %}
                <tr>
                    <td>{{ prod[1] }}</td>
                    <td>{{ prod[2] }}</td>
                    <td>{{ prod[4] }}</td>
                    <td>
                        <a href="/admin/delete_product/{{ prod[0] }}" style="color:#ef4444;">🗑️ حذف محصول</a>
                    </td>
                </tr>
                {% endfor %}
            </table>

            <h3>🔍 سیستم پیگیری کدهای خرید مربیان</h3>
            <form method="POST" action="/admin/check_order">
                <input type="text" name="track_code" placeholder="کد پیگیری را وارد کنید" style="width:70%;" required>
                <button type="submit" class="btn">🔎 پیگیری</button>
            </form>
            {% if order_search %}
                <div style="background:#0284c7; padding:10px; margin-top:5px; border-radius:5px;">
                    📌 <b>خریدار:</b> {{ order_search[2] }} | <b>محصول:</b> {{ order_search[3] }}<br>
                    📝 <b>جزئیات سفارش:</b> {{ order_search[4] }}
                </div>
            {% endif %}
        </div>

        <div id="adm-gifts" class="section">
            <h3>🎁 تعریف کد هدیه جدید (مورد ۱۸)</h3>
            <form method="POST" action="/admin/add_gift">
                <input type="text" name="g_code" placeholder="کد هدیه (مثال: GIFT2026)" required>
                <select name="g_type">
                    <option value="coins">سکه</option>
                    <option value="credit">اعتبار</option>
                    <option value="trans">کارت نقل و انتقالات</option>
                    <option value="wallet">موجودی کیف پول</option>
                </select>
                <input type="text" name="g_val" placeholder="مقدار جایزه (عدد)" required>
                <button type="submit" class="btn">ثبت کد هدیه</button>
            </form>
        </div>

        <div id="adm-locks" class="section">
            <h3>🔒 مدیریت قفل و محدودیت‌های بازی (مورد ۱۴)</h3>
            <form method="POST" action="/admin/update_permissions">
                <select name="target_acc">
                    <option value="رایگان">اکانت رایگان</option>
                    <option value="نرمال">اکانت نرمال</option>
                    <option value="حرفه ای">اکانت حرفه‌ای</option>
                </select><br>
                <label><input type="checkbox" name="lock_player" value="1"> قفل بخش بازیکنان</label><br>
                <label><input type="checkbox" name="lock_team" value="1"> قفل بخش تیم من</label><br>
                <label><input type="checkbox" name="lock_league" value="1"> قفل بخش لیگ‌ها</label><br>
                <label><input type="checkbox" name="lock_tour" value="1"> قفل بخش تورنمنت‌ها</label><br>
                <label><input type="checkbox" name="lock_shop" value="1"> قفل بخش فروشگاه</label><br>
                <label><input type="checkbox" name="lock_trans" value="1"> قفل بخش نقل و انتقالات</label><br>
                <button type="submit" class="btn">اعمال قفل‌های هوشمند</button>
            </form>
        </div>

        <div id="adm-transfers" class="section">
            <h3>📩 پیام‌های دریافتی مربیان (مورد ۱۰ - اصلاح شده)</h3>
            {% for log in logs %}
                <div style="background:#1e293b; padding:8px; margin:4px 0; border-right:4px solid #38bdf8; text-align:right;">
                    <b>نوع پیام: {{ log[1] }} | فرستنده: {{ log[0] }}</b><br>
                    <span>متن: {{ log[2] }}</span>
                </div>
            {% endfor %}
        </div>

    {% elif role == "coach" %}
        <h2>🛡️ پنل مربیگری: {{ data[1] }}</h2>
        
        <div class="status-card">
            🪙 موجودی سکه: <b>{{ data[2] }}</b> | 💎 اعتبار: <b>{{ data[3] }}</b><br>
            🔄 کارت نقل و انتقالات: <b>{{ data[4] }}</b> | 💳 کیف پول: <b>{{ data[5] }} تومان</b><br> 🎖️ نوع اکانت شما: <span style="color:#38bdf8; font-weight:bold;">{{ data[6] }}</span>
        </div>

        <div class="grid-menu">
            {% if perms[1] == 0 %}<button class="btn" onclick="showSec('c-team')">۱. 🏃‍♂️ تیم من & کارت‌ها</button>{% endif %}
            <button class="btn" onclick="showSec('c-nextmatch')">۲. 📅 بازی پیش رو & ثبت ترکیب</button>
            {% if perms[7] == 0 %}<button class="btn" onclick="showSec('c-history')">۳. 📜 تاریخچه بازی‌ها</button>{% endif %}
            {% if perms[8] == 0 %}<button class="btn" onclick="showSec('c-honors')">۴. 🏆 افتخارات من</button>{% endif %}
            {% if perms[3] == 0 %}<button class="btn" onclick="showSec('c-tournaments')">۵. 🎪 تورنمنت‌ها</button>{% endif %}
            {% if perms[2] == 0 %}<button class="btn" onclick="showSec('c-standards')">۶. 🌍 تیم‌های استاندارد</button>{% endif %}
            {% if perms[5] == 0 %}<button class="btn" onclick="showSec('c-transfer')">۷. 🔄 ثبت نقل و انتقالات</button>{% endif %}
            {% if perms[4] == 0 %}<button class="btn" onclick="showSec('c-shop')">۸. 🏪 فروشگاه کارتی</button>{% endif %}
            {% if perms[10] == 0 %}<button class="btn" onclick="showSec('c-gifts')">🎁 کد هدیه</button>{% endif %}
            {% if perms[9] == 0 %}<button class="btn" onclick="showSec('c-contact')">۹. 📞 ارتباط با ما</button>{% endif %}
        </div>
        <br><a href="/" class="btn" style="background:#ef4444; width:90px; display:inline-block;">🔒 خروج</a>

        <div id="c-team" class="section active">
            <h3>🏃‍♂️ بازیکنان تحت قرارداد شما</h3>
            <table>
                <tr>
                    <th>نام بازیکن</th>
                    <th>کارت بازیکن (مورد ۴)</th>
                </tr>
                {% for p in coach_players %}
                <tr>
                    <td><b>{{ p[2] }}</b></td>
                    <td>
                        {% if p[5] %}
                            <a href="{{ p[5] }}" target="_blank" class="btn" style="background:#eab308; color:#000; padding:3px 8px; font-size:11px;">📥 دانلود کارت بازیکن</a>
                        {% else %}
                            <span style="color:#94a3b8;">آپلود نشده</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="c-nextmatch" class="section">
            <h3>📅 بازی‌های فعال و فرم هوشمند ثبت ترکیب</h3>
            {% for m in matches %}
                {% if m[5] == 'برگزاری نشده' %}
                <div style="background:#1e293b; padding:10px; margin-bottom:12px; border-radius:6px;">
                    📌 <b>تورنمنت: {{ m[3] }}</b><br>
                    ⚔️ مسابقه: {{ m[1] }} vs {{ m[2] }}<br>
                    وضعیت مجاز: {% if m[7] == 1 %}<span style="color:green;">مجاز به انتخاب تیم خود یا استاندارد</span>{% else %}<span style="color:red;">فقط مجاز به انتخاب تیم استاندارد</span>{% endif %}
                    <hr>
                    <form method="POST" action="/coach/submit_lineup">
                        <input type="hidden" name="match_id" value="{{ m[0] }}">
                        <input type="hidden" name="code" value="{{ code }}">
                        
                        <label><b>نوع تیم انتخابی برای این مسابقه:</b></label><br>
                        <select name="team_type" required>
                            {% if m[7] == 1 %}<option value="تیم_خودم">🏃‍♂️ بازی با تیم خودم</option>{% endif %}
                            <option value="تیم_استاندارد">🌍 بازی با تیم‌های استاندارد فدراسیون</option>
                        </select><br>

                        <label><b>اسامی ۷ بازیکن منتخب خود را بنویسید:</b></label><br>
                        <textarea name="players_list" rows="3" placeholder="مثال: امباپه، وینیسیوس، مودریچ و..." required></textarea>
                        <button type="submit" class="btn" style="background:green; width:100%;">📋 ثبت رسمی ترکیب برای داور</button>
                    </form>
                </div>
                {% endif %}
            {% endfor %}
        </div>

        <div id="c-history" class="section">
            <h3>📜 تاریخچه بازی‌ها و نتایج</h3>
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
            <h3>🏆 تالار افتخارات رسمی شما</h3>
            <p style="background:#1e293b; padding:15px; border-radius:6px; font-style:italic; border-right:4px solid #eab308;">" {{ data[7] }} "</p>
        </div>

        <div id="c-tournaments" class="section">
            <h3>🎪 تورنمنت‌های فدراسیون</h3>
            {% for t in tours %}
            <div style="background:#1e293b; padding:10px; margin-bottom:8px; border-radius:6px;">
                🏆 <b>{{ t[1] }}</b> (وضعیت: {{ t[2] }})<br>
                
                {% if t[2] == 'ثبت نام' %}
                    <form method="POST" action="/coach/reg_tournament" style="margin:5px 0;">
                        <input type="hidden" name="code" value="{{ code }}">
                        <input type="hidden" name="t_id" value="{{ t[0] }}">
                        <button type="submit" class="btn">📩 درخواست ثبت نام در تورنمنت</button>
                    </form>
                {% else %}
                    <div style="text-align:right; font-size:12px; background:#334155; padding:5px; border-radius:5px;">
                        📊 <b>مدیا شیت‌ها و جداول تصویری:</b><br>
                        🔹 جدول بازی‌ها: {% if t[3] %}{% for img in t[3].split(',') %}<a href="{{ img }}" target="_blank">🖼️ عکس</a> {% endfor %}{% else %}ندارد{% endif %}<br>
                        🔹 نتایج مسابقات: {% if t[4] %}{% for img in t[4].split(',') %}<a href="{{ img }}" target="_blank">🖼️ عکس</a> {% endfor %}{% else %}ندارد{% endif %}<br>
                        🔹 جدول رده‌بندی: {% if t[5] %}{% for img in t[5].split(',') %}<a href="{{ img }}" target="_blank">🖼️ عکس</a> {% endfor %}{% else %}ندارد{% endif %}<br>
                        🔹 جدول گلزنان: {% if t[6] %}{% for img in t[6].split(',') %}<a href="{{ img }}" target="_blank">🖼️ عکس</a> {% endfor %}{% else %}ندارد{% endif %}<br>
                        🔹 پاس گل‌ها: {% if t[7] %}{% for img in t[7].split(',') %}<a href="{{ img }}" target="_blank">🖼️ عکس</a> {% endfor %}{% else %}ندارد{% endif %}<br>
                        🔹 کلین‌شیت‌ها: {% if t[8] %}{% for img in t[8].split(',') %}<a href="{{ img }}" target="_blank">🖼️ عکس</a> {% endfor %}{% else %}ندارد{% endif %}<br>
                    </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <div id="c-standards" class="section">
            <h3>🌍 بانک اطلاعاتی تیم‌های استاندارد</h3>
            {% for st in std_teams %}
                <div style="background:#1e293b; padding:10px; margin-bottom:8px; border-radius:6px; text-align:right;">
                    🛡️ <b>تیم: {{ st[2] }}</b> | ⭐ ستاره: {{ st[4] }} | 💎 اعتبار مورد نیاز برای مسابقه: {{ st[3] }}
                    <br><span style="font-size:11px; color:#38bdf8;">🏃‍♂️ بخش بازیکنان این تیم:</span>
                    <div style="margin-top:5px;">
                        {% for sp in std_players %}
                            {% if sp[1] == st[0] %}
                                <span class="badge">{{ sp[2] }} {% if sp[3] %}(<a href="{{ sp[3] }}" target="_blank" style="color:#000;">کارت</a>){% endif %}</span>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>
            {% endfor %}
        </div>

        <div id="c-transfer" class="section">
            <h3>🔄 فرم ثبت توافق رسمی نقل و انتقالات برای ادمین</h3>
            <form method="POST" action="/coach/submit_transfer">
                <input type="hidden" name="code" value="{{ code }}">
                <input type="text" name="message" placeholder="مثال: واگذاری هری کین به تیم Y در قبال ۵۰۰ سکه" required>
                <button type="submit" class="btn">📩 ارسال مستقیم به ادمین</button>
            </form>
        </div>

        <div id="c-shop" class="section">
            <h3>🏪 فروشگاه رسمی سوپرلیگ کارتی</h3>
            
            {% for prod in products %}
            <div style="background:#1e293b; padding:12px; margin-bottom:10px; border-radius:6px; text-align:right;">
                <h4>📦 {{ prod[1] }}</h4>
                <p>نوع فروش: <b>{{ prod[2] }}</b> | قیمت: <b>{{ prod[4] }}</b></p>
                
                {% if prod[2] == 'قطعی_سکه' %}
                    <form method="POST" action="/coach/buy_product_coins">
                        <input type="hidden" name="code" value="{{ code }}">
                        <input type="hidden" name="p_id" value="{{ prod[0] }}">
                        <button type="submit" class="btn" style="background:green;">💳 خرید قطعی و کسر سکه</button>
                    </form>
                
                {% elif prod[2] == 'قطعی_پولی' %}
                    <div style="background:#334155; padding:8px; border-radius:5px;">
                        <p style="color:#eab308; margin:0 0 5px 0;">روش پرداخت را انتخاب کنید:</p>
                        <button class="btn" onclick="alert('برای خرید مستقیم پولی به آیدی تلگرام مربی پیام دهید و هزینه را پرداخت کنید: @Mamad13287')">💳 پرداخت مستقیم</button>
                        
                        <form method="POST" action="/coach/buy_product_wallet" style="display:inline-block; margin:0;">
                            <input type="hidden" name="code" value="{{ code }}">
                            <input type="hidden" name="p_id" value="{{ prod[0] }}">
                            <button type="submit" style="font-size:12px; cursor:pointer; padding:8px 15px; border-radius:6px; background:blue; color:white; border:none; font-weight:bold;">💼 خرید از کیف پول</button>
                        </form>
                    </div>

                {% elif prod[2] == 'شانسی' %}
                    <form method="POST" action="/coach/buy_product_box">
                        <input type="hidden" name="code" value="{{ code }}">
                        <input type="hidden" name="p_id" value="{{ prod[0] }}">
                        <button type="submit" class="btn" style="background:#eab308; color:#000;">🎰 چرخاندن گردونه شانسی</button>
                    </form>
                {% endif %}
            </div>
            {% endfor %}

            {% if track_msg %}
                <div style="background:green; padding:10px; margin-top:8px; border-radius:5px;">
                    🎉 {{ track_msg }}
                </div>
            {% endif %}
        </div>

        <div id="c-gifts" class="section">
            <h3>🎁 فعال‌سازی کد هدیه دریافتی</h3>
            <form method="POST" action="/coach/claim_gift">
                <input type="hidden" name="code" value="{{ code }}">
                <input type="text" name="g_code" placeholder="کد هدیه را اینجا بنویسید" required style="text-align:center;">
                <button type="submit" class="btn" style="background:#eab308; color:#000; width:100%;">🎁 دریافت جایزه</button>
            </form>
        </div>

        <div id="c-contact" class="section">
            <h3>📞 پل‌های ارتباطی با فدراسیون</h3>
            <p style="font-size:18px; color:#38bdf8; font-weight:bold;">🆔 آیدی تلگرام مدیریت سوپرلیگ: @Mamad13287</p>
            <p style="font-size:12px; color:#94a3b8;">جهت گزارش مشکلات، کدهای پیگیری مالی و هماهنگی مسابقات پیام دهید.</p>
        </div>
    {% endif %}

</div>

<script>
    function showSec(id) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById(id).classList.add('active');
    }
    function toggleShopFields() {
        let type = document.getElementById('p_type_select').value;
        if(type === 'شانسی') {
            document.getElementById('shop_content_div').style.display = 'none';
            document.getElementById('shop_box_div').style.display = 'block';
        } else {
            document.getElementById('shop_content_div').style.display = 'block';
            document.getElementById('shop_box_div').style.display = 'none';
        }
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
        init_db()
    except:
        pass
    code = request.form.get('code', '').strip()
    if code == ADMIN_PASSWORD:
        return reload_admin_dashboard()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coaches WHERE login_code = %s", (code,))
    coach = cursor.fetchone()
    if coach:
        cursor.execute("SELECT * FROM account_permissions WHERE account_type = %s", (coach[6],))
        perms = cursor.fetchone() or (coach[6],0,0,0,0,0,0,0,0,0,0)
        cursor.execute("SELECT * FROM matches")
        matches = cursor.fetchall()
        cursor.execute("SELECT * FROM tournaments")
        tours = cursor.fetchall()
        cursor.execute("SELECT * FROM players WHERE team_code=%s", (code,))
        coach_players = cursor.fetchall()
        cursor.execute("SELECT * FROM standard_teams")
        std_teams = cursor.fetchall()
        cursor.execute("SELECT * FROM standard_players")
        std_players = cursor.fetchall()
        cursor.execute("SELECT * FROM shop_products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template_string(HTML_TEMPLATE, role="coach", data=coach, code=code, perms=perms, matches=matches, tours=tours, coach_players=coach_players, std_teams=std_teams, std_players=std_players, products=products)
    
    cursor.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, role="none", error="❌ کد ورود مربیگری یا رمز ادمین اشتباه است.")

def reload_admin_dashboard(order_search=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coaches")
    teams = cursor.fetchall()
    cursor.execute("SELECT * FROM admin_logs ORDER BY id DESC")
    logs = cursor.fetchall()
    cursor.execute("SELECT * FROM matches")
    matches = cursor.fetchall()
    cursor.execute("SELECT * FROM tournaments")
    tours = cursor.fetchall()
    cursor.execute("SELECT * FROM tournament_regs")
    regs = cursor.fetchall()
    cursor.execute("SELECT * FROM standard_leagues")
    std_leagues = cursor.fetchall()
    cursor.execute("SELECT * FROM standard_teams")
    std_teams = cursor.fetchall()
    cursor.execute("SELECT * FROM shop_products")
    products = cursor.fetchall()
    cursor.execute("SELECT players.id, coaches.team_name, players.player_name, players.card_url, players.position, players.download_url FROM players JOIN coaches ON players.team_code = coaches.login_code")
    all_players = cursor.fetchall()
    cursor.execute("SELECT * FROM match_lineups")
    lineups = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, role="admin", teams=teams, logs=logs, matches=matches, tours=tours, regs=regs, std_leagues=std_leagues, std_teams=std_teams, products=products, all_players=all_players, lineups=lineups, order_search=order_search)

@app.route('/admin/create_team', methods=['POST'])
def admin_create_team():
    t_name = request.form.get('t_name', '').strip()
    code = generate_mix_code() # ۲- اختصاص کد ترکیبی عدد و حروف
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO coaches (login_code, team_name) VALUES (%s, %s)", (code, t_name))
    conn.commit()
    cursor.close()
    conn.close()
    return f"<h3>تیم مربی ساخته شد! کد ۶ رقمی ترکیبی مربی: <b style='color:cyan;'>{code}</b></h3><br><a href='/'>بازگشت به پنل</a>"

@app.route('/admin/update_coach', methods=['POST'])
def admin_update_coach():
    code = request.form.get('code')
    acc_type = request.form.get('acc_type')
    coins = int(request.form.get('u_coins'))
    credit = int(request.form.get('u_credit'))
    t_cards = int(request.form.get('u_trans_cards')) # ۱۳- افزودن کارت نقل و انتقال
    wallet = int(request.form.get('u_wallet')) # ۱۳- افزودن مقدار کیف پول
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE coaches SET account_type=%s, coins=%s, credit=%s, transfer_cards=%s, wallet=%s WHERE login_code=%s", (acc_type, coins, credit, t_cards, wallet, code))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/add_honors', methods=['POST'])
def admin_add_honors():
    # ۷- افزودن متن تالار افتخارات مربی توسط مدیر
    code = request.form.get('code')
    txt = request.form.get('honors_text')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE coaches SET honors=%s WHERE login_code=%s", (txt, code))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/add_player_to_team', methods=['POST'])
def admin_add_player_to_team():
    # ۳ و ۴- افزودن بازیکن جدید و لینک دانلود کارت توسط مدیر فدراسیون
    p_name = request.form.get('p_name')
    dl_url = request.form.get('dl_url')
    t_code = request.form.get('t_code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO players (team_code, player_name, download_url) VALUES (%s, %s, %s)", (t_code, p_name, dl_url))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/edit_player_details', methods=['POST'])
def admin_edit_player_details():
    # ۳ و ۴- ویرایش نام بازیکن و لینک دانلود کارت
    p_id = request.form.get('p_id')
    new_name = request.form.get('new_name')
    new_dl = request.form.get('new_dl')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET player_name=%s, download_url=%s WHERE id=%s", (new_name, new_dl, p_id))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/delete_player/<p_id>')
def admin_delete_player(p_id):
    # ۳- حذف بازیکن توسط مدیر
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id=%s", (p_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/create_match', methods=['POST'])
def admin_create_match():
    t_a = request.form.get('t_a')
    t_b = request.form.get('t_b')
    t_name = request.form.get('tour_name')
    desc = request.form.get('desc')
    allow_own = 1 if request.form.get('allow_own') else 0 # ۵- مشخص کردن امکان بازی با تیم خود
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO matches (team_a, team_b, tournament_name, description, allow_own_team) VALUES (%s, %s, %s, %s, %s)", (t_a, t_b, t_name, desc, allow_own))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/submit_result', methods=['POST'])
def submit_result():
    # ۶- نتایج بازی ثبت شده توسط مدیر مستقیماً به بخش تاریخچه دو تیم منتقل می‌شود
    m_id = request.form.get('m_id')
    res = request.form.get('res_text')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET result=%s WHERE id=%s", (res, m_id))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/coach/submit_lineup', methods=['POST'])
def coach_submit_lineup():
    # ۵- ثبت هوشمند ترکیب مربی شامل ۷ بازیکن با فیلتر تیم مربی یا استاندارد
    m_id = request.form.get('match_id')
    code = request.form.get('code')
    t_type = request.form.get('team_type')
    p_list = request.form.get('players_list')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO match_lineups (match_id, team_code, team_type, players_list) VALUES (%s, %s, %s, %s)", (m_id, code, t_type, p_list))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>ترکیب ۷ نفره شما ثبت شد و برای داور مسابقه ارسال گردید.</h3><br><a href='/'>بازگشت</a>"

@app.route('/coach/submit_transfer', methods=['POST'])
def coach_submit_transfer():
    # ۱۰- تضمین دریافت ۱۰۰٪ پیام توافقی مربیان به دست مدیر فدراسیون
    code = request.form.get('code')
    msg = request.form.get('message')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    c = cursor.fetchone()
    t_name = c[0] if c else "نامشخص"
    cursor.execute("INSERT INTO admin_logs (team_name, log_type, message) VALUES (%s, 'نقل و انتقالات مربی', %s)", (t_name, msg))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>پیام نقل و انتقالات با موفقیت برای مدیر ارسال شد.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/create_tournament', methods=['POST'])
def admin_create_tournament():
    name = request.form.get('tour_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tournaments (name) VALUES (%s)", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/coach/reg_tournament', methods=['POST'])
def coach_reg_tournament():
    # ۸- ثبت نام اولیه در تورنمنت و رفتن به وضعیت انتظار تایید مدیر
    code = request.form.get('code')
    t_id = request.form.get('t_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_name FROM coaches WHERE login_code=%s", (code,))
    t_name = cursor.fetchone()[0]
    cursor.execute("INSERT INTO tournament_regs (tournament_id, team_name) VALUES (%s, %s)", (t_id, t_name))
    conn.commit()
    cursor.close()
    conn.close()
    return "<h3>درخواست ثبت‌نام شما ارسال شد و در انتظار تایید مدیریت است.</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/approve_reg/<reg_id>')
def admin_approve_reg(reg_id):
    # ۸- تایید درخواست مربی توسط ادمین
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_regs SET status='تایید شده' WHERE id=%s", (reg_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/reject_reg/<reg_id>')
def admin_reject_reg(reg_id):
    # ۸- رد درخواست ثبت نام مربی
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tournament_regs WHERE id=%s", (reg_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/start_tournament/<t_id>')
def admin_start_tournament(t_id):
    # ۸- شروع تورنمنت و حذف مابقی فرم ثبت نام و ایجاد پنل آپلود عکس پیشرفته مدیریت جداول
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournaments SET status='در حال برگزاری' WHERE id=%s", (t_id,))
    cursor.execute("DELETE FROM tournament_regs WHERE tournament_id=%s AND status='انتظار تایید'", (t_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/upload_tour_media', methods=['POST'])
def admin_upload_tour_media():
    # ۸- امکان آپلود و افزودن چند عکس مستقیم با ویرگول برای جداول رده بندی، نتایج، گلزنان، پاس گل و کلین شیت
    t_id = request.form.get('t_id')
    s = request.form.get('img_stats')
    r = request.form.get('img_results')
    st = request.form.get('img_standings')
    sc = request.form.get('img_scorers')
    asst = request.form.get('img_assists')
    cl = request.form.get('img_cleansheets')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournaments SET stats_images=%s, results_images=%s, standings_images=%s, scorers_images=%s, assists_images=%s, cleansheets_images=%s WHERE id=%s", (s, r, st, sc, asst, cl, t_id))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/add_std_league', methods=['POST'])
def admin_add_std_league():
    name = request.form.get('l_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO standard_leagues (league_name) VALUES (%s)", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/add_std_team', methods=['POST'])
def admin_add_std_team():
    # ۹- تعیین تعداد ستاره و اعتبار مورد نیاز برای استفاده در بازی استاندارد
    l_id = request.form.get('l_id')
    name = request.form.get('t_name')
    cre = request.form.get('credit_req')
    stars = request.form.get('stars')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO standard_teams (league_id, team_name, credit_required, stars) VALUES (%s, %s, %s, %s)", (l_id, name, cre, stars))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/add_std_player', methods=['POST'])
def admin_add_std_player():
    # ۹- افزودن بازیکن به بخش جدا شده تیم استاندارد به همراه لینک کارت تفکیک شده
    t_id = request.form.get('std_t_id')
    p_name = request.form.get('p_name')
    dl = request.form.get('dl_url')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO standard_players (team_id, player_name, download_url) VALUES (%s, %s, %s)", (t_id, p_name, dl))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/add_product', methods=['POST'])
def admin_add_product():
    # ۱۱- پنل پیشرفته مدیریت آیتم‌های فروشگاه کارتی (سه مورد مجزا)
    name = request.form.get('p_name')
    p_type = request.form.get('p_type')
    price = int(request.form.get('price'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO shop_products (name, type, price_type, price_value) VALUES (%s, %s, %s, %s) RETURNING id", (name, p_type, 'سکه' if 'سکه' in p_type else 'تومان', price))
    p_id = cursor.fetchone()[0]
    
    if p_type == 'قطعی_سکه':
        c_player = request.form.get('c_player','')
        c_credit = request.form.get('c_credit') or '0'
        c_trans = request.form.get('c_trans') or '0'
        dl_url = request.form.get('c_player_dl','')
        val_str = f"{c_player}:{dl_url}:{c_credit}:{c_trans}"
        cursor.execute("UPDATE shop_products SET content_type='pack', content_value=%s WHERE id=%s", (val_str, p_id))
    elif p_type == 'شانسی':
        b_player = request.form.get('b_player', 'بازیکن معمولی باکس')
        b_chance = int(request.form.get('b_chance') or 5)
        cursor.execute("INSERT INTO box_items (product_id, player_name, chance) VALUES (%s, %s, %s)", (p_id, b_player, b_chance))
        
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/delete_product/<p_id>')
def admin_delete_product(p_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop_products WHERE id=%s", (p_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/coach/buy_product_coins', methods=['POST'])
def buy_product_coins():
    # ۱۱- مورد اول: خرید قطعی با سکه (پک ها) و اعمال فوری محتویات به مربی همراه کد پیگیری
    code = request.form.get('code')
    p_id = request.form.get('p_id')
    track = "TRK" + str(random.randint(100000, 999999))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coins, team_name FROM coaches WHERE login_code=%s", (code,))
    c = cursor.fetchone()
    cursor.execute("SELECT * FROM shop_products WHERE id=%s", (p_id,))
    p = cursor.fetchone()
    
    if c and p and c[0] >= p[4]:
        new_coins = c[0] - p[4]
        cursor.execute("UPDATE coaches SET coins=%s WHERE login_code=%s", (new_coins, code))
        
        parts = p[6].split(':')
        p_name = parts[0] if len(parts) > 0 else ""
        dl_url = parts[1] if len(parts) > 1 else ""
        add_cre = int(parts[2]) if len(parts) > 2 and parts[2] else 0
        add_tr = int(parts[3]) if len(parts) > 3 and parts[3] else 0
        
        if p_name:
            cursor.execute("INSERT INTO players (team_code, player_name, download_url) VALUES (%s, %s, %s)", (code, p_name, dl_url))
        cursor.execute("UPDATE coaches SET credit = credit + %s, transfer_cards = transfer_cards + %s WHERE login_code=%s", (add_cre, add_tr, code))
        
        cursor.execute("INSERT INTO shop_orders (track_code, team_name, product_name, details) VALUES (%s, %s, %s, %s)", (track, c[1], p[1], f"خرید قطعی پک با کسر {p[4]} سکه."))
        conn.commit()
        msg = f"✅ خرید موفق! محصول فعال شد. کد پیگیری شما: {track}"
    else:
        msg = "❌ سکه شما برای خرید این پک کافی نیست!"
        
    cursor.close()
    conn.close()
    return f"<h3>{msg}</h3><br><a href='/'>بازگشت</a>"

@app.route('/coach/buy_product_wallet', methods=['POST'])
def buy_product_wallet():
    # ۱۱- مورد دوم: خرید از طریق موجودی کیف پول و چک کردن اعتبار مربی همراه با آیدی پیگیری تلگرام ادمین
    code = request.form.get('code')
    p_id = request.form.get('p_id')
    track = "TRK" + str(random.randint(100000, 999999))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT wallet, team_name FROM coaches WHERE login_code=%s", (code,))
    c = cursor.fetchone()
    cursor.execute("SELECT * FROM shop_products WHERE id=%s", (p_id,))
    p = cursor.fetchone()
    
    if c and p and c[0] >= p[4]:
        new_wallet = c[0] - p[4]
        cursor.execute("UPDATE coaches SET wallet=%s WHERE login_code=%s", (new_wallet, code))
        cursor.execute("INSERT INTO shop_orders (track_code, team_name, product_name, details) VALUES (%s, %s, %s, %s)", (track, c[1], p[1], f"خرید از کیف پول با کسر {p[4]} تومان."))
        conn.commit()
        msg = f"✅ خرید با موفقیت از کیف پول کسر شد! کد پیگیری مالی شما: {track}"
    else:
        msg = "❌ اعتبار کیف پول شما کم است! لطفاً ابتدا آن را شارژ کنید."
        
    cursor.close()
    conn.close()
    return f"<h3>{msg}</h3><br><a href='/'>بازگشت</a>"

@app.route('/coach/buy_product_box', methods=['POST'])
def buy_product_box():
    # ۱۱- مورد سوم: خرید شانسی و چرخاندن گردونه کاملاً تصادفی با رعایت شانس‌ها بدون تکرار یکنواخت برای همه تیم‌ها
    code = request.form.get('code')
    p_id = request.form.get('p_id')
    track = "TRK" + str(random.randint(100000, 999999))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coins, team_name FROM coaches WHERE login_code=%s", (code,))
    c = cursor.fetchone()
    cursor.execute("SELECT * FROM shop_products WHERE id=%s", (p_id,))
    p = cursor.fetchone()
    
    if c and p and c[0] >= p[4]:
        cursor.execute("SELECT player_name, chance FROM box_items WHERE product_id=%s", (p_id,))
        items = cursor.fetchall()
        if not items:
            items = [("امباپه ویژه", 2), ("بازیکن تصادفی لیگ", 8)]
            
        pool = []
        for name, weight in items:
            pool.extend([name] * weight)
        selected_player = random.choice(pool)
        
        cursor.execute("UPDATE coaches SET coins = coins - %s WHERE login_code=%s", (p[4], code))
        cursor.execute("INSERT INTO players (team_code, player_name) VALUES (%s, %s)", (code, selected_player))
        cursor.execute("INSERT INTO shop_orders (track_code, team_name, product_name, details) VALUES (%s, %s, %s, %s)", (track, c[1], p[1], f"باز کردن باکس شانسی و برنده شدن بازیکن: {selected_player}"))
        conn.commit()
        msg = f"🎉 شانس شما با موفقیت چرخید! بازیکن دریافتی: [{selected_player}] | کد پیگیری سیستم: {track}"
    else:
        msg = "❌ سکه کافی برای چرخاندن این باکس شانسی را ندارید!"
        
    cursor.close()
    conn.close()
    return f"<h3>{msg}</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/check_order', methods=['POST'])
def admin_check_order():
    tc = request.form.get('track_code').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shop_orders WHERE track_code=%s", (tc,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return reload_admin_dashboard(order_search=res)

@app.route('/admin/add_gift', methods=['POST'])
def admin_add_gift():
    # ۱۸- بخش تعریف کد هدیه جدید و تعیین نوع و مقدار جایزه توسط مدیر
    gc = request.form.get('g_code').strip()
    gt = request.form.get('g_type')
    gv = request.form.get('g_val').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gift_codes (code, reward_type, reward_value) VALUES (%s, %s, %s) ON CONFLICT (code) DO UPDATE SET reward_type=%s, reward_value=%s", (gc, gt, gv, gt, gv))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/coach/claim_gift', methods=['POST'])
def coach_claim_gift():
    # ۱۸- بررسی هوشمند کد هدیه و اعمال فوری هدیه روی حساب مربی
    code = request.form.get('code')
    gc = request.form.get('g_code').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gift_codes WHERE code=%s", (gc,))
    g = cursor.fetchone()
    
    if g:
        rtype = g[1]
        rval = int(g[2])
        if rtype == 'coins':
            cursor.execute("UPDATE coaches SET coins = coins + %s WHERE login_code=%s", (rval, code))
        elif rtype == 'credit':
            cursor.execute("UPDATE coaches SET credit = credit + %s WHERE login_code=%s", (rval, code))
        elif rtype == 'trans':
            cursor.execute("UPDATE coaches SET transfer_cards = transfer_cards + %s WHERE login_code=%s", (rval, code))
        elif rtype == 'wallet':
            cursor.execute("UPDATE coaches SET wallet = wallet + %s WHERE login_code=%s", (rval, code))
            
        cursor.execute("DELETE FROM gift_codes WHERE code=%s", (gc,)) # یکبار مصرف
        conn.commit()
        msg = "🎉 کد هدیه معتبر بود! جوایز با موفقیت به اکانت شما اضافه شد."
    else:
        msg = "❌ این کد هدیه نامعتبر است یا قبلاً توسط شخص دیگری استفاده شده است!"
        
    cursor.close()
    conn.close()
    return f"<h3>{msg}</h3><br><a href='/'>بازگشت</a>"

@app.route('/admin/update_permissions', methods=['POST'])
def admin_update_permissions():
    # ۱۴- فراهم کردن امکان قفل کردن تمام بخش‌ها و منوهای بازی به صورت مجزا
    target = request.form.get('target_acc')
    lp = 1 if request.form.get('lock_player') else 0
    lt = 1 if request.form.get('lock_team') else 0
    ll = 1 if request.form.get('lock_league') else 0
    ltour = 1 if request.form.get('lock_tour') else 0
    ls = 1 if request.form.get('lock_shop') else 0
    ltrans = 1 if request.form.get('lock_trans') else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE account_permissions 
        SET player_locked=%s, team_locked=%s, league_locked=%s, tournament_locked=%s, shop_locked=%s, transfer_locked=%s 
        WHERE account_type=%s
    ''', (lp, lt, ll, ltour, ls, ltrans, target))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

@app.route('/admin/delete_team/<code>')
def admin_delete_team(code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM coaches WHERE login_code = %s", (code,))
    conn.commit()
    cursor.close()
    conn.close()
    return reload_admin_dashboard()

if __name__ == '__main__':
    try:
        init_db()
    except:
        pass
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
