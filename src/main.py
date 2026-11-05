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
FALLBACK_IMAGES = ["https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80"]

def get_dynamic_image(keyword):
    """💡 AI가 지정한 맞춤형 키워드로 관련성 100%의 썸네일을 1장만 가져옵니다."""
    api_key = os.environ.get("UNSPLASH_API_KEY")
    if not api_key or not keyword:
        return random.choice(FALLBACK_IMAGES)
    try:
        url = f"https://api.unsplash.com/photos/random?query={keyword}&client_id={api_key}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return data['urls']['raw'] + "&w=1200&h=675&fit=crop&q=80"
    except:
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
    print("[2/3] 이슈 동향 및 기술 분석 롱폼 리포트 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles)
    
    system_prompt = """
    당신은 반도체 산업 트렌드를 꿰뚫고 있는 화학공학 전공 시니어 공정 엔지니어입니다.
    
    [가이드 및 포맷]
    1. 사진(이미지) 삽입은 난잡해지므로 절대 금지합니다.
    2. 글의 내용이 비어보이지 않도록 텍스트 분량을 아주 길게(최소 3,500자 이상) 작성하세요.
    3. 사진 대신 아래 시각화 기법으로 전문성을 높이세요:
       - 핵심 기술 원리나 공정 순서는 반드시 `mermaid` 다이어그램으로 그리세요.
       - 기술 스펙이나 장단점 비교는 반드시 마크다운 표(Table)를 사용하세요.
    4. 수식은 LaTeX(백슬래시) 금지, HTML 태그(<sub>, <sup>, &rarr;)만 사용하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요.
    
    Title: [일일브리핑] (제목)
    Image_Keyword: (Unsplash 검색용 영어 단어 1~2개, 예: semiconductor, cleanroom, microchip)
    Content:
    [서론 요약, 본론(다이어그램/표 포함), 결론으로 구성된 아주 상세한 본문]

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
        keyword = re.search(r'Image_Keyword:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except:
        title = f"[일일브리핑] {datetime.datetime.now().strftime('%m월 %d일')} 반도체 동향"
        keyword = "semiconductor"
        content = full_text
        
    return title, keyword, content

def save_to_markdown(title, keyword, content):
    print(f"[3/3] 맞춤형 썸네일({keyword}) 검색 및 파일 저장 중...")
    
    content = content.replace('\\', '\\\\')
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    
    # 💡 AI가 지정한 키워드로 썸네일 검색
    header_image = get_dynamic_image(keyword)
    
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
    print(f"✅ 리포트 생성 완료")

def main():
    print("=== 뉴스 브리핑 시작 ===")
    articles = collect_news()
    if articles:
        title, keyword, content = generate_blog_content(articles)
        save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
