import os
import datetime
import re
import random
import feedparser
import requests
from openai import OpenAI

RSS_FEEDS = {
    '반도체이슈': 'https://news.google.com/rss/search?q=반도체+동향+OR+투자+OR+수율+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '공정/소재': 'https://news.google.com/rss/search?q=반도체+공정+OR+소재+OR+EUV+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# API 실패 시 블로그가 멈추지 않도록 비상용 이미지 탑재
FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&h=675&q=80"
]

def get_dynamic_image():
    """💡 Unsplash API를 통해 반도체/화공학 관련 고화질 이미지를 실시간으로 뽑아옵니다."""
    api_key = os.environ.get("UNSPLASH_API_KEY")
    if not api_key:
        return random.choice(FALLBACK_IMAGES)
    
    queries = ["semiconductor", "microchip", "silicon wafer", "chemistry lab", "cleanroom", "electronic circuit"]
    query = random.choice(queries)
    
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&client_id={api_key}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        # 블로그 썸네일에 완벽한 16:9 비율 파라미터 강제 주입
        return data['urls']['raw'] + "&w=1200&h=675&fit=crop&q=80"
    except Exception as e:
        print(f"이미지 API 호출 실패 (비상용 이미지 대체): {e}")
        return random.choice(FALLBACK_IMAGES)

def collect_news():
    articles = []
    print("[1/3] 최신 반도체 이슈 수집 중...")
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:8]: 
                articles.append(f"[{source}] {getattr(entry, 'title', '')}")
        except:
            pass
    return articles

def generate_blog_content(articles):
    print("[2/3] 이슈 동향 및 기술 분석 리포트 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles)
    
    system_prompt = """
    당신은 반도체 산업 트렌드를 꿰뚫고 있는 화학공학 전공 공정 엔지니어입니다.
    오늘의 뉴스 기사를 분석하여, '시장 이슈 동향'과 '엔지니어 시선의 기술적 분석'이 결합된 전문 리포트를 작성하세요.

    [가이드 및 포맷]
    1. 사진 삽입 금지, 수식은 반드시 HTML(<sub>, <sup>, &rarr;)만 사용 (LaTeX 금지).
    2. 블로그 홈에서 잘 보이도록 글의 서두에 인용구(`>`)로 핵심을 3줄 요약하세요.
    3. 본문 구조는 다음을 따르세요:
       - ## 📰 오늘의 반도체 핫이슈
       - ## 🔬 엔지니어의 시선: 기술 분석 (이슈에 얽힌 원리를 Mermaid 다이어그램으로 시각화)
       - ## 💡 시장 전망 및 시사점
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요. (JSON 금지)
    
    Title: [일일브리핑] (제목)
    Content:
    [본문]

    수집된 기사:
    {raw_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.6
    )
    
    full_text = response.choices[0].message.content
    try:
        title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except:
        title = f"[일일브리핑] {datetime.datetime.now().strftime('%m월 %d일')} 반도체 동향"
        content = full_text
        
    return title, content

def inject_html_images(content):
    lines = content.split('\n')
    new_lines = []
    img_count = 0
    for line in lines:
        new_lines.append(line)
        if line.startswith('## ') and img_count < 2:
            img = get_dynamic_image()
            html_img = f'\n<img src="{img}" alt="반도체 공정 자료" style="width:100%; border-radius:12px; margin: 20px 0;">\n'
            new_lines.append(html_img)
            img_count += 1
    return '\n'.join(new_lines)

def save_to_markdown(title, content):
    print("[3/3] 동적 이미지 주입 및 파일 저장 중...")
    
    content = content.replace('\\', '\\\\')
    content = inject_html_images(content)
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    
    # 썸네일도 실시간 검색 이미지 적용
    header_image = get_dynamic_image()
    
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 브리핑, 트렌드 동향]
tags: [반도체이슈, 공정기술, 시장전망]
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    print(f"✅ 뉴스 파일 생성 완료")

def main():
    print("=== 뉴스 브리핑 시작 ===")
    articles = collect_news()
    if articles:
        title, content = generate_blog_content(articles)
        save_to_markdown(title, content)

if __name__ == "__main__":
    main()
