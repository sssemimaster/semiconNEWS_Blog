import os
import datetime
import json
import re
import random
import feedparser
import requests
from openai import OpenAI

RSS_FEEDS = {
    '공정기술/수율': 'https://news.google.com/rss/search?q=반도체+공정+OR+수율+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '반도체소재/화학': 'https://news.google.com/rss/search?q=반도체+소재+OR+포토레지스트+OR+특스가스+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    'EUV/노광/식각': 'https://news.google.com/rss/search?q=EUV+OR+노광+OR+식각+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '첨단패키징/HBM': 'https://news.google.com/rss/search?q=반도체+패키징+OR+HBM+OR+TSV+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '증착/세정/검사': 'https://news.google.com/rss/search?q=반도체+증착+OR+세정+OR+장비+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 16:9 비율로 고정된 반도체/연구실 썸네일 및 본문용 이미지 풀
TECH_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&h=675&q=80", 
    "https://images.unsplash.com/photo-1581092335397-9583eb92d232?auto=format&fit=crop&w=1200&h=675&q=80", 
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"
]

def collect_news():
    articles = []
    print("[1/4] 반도체 공정 및 소재 중심 RSS 피드 수집 중...")
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:6]: 
                title = getattr(entry, 'title', '제목 없음')
                link = getattr(entry, 'link', '')
                articles.append(f"[{source}] {title} ({link})")
        except Exception as e:
            print(f"[{source}] 수집 건너뜀: {e}")
    return articles

def generate_blog_content(articles):
    print("[2/4] OpenAI로 심층 화공학 분석 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles[:30])
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    image_pool_str = "\n".join(TECH_IMAGES)
    
    system_prompt = """
    당신은 화학공학을 전공한 4년차 학부생이자 예비 반도체 공정 엔지니어입니다.
    제공된 뉴스 기사를 바탕으로 아주 디테일하고 학술적인 롱폼(Long-form, 최소 2500자 이상) 분석 마크다운 아티클을 작성하세요.

    [작성 및 심화 가이드]
    1. 겉핥기식 요약이 아닌, 화학공학 전공 지식(화학 반응식, 열역학, 유체 역학, 재료 공학적 특성 등)을 동원하여 기사 속 기술의 원리와 한계점을 깊이 있게 분석하세요.
    2. 각 섹션은 최소 4~5문단으로 길고 상세하게 작성하세요.
    3. 적절한 위치에 이모지(🧪, 🔬, ⚙️, ⚡)를 활용하고 핵심 용어는 **굵은 글씨** 처리하세요.
    4. 내용이 길어지더라도 완전한 형태의 JSON으로 출력하세요.
    """

    user_prompt = f"""
    반드시 JSON 형식으로만 응답하세요. 키는 "title"과 "content" 입니다.

    [이미지 자동 삽입 가이드]
    본문 내용이 전환되는 핵심 섹션(H2) 아래나, 시각적 환기가 필요한 곳에 아래 이미지 URL 중 2~3개를 골라 마크다운 형식으로 삽입하세요.
    삽입 예시: `![EUV 노광 공정과 화학 반응]({TECH_IMAGES[0]})`
    사용 가능 이미지 목록:
    {image_pool_str}

    [마크다운 콘텐츠 필수 구조]
    - 서론: 오늘의 주요 공정/소재 이슈 개요 (학부생의 시선)
    - 본론 1~4: 기사에 언급된 공정(식각 가스, 레지스트 반응, 증착 메커니즘 등)에 대한 화공학적 딥다이브 분석.
    - 본론 5: 오늘의 핵심 화학 물질 및 장비 용어 정리 (마크다운 표 사용)
    - 결론: 예비 엔지니어로서의 인사이트와 향후 수율 극복 과제

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6,
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']

def save_to_markdown(title, content):
    print("[3/4] 마크다운 파일 생성 중...")
    now = datetime.datetime.now()
    
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    
    if len(filename) > 100:
        filename = f"_posts/{date_str}-daily-process-news.md"
    
    header_image = random.choice(TECH_IMAGES)
    
    # 💡 image path에 큰따옴표 추가하여 엑스박스 에러 해결
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 공정, 기술분석]
tags: [화학공학, 8대공정, 반도체소재, 수율, 공정엔지니어]
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 엑스박스 에러 해결된 파일 생성 완료: {filename}")

def main():
    print("=== 화공학도의 반도체 공정 자동화 블로그 시작 ===")
    articles = collect_news()
    if not articles:
        print("수집된 뉴스가 없습니다.")
        return
        
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("[4/4] 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
