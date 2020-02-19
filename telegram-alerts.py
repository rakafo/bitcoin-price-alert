#!/usr/local/venv/bin/python3

import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import json
import re
import time
import os

# global vars so that job_check_position() can alert only when price initially moved in the needed direction, not back and forth
profit_step = 35
loss_step = 35
profit_target = 70
UPDATE_INTERVAL = 60

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_price():
    """query bitmex api for price"""
    try:
        r = requests.get('https://www.bitmex.com/api/v1/trade?symbol=XBT&count=1&reverse=true')
        response = json.loads(r.text)[0]
        # check if correct response received. If not, due to i.e. overload try later, in a blocking fashion.
        if type(response['price']) == int or type(response['price']) == float:
            return response['price']
        else:
            logger.warning(f'Received bad data from bitmex: {response}')
            time.sleep(10)
            get_current_price()
    except Exception as e:
        print(e)


def job_check_price(context):
    """get alert when price reaches the target"""
    chat_id = context.job.context.message.chat_id
    msg = context.job.context.message.text
    side = msg.split()[1]
    target_price = int(msg.split()[2])
    curr_price = get_current_price()
    fulfilled = False
    if side == 'long':
        fulfilled = True if curr_price >= target_price else False
    elif side == 'short':
        fulfilled = True if curr_price <= target_price else False
    if fulfilled:
        context.bot.send_message(chat_id, text=f'Want price reached:\n'
                                               f'\t- side: {side}\n'
                                               f'\t- target price: {target_price}\n'
                                               f'\t- current price: {curr_price}')
        context.job.schedule_removal()


def job_check_position(context):
    """get alert when price reaches the target"""
    chat_id = context.job.context.message.chat_id
    msg = context.job.context.message.text
    side = msg.split()[1]
    bought_price = int(msg.split()[2])
    sl_price = int(msg.split()[4])
    curr_price = get_current_price()
    global profit_step, loss_step
    if side == 'long':
        if curr_price >= bought_price + profit_step:
            profit_step += 35 # alert on every 35 step change
            context.bot.send_message(chat_id, text=f'New profit height: '
                                                   f'\n\t- buy price: {bought_price}'
                                                   f'\n\t- current price: {curr_price}'
                                                   f'\n\t- difference: {curr_price - bought_price}'
                                                   f'\n\t- will next alert above price: {bought_price + profit_step}')
        if curr_price <= bought_price - loss_step:
            loss_step += 35 # alert on every 35 step change
            context.bot.send_message(chat_id, text=f'New loss height: '
                                                   f'\n\t- buy price: {bought_price}'
                                                   f'\n\t- current price: {curr_price}'
                                                   f'\n\t- difference: {curr_price - bought_price}'
                                                   f'\n\t- will next alert below price: {bought_price - loss_step}')
        if sl_price >= curr_price:
            context.bot.send_message(chat_id, text=f'Stop-loss level reached: '
                                                   f'\n\t- buy price: {bought_price}'
                                                   f'\n\t- current price: {curr_price}'
                                                   f'\n\t- difference: {curr_price - bought_price}')
            context.job.schedule_removal()

    elif side == 'short':
        if curr_price <= bought_price - profit_step:
            profit_step += 35 # alert on every 35 step change
            context.bot.send_message(chat_id, text=f'New profit height: '
                                                   f'\n\t- buy price: {bought_price}'
                                                   f'\n\t- current price: {curr_price}'
                                                   f'\n\t- difference: {bought_price - curr_price}'
                                                   f'\n\t- will next alert above price: {bought_price - profit_step}')
        if curr_price >= bought_price + loss_step:
            loss_step += 35 # alert on every 35 step change
            context.bot.send_message(chat_id, text=f'New loss height: '
                                                   f'\n\t- buy price: {bought_price}'
                                                   f'\n\t- current price: {curr_price}'
                                                   f'\n\t- difference: {bought_price - curr_price}'
                                                   f'\n\t- will next alert above price: {bought_price + loss_step}')
        if sl_price <= curr_price:
            context.bot.send_message(chat_id, text=f'Stop-loss level reached: '
                                                   f'\n\t- buy price: {bought_price}'
                                                   f'\n\t- current price: {curr_price}'
                                                   f'\n\t- difference: {bought_price - curr_price}')
            context.job.schedule_removal()


