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

TECH_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&h=675&q=80"
]

def collect_news():
    articles = []
    print("[1/4] 뉴스 수집 중...")
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
    print("[2/4] 순수 텍스트 기반 롱폼 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 누락")
        
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles[:20])
    
    # 💡 JSON 에러를 피하기 위해 순수 텍스트 포맷으로 지시
    system_prompt = """
    당신은 화학공학 전공 반도체 엔지니어입니다. 화학 반응식과 공정 원리가 포함된 아주 전문적이고 상세한 롱폼 아티클(최소 2500자)을 작성하세요.
    수식은 반드시 $$ 기호로 감싸고, \mathrm{} 과 \to 를 사용하세요. (예: $$ \mathrm{SiH}_4 \to \mathrm{Si} + 2\mathrm{H}_2 $$)
    절대 본문에 이미지를 임의로 삽입하지 마세요.
    """

    user_prompt = f"""
    반드시 아래의 양식으로만 출력하세요. (JSON 포맷 절대 금지)
    
    Title: [포스팅 제목]
    Content:
    [서론, 본론(H2 활용), 용어정리, 결론으로 구성된 마크다운 본문]

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.5
    )
    
    full_text = response.choices[0].message.content
    
    # 순수 텍스트에서 제목과 본문 분리 추출
    try:
        title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except AttributeError:
        title = f"{datetime.datetime.now().strftime('%Y년 %m월 %d일')} 반도체 공정 주요 동향"
        content = full_text
        
    return title, content

def inject_html_images(content, image_list):
    """💡 마크다운 이미지 오류를 피하기 위해 완벽한 HTML 태그로 이미지를 주입"""
    lines = content.split('\n')
    new_lines = []
    img_count = 0
    for line in lines:
        new_lines.append(line)
        # H2(##) 태그 아래에 HTML 이미지 삽입
        if line.startswith('## ') and img_count < 2:
            img = random.choice(image_list)
            html_img = f'\n<img src="{img}" alt="반도체 공정 이미지" style="width:100%; border-radius:12px; margin: 20px 0;">\n'
            new_lines.append(html_img)
            img_count += 1
    return '\n'.join(new_lines)

def save_to_markdown(title, content):
    print("[3/4] 수식 보호 및 HTML 이미지 주입 중...")
    
    # 💡 깃허브 블로그가 수식 기호(\)를 지워버리는 것을 막기 위해 모든 백슬래시를 두 배로 늘림
    content = content.replace('\\', '\\\\')
    
    # 이미지 안전 주입
    content = inject_html_images(content, TECH_IMAGES)
    
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
tags: [화학공학, 8대공정, 공정엔지니어]
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 에러 없는 최종 파일 생성 완료: {filename}")

def main():
    print("=== 뉴스 브리핑 스크립트 시작 ===")
    articles = collect_news()
    if not articles: return
    title, content = generate_blog_content(articles)
    save_to_markdown(title, content)
    print("[4/4] 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
