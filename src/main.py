import os
import datetime
import json
import re
import random
import feedparser
import requests
from openai import OpenAI

# 1. 수집할 구글 뉴스 RSS 목록
RSS_FEEDS = {
    '구글뉴스(반도체)': 'https://news.google.com/rss/search?q=반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(삼성전자)': 'https://news.google.com/rss/search?q=삼성전자+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(SK하이닉스)': 'https://news.google.com/rss/search?q=SK하이닉스+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(TSMC)': 'https://news.google.com/rss/search?q=TSMC+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '구글뉴스(엔비디아)': 'https://news.google.com/rss/search?q=엔비디아+반도체+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 2. 고화질 기술/반도체 썸네일 이미지 목록 (무작위 삽입용)
TECH_IMAGES = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80", # 마이크로칩
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80", # 테크/사이버
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80", # 매트릭스/코드
    "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?auto=format&fit=crop&w=1200&q=80", # 하드웨어/메인보드
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&q=80", # 랩탑/테크
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&q=80"  # 프로세서
]

def collect_news():
    articles = []
    print("[1/4] 구글 뉴스 RSS 피드 수집 중...")
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:6]: # 각 섹션당 기사 수집량 6개로 증가
                title = getattr(entry, 'title', '제목 없음')
                link = getattr(entry, 'link', '')
                articles.append(f"[{source}] {title} ({link})")
        except Exception as e:
            print(f"[{source}] 수집 건너뜀: {e}")
    return articles

def generate_blog_content(articles):
    print("[2/4] OpenAI (gpt-4o-mini)로 상세 블로그 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
    client = OpenAI(api_key=api_key)
    
    # 넉넉하게 30개의 기사를 프롬프트에 제공
    raw_text = "\n".join(articles[:30])
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # 💡 프롬프트를 강화하여 내용을 훨씬 길고 전문적으로 작성하도록 지시
    system_prompt = """
    당신은 반도체 산업 전문 애널리스트이자 베스트셀러 IT 블로거입니다. 
    제공된 뉴스 기사들을 깊이 있게 분석하여, 구글 검색(SEO)에 최적화된 매우 상세한 롱폼(Long-form) 마크다운 아티클을 작성하세요.

    [가독성 및 분량 극대화 가이드]
    1. 각 본론 섹션(H2 `##`)마다 최소 3~4개의 문단으로 나누어 아주 상세하게 풀어서 설명하세요. 짧게 요약하지 말고 배경지식까지 덧붙여서 길게 작성해야 합니다.
    2. 독자가 읽기 편하도록 적절한 위치에 이모지(⚡, 📊, 🔍, 💡, 🚀)를 적극적으로 활용하세요.
    3. 중요한 숫자(매출, 주가, 점유율 등), 기업명, 핵심 반도체 공정명은 반드시 **굵은 글씨** 처리하세요.
    4. 주요 요약 섹션에는 인용구 blockquote(`>`)를 사용하세요.
    5. 내용이 길어지더라도 끝까지 끊기지 않고 완전한 형태의 JSON으로 출력하세요.
    """

    user_prompt = f"""
    반드시 JSON 형식으로만 응답하세요. 
    키는 "title" (검색 유입이 잘 되도록 날짜 {today_str} 및 매력적인 키워드 포함)과 "content" (완벽한 마크다운) 두 개입니다.

    [마크다운 콘텐츠 필수 구조]
    - 서론: 오늘 반도체 시장 흐름 및 증시 요약 (최소 5문장 이상 길게)
    - 본론 1~4: 주요 섹터별(메모리, 파운드리, 소부장, AI 반도체 등) 상세 분석. 각 섹터별로 현재 상황, 원인, 전망을 깊이 있게 다룰 것. 관련 기사 원문 링크도 문맥에 맞게 연결하세요.
    - 본론 5 (핵심 요약): 언급된 **관련 기업 및 필수 반도체 용어 정리** (마크다운 표 `|---|` 사용)
    - 결론: 오늘의 산업적 시사점 및 개인 투자자를 위한 투자 인사이트 (아주 구체적으로 작성)

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4, # 조금 더 창의적이고 풍부한 어휘를 쓰도록 0.4로 세팅
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']

def save_to_markdown(title, content):
    print("[3/4] Chirpy 테마 규격 마크다운 파일 생성 중...")
    now = datetime.datetime.now()
    
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    
    if len(filename) > 100:
        filename = f"_posts/{date_str}-daily-semicon-news.md"
    
    # 💡 썸네일 이미지 무작위 뽑기
    header_image = random.choice(TECH_IMAGES)
    
    # 💡 Chirpy 테마 전용 Front Matter (이미지 경로 포함)
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체, 일일브리핑]
tags: [반도체, HBM, 파운드리, AI반도체, 테크]
image:
  path: {header_image}
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ Chirpy 테마 + 썸네일 이미지 파일 생성 완료: {filename}")

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
