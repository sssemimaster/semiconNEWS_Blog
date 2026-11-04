import os
import datetime
import json
import re
import random
import feedparser
import requests
from openai import OpenAI

# 1. 수집할 구글 뉴스 RSS 목록 (공정, 소재, 장비 중심으로 전면 개편)
RSS_FEEDS = {
    '공정기술/수율': 'https://news.google.com/rss/search?q=반도체+공정+OR+수율+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '반도체소재/화학': 'https://news.google.com/rss/search?q=반도체+소재+OR+포토레지스트+OR+특스가스+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    'EUV/노광/식각': 'https://news.google.com/rss/search?q=EUV+OR+노광+OR+식각+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '첨단패키징/HBM': 'https://news.google.com/rss/search?q=반도체+패키징+OR+HBM+OR+TSV+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '증착/세정/검사': 'https://news.google.com/rss/search?q=반도체+증착+OR+세정+OR+장비+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 2. 반도체 웨이퍼, 팹(Fab), 화학 공정 느낌의 고화질 이미지
TECH_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&q=80", # 랩/연구실 느낌
    "https://images.unsplash.com/photo-1581092335397-9583eb92d232?auto=format&fit=crop&w=1200&q=80", # 엔지니어/소재
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&q=80"
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
    print("[2/4] OpenAI로 화공학도 관점의 공정 분석 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles[:30])
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # 💡 프롬프트 전면 수정: 화공학도 페르소나 및 8대 공정 기술 중심
    system_prompt = """
    당신은 화학공학을 전공하며 반도체 공정 엔지니어를 꿈꾸는 열정적인 대학생 블로거입니다. 
    단순한 주식 시황이나 실적 발표 뉴스는 철저히 배제하고, 화학공학(반응, 열역학, 유체, 재료공학) 및 반도체 8대 공정(노광, 식각, 증착, 패키징 등)의 관점에서 최신 기술 이슈를 분석하는 롱폼 마크다운 아티클을 작성하세요.

    [작성 가이드]
    1. 각 본론 섹션(H2 `##`)은 특정 공정 기술이나 신소재 이슈를 다뤄야 합니다. 기술적 원리, 현재의 한계점, 극복 방안을 화공학도의 시선에서 최소 3~4문단으로 아주 상세하게 풀어서 설명하세요.
    2. 중요한 화학 물질명, 공정 장비명, 물리/화학적 수치는 반드시 **굵은 글씨** 처리하세요.
    3. 적절한 위치에 이모지(🧪, 🔬, ⚙️, ⚡, 칩)를 활용하여 딱딱한 기술 글의 가독성을 높이세요.
    4. 내용이 길어지더라도 끝까지 끊기지 않고 완전한 형태의 JSON으로 출력하세요.
    """

    user_prompt = f"""
    반드시 JSON 형식으로만 응답하세요. 
    키는 "title" (검색 유입이 잘 되도록 날짜 {today_str} 및 구체적인 공정/소재 키워드 포함)과 "content" (완벽한 마크다운) 두 개입니다.

    [마크다운 콘텐츠 필수 구조]
    - 서론: 오늘 주목할 만한 반도체 공정/소재 분야의 흐름 요약 (blockquote `>` 활용, 학부생의 호기심 어린 톤 앤 매너)
    - 본론 1~4: 기사에 언급된 핵심 공정(예: EUV 노광에서의 레지스트 반응, 식각 가스의 화학적 특성, TSV 패키징의 열 관리 등)에 대한 딥다이브 분석. 원문 링크를 문맥에 맞게 연결할 것.
    - 본론 5 (오늘의 공정 단어장): 언급된 **주요 반도체 공정 용어 및 화학 물질 정리** (마크다운 표 `|---|` 사용)
    - 결론: 화공학도의 시선 - 향후 반도체 미세화 및 수율 확보를 위해 공정 엔지니어가 나아가야 할 방향과 인사이트

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5, # 기술적 추론과 블로거다운 문장력을 위해 온도값 약간 상승
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
    
    # 💡 카테고리와 태그를 공정 엔지니어링 맞춤형으로 변경
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 공정, 기술분석]
tags: [화학공학, 8대공정, 반도체소재, 수율, 공정엔지니어]
image:
  path: {header_image}
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 파일 생성 완료: {filename}")

def main():
    print("=== 화공학도의 반도체 공정 자동화 블로그 시작 ===")
    articles = collect_news()
    if not articles:
        print("수집된 뉴스가 없습니다.")
        return
        
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("[4/4] 로컬 파일 쓰기 완료. GitHub Actions가 커밋을 진행합니다.")

if __name__ == "__main__":
    main()
