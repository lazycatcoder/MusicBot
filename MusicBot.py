# This is a telegram bot that searches for music according to your request

import os
import re
import csv
import telebot
from telebot import types
from telebot.types import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telebot import apihelper
import threading
import requests
from bs4 import BeautifulSoup
import datetime
import time
import logging


# Global variable
music_list = []
music_list_show = []
music_chunks = []
current_chunk = 0

# # Logger
# logger = telebot.logger
# telebot.logger.setLevel(logging.DEBUG)

# Configuration
TOKEN = 'xxxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'  # Your token

# Set proxy (if you need to use a proxy enter the address and port)
# PROXY_HOST = 'https://0.0.0.0:8080'
# apihelper.proxy = {'https': PROXY_HOST}

# Init bot
bot = telebot.TeleBot(TOKEN)


# The first function is a handler for the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "\U0001F916 \nHello! \nI am a music bot, I will help you find your favorite songs. \n\n\U000026A1 Please enter the title of the song you want to search:")
    return

# Main function
@bot.message_handler(func=lambda message: True)
def search_music(message):
    global music_list, music_list_show, music_chunks, current_chunk

    search_query=""
    search_query = message.text.replace(' ', '+').lower()
    
    if len(search_query) < 4:
        bot.reply_to(message, "\U0001F614 Sorry, your request must be at least 4 characters long. Please enter the song name again.")
    else:
        # Define a regular expression pattern to match emojis
        emoji_pattern = re.compile("[\U0001F000-\U0001F9EF]")

        # Define a list of media file types
        media_file_types = [".jpg", ".jpeg", ".png", ".gif", ".mp3", ".mp4", ".avi", ".mpeg4", ".pdf"]
        
        # Check if the search query is emoji
        if emoji_pattern.match(search_query):
            bot.reply_to(message, "\U0001F614 Sorry, your request was entered incorrectly. Please try again.")

        # Check if the search query is a media file
        elif any(search_query.endswith(file_type) for file_type in media_file_types):
            bot.reply_to(message, "\U0001F614 Sorry, your request was entered incorrectly. Please try again.")

        else:
            # Write requests to csv file
            def write_to_csv(search_query):
                folder_name = 'requests'
                date_format = '%Y-%m-%d'
                current_date = datetime.datetime.now().strftime(date_format)
                year, month, day = current_date.split('-')

                folder_path = os.path.join(folder_name, year, month, day)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)

                file_name = f'music_bot_searches_{current_date}.csv'
                
                file_path = os.path.join(folder_path, file_name)

                query = search_query.replace('+', ' ')

                now = datetime.datetime.now()

                # Create a list containing the search query and the current date and time
                data = [query, now.strftime('%Y-%m-%d %H:%M:%S')]

                # Write the data to a CSV file named "music_bot_searches.csv"
                with open(file_path, 'a', encoding="cp1251", newline='') as file:  #encoding="utf-8"
                    writer = csv.writer(file, delimiter=",")
                    writer.writerow(data)
                    
            write_to_csv(search_query)

            url = f"https://drivemusic.club/?do=search&subaction=search&story={search_query}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
            }

            req = requests.get(url=url, headers=headers)
            src = req.text
            soup = BeautifulSoup(src, "lxml")

            search_results = soup.find_all('div', class_='music-popular-wrapper')

            num = 0
            music_list = []
            music_list_show = []

            # Extract music data from HTML
            for result in search_results:
                music_title_element = result.find('a', class_='popular-play-author')
                if music_title_element is not None:
                    music_title = music_title_element.text.strip()
                else:
                    continue

                music_artist_element = result.find('div', class_='popular-play-composition')
                if music_artist_element is not None:
                    music_artist = music_artist_element.text.strip()
                else:
                    continue

                music_duration_element = result.find('div', class_='popular-download-number')
                if music_duration_element is not None:
                    music_duration = music_duration_element.text.strip()
                else:
                    continue

                music_bitrate_element = result.find('div', class_='popular-download-date')
                if music_bitrate_element is not None:
                    music_bitrate = music_bitrate_element.text.strip()
                else:
                    continue

                music_url_element = result.find('a', class_='popular-play__item')
                if music_url_element is not None:
                    music_url = music_url_element['data-url']
                else:
                    continue

                num += 1

                # Music file size calculation
                minutes, seconds = map(int, music_duration.split(":"))
                music_length = minutes * 60 + seconds
                
                channels = 2
                bitrate = int(music_bitrate[:-4])
                length = int(music_length)

                file_size = (((bitrate * length * 1000 / 8) * channels) / 1024 / 1024) / 2
                file_size_rounded = round(file_size, 1)
                music_size = str(file_size_rounded) + " MB" 


                music_list.append({'num': num, 'song': music_title, 'artist': music_artist, 'duration': music_duration, 'bitrate': music_bitrate, 'url': music_url, 'size': music_size})
                music_list_show.append(str(num) + '. ' + music_artist + '-' + music_title + ' ' + music_duration + ' ' + music_bitrate + ' ' + music_size)

            if len(music_list_show) == 0:
                bot.reply_to(message, "\U0001F614 Sorry, no results found. Please try again.")
            else:
                music_chunks = [music_list[i:i+10] for i in range(0, len(music_list), 10)]
                current_chunk = 0
                music_list_show = ['\U0001F50D Search Results:\n'] + [str(music['num']) + '. ' + music['artist'] + ' - ' + music['song'] + ' ' + music['duration'] + ' ' + music['bitrate'] + ' ' + music['size'] for music in music_chunks[current_chunk]]

                # Helper function to get the inline keyboard with Next and Prev buttons
                def get_keyboard(current, total):
                    keyboard = types.InlineKeyboardMarkup()
                    row = []
                    if current > 0:
                        row.append(types.InlineKeyboardButton(text='Prev', callback_data='prev'))
                    if current < total - 1:
                        row.append(types.InlineKeyboardButton(text='Next', callback_data='next'))
                    keyboard.add(*row)
                    return keyboard
                  
                bot.send_message(chat_id=message.chat.id, text='\n'.join(music_list_show),
                                reply_markup=get_keyboard(current_chunk, len(music_chunks)))

                # Offer to select a song number
                choice = bot.send_message(message.chat.id, '\U000026A1 Enter the number of the song you want to play or enter the title of a new song you want to search:')

                @bot.callback_query_handler(func=lambda call: True)
                def callback_query(call):
                    global current_chunk, music_list_show          

                    # If the user clicked the 'next' button and there are more songs to display
                    if call.data == 'next':
                        if current_chunk < len(music_chunks) - 1:
                            # Increment the chunk index and update the music list
                            current_chunk += 1
                            music_list_show = ['\U0001F50D Search Results:\n'] + [str(music['num']) + '. ' + music['artist'] + ' - ' + music['song'] + ' ' + music['duration'] + ' ' + music['bitrate'] + ' ' + music['size'] for music in music_chunks[current_chunk]]
                        else:
                            # Inform the user that there are no more songs to display
                            bot.answer_callback_query(call.id, text="No more songs.")
                    # If the user clicked the 'prev' button and there are more songs to display
                    elif call.data == 'prev':
                        if current_chunk > 0:
                            # Decrement the chunk index and update the music list
                            current_chunk -= 1
                            music_list_show = ['\U0001F50D Search Results:\n'] + [str(music['num']) + '. ' + music['artist'] + ' - ' + music['song'] + ' ' + music['duration'] + ' ' + music['bitrate'] + ' ' + music['size'] for music in music_chunks[current_chunk]]
                        else:
                            bot.answer_callback_query(call.id, text="You're already at the beginning.")
                    else:
                        bot.answer_callback_query(call.id, text="\U0001F937 Unknown command.")

                    # Update the message containing the music list with the new information
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='\n'.join(music_list_show),
                                        reply_markup=get_keyboard(current_chunk, len(music_chunks)))

                @bot.message_handler(func=lambda message: True)
                def download_song(message):
                    while True:
                        try:
                            selected_song = int(message.text)

                            if 1 <= selected_song <= len(music_list):
                                download_url = music_list[selected_song - 1]['url']

                                # Start a new thread to download the song
                                download_thread = threading.Thread(target=download_and_send, args=(message.chat.id, download_url, threading.current_thread()))
                                download_thread.start()

                                # Prompt user to select another song or search for a new one
                                choice = bot.send_message(message.chat.id, 'Your song is downloading...\n\U0001F609I will send it to you soon.\n\n\U000026A1 Enter the number of another song to download, or enter the title of a new song you want to search:')
                                bot.register_next_step_handler(choice, download_song)
                                break 
                            else:
                                bot.reply_to(message, f"\U0001F614 Invalid selection. Please enter a number between 1 and {len(music_list)}:")
                                bot.register_next_step_handler(message, download_song)
                                return    
                        except ValueError:  
                            search_music(message)
                            return 

                def download_and_send(chat_id, download_url, download_thread):
                    # Download the song
                    req = requests.get(download_url)

                    # Save the song to disk
                    with open('song.mp3', 'wb') as f:
                        f.write(req.content)

                    # Send the song to the chat
                    with open('song.mp3', 'rb') as f:
                        bot.send_audio(chat_id, f)

                    # Delete the downloaded song file
                    os.remove('song.mp3')

                    # Wait for download thread to finish before closing it
                    download_thread.join()  

                    # Unregister the next step handler to prevent memory leaks
                    bot.unregister_next_step_handler(choice)

            bot.register_next_step_handler(choice, download_song)


if __name__ == '__main__':
    while True:
        try:
            # Start polling
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
            # Wait for 15 seconds before restarting the bot
            time.sleep(15)