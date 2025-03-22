import logging
import os
import json
import random
import re
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)

# Konfiguratsiya
TOKEN = "7684768713:AAFQvFC2PHTLVQycopDQ9fvQ6AvSwTo-oYA"
ADMIN_ID = 7630251636
DATA_FILE = 'data.json'

# Conversation holatlari
(
    AWAITING_PART,
    AWAITING_NAME,
    AWAITING_FILE,
    AWAITING_CONTACT_OR_INFO,
    AWAITING_PHONE,
) = range(5)

# Funksiyalar
def validate_phone(phone: str) -> bool:
    pattern = r'^\+998\d{9}$'
    return re.match(pattern, phone) is not None

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault('part1', {})
            data.setdefault('part2', {})
            data.setdefault('part3', {})
            data.setdefault('users', {})
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"part1": {}, "part2": {}, "part3": {}, "users": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ADMIN QISMI
async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Siz admin emassiz!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("Part1", callback_data='part1'),
         InlineKeyboardButton("Part2", callback_data='part2'),
         InlineKeyboardButton("Part3", callback_data='part3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qaysi partga qo'shmoqchisiz?", reply_markup=reply_markup)
    return AWAITING_PART

async def receive_part(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['part'] = query.data
    await query.edit_message_text(text="Fayl nomini kiriting:")
    return AWAITING_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Endi faylni yuboring (document):")
    return AWAITING_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file_id = None
    if update.message.document:
        file_id = update.message.document.file_id
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
    
    if not file_id:
        await update.message.reply_text("❌ Xato: Faqat document yoki photo qabul qilinadi!")
        return AWAITING_FILE
    
    data = load_data()
    part = context.user_data['part']
    name = context.user_data['name']
    
    data[part][name] = file_id
    save_data(data)
    
    await update.message.reply_text(f"✅ {name} fayli {part} ga muvaffaqqiyatli qo'shildi!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Bekor qilindi!")
    return ConversationHandler.END

# FOYDALANUVCHI QISMI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    data = load_data()
    
    if str(user.id) not in data['users']:
        keyboard = [[KeyboardButton("📱 Kontaktni ulashish", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "Botdan foydalanish uchun ro'yxatdan o'tishingiz kerak!\n"
            "Quyidagi tugma orqali kontaktingizni ulashing yoki "
            "Ism Familiya, +998xxxxxxxxx formatida yuboring:",
            reply_markup=reply_markup
        )
        return AWAITING_CONTACT_OR_INFO
    else:
        await show_main_menu(update)
        return ConversationHandler.END

async def show_main_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("Part1", callback_data='part1'),
         InlineKeyboardButton("Part2", callback_data='part2'),
         InlineKeyboardButton("Part3", callback_data='part3')],
        [InlineKeyboardButton("Random 🎲", callback_data='random')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Quyidagi partlardan birini tanlang:", reply_markup=reply_markup)

async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    user = update.effective_user
    user_id = str(user.id)
    
    user_data = {
        'name': f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
        'phone': contact.phone_number,
        'username': user.username
    }
    
    data = load_data()
    data['users'][user_id] = user_data
    save_data(data)
    
    await update.message.reply_text("✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
    await show_main_menu(update)
    return ConversationHandler.END

async def receive_text_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user = update.effective_user
    user_id = str(user.id)
    
    if ',' in text:
        parts = [p.strip() for p in text.split(',', 1)]
        if len(parts) == 2 and validate_phone(parts[1]):
            name, phone = parts
            user_data = {
                'name': name,
                'phone': phone,
                'username': user.username
            }
            
            data = load_data()
            data['users'][user_id] = user_data
            save_data(data)
            
            await update.message.reply_text("✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
            await show_main_menu(update)
            return ConversationHandler.END
    
    context.user_data['temp_name'] = text
    await update.message.reply_text("Iltimos telefon raqamingizni kiriting (+998xxxxxxxxx):")
    return AWAITING_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text
    user = update.effective_user
    user_id = str(user.id)
    
    if validate_phone(phone):
        user_data = {
            'name': context.user_data.get('temp_name', ''),
            'phone': phone,
            'username': user.username
        }
        
        data = load_data()
        data['users'][user_id] = user_data
        save_data(data)
        
        await update.message.reply_text("✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
        await show_main_menu(update)
        return ConversationHandler.END
    
    await update.message.reply_text("❗ Noto'g'ri telefon raqami formati. Iltimos qayta kiriting:")
    return AWAITING_PHONE

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data in ['part1', 'part2', 'part3']:
        part_files = load_data().get(data, {})
        if not part_files:
            await query.edit_message_text(f"⚠️ {data}da hozircha fayllar mavjud emas!")
            return
        
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f'file_{data}_{name}')] 
            for name in part_files.keys()
        ]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data='back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"{data} fayllari:", reply_markup=reply_markup)
    
    elif data == 'random':
        data_dict = load_data()
        results = []
        for part in ['part1', 'part2', 'part3']:
            files = data_dict.get(part, {})
            if files:
                name, file_id = random.choice(list(files.items()))
                results.append((part, name, file_id))
        
        if not results:
            await query.edit_message_text("⚠️ Hozircha fayllar mavjud emas!")
            return
        
        for part, name, file_id in results:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_id,
                caption=f"🎲 Random tanlov: {name} ({part})"
            )
    
    elif data.startswith('file_'):
        _, part, name = data.split('_', 2)
        file_id = load_data()[part].get(name)
        if file_id:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_id,
                caption=f"{name} ({part})"
            )
    
    elif data == 'back':
        await start(update, context)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Ro'yxatdan o'tish handleri
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AWAITING_CONTACT_OR_INFO: [
                MessageHandler(filters.CONTACT, receive_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_info)
            ],
            AWAITING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    # Admin handleri
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('add', add_question)],
        states={
            AWAITING_PART: [CallbackQueryHandler(receive_part, pattern="^part")],
            AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            AWAITING_FILE: [MessageHandler(filters.Document.ALL | filters.PHOTO, receive_file)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True,
        per_user=True,
    )

    application.add_handler(reg_conv)
    application.add_handler(admin_conv)
    application.add_handler(CallbackQueryHandler(handle_query))

    application.run_polling()

if __name__ == '__main__':
    main()