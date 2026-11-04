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
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"
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
            print(f"[{source}] 수집 건너뜀: {e}")
    return articles

def generate_blog_content(articles):
    print("[2/4] OpenAI 분석 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 누락되었습니다.")
        
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles[:30])
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # AI가 헷갈리지 않게 아예 완성된 마크다운 코드를 제공
    image_md_list = [f"- ![참고 자료]({img})" for img in TECH_IMAGES]
    image_pool_str = "\n".join(image_md_list)
    
    system_prompt = """
    당신은 화학공학 전공 4년차 학부생이자 예비 반도체 엔지니어입니다.
    제공된 뉴스를 바탕으로 화학공학 지식(반응식, 열역학)이 포함된 롱폼(최소 2500자) 마크다운 아티클을 작성하세요.

    [작성 가이드]
    1. 화학 반응식이나 수식을 작성할 때는 무조건 `$$` 기호로 감싸세요. (예: `$$ \mathrm{SiH}_4 \to \mathrm{Si} + 2\mathrm{H}_2 $$`)
    """

    user_prompt = f"""
    반드시 JSON 형식으로 응답하세요. 키는 "title"과 "content" 입니다.

    [이미지 자동 삽입 가이드]
    본문 H2 섹션 아래 2~3곳에 아래 제공된 마크다운 코드를 1글자도 바꾸지 말고 그대로 복사해서 삽입하세요. (절대 URL 앞뒤에 따옴표를 넣지 마세요!)
    
    사용 가능한 마크다운 이미지 코드:
    {image_pool_str}

    [마크다운 콘텐츠 필수 구조]
    - 서론: 오늘의 주요 공정/소재 이슈 개요
    - 본론 1~4: 기사에 언급된 공정에 대한 화공학적 딥다이브 분석 및 화학 반응식 포함
    - 본론 5: 핵심 화학 물질 및 장비 용어 정리 (표)
    - 결론: 예비 엔지니어로서의 인사이트

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
    print("[3/4] 텍스트 교정 및 마크다운 파일 생성 중...")
    
    # 💡 1. 괄호 수식을 블로그 호환형 $$ 수식으로 강제 변경
    content = content.replace('\\[', '$$').replace('\\]', '$$')
    content = content.replace('\[', '$$').replace('\]', '$$')
    
    # 💡 2. Kramdown 파서가 백슬래시를 먹어치우는 현상(ext 에러) 원천 차단
    # 자주 쓰이는 기호들의 백슬래시를 강제로 2개로 늘림
    latex_commands = ['text', 'mathrm', 'rightarrow', 'to', 'leftarrow', 'uparrow', 'downarrow', 'Delta', 'mu', 'alpha', 'beta', 'gamma']
    for cmd in latex_commands:
        content = content.replace(f'\\{cmd}', f'\\\\{cmd}')
        
    # 💡 3. \text 폰트 깨짐 방지를 위해 \mathrm으로 일괄 변경
    content = content.replace(r'\\text', r'\\mathrm')
    
    # 💡 4. AI가 괄호 안에 따옴표를 넣은 엑스박스 이미지 강제 교정
    content = content.replace('("https://images', '(https://images').replace('80")', '80)')

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    if len(filename) > 100:
        filename = f"_posts/{date_str}-daily-process-news.md"
    
    header_image = random.choice(TECH_IMAGES)
    
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
    
    print(f"✅ 교정 완료 및 파일 생성: {filename}")

def main():
    print("=== 화공학도의 반도체 공정 블로그 시작 ===")
    articles = collect_news()
    if not articles:
        print("수집된 뉴스가 없습니다.")
        return
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("[4/4] 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
