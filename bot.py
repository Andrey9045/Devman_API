import telegram


bot = telegram.Bot(token='8474664474:AAH0TKeJUNvMqaabwycH1GlbL2pqf27tRpc')
updates = bot.get_updates()
print(updates[1])
bot.send_message(text='Hi Andrey!)', chat_id='1465804930')