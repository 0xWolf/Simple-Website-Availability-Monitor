import requests
import sqlite3
import time
from datetime import datetime
import signal
import sys

# 网站列表
websites = [
    "https://www.bilibili.com"
]

# chrome header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
}

# 创建SQLite数据库连接
conn = sqlite3.connect('website_monitor.db')
cursor = conn.cursor()

# 创建表格（如果不存在）
cursor.execute('''
CREATE TABLE IF NOT EXISTS website_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    website TEXT,
    current_month TEXT,
    normal_work_time INTEGER,
    downtime INTEGER,
    last_updated TEXT
)
''')

# 网站存活探测函数
def check_website_status(website):
    try:
        response = requests.get(website, headers=headers, timeout=10)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.RequestException:
        return False

# 获取当前月份
def get_current_month():
    return datetime.now().strftime("%Y-%m")

# 初始化加载数据库中的当前状态
def load_website_status(current_month):
    website_status = {}
    
    cursor.execute('''
    SELECT website, normal_work_time, downtime FROM website_status WHERE current_month = ?
    ''', (current_month,))
    
    rows = cursor.fetchall()
    
    for row in rows:
        website_status[row[0]] = {
            'normal_work_time': row[1],
            'downtime': row[2]
        }
    
    return website_status

# 更新数据库中的记录
def update_website_status(website, normal_work_time, downtime, current_month):
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
    SELECT * FROM website_status WHERE website = ? AND current_month = ?
    ''', (website, current_month))
    
    data = cursor.fetchone()
    
    if data:
        # 如果数据存在，更新
        cursor.execute('''
        UPDATE website_status
        SET normal_work_time = ?, downtime = ?, last_updated = ?
        WHERE website = ? AND current_month = ?
        ''', (normal_work_time, downtime, last_updated, website, current_month))
    else:
        # 如果数据不存在，插入新记录
        cursor.execute('''
        INSERT INTO website_status (website, current_month, normal_work_time, downtime, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ''', (website, current_month, normal_work_time, downtime, last_updated))
    
    conn.commit()

# 定义程序终止时的处理方法
def handle_signal(signum, frame):
    print("\n程序终止中... 保存数据")
    conn.close()  # 关闭数据库连接
    sys.exit(0)

# 注册终止信号处理函数
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# 监控主循环
def monitor_websites():
    current_month = get_current_month()
    website_status = load_website_status(current_month)

    while True:
        new_month = get_current_month()
        if new_month != current_month:
            current_month = new_month
            website_status = load_website_status(current_month)

        for website in websites:
            if website not in website_status:
                website_status[website] = {'normal_work_time': 0, 'downtime': 0}

            if check_website_status(website):
                website_status[website]['normal_work_time'] += 1
            else:
                website_status[website]['downtime'] += 1
                print(f"{datetime.now()} - {website} -> 当前无法访问")

            update_website_status(website, website_status[website]['normal_work_time'], website_status[website]['downtime'], current_month)

        time.sleep(60)

# 启动监控
if __name__ == "__main__":
    monitor_websites()
