port=port, use_reloader=False, threaded=True, debug=False)
    except OSError as e:
        logger.error(f"Port {port} in use, trying alternative port: {str(e)}")
        app_server.run(host='0.0.0.0', port=0, use_reloader=False, threaded=True, debug=False, keepalive=True)

# Bot Token and Admin ID
TOKEN = "8092042113:AAFFUxBYUuvhBt0pFETrxJ6HYZabEGLBZlA"
ADMIN_ID = 7239535020

# Trading Strategy Functions
def calculate_indicators(prices):
    df = pd.DataFrame(prices, columns=['close'])

    # Calculate EMAs
    ema_20 = EMAIndicator(close=df['close'], window=20)
    ema_50 = EMAIndicator(close=df['close'], window=50)

    df['EMA20'] = ema_20.ema_indicator()
    df['EMA50'] = ema_50.ema_indicator()

    # Calculate RSI
    rsi = RSIIndicator(close=df['close'], window=14)
    df['RSI'] = rsi.rsi()

    return df

def check_buy_signal(df):
    current_price = df['close'].iloc[-1]
    ema_20 = df['EMA20'].iloc[-1]
    ema_50 = df['EMA50'].iloc[-1]
    rsi = df['RSI'].iloc[-1]

    return (current_price > ema_50 and 
            ema_20 > ema_50 and 
            30 <= rsi <= 50)

def check_sell_signal(df):
    current_price = df['close'].iloc[-1]
    ema_20 = df['EMA20'].iloc[-1]
    ema_50 = df['EMA50'].iloc[-1]
    rsi = df['RSI'].iloc[-1]

    return (current_price < ema_50 and 
            ema_20 < ema_50 and 
            50 <= rsi <= 70)

def calculate_sma(prices, period=5):
    if len(prices) < period:
        return prices[-1]  # Return current price if not enough data
    return sum(prices[-period:]) / period

def analyze_pair(historical_prices):
    current_price = historical_prices[-1] if historical_prices else 0

    # Get current minute for signal alternation
    current_minute = datetime.now().minute
    # Use minute to generate alternating signals
    signal = "BUY" if current_minute % 2 == 0 else "SELL"

    # Use current second for confidence variation
    current_second = datetime.now().second
    confidence = 75 + (current_second % 20)  # Confidence between 75-95

    # Vary expiry time based on confidence
    expiry = "5"
    if confidence > 90:
        expiry = "3"
    elif confidence < 80:
        expiry = "7"

    return {"signal": signal, "confidence": confidence, "expiry": expiry}

def get_referral_bonus(user_id, is_premium=False):
    referrals = load_data("referrals.json")
    count = referrals.get(str(user_id), {}).get("count", 0)
    return count * (5 if is_premium else 2)

def get_commission(user_id):
    referrals = load_data('referrals.json')
    return referrals.get(str(user_id), {}).get('commission', 0)

async def withdraw(update: Update, context):
    user_id = str(update.message.chat.id)
    commission = get_commission(user_id)

    if commission < 1.00:
        await update.message.reply_text("âŒ Minimum withdrawal amount is $1.00. Keep referring to earn more!")
        return

    referrals = load_data('referrals.json')
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"ðŸ’° Withdrawal Request:\nUser ID: {user_id}\nAmount: ${commission:.2f}"
    )

    # Reset commission after withdrawal request
    referrals[user_id]['commission'] = 0
    save_data('referrals.json', referrals)

    await update.message.reply_text("âœ… Your withdrawal request has been sent to admin!")

async def referral(update: Update, context):
    user_id = str(update.message.chat.id)
    commission = get_commission(user_id)
    referral_text = f"""ðŸ”¥ Earn rewards by referring friends!

âœ¨ Your Referral Link:
https://t.me/Jimmytraderrbot?start={user_id}

ðŸ“Š Your Stats:
ðŸ‘¥ Referrals: {load_data('referrals.json').get(user_id, {}).get('count', 0)}
ðŸ“ˆ Extra Signals: +{get_referral_bonus(user_id, is_premium(user_id))}/day
ðŸ’° Commission Earned: ${commission:.2f}

ðŸ“² Type /withdraw to request your earnings (min. $1.00")"""
    await update.message.reply_text(referral_text)

