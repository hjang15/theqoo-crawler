import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import time
from datetime import datetime
import os
import sys

# === 브랜드 & 감성 분석 ===
def detect_brand(title):
    if '로라메르시에' in title or '로라 메르시에' in title or '로라' in title:
        return '로라메르시에'
    elif '베어미네랄' in title or '베어 미네랄' in title:
        return '베어미네랄'
    else:
        return None

def detect_sentiment(title):
    positive_words = [
        '추천', '최고', '좋다', '만족', '예쁨',
        '대박', '존예', '꿀템', '인생템', '가성비',
        '갓성비', '짱좋다', '짱짱', '최애', '찐',
        '감동', '개이쁨', '예뻐', '넘좋다', '맘에듦',
        '강추', '완전좋음', '만족도최고', '신세계', '갓템',
        '대존예', '취저', '이쁨', '핵좋음', '완전예쁨',
        '역대급', '레전드', '인생아이템', '넘예', '인정템',
        '신박하다', '기대이상', '핵만족', '예쁨주의', '취향저격',
        '엄지척', '하트백만개', '질샌다', '너무좋음', '대박템',
        '가심비갑', '반함', '대존맛', '예쁨주의보', '소장각',
        '갓템인정', '핵예쁨'
    ]

    negative_words = [
        '별로', '실망', '최악', '후회', '불만',
        '비추', '헐', '노답', '구림', '별로였음',
        '별로다', '망함', '최악임', '다신안삼',
        '돈아깝', '별점1', '후회됨', '진심별로', '실패',
        '별루', '별로였어요', '비추천', '쓰레기', '별점깎음',
        '헛돈', '돈버림', '구매후회', '완전별로', '진심실망',
        '별1개', '다신안사', '실패작', '비싸기만함', '최악의선택',
        '돈값못함', '그저그럼', '평타이하', '아쉬움', '아깝다',
        '불호', '전혀추천안함'
    ]

    if any(word in title for word in positive_words):
        return '긍정'
    elif any(word in title for word in negative_words):
        return '부정'
    else:
        return '중립'

# === 크롤링 ===
def crawl_theqoo():
    urls = [f"https://theqoo.net/beauty?page={i}" for i in range(1, 31)]
    matching_posts = []

    for url in urls:
        res = requests.get(url)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr')

        for row in rows:
            no_tag = row.select_one('td.no')
            title_tag = row.select_one('.title a')
            time_tag = row.select_one('td.time')
            view_tag = row.select_one('td.m_no')
            reply_tag = row.select_one('a.replyNum')

            if no_tag and title_tag and time_tag and view_tag:
                post_no = no_tag.get_text(strip=True)
                title = title_tag.get_text(strip=True)
                link = 'https://theqoo.net' + title_tag.get('href')
                time_str = time_tag.get_text(strip=True)
                views = int(view_tag.get_text(strip=True).replace(',', '').strip())
                replies = int(reply_tag.get_text(strip=True)) if reply_tag else 0
                brand = detect_brand(title)

                if brand:
                    sentiment = detect_sentiment(title)
                    matching_posts.append({
                        '글번호': post_no,
                        '제목': title,
                        '링크': link,
                        '작성시간': time_str,
                        '조회수': views,
                        '댓글수': replies,
                        '감성': sentiment,
                        '브랜드': brand
                    })

        time.sleep(1)

    return pd.DataFrame(matching_posts)

# === HTML 메일 본문 ===
def generate_email_body_html(df):
    if df.empty:
        return "<p>이번에 크롤링된 게시글이 없습니다.</p>"

    body = """
    <p>더쿠 게시글 크롤링 결과</p>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
        <tr>
            <th>글번호</th>
            <th>제목</th>
            <th>댓글수</th>
            <th>조회수</th>
            <th>감성</th>
            <th>작성시간</th>
            <th>링크</th>
        </tr>
    """
    max_title_length = 50
    for row in df.itertuples():
        title_short = (row.제목[:max_title_length] + '...') if len(row.제목) > max_title_length else row.제목
        body += f"""
        <tr>
            <td>{row.글번호}</td>
            <td>{title_short}</td>
            <td>{row.댓글수}</td>
            <td>{row.조회수}</td>
            <td>{row.감성}</td>
            <td>{row.작성시간}</td>
            <td><a href="{row.링크}">바로가기</a></td>
        </tr>
        """
    body += "</table>"
    return body

# === Gmail 발송 ===
def send_gmail_email(subject, html_body):
    sender = os.environ.get("GMAIL_SENDER")
    receiver = os.environ.get("GMAIL_RECEIVER")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not receiver or not app_password:
        print("❌ Gmail credentials (GMAIL_SENDER, GMAIL_RECEIVER, GMAIL_APP_PASSWORD) are missing!")
        sys.exit(1)

    msg = MIMEText(html_body, 'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, app_password)
            server.send_message(msg)
        print("✅ 메일 발송 완료")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {e}")
        sys.exit(1)

# === 메인 ===
def main():
    df = crawl_theqoo()
    today_str = datetime.now().strftime("%Y%m%d")
    csv_file = f"theqoo_brand_data_{today_str}.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"✅ CSV 저장 완료: {csv_file}")

    html_body = generate_email_body_html(df)
    send_gmail_email(f"더쿠 게시글 크롤링 결과 - {today_str}", html_body)

if __name__ == "__main__":
    main()
