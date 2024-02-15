from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
#import asyncio


# Define your Telegram bot token here
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'



# Define your Telegram bot token here


# Dictionary to store user states
user_state = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Welcome to Anime Bot. Enter the name of an anime or manga to get a synopsis about it.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Enter the name of an anime or manga to get a synopsis about it.If Timeout occurs enter the value again')

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('This is a custom command')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message_text = update.message.text
    print("User Input:", message_text)

    # Check if the user input is a string (anime/manga name)
    if not message_text.isdigit():
        # Clear previous state
        user_state[user_id] = {"search_query": message_text, "anime_links": [], "manga_links": []}

        # Fetch the HTML content of the webpage
        url = f'https://myanimelist.net/search/all?q={message_text}&cat=all'
        response = requests.get(url)
        html_content = response.text

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all article elements
        article_elements = soup.find_all('article')

        # Define lists to store anime and manga links
        anime_links = []
        manga_links = []

        # Iterate over the first two article elements
        for i, article_element in enumerate(article_elements[:2]):
            # Find all anchor tags with class 'hoverinfo_trigger fw-b fl-l' inside the article
            if i == 0:
                # For the first article, collect anime links
                anime_links_elements = article_element.select('a.hoverinfo_trigger.fw-b.fl-l')
                anime_links.extend([{'href': a_element.get('href', ''), 'name': a_element.get_text().strip()} for a_element in anime_links_elements])
            elif i == 1:
                # For the second article, collect manga links
                manga_links_elements = article_element.select('a.hoverinfo_trigger.fw-b')
                manga_links.extend([{'href': a_element.get('href', ''), 'name': a_element.get_text().strip()} for a_element in manga_links_elements])
        
        user_state[user_id]["anime_links"] = anime_links
        user_state[user_id]["manga_links"] = manga_links


        # Output the extracted anime and manga links with numbers
        anime_links_text = "\n".join([f"{i+1}. {link['name']}" for i, link in enumerate(anime_links)])
        manga_links_text = "\n".join([f"{i+1+len(anime_links)}. {link['name']}" for i, link in enumerate(manga_links)])

        await update.message.reply_text("Anime Links:\n" + anime_links_text + "\n\nManga Links:\n" + manga_links_text)
        await update.message.reply_text("Enter the number of the link to view its synopsis: ")

    # Check if the user input is a digit (selected link number)
    elif user_state[user_id].get("anime_links") or user_state[user_id].get("manga_links"):
        user_data = user_state[user_id]
        try:
            selected_input = int(message_text)
            selected_link_index = selected_input - 1

            # Check if the selected link index is within the range of available links
            if 0 <= selected_link_index < len(user_data["anime_links"]) + len(user_data["manga_links"]):
                selected_link = user_data["anime_links"][selected_link_index] if selected_link_index < len(user_data["anime_links"]) else user_data["manga_links"][selected_link_index - len(user_data["anime_links"])]
                
                check_val = len(user_data["anime_links"])
                if selected_input < check_val:
                    link_nature = 'anime'
                else:
                    link_nature = 'manga'

                print(link_nature)
                # Run Playwright code
                image_url, synopsis_text = await get_image_and_synopsis(selected_link['href'])

                #await update.message.reply_text(synopsis_text)
                #await update.message.reply_text("Image URL: " + image_url)
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
                await update.message.reply_text(synopsis_text)


            else:
                await update.message.reply_text("Invalid number. Please enter a valid number.")
        except ValueError:
            await update.message.reply_text("Invalid input. Please enter a valid number.")
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {str(e)}")

    else:
        await update.message.reply_text("Enter Anime or Manga name first.")





async def get_image_and_synopsis(link):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Open a new page
        page = await context.new_page()

        # Navigate to the selected link
        await page.goto(link)

        try:
            # Find the lazy-loaded image element
            first_lazy_loaded_image = await page.wait_for_selector('img.lazyloaded')
            # Get the source (src) attribute of the image
            image_url = await first_lazy_loaded_image.get_attribute('src')
            print('Image URL:', image_url)
        except Exception as e:
            print('No image with class "lazyloaded" found.')
            image_url = "Image not found."

        
        synopsis_element = await page.query_selector('p[itemprop="description"]')

        if synopsis_element:
                # If <p> tag exists, retrieve synopsis from it
            synopsis_text = await synopsis_element.text_content()
        else:
                    # If <p> tag doesn't exist, search for <span> tag
            synopsis_element = await page.query_selector('span[itemprop="description"]')
            if synopsis_element:
                 # If <span> tag exists, retrieve synopsis from it
                synopsis_text = await synopsis_element.text_content()
            else:
                    # If neither <p> nor <span> tags exist, set synopsis_text to a default message
                 synopsis_text = "Synopsis not found."

        # Close the browser
        await context.close()
        await browser.close()

        return image_url, synopsis_text

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    print('Starting Bot....')
   


    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Polls the bot
    print('Polling....')
    app.run_polling()
