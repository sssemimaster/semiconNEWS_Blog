import os
import datetime
import json
import feedparser
import requests
from openai import OpenAI

RSS_FEEDS = {
    '구글뉴스(반도체)': 'https://news.google.com/rss/search?q=반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(삼성전자)': 'https://news.google.com/rss/search?q=삼성전자+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(SK하이닉스)': 'https://news.google.com/rss/search?q=SK하이닉스+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(TSMC)': 'https://news.google.com/rss/search?q=TSMC+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(엔비디아)': 'https://news.google.com/rss/search?q=엔비디아+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def collect_news():
    articles = []
    print("[1/4] 구글 뉴스 RSS 피드 수집 중...")
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:5]:
                title = getattr(entry, 'title', '제목 없음')
                link = getattr(entry, 'link', '')
                articles.append(f"[{source}] {title} ({link})")
        except Exception as e:
            print(f"[{source}] 수집 건너뜀: {e}")
    return articles

def generate_blog_content(articles):
    print("[2/4] OpenAI (gpt-4o-mini)로 블로그 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
    client = OpenAI(api_key=api_key)
    
    raw_text = "\n".join(articles[:25])
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # 💡 [여기 수정] 기존 system_prompt 변수의 문자열 부분을 아래 가이드로 교체합니다.
    system_prompt = """
    당신은 반도체 산업 전문 블로거입니다. 
    오늘 수집된 뉴스를 바탕으로 독자가 읽기 편한 롱폼 마크다운 아티클을 작성하세요.

    [가독성 극대화 가이드]
    1. 적절한 위치에 리액트 방식 이모지(⚡, 📊, 🔍, 💡, 🚀)를 적극적으로 활용하세요.
    2. 중요한 숫자, 기업명, 공정명은 **굵은 글씨** 처리하세요.
    3. 주요 요약 섹션에는 인용구 blockquote(`>`)를 사용하세요.
    4. 섹션과 섹션 사이에는 구분선(`---`)을 넣어 단락을 깔끔하게 분리하세요.
    5. 마지막 관련 기업 정리 섹션은 마크다운 표(`|---|`)를 이용해 깔끔하게 정돈하세요.
    """

    user_prompt = f"""
    반드시 JSON 형식으로만 응답하세요. 
    키는 "title" (검색 유입이 잘 되도록 날짜 {today_str} 포함)과 "content" (완벽한 마크다운) 두 개입니다.

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']
import random

# 반도체/테크 관련 Unsplash 고화질 키워드 이미지 URL 리스트
TECH_IMAGES = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80", # Microchip
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80", # Tech/Cyber
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80", # Matrix/Code
    "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?auto=format&fit=crop&w=1200&q=80", # Hardware
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&q=80"  # Laptop/Tech
]

def save_to_markdown(title, content):
    print("[3/4] 마크다운 파일 및 대표 이미지 생성 중...")
    now = datetime.datetime.now()
    
    date_str = now.strftime("%Y-%m-%d")
    import re
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    
    if len(filename) > 100:
        filename = f"_posts/{date_str}-daily-semicon-news.md"
    
    # 대표 이미지 무작위 선택
    header_image = random.choice(TECH_IMAGES)
    
    front_matter = f"""---
layout: post
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체, 일일브리핑]
tags: [반도체, HBM, 파운드리, AI반도체, 주식]
image: "{header_image}"
---

![반도체 헤더 이미지]({header_image})

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 대표 이미지가 포함된 파일 생성 완료: {filename}")

def main():
    print("=== GitHub Pages 블로그 자동화 시작 ===")
    articles = collect_news()
    if not articles:
        print("수집된 뉴스가 없습니다.")
        return
        
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("[4/4] 로컬 파일 쓰기 완료. GitHub Actions가 커밋을 진행합니다.")

if __name__ == "__main__":
    main()