def want(update, context):
    """set long|short price alert"""
    if not bool(re.search('^/want (long|short) [0-9]*$', update.message.text)):
        update.message.reply_text('Usage: /want (long|short) <price:int>')
        return
    logger.info(f'New command: {update.message.text}')
    single_reply = []
    job_name = update.message.text
    # check and remove if any old job for same want exists
    for i in context.job_queue.jobs():
        if bool(re.search(job_name.split()[1], i.name)):
            i.schedule_removal()
            single_reply.append(f'Removed old alert: {i.name}')

    context.job_queue.run_repeating(job_check_price, UPDATE_INTERVAL, name=job_name, context=update)
    single_reply.append(f'Created new alert: {job_name}')
    update.message.reply_text('\n'.join(single_reply))


def position(update, context):
    """alert on current position changes"""
    if not bool(re.search('^/position (long|short) [0-9]* sl [0-9]*$', update.message.text)):
        update.message.reply_text('Usage: /position (long|short) <price:int> sl <stop loss price:int>')
        return
    logger.info(f'New command: {update.message.text}')
    single_reply = []
    job_name = update.message.text
    # check and remove if any old job exists
    for i in context.job_queue.jobs():
        if bool(re.search(job_name.split()[0], i.name)):
            i.schedule_removal()
            single_reply.append(f'Removed old alert: {i.name}')
            #  reset global values for new alert
            global profit_step, loss_step
            profit_step = 35
            loss_step = 35

    context.job_queue.run_repeating(job_check_position, UPDATE_INTERVAL, name=job_name, context=update)
    single_reply.append(f'Created new alert: {job_name}')
    update.message.reply_text('\n'.join(single_reply))


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning(f'Update {update} caused error {context.error}')


def end(update, context):
    """end want|position jobs"""
    if not bool(re.search('^/end (want|position)$', update.message.text)):
        update.message.reply_text('Usage: /end (want|position)')
        return
    logger.info(f'New command: {update.message.text}')
    end_what = update.message.text.split()[1]
    found_job = False
    single_reply = []
    for i in context.job_queue.jobs():
        if bool(re.search(end_what, i.name)):
            found_job = True
            i.schedule_removal()
            single_reply.append(f'\t- {i.name}')
    if found_job:
        single_reply.insert(0, f'Ending {end_what} jobs:')
        single_reply = '\n'.join(single_reply)
        update.message.reply_text(single_reply)
    else:
        update.message.reply_text(f'No {end_what} jobs found')


def jobs(update, context):
    """prints all active jobs
    scheduled jobs are removed next time they're run, so will stay in list for 1 UPDATE_INTERVAL"""
    logger.info(f'New command: {update.message.text}')
    single_reply = []
    for i in context.job_queue.jobs():
        single_reply.append(f'\t- {i.name}')
    if single_reply:
        single_reply.insert(0, 'All jobs:')
    else:
        single_reply.append('No jobs active')

    update.message.reply_text('\n'.join(single_reply))


def unknown(update, context):
    update.message.reply_text("Available commands:\n"
                              "\t /want {long|short} <price:int> - get alerts when price reaches require price-point\n"
                              "\t /position (long|short) <price:int> sl <stop loss price:int> - get periodic alerts regarding your position\n"
                              "\t /jobs - list all jobs\n"
                              "\t /end {want|position} - end jobs in your selected category")


def main():
    #  fetch telegram messages
    cred_file = json.loads(open('credentials', 'r').read())
    updater = Updater(cred_file['token'], use_context=True)

    #  pass telegram messages to handlers
    dp = updater.dispatcher

    # add handlers to dispatch pool
    dp.add_handler(CommandHandler("want", want, pass_job_queue=True))
    dp.add_handler(CommandHandler("end", end, pass_job_queue=True))
    dp.add_handler(CommandHandler("jobs", jobs, pass_job_queue=True))
    dp.add_handler(CommandHandler("position", position, pass_job_queue=True))
    dp.add_handler(MessageHandler(Filters.regex("/.*"), unknown))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()


if __name__ == '__main__':
    main()