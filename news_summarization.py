import requests
from transformers import pipeline
from gtts import gTTS #used for text-to-speech
from bs4 import BeautifulSoup
import re

def search_url_space_news(URL):
    r = requests.get(URL)
    soup = BeautifulSoup(r.text, 'html.parser')
    atags = soup.find_all(['a'])
    hrefs = [link['href'] for link in atags]
    return hrefs

def clean_invalid_urls(urls, exclude_list):
    val = []
    for url in urls:
        if 'https://' in url and not any(exclude_word in url for exclude_word in exclude_list):
            res = re.findall(r'(https?://\S+)', url)[0].split('&')[0]
            val.append(res)
    return list(set(val))

def get_text_from_urls(urls):
    articles = []
    titles = []
    for url in urls:
        # Headers to accept web cookies
        headers = {'User-Agent': 'Mozilla/5.0'}
        cookies = {"CONSENT": "YES+cb.20210720-07-p0.en+FX+410"}
        r = requests.get(url, headers=headers, cookies=cookies)
        if r.status_code != 200:
            continue

        # Scrape headers and paragraphs through articles
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all(['p'])
        text = [paragraph.text for paragraph in paragraphs]
        article = ' '.join(text)
        article = article.rstrip()

        # Minimal number of symbols in article, prevent returning cookies or terms error
        if len(article) < 200:
            continue

        articles.append(article)
        url_h1_tags = soup.find_all(['h1'])
        url_titles = [title.text.strip() for title in url_h1_tags]
        titles.append(url_titles)

    return titles, articles

def add_eos_symbol(articles):
    sentences = []
    for i, article in enumerate(articles):
        article = article.replace('.', '.<eos>')
        article = article.replace('!', '!<eos>')
        article = article.replace('?', '?<eos>')
        sentences.append(article.split('<eos>'))
    
    return sentences

def split_texts_to_chunks(sentences):
    max_tokens_chunk = 500
    chunks = []

    for i, article_sentences in enumerate(sentences):
        chunks.append([])
        current_chunk = 0
        for sentence in article_sentences:
            if len(chunks[i]) == current_chunk + 1:
                if len(chunks[i][current_chunk]) + len(sentence.split(' ')) <= max_tokens_chunk:
                    chunks[i][current_chunk].extend(sentence.split(' '))
                else:
                    current_chunk += 1
                    chunks[i].append(sentence.split(' '))
            else:
                print(current_chunk)
                chunks[i].append(sentence.split(' '))
    return chunks

def summarize_all_chunks(chunks, summarizer):
    summarized_texts = []
    for article_chunks in chunks:
        article_text = []
        result = summarizer(article_chunks, max_length=120, min_length=30, do_sample=False)
        article_text = ' '.join([summ['summary_text'] for summ in result])
        summarized_texts.append(article_text)
    return summarized_texts

def merge_texts_into_space_report(summarized_texts):
    all_summarized_text = ""
    for summarized_text in summarized_texts:
        all_summarized_text += summarized_text
    return all_summarized_text

def make_mp3_text_to_speech(all_summarized_text, filename):
    tts = gTTS(text=all_summarized_text, lang='en')
    tts.save(filename)

def main():
    # Load summarization model from HuggingFace
    summarizer = pipeline("summarization")
    
    URL = f"https://www.google.com/search?q=space.com+latest+news&tbm=nws"
    
    hrefs = search_url_space_news(URL)
    
    # list of all invalid words in hrefs which should be removed 
    exclude_list = ['maps', 'policies', 'preferences', 'accounts', 'support']
    
    cleaned_urls = clean_invalid_urls(hrefs, exclude_list)
    
    titles, articles = get_text_from_urls(cleaned_urls)
    
    # Add <eos> for better result and splitting of the text
    sentences = add_eos_symbol(articles)
    
    # Split text to chunks for easier text manipulation
    chunks = split_texts_to_chunks(sentences)
    
    # Summarize all chunks and convert them into text
    summarized_texts = summarize_all_chunks(chunks, summarizer)
    
    # Merge all summarized texts into one space report
    all_summarized_texts = merge_texts_into_space_report(summarized_texts)
    
    # Text-to-speech for space report
    filename = "space_news_report.mp3"
    make_mp3_text_to_speech(filename)
      
    

if __name__ == "__main__":
    main()