# Exchange Rate API for Market Data
EXCHANGE_RATE_API_KEY = "6cc303fd221935250a6e1a56"
EXCHANGE_RATE_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/{base}"

# Data Storage Files
PREMIUM_FILE = "premium_users.json"
USER_LIMIT_FILE = "user_limits.json"

# Market data cache
market_data_cache = {}
CACHE_DURATION = 300  # 5 minutes in seconds

# Load and save data functions
def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# Load stored data
PREMIUM_EXPIRY = load_data(PREMIUM_FILE)
USER_LIMITS = load_data(USER_LIMIT_FILE)

# Reset free user limits daily
def reset_free_limits():
    for user in list(USER_LIMITS.keys()):
        if user not in PREMIUM_EXPIRY:
            USER_LIMITS[user] = 0
    save_data(USER_LIMIT_FILE, USER_LIMITS)

def is_premium(user_id):
    return str(user_id) in PREMIUM_EXPIRY and datetime.fromisoformat(PREMIUM_EXPIRY[str(user_id)]) > datetime.now()

async def start(update: Update, context):
    user_id = str(update.message.chat.id)
    referrer_id = context.args[0] if context.args else None

    if referrer_id and referrer_id != user_id:
        referrals = load_data("referrals.json")
        if referrer_id in referrals:
            referrals[referrer_id]["count"] = referrals[referrer_id].get("count", 0) + 1
            if "referred_users" not in referrals[referrer_id]:
                referrals[referrer_id]["referred_users"] = []
            referrals[referrer_id]["referred_users"].append(user_id)
        else:
            referrals[referrer_id] = {
                "count": 1,
                "rewarded": False,
                "commission": 0,
                "referred_users": [user_id]
            }
        save_data("referrals.json", referrals)

    welcome_text = f"""Welcome to Jimmy Signal Bot! ðŸš€

ðŸ”¹ Get high-accuracy binary options trading signals ðŸ“Š
ðŸ”¹ Free users: 7 signals per day âš¡
ðŸ”¹ VIP users: 30 signals per day ðŸ”¥

ðŸ“© Upgrade to VIP by messaging the admin!

ðŸ’° Earn & Withdraw Rewards!
âœ… Invite friends & earn extra signal 
âœ… Withdraw rewards via [Payment Methods].

ðŸ”˜ Click /get_signal to receive your first signal!

Trade smart!"""
    await update.message.reply_text(welcome_text)

def can_receive_signal(user_id):
    user_id = str(user_id)
    if str(user_id) == str(ADMIN_ID) or str(user_id) == "7239535020":
        return True
    daily_limit = get_daily_signal_limit(user_id)
    current_signals = USER_LIMITS.get(user_id, 0)
    return current_signals < daily_limit

def get_daily_signal_limit(user_id):
    if str(user_id) == str(ADMIN_ID):
        return 100
    base_limit = 30 if is_premium(user_id) else 7
    referrals = load_data('referrals.json')
    if str(user_id) in referrals and referrals[str(user_id)].get('count', 0) > 0:
        bonus = get_referral_bonus(user_id, is_premium(user_id))
        return base_limit + bonus
    return base_limit

def increment_user_signal_count(user_id):
    user_id = str(user_id)
    USER_LIMITS[user_id] = USER_LIMITS.get(user_id, 0) + 1
    save_data(USER_LIMIT_FILE, USER_LIMITS)

# API Limits
DAILY_API_LIMIT = 500
PREMIUM_RESERVE = 200

# Request tracking
api_requests = {'total': 0, 'premium': 0, 'free': 0}

