#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram бот для проверки баланса API-ключей tkbk.io
"""

import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы API
API_BASE = "https://api.apiclaudecode.cloud"

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "8778052231:AAFYoWr4wayExTzQq-elaz0TPEyUww4AiV8")


def get_api_id(api_key: str) -> str | None:
    """Получает ID ключа по API-ключу"""
    try:
        response = requests.post(
            f"{API_BASE}/apiStats/api/get-key-id",
            json={"apiKey": api_key},
            timeout=10
        )
        data = response.json()
        if data.get("success"):
            return data["data"]["id"]
    except Exception as e:
        logger.error(f"Ошибка получения API ID: {e}")
    return None


def get_key_stats(api_id: str) -> dict | None:
    """Получает статистику ключа по его ID"""
    try:
        response = requests.post(
            f"{API_BASE}/apiStats/api/user-stats",
            json={"apiId": api_id},
            timeout=10
        )
        data = response.json()
        if data.get("success"):
            return data["data"]
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
    return None


def format_balance(stats: dict) -> str:
    """Форматирует статистику в читаемый вид"""
    name = stats.get("name", "—")
    is_active = stats.get("isActive", False)
    status = "✅ Активен" if is_active else "❌ Неактивен"
    
    limits = stats.get("limits", {})
    total_limit = limits.get("totalCostLimit", 0)
    current_total = limits.get("currentTotalCost", 0)
    remaining = total_limit - current_total if total_limit > 0 else 0
    
    usage = stats.get("usage", {}).get("total", {})
    total_cost = usage.get("formattedCost", "$0.00")
    requests_count = usage.get("requests", 0)
    tokens = usage.get("tokens", 0)
    
    daily_cost = limits.get("currentDailyCost", 0)
    
    permissions = stats.get("permissions", "[]")
    services = []
    if "claude" in permissions:
        services.append("Claude")
    if "gemini" in permissions:
        services.append("Gemini")
    if "openai" in permissions:
        services.append("OpenAI")
    services_text = ", ".join(services) if services else "Все"
    
    return f"""📊 <b>Статистика API-ключа</b>

<b>Название:</b> {name}
<b>Статус:</b> {status}

━━━━━━━━━━━━━━━
💰 <b>Баланс</b>
━━━━━━━━━━━━━━━
🟢 Общий лимит: ${total_limit:.2f}
🔵 Использовано: {total_cost}
🔴 Остаток: <b>${remaining:.2f}</b>

━━━━━━━━━━━━━━━
📈 <b>Использование</b>
━━━━━━━━━━━━━━━
💬 Запросов: {requests_count}
📊 Токенов: {tokens:,}
📅 За сегодня: ${daily_cost:.2f}

━━━━━━━━━━━━━━━
🔧 <b>Сервисы</b>
━━━━━━━━━━━━━━━
{services_text}
"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👋 Привет! Я бот для проверки баланса API-ключей tkbk.io\n\n"
        "📎 Просто отправь мне свой API-ключ (начинается с 'cr_') и я покажу статистику.",
        parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📖 <b>Как использовать:</b>\n\n"
        "1. Отправь мне свой API-ключ (начинается с 'cr_')\n"
        "2. Я покажу тебе статистику использования\n\n"
        "🔹 /start - Начать заново\n"
        "🔹 /help - Показать справку",
        parse_mode="HTML"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (API-ключей)"""
    api_key = update.message.text.strip()
    
    if not api_key.startswith("cr_"):
        await update.message.reply_text(
            "❌ Неверный формат ключа! API-ключ должен начинаться с 'cr_'",
            parse_mode="HTML"
        )
        return
    
    await update.message.reply_text("⏳ Проверяю баланс...")
    
    api_id = get_api_id(api_key)
    if not api_id:
        await update.message.reply_text(
            "❌ Ключ не найден или произошла ошибка!",
            parse_mode="HTML"
        )
        return
    
    stats = get_key_stats(api_id)
    if not stats:
        await update.message.reply_text(
            "❌ Не удалось получить статистику!",
            parse_mode="HTML"
        )
        return
    
    await update.message.reply_text(
        format_balance(stats),
        parse_mode="HTML"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")


def main():
    """Главная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("Необходимо указать токен бота в переменной BOT_TOKEN!")
        return
    
    logger.info("Бот запускается...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
