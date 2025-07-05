import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def crawl_naver_blog():
    url = "https://search.naver.com/search.naver?ssc=tab.blog.all&query=로라%20메르시에&sm=tab_opt&nso=so%3Add%2Cp%3A1d"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    posts = []

    for item in soup.select('.api_subject_bx'):
        title_tag = item.select_one('.api_txt_lines.total_tit')
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag['href']
            date = item.select_one('.sub_time')
            date_str = date.get_text(strip=True) if date else ''
            posts.append({'구분': '블로그', '제목': title, '링크': link, '날짜': date_str})

    return posts

def crawl_naver_cafe():
    url = "https://search.naver.com/search.naver?cafe_where=articleg&date_option=2&nso_open=1&prdtype=0&query=로라+메르시에&sm=mtb_opt&ssc=tab.cafe.all&st=date&stnm=date&opt_tab=0&nso=so%3Add%2Cp%3A1d"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    posts = []

    for item in soup.select('.api_subject_bx'):
        title_tag = item.select_one('.api_txt_lines.total_tit')
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag['href']
            date = item.select_one('.sub_time')
            date_str = date.get_text(strip=True) if date else ''
            posts.append({'구분': '카페', '제목': title, '링크': link, '날짜': date_str})

    return posts

def generate_email_body(df):
    if df.empty:
        return "<p>오늘 수집된 데이터가 없습니다.</p>"
    
    body = """
    <p>📝 오늘 네이버 블로그 & 카페 게시글</p>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; width:100%;">
        <tr><th>구분</th><th>제목</th><th>날짜</th><th>링크</th></tr>
    """
    for row in df.itertuples():
        title_short = (row.제목[:50] + '...') if len(row.제목) > 50 else row.제목
        body += f"""
        <tr>
            <td>{row.구분}</td>
            <td>{title_short}</td>
            <td>{row.날짜}</td>
            <td><a href="{row.링크}">바로가기</a></td>
        </tr>
        """
    body += "</table>"
    return body

def send_gmail(subject, html_body):
    sender = os.environ.get("GMAIL_SENDER")
    receiver = os.environ.get("GMAIL_RECEIVER")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    msg = MIMEText(html_body, 'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, app_password)
        server.send_message(msg)

    print("✅ 메일 발송 완료")

def main():
    blog_posts = crawl_naver_blog()
    time.sleep(1)
    cafe_posts = crawl_naver_cafe()

    all_posts = blog_posts + cafe_posts
    df = pd.DataFrame(all_posts)
    today = datetime.now().strftime('%Y%m%d')
    df.to_csv(f'naver_posts_{today}.csv', index=False, encoding='utf-8-sig')

    html_body = generate_email_body(df)
    send_gmail(f"네이버 블로그/카페 크롤링 결과 - {today}", html_body)

if __name__ == "__main__":
    main()
