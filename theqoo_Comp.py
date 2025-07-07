import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import time
from datetime import datetime, timedelta, timezone
import os
import sys

# === 브랜드 & 감성 분석 ===
def detect_brand(title):
    brand_keywords = {
        '로라 메르시에': ['로라 메르시에', '로라메르시에', '로라'],
        '베어미네랄': ['베어미네랄', '베어 미네랄'],
        '아워 글래스': ['아워 글래스', '아워', '아워 글라스'],
        '나스': ['나스'],
        '맥': ['맥'],
        '바비 브라운': ['바비 브라운', '바비'],
        '메이크업 포에버': ['메이크업 포에버', '메포'],
        '베네피트': ['베네피트'],
        '아르마니': ['아르마니'],
        '지방시': ['지방시'],
        '샬롯 틸버리': ['샬롯 틸버리', '샬롯'],
        '샤넬': ['샤넬'],
        '디올': ['디올']
    }
    for brand, keywords in brand_keywords.items():
        if any(keyword in title for keyword in keywords):
            return brand
    return None

def detect_sentiment(title):
    positive_words = [
        '추천', '최고', '좋다', '만족', '예쁨', '대박', '존예', '꿀템', '인생템',
        '가성비', '갓성비', '짱좋다', '짱짱', '최애', '찐', '감동', '개이쁨',
        '예뻐', '넘좋다', '맘에듦', '강추', '완전좋음', '만족도최고', '신세계',
        '갓템', '대존예', '취저', '이쁨', '핵좋음', '완전예쁨', '역대급', '레전드',
        '인생아이템', '넘예', '인정템', '신박하다', '기대이상', '핵만족', '예쁨주의',
        '취향저격'
    ]
    negative_words = [
        '별로', '실망', '최악', '후회', '불만', '비추', '헐', '노답', '구림',
        '별로였음', '별로다', '망함', '최악임', '다신안삼', '돈아깝', '별점1',
        '후회됨', '진심별로', '실패', '별루', '비추천', '쓰레기', '헛돈',
        '돈버림', '구매후회', '완전별로', '진심실망', '비싸기만함'
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
                        '브랜드': brand,
                        '글번호': post_no,
                        '제목': title,
                        '링크': link,
                        '작성시간': time_str,
                        '조회수': views,
                        '댓글수': replies,
                        '감성': sentiment
                    })

        time.sleep(1)

    return pd.DataFrame(matching_posts)

# === 메일 본문 ===
def generate_email_body_html(df):
    if df.empty:
        return "<p>이번에 크롤링된 게시글이 없습니다.</p>"

    kst = timezone(timedelta(hours=9))
    today_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M 기준")

    brand_order = [
        '로라 메르시에', '베어미네랄', '아워 글래스',
        '나스', '맥', '바비 브라운', '메이크업 포에버',
        '베네피트', '아르마니', '지방시', '샬롯 틸버리',
        '샤넬', '디올'
    ]

    body = f"""
    <p>더쿠 게시글 크롤링 결과</p>
    <p><small>-. 크롤링 기준: 더쿠 뷰티 게시판 page 1~31, {today_str} (한국시간)</small></p>
    <p><small>-. 참고: 다수 브랜드 언급 시 한 브랜드 결과값에만 노출됩니다 (상위 표 기준으로 노출)</small></p>
    """

    for brand in brand_order:
        df_brand = df[df['브랜드'] == brand]
        if df_brand.empty:
            continue

        body += f"<h3>{brand}</h3>"
        body += """
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
        for row in df_brand.itertuples():
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
        body += "</table><br>"

    return body

# === 메일 발송 ===
def send_gmail_email(subject, html_body):
    sender = os.environ.get("GMAIL_SENDER")
    receivers = os.environ.get("GMAIL_RECEIVER")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not receivers or not app_password:
        print("❌ Gmail credentials are missing!")
        sys.exit(1)

    receiver_list = [email.strip() for email in receivers.split(",")]

    msg = MIMEText(html_body, 'html')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = "undisclosed-recipients:;"  # 숨김 참조처럼

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, receiver_list, msg.as_string())
        print("✅ 메일 발송 완료")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {e}")
        sys.exit(1)

# === 메인 ===
def main():
    df = crawl_theqoo()
    today_str = datetime.now().strftime("%Y%m%d")
    csv_file = f"theqoo_competitor_data_{today_str}.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"✅ CSV 저장 완료: {csv_file}")

    html_body = generate_email_body_html(df)
    send_gmail_email(f"[크롤링]더쿠 게시글 크롤링 결과 - {today_str}", html_body)

if __name__ == "__main__":
    main()
