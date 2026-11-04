import os
import datetime
import re
import random
import feedparser
import requests
from openai import OpenAI

RSS_FEEDS = {
    '공정기술': 'https://news.google.com/rss/search?q=반도체+공정+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '소재화학': 'https://news.google.com/rss/search?q=반도체+소재+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '노광식각': 'https://news.google.com/rss/search?q=EUV+OR+식각+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 썸네일(헤더)용 이미지만 남김
HEADER_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&h=675&q=80"
]

def collect_news():
    articles = []
    print("[1/3] 뉴스 수집 중...")
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:6]: 
                articles.append(f"[{source}] {getattr(entry, 'title', '')}")
        except:
            pass
    return articles

def generate_blog_content(articles):
    print("[2/3] 다이어그램 및 시각화 포함 롱폼 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 누락")
        
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles[:20])
    
    system_prompt = """
    당신은 화학공학 전공 반도체 공정 엔지니어입니다.
    
    [시각화 및 가독성 극대화 규칙]
    1. 사진(이미지) 삽입은 절대 금지합니다.
    2. 글의 가독성을 높이기 위해 본문 중간에 반드시 아래의 시각화 기법을 적극 활용하세요.
       - Mermaid 다이어그램: 공정 순서, 화학 반응 메커니즘 등을 `mermaid` 코드 블록으로 그리세요. (예: graph TD; A-->B;)
       - 마크다운 표(Table): 소재 특성 비교, 장단점 등을 표로 깔끔하게 정리하세요.
       - 인용구(Blockquote): 핵심 요약이나 인사이트는 `>` 를 활용해 눈에 띄게 강조하세요.
    3. 수식은 LaTeX(백슬래시)를 절대 쓰지 말고, HTML 태그(<sub>, <sup>, &rarr;, &Delta;)만 사용하세요. (예: SiH<sub>4</sub> &rarr; Si + 2H<sub>2</sub>)
    4. 글은 학부생과 주니어 엔지니어가 딥다이브할 수 있도록 아주 길고 상세하게(최소 3000자 이상) 작성하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요. (JSON 포맷 절대 금지)
    
    Title: [포스팅 제목]
    Content:
    [서론, 본론(다이어그램/표 포함), 결론으로 구성된 마크다운 본문]

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.5
    )
    
    full_text = response.choices[0].message.content
    
    try:
        title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except AttributeError:
        title = f"{datetime.datetime.now().strftime('%Y년 %m월 %d일')} 반도체 공정 기술 동향"
        content = full_text
        
    return title, content

def save_to_markdown(title, content):
    print("[3/3] 마크다운 파일 생성 중...")
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    if len(filename) > 100:
        filename = f"_posts/{date_str}-daily-process-news.md"
    
    header_image = random.choice(HEADER_IMAGES)
    
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 공정, 기술분석]
tags: [화학공학, 8대공정, 공정엔지니어, 반도체뉴스]
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 파일 생성 완료: {filename}")

def main():
    print("=== 뉴스 브리핑 스크립트 시작 ===")
    articles = collect_news()
    if not articles: return
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("=== 자동화 완료 ===")

if __name__ == "__main__":
    main()
