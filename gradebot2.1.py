import telebot
import csv
import matplotlib
import io
import os
from dotenv import load_dotenv
import pandas as pd
import sqlite3
from io import BytesIO
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import PIL
load_dotenv()
TOKEN= os.getenv
valid = {'математика', 'русский', 'английский', 'физика', 'химия', 'биология', 'история', 'география', 'информатика', 'литература', 'обж', 'физкультура', 'музыка', 'рисование', 'технология'}
bot = telebot.TeleBot('TOKEN')
DB_PATH = 'grades.db'
def init_db():
  if not os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE grades (
    user_id INTEGER,
    subject TEXT,
    grade INTEGER,
    timestamp TEXT
    )
    ''')
    conn.commit()
    conn.close()
# === КОМАНДА /add ===
@bot.message_handler(commands=['add'])
def add_command(message):
  text = message.text.split()
  if len(text) < 3:
    bot.reply_to(message, "Пример: /add математика 5 4 3")
    return

  chat_id = message.chat.id
  subject = text[1]
  if subject.lower() not in valid:
    bot.reply_to(message, 'Разрешены: математика, русский, английский, физика, химия, биология, история, география, информатика, литература, обж, физкультура, музыка, рисование, технология')
    return
  try:
    grades = [int(x) for x in text[2:] if x.isdigit() and 1 <= int(x) <= 5]
    if not grades:
      bot.reply_to(message, "Нет оценок от 1 до 5")
      return

    with sqlite3.connect(DB_PATH) as conn:
      cursor = conn.cursor()
      init_db()
      for g in grades:
        cursor.execute(
        'INSERT INTO grades (user_id, subject, grade) VALUES (?, ?, ?)',(chat_id, subject, g))


      bot.reply_to(message, f"✅ Добавлено {len(grades)} оценок по '{subject}'")

  except Exception as e:
    bot.reply_to(message, f"❌ Ошибка: {e}")

# === КОМАНДА /stats ===
@bot.message_handler(commands=['stats'])
def stats_command(message):
  chat_id = message.chat.id
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()

  cursor.execute("SELECT COUNT(*), AVG(grade) FROM grades WHERE user_id = ?", (chat_id,))
  total, avg = cursor.fetchone()

  if total == 0:
    bot.reply_to(message, "Нет оценок. Сначала добавь через /add")
    conn.close()
    return

  cursor.execute("""
  SELECT subject, COUNT(*), AVG(grade)
  FROM grades
  WHERE user_id = ?
  GROUP BY subject
  ORDER BY subject
  """, (chat_id,))
  subjects = cursor.fetchall()
  conn.close()

  msg = f"📊 Статистика:\nВсего оценок: {total}\nСредний балл: {avg:.2f}\n\nПо предметам:\n"
  for subj, cnt, s_avg in subjects:
    msg += f"• ✅ {subj}: {s_avg:.2f} ({cnt} оценок)\n"

  bot.send_message(chat_id, msg) # ← ВАЖНО: не reply_to, а send_message
@bot.message_handler(commands=['start'])
def start_command(message):
  bot.reply_to(message, '👋 Привет! Я GradeBot - твой школьный помощник по оценкам.\n\n Команды: \n•/import - выгрузить оценки в базу\n\n• /add предмет оценка - добавить оценку\n• /stats - показать средний балл\n• /export - скачать CSV файл\n•/graph - присылает график твоих оценок\n•/help или /about - помощь с GradeBot\n\nУдачи в учёбе!💯')
@bot.message_handler(commands=['export'])
def export_command(message):
  chat_id = message.chat.id
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute('SELECT subject, grade, timestamp FROM grades WHERE user_id = ?', (chat_id,))
  rows = cursor.fetchall()
  conn.close()
  if not rows:
    bot.reply_to(message,'📎 У тебя пока нет  оценок для экспорта.')
    return
  output = io.StringIO()
  writer = csv.writer(output)
  writer.writerow(rows)
  output.seek(0)
  csv_data = output.getvalue().encode('utf-8-sig')
  bot.send_document(
      message.chat.id,
      io.BytesIO(csv_data),
      caption='📤 Твои оценки (CSV)',
      visible_file_name ='оценки.csv'
  )
@bot.message_handler(commands=['help', 'about'])
def help_command(message):
  bot.reply_to(message,'❓🤖 Помощь по GradeBot\n\n/add предмет оценка\n→ Добавить одну или несколько оценок.\nПример: /add математика 5 или: /add русский 4 5 3\n\n/stats\n→ Показать средний балл по всем предметам.\n\n/import - затем присылай csv и все оценки выгрузятся в базу\n\n/export\n→ Получить файл с оценками (CSV).\n\n/graph\n→ Присылает график твоих оценок\n\n⚠️ Советы:\n• Предмет пиши строчными буквами (без заглавных).\n• Оценки - только цифры от 1 до 5.\n• Бот не работает ночью - как и ты! 😴')

@bot.message_handler(commands=['graph'])
def graph_command(message):
  chat_id = message.chat.id
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute('SELECT grade  FROM grades WHERE user_id = ? ORDER BY timestamp', (chat_id,))
  rows = cursor.fetchall()
  conn.close()
  if not rows:
    bot.reply_to(message,'📎 У тебя пока нет оценок для графика.')
    return

  grades = [row[0] for row in rows]
  x = list(range(1, len(grades) + 1))
  y = grades

  plt.figure(figsize=(6,4))
  plt.plot(x, y, 'o-', color='b')
  plt.title("Твои оценки", fontsize=14)
  plt.xlabel("№ оценки")
  plt.ylabel("Балл")
  plt.ylim(0,5.5)
  plt.yticks([1,2,3,4,5])
  plt.grid(True)

  buf = BytesIO()
  plt.savefig(buf, format='png', bbox_inches='tight')
  buf.seek(0)
  plt.close()
  bot.send_photo(chat_id, buf, caption="График 📈")
@bot.message_handler(commands=['import'])
def import_command(message):
  bot.reply_to(message, 'Пришлите CSV-файл с колонками: subject, grade')
@bot.message_handler(content_types=['document'])
def document_command(message):
  if not message.document:
    bot.reply_to(message, '❌ Не получилось прочитать файл. Пришлите .csv напрямую.')
  if not message.document.file_name.endswith('.csv'):
    bot.reply_to(message,'❌ Нужен файл .csv' )
    return
  try:
    file_info = bot.get_file(message.document.file_id)
    download_file = bot.download_file(file_info.file_path)
    csv_data = download_file.decode("utf-8")
    df = pd.read_csv(io.StringIO(csv_data), skipinitialspace=True)
    if 'subject' not in df.columns or 'grade' not in df.columns:
      bot.reply_to(message, 'В CSV должны быть колонки: subject, grade')
      return
    df = df[pd.to_numeric(df['grade'], errors='coerce').between(1, 5)]
    df = df.dropna(subset=['subject'])
    if df.empty:
      bot.reply_to(message, 'Нет корректных данных для импорта')
      return
    chat_id = message.chat.id
    conn = sqlite3.connect('grades.db')
    cursor = conn.cursor()
    for _, row in df.iterrows():
      cursor.execute(
        'INSERT INTO grades (user_id, subject, grade) VALUES (?, ?, ?)',
        (chat_id, str(row['subject']), int(row['grade']))
      )
    conn.commit()
    conn.close()
    bot.reply_to(message, f'✅ Импортировано {len(df)} оценок')
  except Exception as e:
    bot.reply_to(message, f'❌ Ошибка при импорте: {e}')

bot.polling(none_stop=True)
