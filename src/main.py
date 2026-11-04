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

TECH_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&h=675&q=80", 
    "https://images.unsplash.com/photo-1581092335397-9583eb92d232?auto=format&fit=crop&w=1200&h=675&q=80", 
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&h=675&q=80"
]

def collect_news():
    articles = []
    print("[1/4] 반도체 공정 중심 RSS 수집 중...")
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
            pass
    return articles

def generate_blog_content(articles):
    print("[2/4] OpenAI 분석 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 누락")
        
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles[:30])
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    system_prompt = """
    당신은 화학공학 전공 반도체 엔지니어입니다. 제공된 뉴스를 바탕으로 화학공학 지식이 포함된 롱폼 아티클을 작성하세요.

    [화학 반응식 절대 규칙 - 위반 시 시스템 붕괴]
    1. LaTeX 기호(`$$`, `\text`, `\rightarrow`)를 **절대 사용하지 마세요.**
    2. 무조건 **HTML 태그**를 사용하여 화학식을 작성하세요.
       - 아래첨자: `<sub>` (예: `SiH<sub>4</sub>`)
       - 위첨자: `<sup>` (예: `O<sup>2-</sup>`)
       - 화살표: `&rarr;` (예: `SiH<sub>4</sub> &rarr; Si + 2H<sub>2</sub>`)
    3. 본문에 이미지를 임의로 삽입하지 마세요. (시스템이 자동으로 삽입합니다)
    """

    user_prompt = f"""
    반드시 JSON으로 응답하세요. (키: "title", "content")

    [구조]
    - 서론: 오늘의 이슈 개요
    - 본론 1~4: 화공학적 딥다이브 (반드시 위 규칙에 맞춘 HTML 화학 반응식 포함)
    - 본론 5: 용어 정리 (표)
    - 결론: 인사이트

    기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5,
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']

def inject_images_deterministically(content, image_list):
    """파이썬이 직접 본문의 H2(##) 아래에 이미지를 꽂아넣어 에러를 0%로 만듭니다."""
    # 만약 AI가 프롬프트를 무시하고 이미지를 넣었다면 모두 삭제
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    
    lines = content.split('\n')
    new_lines = []
    inserted_count = 0
    
    for line in lines:
        new_lines.append(line)
        # H2 헤더를 만날 때마다 그 아래에 이미지 삽입 (최대 2번)
        if line.startswith('## ') and inserted_count < 2:
            img = random.choice(image_list)
            new_lines.append(f"\n![공정 참고 자료]({img})\n")
            inserted_count += 1
            
    return '\n'.join(new_lines)

def save_to_markdown(title, content):
    print("[3/4] 이미지 주입 및 마크다운 파일 생성 중...")
    
    # 이미지 100% 안전 주입
    content = inject_images_deterministically(content, TECH_IMAGES)
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    if len(filename) > 100:
        filename = f"_posts/{date_str}-daily-process-news.md"
    
    header_image = random.choice(TECH_IMAGES)
    
    # 썸네일 잘림(Crop) 방지 CSS 기본 주입
    css_injection = """
<style>
  .post-content img, .preview-img img, .post-header img {
    object-fit: contain !important;
    background-color: transparent !important;
  }
</style>
"""

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
{css_injection}
"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 파일 생성 완료: {filename}")

def main():
    print("=== 화공학도의 반도체 공정 블로그 시작 ===")
    articles = collect_news()
    if not articles:
        return
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("[4/4] 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