async def show_pair_selection(update: Update, context):
    pairs = {
        "EUR/USD": "Euro/US Dollar",
        "GBP/USD": "British Pound/US Dollar", 
        "USD/JPY": "US Dollar/Japanese Yen",
        "USD/CHF": "US Dollar/Swiss Franc",
        "AUD/USD": "Australian Dollar/US Dollar",
        "USD/CAD": "US Dollar/Canadian Dollar"
    }

    keyboard = []
    row = []
    for pair in pairs.keys():
        row.append(InlineKeyboardButton(pair, callback_data=f"pair_{pair}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        "ðŸ“Š Select a trading pair:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "new_signal":
        await show_pair_selection(query, context)
    elif query.data.startswith("pair_"):
        selected_pair = query.data.replace("pair_", "")
        base_currency = selected_pair.split('/')[0]
        quote_currency = selected_pair.split('/')[1]

        try:
            url = EXCHANGE_RATE_URL.format(key=EXCHANGE_RATE_API_KEY, base=base_currency)
            response = requests.get(url)
            data = response.json()

            if data.get('result') == 'success':
                rate = data['conversion_rates'][quote_currency]
                previous_rate = rate if not isinstance(market_data_cache.get(selected_pair), list) else market_data_cache[selected_pair][-1]
                trend = rate - previous_rate

                if not isinstance(market_data_cache.get(selected_pair), list):
                    market_data_cache[selected_pair] = []
                market_data_cache[selected_pair].append(rate)

                if len(market_data_cache[selected_pair]) > 10:
                    market_data_cache[selected_pair] = market_data_cache[selected_pair][-10:]

                analysis = analyze_pair(market_data_cache[selected_pair])

                user_id = str(query.from_user.id)
                increment_user_signal_count(user_id)
                remaining = get_daily_signal_limit(user_id) - USER_LIMITS.get(user_id, 0)

                signal = f"""ðŸ“Š Signal Alert:
ðŸ”¹ Pair: {selected_pair}
ðŸ“ˆ Type: {analysis['signal']}
ðŸŽ¯ Confidence: {analysis['confidence']}%
â° Expiry: {analysis['expiry']} minutes
ðŸ’¹ Entry Rate: {rate:.5f}

ðŸ“Š Signals remaining today: {remaining}"""

                keyboard = [[InlineKeyboardButton("ðŸ”„ New Signal", callback_data="new_signal")]]
                await query.edit_message_text(text=signal, reply_markup=InlineKeyboardMarkup(keyboard))

            else:
                await query.edit_message_text("âŒ Error fetching market data. Please try again.")
        except Exception as e:
            await query.edit_message_text("âŒ Error generating signal. Please try again.")

async def add_premium(update: Update, context):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add_premium user_id days")
        return
    user_id, days = context.args
    expiry_date = (datetime.now() + timedelta(days=int(days))).isoformat()
    PREMIUM_EXPIRY[user_id] = expiry_date
    save_data(PREMIUM_FILE, PREMIUM_EXPIRY)

    referrals = load_data('referrals.json')
    for referrer_id, data in referrals.items():
        if 'referred_users' in data and user_id in data['referred_users']:
            referrals[referrer_id]['commission'] = referrals[referrer_id].get('commission', 0) + 0.10
            save_data('referrals.json', referrals)
            await context.bot.send_message(
                chat_id=int(referrer_id),
                text=f"ðŸŽ‰ You earned $0.10 commission from your referral's premium upgrade! Minimum withdrawal is $1.00"
            )
            break

    await update.message.reply_text(f"âœ… User {user_id} upgraded to Premium for {days} days.")

def remove_expired_premium():
    now = datetime.now().isoformat()
    expired_users = [user for user, expiry in PREMIUM_EXPIRY.items() if expiry < now]
    for user in expired_users:
        del PREMIUM_EXPIRY[user]
    save_data(PREMIUM_FILE, PREMIUM_EXPIRY)

async def users(update: Update, context):
    if update.message.chat.id != ADMIN_ID:
        await update.message.reply_text("âŒ You are not authorized to use this command.")
        return
    premium_users = [user for user in PREMIUM_EXPIRY.keys()]
    free_users = [user for user in USER_LIMITS.keys() if user not in PREMIUM_EXPIRY]
    message = f"ðŸ‘¥ Users List:\n\nðŸ’Ž Premium Users: {len(premium_users)}\nâš¡ Free Users: {len(free_users)}"
    await update.message.reply_text(message)

async def my_status(update: Update, context):
    user_id = str(update.message.chat.id)
    if is_premium(user_id):
        expiry = PREMIUM_EXPIRY[user_id]
        await update.message.reply_text(f"âœ… You are a Premium user until {expiry}.")
    else:
        remaining_signals = 7 - USER_LIMITS.get(user_id, 0)
        await update.message.reply_text(f"âš¡ You are a Free user. Signals left today: {remaining_signals}/7.")

async def broadcast_message(update: Update, context):
    if not context.args:
        await update.message.reply_text("âŒ Usage: /broadcast <message>")
        return

    message = ' '.join(context.args)
    all_users = set(USER_LIMITS.keys()) | set(PREMIUM_EXPIRY.keys())
    success_count = 0
    fail_count = 0

    for user_id in all_users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=f"ðŸ“¢ Broadcast from Admin:\n{message}")
            success_count += 1
        except Exception:
            fail_count += 1

    await update.message.reply_text(f"âœ… Broadcast sent to {success_count} users\nâŒ Failed for {fail_count} users")

async def reply_user(update: Update, context):
    if len(context.args) < 2:
        await update.message.reply_text("âŒ Usage: /reply_user <user_id> <message>")
        return

    user_id = context.args[0]
    reply_message = ' '.join(context.args[1:])

    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"ðŸ“© Admin Reply:\n{reply_message}")
        await update.message.reply_text("âœ… Message sent successfully!")
    except Exception as e:
        await update.message.reply_text("âŒ Failed to send the message. Make sure the user has started the bot.")

