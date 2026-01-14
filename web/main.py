import os
from flask import Flask, render_template, send_from_directory, abort

# Настройка папок
template_dir = os.path.abspath('templates')
static_dir = os.path.abspath('static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Путь к папке с APK файлами
FILES_DIRECTORY = os.path.join(os.getcwd(), 'files')

@app.route('/')
def index():
    """Отдает главную страницу"""
    return render_template('index.html')

@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Скачивание APK из папки files.
    """
    try:
        return send_from_directory(directory=FILES_DIRECTORY, path=filename, as_attachment=True)
    except FileNotFoundError:
        return abort(404, description="Файл не найден")

if __name__ == '__main__':
    # Проверка и создание необходимых папок
    if not os.path.exists(FILES_DIRECTORY):
        os.makedirs(FILES_DIRECTORY)
        print(f"[INFO] Создана папка {FILES_DIRECTORY}. Положите туда .apk файлы!")
    
    # Проверка папки static (просто предупреждение)
    if not os.path.exists(static_dir):
        print(f"[WARNING] Папка {static_dir} не найдена! Картинки и стили не загрузятся.")

    print(f"Сервер запущен: http://localhost:6001")
    app.run(host='0.0.0.0', port=6001, debug=True)