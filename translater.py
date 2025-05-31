import os
import polib
import subprocess
from googletrans import Translator

# 翻译配置
SOURCE_LANG = 'zh-cn'
TRANSLATIONS_DIR = 'translations'
LANG_CODE_MAP = {
    "zh": "zh-cn",
    "en": "en",
    "fr": "fr",
    "ja": "ja",
    "ko": "ko",
    # 可继续扩展
}

translator = Translator()

def extract_messages():
    print("🔍 正在提取翻译字符串到 messages.pot ...")
    try:
        subprocess.run([
            'pybabel', 'extract',
            '-F', 'babel.cfg',
            '-o', os.path.join(TRANSLATIONS_DIR, 'messages.pot'),
            '.'
        ], check=True)
        print("✅ 提取完成，生成 messages.pot")
    except subprocess.CalledProcessError:
        print("❌ 提取失败，请检查 pybabel 是否安装、babel.cfg 是否正确")

def init_po_files():
    pot_path = os.path.join(TRANSLATIONS_DIR, 'messages.pot')
    for lang in LANG_CODE_MAP.keys():
        lang_dir = os.path.join(TRANSLATIONS_DIR, lang, 'LC_MESSAGES')
        po_path = os.path.join(lang_dir, 'messages.po')
        if not os.path.exists(po_path):
            print(f"🆕 初始化 {lang} 翻译目录 ...")
            try:
                subprocess.run([
                    'pybabel', 'init',
                    '-l', lang,
                    '-d', TRANSLATIONS_DIR,
                    '-i', pot_path
                ], check=True)
                print(f"✅ 初始化成功: {po_path}")
            except subprocess.CalledProcessError:
                print(f"❌ 初始化失败: {lang}")
        else:
            print(f"✅ 已存在翻译文件: {po_path}")

def update_po_files():
    pot_path = os.path.join(TRANSLATIONS_DIR, 'messages.pot')
    for lang in os.listdir(TRANSLATIONS_DIR):
        lang_dir = os.path.join(TRANSLATIONS_DIR, lang, 'LC_MESSAGES')
        po_path = os.path.join(lang_dir, 'messages.po')
        if os.path.exists(po_path):
            print(f"🔄 正在更新 {po_path} ...")
            try:
                subprocess.run([
                    'pybabel', 'update',
                    '-l', lang,
                    '-d', TRANSLATIONS_DIR,
                    '-i', pot_path
                ], check=True)
                print(f"✅ 已更新: {po_path}")
            except subprocess.CalledProcessError:
                print(f"❌ 更新失败: {po_path}")
        else:
            print(f"⚠️ 跳过更新：找不到 {po_path}")

def translate_po_file(po_path, target_lang):
    print(f"\n🌐 正在处理 {po_path} → {target_lang}")
    po = polib.pofile(po_path)
    changed = False

    for entry in po.untranslated_entries():
        if entry.msgstr.strip() == "":
            try:
                result = translator.translate(entry.msgid, src=SOURCE_LANG, dest=target_lang)
                entry.msgstr = result.text
                print(f"✅ 翻译: {entry.msgid} → {entry.msgstr}")
                changed = True
            except Exception as e:
                print(f"❌ 翻译失败: {entry.msgid} - {e}")

    if changed:
        po.save(po_path)
        print(f"💾 已保存翻译结果: {po_path}")
    else:
        print("✅ 无需翻译，已全部完成")

def compile_translations():
    try:
        subprocess.run(['pybabel', 'compile', '-d', TRANSLATIONS_DIR], check=True)
        print("✅ 所有翻译已成功编译为 .mo 文件")
    except subprocess.CalledProcessError:
        print("❌ pybabel 编译失败，请检查 pybabel 是否已安装")

def main():
    if not os.path.isdir(TRANSLATIONS_DIR):
        print(f"❌ 目录不存在: {TRANSLATIONS_DIR}")
        return

    extract_messages()
    init_po_files()
    update_po_files()

    for lang_dir in os.listdir(TRANSLATIONS_DIR):
        po_path = os.path.join(TRANSLATIONS_DIR, lang_dir, 'LC_MESSAGES', 'messages.po')
        if os.path.exists(po_path):
            target_lang = LANG_CODE_MAP.get(lang_dir, lang_dir)
            translate_po_file(po_path, target_lang)
        else:
            print(f"⚠️ 跳过：找不到 {po_path}")

    compile_translations()

if __name__ == '__main__':
    main()