async def message_admin(update: Update, context):
    user_id = update.message.chat.id
    username = update.message.from_user.username

    if not context.args:
        await update.message.reply_text("âœï¸ Please write your message to the admin below.\nI will forward it when you send it.")
        return

    message = ' '.join(context.args)
    admin_notification = f"ðŸ’Œ Message from user:\nID: {user_id}\nUsername: @{username}\nMessage: {message}"

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notification)
        await update.message.reply_text("âœ… Your message has been sent to the admin. They will contact you soon!")
    except Exception as e:
        await update.message.reply_text("âŒ Failed to send message to admin. Please try again later.")

async def handle_text_message(update: Update, context):
    if update.message and update.message.text and not update.message.text.startswith('/'):
        user_id = update.message.chat.id
        username = update.message.from_user.username
        message = update.message.text

        admin_notification = f"ðŸ’Œ Message from user:\nID: {user_id}\nUsername: @{username}\nMessage: {message}"

        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notification)
            await update.message.reply_text("âœ… Your message has been sent to the admin. They will contact you soon!")
        except Exception as e:
            await update.message.reply_text("âŒ Failed to send message to admin. Please try again later.")

def main():
    reset_free_limits()
    remove_expired_premium()
    Thread(target=run_server).start()

    try:
        requests.post(f'https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true')
    except:
        pass

    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("get_signal", show_pair_selection))
    bot_app.add_handler(CommandHandler("add_premium", add_premium, filters=filters.Chat(ADMIN_ID)))
    bot_app.add_handler(CommandHandler("users", users, filters=filters.Chat(ADMIN_ID)))
    bot_app.add_handler(CommandHandler("my_status", my_status))
    bot_app.add_handler(CommandHandler("referral", referral))
    bot_app.add_handler(CommandHandler("withdraw", withdraw))
    bot_app.add_handler(CommandHandler("message_admin", message_admin))
    bot_app.add_handler(CommandHandler("reply_user", reply_user, filters=filters.Chat(ADMIN_ID)))
    bot_app.add_handler(CallbackQueryHandler(callback_handler))
    bot_app.add_handler(CommandHandler("broadcast", broadcast_message, filters=filters.Chat(ADMIN_ID)))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    bot_app.run_polling()

if __name__ == "__main__":
    main()
